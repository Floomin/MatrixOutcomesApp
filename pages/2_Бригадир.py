import streamlit as st
from navigation import show_nav
show_nav()
import pandas as pd
import io
from database.connection import execute_query

# === 1. ЗАХИСТ СТОРІНКИ ===
if not st.session_state.get('logged_in') or st.session_state.get('user_role') not in ['Brigadier', 'Admin']:
    st.error("🚫 Доступ заборонено. Ця сторінка тільки для Бригадирів та Адміністраторів.")
    st.stop()

# === 2. ОТРИМАННЯ ТА ОБРОБКА ДАНИХ ===
@st.cache_data(ttl=60)
def get_brigade_data(user_id, role):
    if role == 'Admin':
        brigade_name = "Всі бригади (Адмін-режим)"
        query_brigade = "Тестова бригада" 
    else:
        q_name = "SELECT BrigadeName FROM tbl_Users WHERE UserID = ?"
        res = execute_query(q_name, (user_id,))
        brigade_name = res[0]['BrigadeName'] if res else "Невідома бригада"
        query_brigade = brigade_name

    query_contracts = """
        SELECT 
            m.AgreementUID, m.ContractNumber, m.CounterpartyName, m.Village, 
            m.CadastralNumber, m.Area,
            u.FullName AS ManagerName,
            r.ResultID, r.Outcome, r.ProcessingStatus, r.UpdatedAt,
            r.IsConflict, r.ExitOrder, r.CompetitorName
        FROM tbl_MainRegistry m
        INNER JOIN tbl_User_Villages uv ON m.Village = uv.VillageName
        INNER JOIN tbl_Users u ON uv.UserID = u.UserID
        LEFT JOIN tbl_Manager_Results r ON m.AgreementUID = r.AgreementUID AND r.ManagerID = u.UserID
        WHERE u.BrigadeName = ? AND u.Role = 'Manager'
    """
    data = execute_query(query_contracts, (query_brigade,))
    return brigade_name, pd.DataFrame(data) if data else pd.DataFrame()

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Реєстр')
    return output.getvalue()

# === 3. ІНТЕРФЕЙС ===
brigade_name, df_all = get_brigade_data(st.session_state['user_id'], st.session_state['user_role'])

st.title(f"📊 Дашборд: :blue[{brigade_name}]")

if df_all.empty:
    st.warning("У вашій бригаді поки що немає закріплених договорів або менеджерів.")
    st.stop()

df_new = df_all[df_all['ResultID'].isna()]
df_done = df_all[df_all['ResultID'].notna()].copy()

if not df_done.empty:
    df_done['DateOnly'] = pd.to_datetime(df_done['UpdatedAt']).dt.date

# === РОЗБИВКА НА ВКЛАДКИ ===
tab_main, tab_dynamics, tab_details = st.tabs(["📊 Загальна статистика", "📈 Динаміка обробки", "🔍 Деталізація"])

# --- ВКЛАДКА 1: ЗАГАЛЬНА СТАТИСТИКА ---
with tab_main:
    total_contracts = len(df_all)
    done_contracts = len(df_done)
    new_contracts = len(df_new)
    progress_pct = int((done_contracts / total_contracts) * 100) if total_contracts > 0 else 0
    
    stayed_contracts = len(df_done[df_done['Outcome'] == 'Залишається'])
    retention_rate = int((stayed_contracts / done_contracts) * 100) if done_contracts > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("📋 Всього", total_contracts)
    col2.metric("✅ Оброблено", done_contracts)
    col3.metric("⏳ Залишилось", new_contracts)
    col4.metric("🎯 Виконання", f"{progress_pct}%")
    col5.metric("🤝 Утримання", f"{retention_rate}%", help="Відсоток тих, хто погодився залишитись.")

    st.progress(progress_pct / 100)
    st.markdown("---")

    # Блок: Розподіл результатів (на всю ширину)
    st.subheader("Розподіл результатів")
    if not df_done.empty:
        status_counts = df_done['Outcome'].value_counts()
        st.bar_chart(status_counts, color="#1f77b4")
        
        competitors = df_done[df_done['CompetitorName'].notna() & (df_done['CompetitorName'] != '')]
        if not competitors.empty:
            st.write("**Топ конкурентів:**")
            comp_counts = competitors['CompetitorName'].value_counts()
            st.dataframe(comp_counts, column_config={"count": "Втрачені договори"})
    else:
        st.info("Немає даних для графіків.")

    st.markdown("---")

    # Блок: Рейтинг Менеджерів (на всю ширину)
    st.subheader("👥 Рейтинг Менеджерів")
    leaderboard = df_all.groupby('ManagerName').agg(
        Всього=('AgreementUID', 'count'), Оброблено=('ResultID', 'count')
    ).reset_index()
    leaderboard['Залишилось'] = leaderboard['Всього'] - leaderboard['Оброблено']
    leaderboard['Прогрес (%)'] = (leaderboard['Оброблено'] / leaderboard['Всього'] * 100).fillna(0).astype(int)
    
    st.dataframe(
        leaderboard, hide_index=True, use_container_width=True,
        column_config={"Прогрес (%)": st.column_config.ProgressColumn("Прогрес", format="%d%%", min_value=0, max_value=100)}
    )

