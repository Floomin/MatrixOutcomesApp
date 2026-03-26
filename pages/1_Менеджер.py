import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import execute_query

# === 1. ЗАХИСТ СТОРІНКИ ===
if not st.session_state.get('logged_in') or st.session_state.get('user_role') not in ['Manager', 'Admin']:
    st.error("🚫 Доступ заборонено. Будь ласка, авторизуйтесь як Менеджер.")
    st.stop()

# === 2. ФУНКЦІЇ ДЛЯ ОТРИМАННЯ ДАНИХ ===
@st.cache_data(ttl=60)
def get_unprocessed_contracts(user_id):
    query = """
        SELECT m.*
        FROM tbl_MainRegistry m
        INNER JOIN tbl_User_Villages v ON m.Village = v.VillageName AND v.UserID = ?
        LEFT JOIN tbl_Manager_Results r ON m.AgreementUID = r.AgreementUID 
             AND (r.ProcessingStatus = 'Submitted' OR r.ProcessingStatus = 'Reserve')
        WHERE r.ResultID IS NULL
    """
    data = execute_query(query, (user_id,))
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_processed_contracts(user_id):
    query = """
        SELECT m.CounterpartyName, m.CadastralNumber, r.Outcome, r.ProcessingStatus, r.UpdatedAt
        FROM tbl_Manager_Results r
        INNER JOIN tbl_MainRegistry m ON r.AgreementUID = m.AgreementUID
        WHERE r.ManagerID = ?
    """
    data = execute_query(query, (user_id,))
    return pd.DataFrame(data) if data else pd.DataFrame()

def reset_filters_on_search():
    if st.session_state.get('search_query_input'):
        st.session_state['filter_year'] = "Всі"
        st.session_state['filter_month'] = "Всі"
        st.session_state['filter_village'] = "Всі"

# === 3. ГОЛОВНИЙ ІНТЕРФЕЙС ===
st.title("💼 Робоче місце менеджера")

user_id = st.session_state['user_id']
df_new = get_unprocessed_contracts(user_id)

# Якщо в сесії НЕМАЄ вибраного договору, показуємо списки і фільтри
if 'process_contract_uid' not in st.session_state:
    
    tab_new, tab_done = st.tabs(["🆕 Необроблені договори", "✅ Оброблені договори"])

    with tab_new:
        if df_new.empty:
            st.success("🎉 Усі договори оброблено! Завдань немає.")
        else:
            df_new['ExpiryDate'] = pd.to_datetime(df_new['ExpiryDate'])
            df_new['Рік'] = df_new['ExpiryDate'].dt.year.astype(str)
            df_new['Місяць'] = df_new['ExpiryDate'].dt.month.astype(str).str.zfill(2)

            current_year = str(datetime.now().year)
            current_month = str(datetime.now().month).zfill(2)

            years = ["Всі"] + sorted(df_new['Рік'].unique().tolist())
            months = ["Всі"] + sorted(df_new['Місяць'].unique().tolist())
            villages = ["Всі"] + sorted(df_new['Village'].unique().tolist())

            if 'filter_year' not in st.session_state:
                st.session_state['filter_year'] = current_year if current_year in years else "Всі"
            if 'filter_month' not in st.session_state:
                st.session_state['filter_month'] = current_month if current_month in months else "Всі"
            if 'filter_village' not in st.session_state:
                st.session_state['filter_village'] = "Всі"

            col_metric, col_search = st.columns([1, 3])
            with col_metric:
                st.metric("Всього необроблених", len(df_new))
            with col_search:
                search_query = st.text_input("🔍 Швидкий пошук", key="search_query_input", on_change=reset_filters_on_search)

            st.write("### Фільтри")
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_year = st.selectbox("Рік закінчення", years, key="filter_year")
            with col2:
                selected_month = st.selectbox("Місяць закінчення", months, key="filter_month")
            with col3:
                selected_village = st.selectbox("Село", villages, key="filter_village")

            filtered_df = df_new.copy()
            if search_query:
                search_query = search_query.lower()
                filtered_df = filtered_df[
                    filtered_df['CounterpartyName'].str.lower().str.contains(search_query, na=False) |
                    filtered_df['CadastralNumber'].str.contains(search_query, na=False)
                ]
                st.info("⚠️ Активний пошук: фільтри тимчасово вимкнено.")
            else:
                if selected_year != "Всі":
                    filtered_df = filtered_df[filtered_df['Рік'] == selected_year]
                if selected_month != "Всі":
                    filtered_df = filtered_df[filtered_df['Місяць'] == selected_month]
                if selected_village != "Всі":
                    filtered_df = filtered_df[filtered_df['Village'] == selected_village]

            st.divider()

            if filtered_df.empty:
                st.warning("За обраними критеріями нічого не знайдено.")
            else:
                grouped = filtered_df.groupby('CounterpartyName')
                for owner, group in grouped:
                    with st.expander(f"👤 {owner} (Договорів: {len(group)})"):
                        
                        for index, row in group.iterrows():
                            uid = row['AgreementUID']
                            contract_num = row.get('ContractNumber', 'Б/Н')
                            
                            st.markdown(f"#### 📄 Договір: :green[{contract_num}]")
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Кадастровий номер:** :green[{row.get('CadastralNumber', '')}]")
                                st.markdown(f"**Площа:** :green[{row.get('Area', 0)} га]")
                                st.markdown(f"**Село:** :green[{row.get('Village', '')}]")
                                
                                expiry = row.get('ExpiryDate')
                                if pd.notnull(expiry):
                                    expiry_str = expiry[:10] if isinstance(expiry, str) else expiry.strftime('%d.%m.%Y')
                                    st.markdown(f"**Закінчення оренди:** ⏳ :green[{expiry_str}]")
                            
                            with col_b:
                                st.markdown(f"**Поле:** :green[{row.get('FieldNumber', '')}]")
                                st.markdown(f"**Культура '25:** :green[{row.get('Crop2025', '')}]")
                                st.markdown(f"**Культура '26:** :green[{row.get('Crop2026', '')}]")
                                st.markdown(f"**Статус:** :green[{row.get('Condition', '')}] / :green[{row.get('PlotStatus', '')}]")
                            
                            with st.expander("Деталі"):
                                st.markdown(f"**Вид договору:** :green[{row.get('ContractType', '')}]")
                                st.markdown(f"**Вид ділянки:** :green[{row.get('LandPlotType', '')}]")
                                st.markdown(f"**Пай:** :green[{row.get('ShareCount', '')}]")
                                
                            # Кнопка тепер індивідуальна для КОЖНОГО договору
                            if st.button(f"✍️ Опрацювати договір {contract_num}", key=f"btn_{uid}"):
                                st.session_state['process_contract_uid'] = uid
                                st.session_state['process_contract_num'] = contract_num
                                st.session_state['process_owner'] = owner
                                st.rerun()
                                
                            st.markdown("---")

    with tab_done:
        df_done = get_processed_contracts(user_id)
        if df_done.empty:
            st.info("Ви ще не обробили жодного договору.")
        else:
            st.dataframe(df_done, hide_index=True, use_container_width=True)

