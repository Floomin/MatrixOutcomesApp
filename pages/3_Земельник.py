import streamlit as st
import pandas as pd
from database.connection import execute_query
from navigation import show_nav

# Викликаємо нашу навігацію
show_nav()

# === 1. ЗАХИСТ СТОРІНКИ ТА ПРАВА ===
if not st.session_state.get('logged_in') or st.session_state.get('user_role') not in ['Landman', 'Admin']:
    st.error("🚫 Доступ заборонено. Ця сторінка тільки для фахівців Земельної служби.")
    st.stop()

subrole = st.session_state.get('user_subrole') # Type1, Type2 або Type3

# === 2. ОТРИМАННЯ ДАНИХ ===
@st.cache_data(ttl=60)
def get_landman_contracts(user_id):
    query = """
        SELECT 
            m.*, 
            r.ResultID, r.Outcome AS ManagerOutcome, r.ProcessingStatus AS ManagerStatus,
            r.ExitOrder, r.CompetitorName, r.ContactType, r.ContactInfo, r.Comment AS ManagerComment, r.IsConflict, r.UpdatedAt AS ManagerUpdatedAt,
            d.DecisionID, d.BoundarySettingDate, d.TerminationDate1C, d.OfficerID
        FROM tbl_MainRegistry m
        INNER JOIN tbl_User_Villages uv ON m.Village = uv.VillageName AND uv.UserID = ?
        LEFT JOIN tbl_Manager_Results r ON m.AgreementUID = r.AgreementUID
        LEFT JOIN tbl_LandOfficer_Decisions d ON m.AgreementUID = d.AgreementUID
    """
    data = execute_query(query, (user_id,))
    return pd.DataFrame(data) if data else pd.DataFrame()

def reset_filters():
    if st.session_state.get('search_query_input'):
        for key in ['filter_year', 'filter_month', 'filter_village', 'filter_field', 'filter_crop']:
            if key in st.session_state: st.session_state[key] = "Всі"

def clear_process_session():
    keys_to_clear = ['process_contract_uid', 'process_contract_num', 'process_owner', 'process_data']
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]

# Відмальовка ДЕТАЛЬНОЇ картки договору
def render_detailed_card(row, uid, contract_num, owner, tab_type=None):
    st.markdown(f"#### 📄 Договір: :green[{contract_num}]")
    
    # --- Блок 1: Дані реєстру 1С ---
    st.markdown("##### 🏛️ Дані реєстру 1С")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**Кадастровий:** :green[{row.get('CadastralNumber', '')}]")
        st.markdown(f"**Село:** {row.get('Village', '')} | **Поле:** {row.get('FieldNumber', '')}")
        st.markdown(f"**Площа:** {row.get('Area', 0)} га | **Пай:** {row.get('ShareCount', '')}")
    with c2:
        st.markdown(f"**Статус ділянки:** {row.get('PlotStatus', '')} | **Вид:** {row.get('ContractType', '')}")
        st.markdown(f"**Культури:** '25: {row.get('Crop2025', '')} | '26: {row.get('Crop2026', '')}")
        expiry = row.get('ExpiryDate')
        expiry_str = expiry[:10] if isinstance(expiry, str) else expiry.strftime('%d.%m.%Y') if pd.notnull(expiry) else ""
        st.markdown(f"**Закінчення:** ⏳ {expiry_str}")
        
    # --- Блок 2: Дані від Менеджера ---
    if pd.notna(row.get('ManagerOutcome')):
        st.markdown("##### 💼 Дані від Менеджера")
        c3, c4 = st.columns(2)
        with c3:
            outcome_color = "green" if row['ManagerOutcome'] == "Залишається" else "red" if row['ManagerOutcome'] == "Вилучається" else "orange"
            st.markdown(f"**Результат:** :{outcome_color}[{row['ManagerOutcome']}]")
            if pd.notna(row.get('ExitOrder')) and row['ExitOrder']: st.markdown(f"**Порядок виходу:** {row['ExitOrder']}")
            if pd.notna(row.get('CompetitorName')) and row['CompetitorName']: st.markdown(f"**Конкурент:** :red[{row['CompetitorName']}]")
        with c4:
            contact = f"{row.get('ContactType', '')} ({row.get('ContactInfo', '')})" if pd.notna(row.get('ContactType')) else "Не вказано"
            st.markdown(f"**Контакт:** {contact}")
            if pd.notna(row.get('ManagerComment')) and row['ManagerComment']: st.info(f"**Коментар:** {row['ManagerComment']}")
            if row.get('IsConflict') == 1: st.error("⚠️ **Увага! Конфліктний пайовик!**")
                
    # --- Блок 3: Кнопки Дій ---
    if tab_type in ['out', 'res'] and subrole in ['Type1', 'Type2', 'Admin']:
        if st.button("📝 Опрацювати рішення", key=f"btn_process_{uid}"):
            st.session_state.update({
                'process_contract_uid': uid,
                'process_contract_num': contract_num,
                'process_owner': owner,
                'process_data': row # Зберігаємо дані для передзаповнення форми
            })
            st.rerun()

    st.markdown("---")