# --- ВКЛАДКА 2: ДИНАМІКА ОБРОБКИ ---
with tab_dynamics:
    st.subheader("Активність у часі")
    if not df_done.empty:
        st.write("**1. Загальна кількість оброблених договорів по днях**")
        timeline_overall = df_done['DateOnly'].value_counts().sort_index()
        st.line_chart(timeline_overall, color="#2ca02c")
        
        col_dyn1, col_dyn2 = st.columns(2)
        with col_dyn1:
            st.write("**2. Динаміка по менеджерах**")
            timeline_managers = pd.crosstab(df_done['DateOnly'], df_done['ManagerName'])
            st.line_chart(timeline_managers)
        with col_dyn2:
            st.write("**3. Динаміка за статусами**")
            timeline_status = pd.crosstab(df_done['DateOnly'], df_done['Outcome'])
            st.line_chart(timeline_status)
    else:
        st.info("Немає оброблених договорів.")

# --- ВКЛАДКА 3: ДЕТАЛІЗАЦІЯ (З EXCEL) ---
with tab_details:
    st.subheader("Реєстри договорів")
    
    if not df_done.empty:
        conflicts = df_done[df_done['IsConflict'] == 1]
        if not conflicts.empty:
            st.error(f"⚠️ **Увага! Виявлено конфліктних пайовиків ({len(conflicts)} шт.):**")
            st.dataframe(conflicts[['ManagerName', 'CounterpartyName', 'Village', 'Outcome']], hide_index=True, use_container_width=True)
            st.markdown("---")

    type_filter = st.radio("Оберіть реєстр для перегляду:", ["В роботі (Необроблені)", "Оброблені"], horizontal=True)
    
    if type_filter == "В роботі (Необроблені)":
        if not df_new.empty:
            display_new = df_new[['ManagerName', 'CounterpartyName', 'ContractNumber', 'Village', 'CadastralNumber', 'Area']].copy()
            display_new.columns = ['Менеджер', 'Пайовик', 'Договір', 'Село', 'Кадастровий', 'Площа']
            st.dataframe(display_new, hide_index=True, use_container_width=True)
            
            excel_data = to_excel(display_new)
            st.download_button(
                label="📥 Завантажити в Excel",
                data=excel_data,
                file_name=f"Необроблені_договори_{brigade_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.success("Всі договори оброблено!")
            
    else:
        if not df_done.empty:
            display_done = df_done[['ManagerName', 'CounterpartyName', 'ContractNumber', 'Outcome', 'Village', 'CompetitorName', 'UpdatedAt']].copy()
            display_done.columns = ['Менеджер', 'Пайовик', 'Договір', 'Результат', 'Село', 'Конкурент', 'Дата обробки']
            display_done['Дата обробки'] = pd.to_datetime(display_done['Дата обробки']).dt.strftime('%d.%m.%Y %H:%M')
            st.dataframe(display_done, hide_index=True, use_container_width=True)
            
            excel_data = to_excel(display_done)
            st.download_button(
                label="📥 Завантажити в Excel",
                data=excel_data,
                file_name=f"Оброблені_договори_{brigade_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("Немає оброблених договорів.")