# === 4. ФОРМА ОБРОБКИ (Відображається замість списків) ===
else:
    st.subheader("📝 Внесення результатів")
    st.markdown(f"Пайовик: **:green[{st.session_state['process_owner']}]**")
    st.markdown(f"Договір №: **:green[{st.session_state['process_contract_num']}]**")
    
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            outcome = st.selectbox("Результат переговорів *", ["", "Залишається", "Вилучається", "Резервується"])
            
            exit_order = ""
            competitor = ""
            if outcome == "Вилучається":
                exit_order = st.selectbox("Порядок виходу", ["Одноосібно на своєму місці", "Одноосібно обмін", "Конкурент"])
                if exit_order == "Конкурент":
                    competitor = st.text_input("Назва конкурента")
            
            is_conflict = st.checkbox("⚠️ Конфліктний пайовик")
            
        with col2:
            contact_type = st.selectbox("Тип контакту", ["Дзвінок", "Зустріч", "Месенджер", "Не вдалося зв'язатися"])
            contact_info = st.text_input("Контактні дані", placeholder="+380...")
            comment = st.text_area("Коментар", placeholder="Деталі розмови...")
        
        st.markdown("---")
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            if st.button("💾 Зберегти результати", type="primary", use_container_width=True):
                if not outcome:
                    st.error("Будь ласка, оберіть 'Результат переговорів'.")
                else:
                    manager_id = st.session_state['user_id']
                    processing_status = "Reserve" if outcome == "Резервується" else "Submitted"
                    uid = st.session_state['process_contract_uid']
                    
                    query = """
                        INSERT INTO tbl_Manager_Results 
                        (AgreementUID, ManagerID, Outcome, ExitOrder, CompetitorName, 
                         ContactType, ContactInfo, Comment, IsConflict, ProcessingStatus, IsLocked)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """
                    
                    try:
                        execute_query(query, (
                            uid, manager_id, outcome, exit_order, competitor,
                            contact_type, contact_info, comment, 
                            1 if is_conflict else 0, processing_status
                        ), fetch=False)
                        
                        st.success(f"✅ Успішно збережено!")
                        # Очищаємо сесію, щоб форма закрилась і повернувся список
                        del st.session_state['process_contract_uid']
                        del st.session_state['process_contract_num']
                        del st.session_state['process_owner']
                        get_unprocessed_contracts.clear() # Очищаємо кеш, щоб договір зник зі списку
                        st.rerun()
                    except Exception as e:
                        st.error(f"Помилка при збереженні: {e}")
                    
        with col_btn2:
            if st.button("❌ Скасувати / Повернутись", use_container_width=True):
                del st.session_state['process_contract_uid']
                del st.session_state['process_contract_num']
                del st.session_state['process_owner']
                st.rerun()