# Форма Земельника
def render_landman_form():
    st.subheader("📝 Оформлення рішення Земельної служби")
    row = st.session_state['process_data']
    st.markdown(f"Пайовик: **:green[{st.session_state['process_owner']}]** | Договір: **:green[{st.session_state['process_contract_num']}]**")
    
    # Безпечне отримання площі
    try:
        area_val = float(row.get('Area', 0.0))
    except:
        area_val = 0.0

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            rem_cad = st.text_input("Вилучені кадастрові номери *", value=str(row.get('CadastralNumber', '')))
            rem_vil = st.text_input("Село вилучення", value=str(row.get('Village', '')))
            rem_fld = st.text_input("Поле вилучення", value=str(row.get('FieldNumber', '')))
        with col2:
            rem_share = st.text_input("Номер паю", value=str(row.get('ShareCount', '')))
            rem_area = st.number_input("Вилучена площа (га) *", value=area_val, step=0.01)
            
            # Підтягуємо конкурента від менеджера, якщо він є
            comp_name = row.get('CompetitorName', '')
            c_party = st.text_input("Контрагент (Конкурент)", value=str(comp_name) if pd.notna(comp_name) else "")
            
        comment = st.text_area("Коментар Земельної служби")
        
        c_btn1, c_btn2 = st.columns(2)
        if c_btn1.button("💾 Зберегти рішення", type="primary", use_container_width=True):
            if not rem_cad or rem_area <= 0:
                st.error("Будь ласка, заповніть обов'язкові поля (Кадастровий номер та Площу > 0).")
                return
                
            query = """
                INSERT INTO tbl_LandOfficer_Decisions 
                (AgreementUID, OfficerID, RemovedCadastralNumbers, RemovedVillage, RemovedField, 
                 RemovedShareNumber, RemovedArea, Counterparty, Comment, DecisionDate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
            """
            try:
                execute_query(query, (
                    st.session_state['process_contract_uid'],
                    st.session_state['user_id'],
                    rem_cad, rem_vil, rem_fld, rem_share, rem_area, c_party, comment
                ), fetch=False)
                
                st.success("✅ Рішення успішно збережено!")
                clear_process_session()
                get_landman_contracts.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Помилка при збереженні: {e}")
                
        if c_btn2.button("❌ Скасувати", use_container_width=True):
            clear_process_session()
            st.rerun()

# === 3. ГОЛОВНИЙ ЦИКЛ ===
st.title("🌍 Робоче місце: Земельна служба")

if 'process_contract_uid' in st.session_state:
    render_landman_form()
else:
    df_all = get_landman_contracts(st.session_state['user_id'])

    if df_all.empty:
        st.success("У вас немає доступних договорів для обробки.")
        st.stop()

    df_all['ExpiryDate'] = pd.to_datetime(df_all['ExpiryDate'])
    df_all['Рік'] = df_all['ExpiryDate'].dt.year.astype(str)
    df_all['Місяць'] = df_all['ExpiryDate'].dt.month.astype(str).str.zfill(2)

    # Розподіл даних
    df_new = df_all[df_all['ResultID'].isna()]
    df_stay = df_all[(df_all['ResultID'].notna()) & (df_all['ManagerOutcome'] == 'Залишається')]
    df_out = df_all[(df_all['ResultID'].notna()) & (df_all['ManagerOutcome'] == 'Вилучається') & (df_all['DecisionID'].isna())]
    df_res = df_all[(df_all['ResultID'].notna()) & (df_all['ManagerOutcome'] == 'Резервується') & (df_all['DecisionID'].isna())]
    df_done = df_all[df_all['DecisionID'].notna()]

    # Шапка та фільтри
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Менеджер думає", len(df_new))
    col_m2.metric("✅ Залишаються", len(df_stay))
    col_m3.metric("❌ До вилучення", len(df_out))
    col_m4.metric("⏸️ До резерву", len(df_res))
    col_m5.metric("🏁 Вже в роботі (ЗС)", len(df_done))

    search_q = st.text_input("🔍 Швидкий пошук (ПІБ або Кадастровий)", key="search_query_input", on_change=reset_filters).lower()

    st.write("### Фільтри")
    cols = st.columns(3)
    y_val = cols[0].selectbox("Рік", ["Всі"] + sorted(df_all['Рік'].unique().tolist()), key="filter_year")
    m_val = cols[1].selectbox("Місяць", ["Всі"] + sorted(df_all['Місяць'].unique().tolist()), key="filter_month")
    v_val = cols[2].selectbox("Село", ["Всі"] + sorted(df_all['Village'].dropna().unique().tolist()), key="filter_village")

    cols2 = st.columns(2)
    f_val = cols2[0].selectbox("Поле", ["Всі"] + sorted(df_all['FieldNumber'].dropna().unique().tolist()), key="filter_field")
    c_val = cols2[1].selectbox("Культура '26", ["Всі"] + sorted(df_all['Crop2026'].dropna().unique().tolist()), key="filter_crop")

    def apply_filters(df):
        if df.empty: return df
        f_df = df.copy()
        if search_q:
            f_df = f_df[f_df['CounterpartyName'].str.lower().str.contains(search_q, na=False) | f_df['CadastralNumber'].str.contains(search_q, na=False)]
        else:
            if y_val != "Всі": f_df = f_df[f_df['Рік'] == y_val]
            if m_val != "Всі": f_df = f_df[f_df['Місяць'] == m_val]
            if v_val != "Всі": f_df = f_df[f_df['Village'] == v_val]
            if f_val != "Всі": f_df = f_df[f_df['FieldNumber'] == f_val]
            if c_val != "Всі": f_df = f_df[f_df['Crop2026'] == c_val]
        return f_df

    f_new = apply_filters(df_new)
    f_stay = apply_filters(df_stay)
    f_out = apply_filters(df_out)
    f_res = apply_filters(df_res)
    f_done = apply_filters(df_done)

    st.divider()

    # Вкладки
    tabs = st.tabs([
        f"⏳ Необроблені Менеджером ({len(f_new)})", 
        f"✅ Залишаються ({len(f_stay)})", 
        f"❌ Виходять ({len(f_out)})", 
        f"⏸️ Резерв ({len(f_res)})", 
        f"🏁 Результат ЗС ({len(f_done)})"
    ])

    with tabs[0]:
        st.info("Ці договори ще знаходяться в роботі у менеджерів. Ви можете лише переглядати їх.")
        if not f_new.empty:
            for owner, group in f_new.groupby('CounterpartyName'):
                with st.expander(f"👤 {owner} ({len(group)})"):
                    for _, row in group.iterrows(): render_detailed_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, 'new')

    with tabs[1]:
        st.success("Ці договори менеджери змогли втримати. Ваша дія не потрібна.")
        if not f_stay.empty:
            for owner, group in f_stay.groupby('CounterpartyName'):
                with st.expander(f"👤 {owner} ({len(group)})"):
                    for _, row in group.iterrows(): render_detailed_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, 'stay')

    with tabs[2]:
        st.error("Увага! Менеджери подали ці договори на вилучення. Потрібна ваша обробка.")
        if not f_out.empty:
            for owner, group in f_out.groupby('CounterpartyName'):
                with st.expander(f"👤 {owner} ({len(group)})"):
                    for _, row in group.iterrows(): render_detailed_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, 'out')

    with tabs[3]:
        st.warning("Договори в резерві. Потребують подальшого оформлення.")
        if not f_res.empty:
            for owner, group in f_res.groupby('CounterpartyName'):
                with st.expander(f"👤 {owner} ({len(group)})"):
                    for _, row in group.iterrows(): render_detailed_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, 'res')

    with tabs[4]:
        st.info("Реєстр договорів, які вже взяті в роботу Земельною службою (внесені площі/кадастри на вилучення).")
        if not f_done.empty:
            for owner, group in f_done.groupby('CounterpartyName'):
                with st.expander(f"👤 {owner} ({len(group)})"):
                    for _, row in group.iterrows(): render_detailed_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, 'done')