import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import execute_query

if not st.session_state.get('logged_in') or st.session_state.get('user_role') not in ['Manager', 'Admin']:
    st.error("🚫 Доступ заборонено.")
    st.stop()

@st.cache_data(ttl=60)
def get_contracts(user_id):
    query = """
        SELECT m.*, r.ResultID, r.Outcome, r.ExitOrder, r.CompetitorName, r.ContactType, 
               r.ContactInfo, r.Comment, r.IsConflict, r.ProcessingStatus, r.UpdatedAt, r.IsLocked,
               (SELECT TOP 1 eq.Status FROM tbl_EditRequests eq WHERE eq.ResultID = r.ResultID ORDER BY eq.RequestDate DESC) AS LastRequestStatus,
               (SELECT TOP 1 eq.AdminComment FROM tbl_EditRequests eq WHERE eq.ResultID = r.ResultID ORDER BY eq.RequestDate DESC) AS AdminComment
        FROM tbl_MainRegistry m
        INNER JOIN tbl_User_Villages v ON m.Village = v.VillageName AND v.UserID = ?
        LEFT JOIN tbl_Manager_Results r ON m.AgreementUID = r.AgreementUID 
    """
    data = execute_query(query, (user_id,))
    return pd.DataFrame(data) if data else pd.DataFrame()

def reset_filters():
    if st.session_state.get('search_query_input'):
        for key in ['filter_year', 'filter_month', 'filter_village', 'filter_field', 'filter_crop']:
            if key in st.session_state: st.session_state[key] = "Всі"

def clear_process_session():
    keys_to_clear = ['process_contract_uid', 'process_contract_num', 'process_owner', 'edit_mode', 'edit_result_id', 'edit_data']
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]

def request_edit(result_id, reason):
    q_req = "INSERT INTO tbl_EditRequests (ResultID, ManagerID, RequestReason) VALUES (?, ?, ?)"
    execute_query(q_req, (result_id, st.session_state['user_id'], reason), fetch=False)
    q_res = "UPDATE tbl_Manager_Results SET ProcessingStatus = 'EditRequest' WHERE ResultID = ?"
    execute_query(q_res, (result_id,), fetch=False)
    st.toast("✅ Запит на редагування відправлено!")
    get_contracts.clear()

def render_contract_card(row, uid, contract_num, owner, tab_type):
    st.markdown(f"#### 📄 Договір: :green[{contract_num}]")
    
    if tab_type != "new":
        outcome_color = "green" if row['Outcome'] == "Залишається" else "red" if row['Outcome'] == "Вилучається" else "orange"
        st.markdown(f"**Результат:** :{outcome_color}[{row['Outcome']}]")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Кадастровий:** :green[{row.get('CadastralNumber', '')}] | **Площа:** :green[{row.get('Area', 0)} га]")
        st.markdown(f"**Село:** :green[{row.get('Village', '')}]")
        expiry = row.get('ExpiryDate')
        expiry_str = expiry[:10] if isinstance(expiry, str) else expiry.strftime('%d.%m.%Y') if pd.notnull(expiry) else ""
        st.markdown(f"**Закінчення:** ⏳ :green[{expiry_str}]")
        
    with col_b:
        st.markdown(f"**Поле:** :green[{row.get('FieldNumber', '')}] | **Статус:** :green[{row.get('PlotStatus', '')}]")
        st.markdown(f"**Культури:** '25: :green[{row.get('Crop2025', '')}] | '26: :green[{row.get('Crop2026', '')}]")
        
    with st.expander("Деталі"):
        st.markdown(f"**Вид:** :green[{row.get('ContractType', '')}] | **Пай:** :green[{row.get('ShareCount', '')}]")
        
    if tab_type == "new":
        if st.button(f"✍️ Опрацювати", key=f"btn_{uid}"):
            st.session_state.update({'process_contract_uid': uid, 'process_contract_num': contract_num, 'process_owner': owner, 'edit_mode': False})
            st.rerun()
            
    elif tab_type == "done":
        status = row['ProcessingStatus']
        if status == 'EditRequest':
            st.warning("⏳ Очікує дозволу на редагування від адміністратора")
        else:
            if row.get('LastRequestStatus') == 'Rejected':
                st.error(f"❌ Запит відхилено. Причина: {row.get('AdminComment', 'Без коментарів')}")
                
            if st.button("🔓 Запросити редагування", key=f"req_{row['ResultID']}"):
                st.session_state[f'requesting_for_{row["ResultID"]}'] = True
                st.rerun()
                
            if st.session_state.get(f'requesting_for_{row["ResultID"]}'):
                reason = st.text_input("Вкажіть причину редагування (обов'язково):", key=f"reason_{row['ResultID']}")
                col1, col2 = st.columns(2)
                if col1.button("Відправити", key=f"send_req_{row['ResultID']}", type="primary"):
                    if reason:
                        request_edit(row['ResultID'], reason)
                        del st.session_state[f'requesting_for_{row["ResultID"]}']
                        st.rerun()
                    else:
                        st.error("Введіть причину!")
                if col2.button("Скасувати", key=f"cancel_req_{row['ResultID']}"):
                    del st.session_state[f'requesting_for_{row["ResultID"]}']
                    st.rerun()
                    
    elif tab_type == "edit":
        if st.button("📝 Редагувати дані", key=f"edit_btn_{uid}"):
            st.session_state.update({
                'process_contract_uid': uid, 
                'process_contract_num': contract_num, 
                'process_owner': owner, 
                'edit_mode': True, 
                'edit_result_id': row['ResultID'],
                'edit_data': row 
            })
            st.rerun()
            
    st.markdown("---")

def render_processing_form():
    is_edit = st.session_state.get('edit_mode', False)
    row_data = st.session_state.get('edit_data', {})
    
    st.subheader("📝 Редагування результатів" if is_edit else "📝 Внесення результатів")
    st.markdown(f"Пайовик: **:green[{st.session_state['process_owner']}]** | Договір: **:green[{st.session_state['process_contract_num']}]**")
    
    def get_idx(options, val): return options.index(val) if pd.notna(val) and val in options else 0
    def get_str(val): return str(val) if pd.notna(val) else ""
    def get_bool(val): return bool(val) if pd.notna(val) else False

    outcomes = ["", "Залишається", "Вилучається", "Резервується"]
    exit_orders = ["Одноосібно на своєму місці", "Одноосібно обмін", "Конкурент"]
    contact_types = ["Дзвінок", "Зустріч", "Месенджер", "Не вдалося зв'язатися"]

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            outcome = st.selectbox("Результат *", outcomes, index=get_idx(outcomes, row_data.get('Outcome')) if is_edit else 0)
            exit_order = st.selectbox("Порядок виходу", exit_orders, index=get_idx(exit_orders, row_data.get('ExitOrder')) if is_edit else 0) if outcome == "Вилучається" else ""
            competitor = st.text_input("Назва конкурента", value=get_str(row_data.get('CompetitorName'))) if exit_order == "Конкурент" else ""
            is_conflict = st.checkbox("⚠️ Конфліктний пайовик", value=get_bool(row_data.get('IsConflict')))
            
        with col2:
            contact_type = st.selectbox("Тип контакту", contact_types, index=get_idx(contact_types, row_data.get('ContactType')) if is_edit else 0)
            contact_info = st.text_input("Контакти", value=get_str(row_data.get('ContactInfo')), placeholder="+380...")
            comment = st.text_area("Коментар", value=get_str(row_data.get('Comment')))
        
        col_btn1, col_btn2 = st.columns(2)
        btn_text = "💾 Оновити результати" if is_edit else "💾 Зберегти"
        
        if col_btn1.button(btn_text, type="primary", use_container_width=True):
            if not outcome:
                st.error("Оберіть 'Результат'.")
                return
                
            status_calc = "Reserve" if outcome == "Резервується" else "Submitted"
            
            if is_edit:
                query = """UPDATE tbl_Manager_Results 
                           SET Outcome=?, ExitOrder=?, CompetitorName=?, ContactType=?, ContactInfo=?, Comment=?, IsConflict=?, ProcessingStatus=?, IsLocked=1, UpdatedAt=GETDATE()
                           WHERE ResultID=?"""
                execute_query(query, (
                    outcome, exit_order, competitor, contact_type, contact_info, comment, 1 if is_conflict else 0, status_calc, st.session_state['edit_result_id']
                ), fetch=False)
                st.success("✅ Дані успішно оновлено!")
            else:
                query = """INSERT INTO tbl_Manager_Results 
                           (AgreementUID, ManagerID, Outcome, ExitOrder, CompetitorName, ContactType, ContactInfo, Comment, IsConflict, ProcessingStatus, IsLocked)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)"""
                execute_query(query, (
                    st.session_state['process_contract_uid'], st.session_state['user_id'], outcome, exit_order, competitor,
                    contact_type, contact_info, comment, 1 if is_conflict else 0, status_calc
                ), fetch=False)
                st.success("✅ Збережено!")
                
            clear_process_session()
            get_contracts.clear()
            st.rerun()
                
        if col_btn2.button("❌ Скасувати", use_container_width=True):
            clear_process_session()
            st.rerun()

# === 4. ГОЛОВНИЙ ЦИКЛ ===
st.title("💼 Робоче місце менеджера")

if 'process_contract_uid' in st.session_state:
    render_processing_form()
else:
    df_all = get_contracts(st.session_state['user_id'])
    
    if not df_all.empty:
        df_all['ExpiryDate'] = pd.to_datetime(df_all['ExpiryDate'])
        df_all['Рік'] = df_all['ExpiryDate'].dt.year.astype(str)
        df_all['Місяць'] = df_all['ExpiryDate'].dt.month.astype(str).str.zfill(2)
        
        # Розподіл на 5 категорій
        df_new = df_all[df_all['ResultID'].isna()]
        df_edit = df_all[df_all['ResultID'].notna() & (df_all['IsLocked'] == 0)]
        
        df_done_stay = df_all[df_all['ResultID'].notna() & (df_all['IsLocked'] == 1) & (df_all['Outcome'] == 'Залишається')]
        df_done_out = df_all[df_all['ResultID'].notna() & (df_all['IsLocked'] == 1) & (df_all['Outcome'] == 'Вилучається')]
        df_done_res = df_all[df_all['ResultID'].notna() & (df_all['IsLocked'] == 1) & (df_all['Outcome'] == 'Резервується')]
    else:
        df_new, df_edit, df_done_stay, df_done_out, df_done_res = [pd.DataFrame()] * 5

    # 5 Метрик в одному ряду
    cols_m = st.columns(5)
    cols_m[0].metric("⏳ Нові", len(df_new))
    cols_m[1].metric("✅ Залишається", len(df_done_stay))
    cols_m[2].metric("❌ Вихід", len(df_done_out))
    cols_m[3].metric("⏸️ Резерв", len(df_done_res))
    cols_m[4].metric("🔓 Редагування", len(df_edit))

    # Пошук окремим рядком для зручності
    search_q = st.text_input("🔍 Швидкий пошук (ПІБ або Кадастровий)", key="search_query_input", on_change=reset_filters).lower()

    st.write("### Фільтри")
    cols = st.columns(3)
    y_val = cols[0].selectbox("Рік", ["Всі"] + sorted(df_all['Рік'].unique().tolist()) if not df_all.empty else ["Всі"], key="filter_year")
    m_val = cols[1].selectbox("Місяць", ["Всі"] + sorted(df_all['Місяць'].unique().tolist()) if not df_all.empty else ["Всі"], key="filter_month")
    v_val = cols[2].selectbox("Село", ["Всі"] + sorted(df_all['Village'].dropna().unique().tolist()) if not df_all.empty else ["Всі"], key="filter_village")

    cols2 = st.columns(2)
    f_val = cols2[0].selectbox("Поле", ["Всі"] + sorted(df_all['FieldNumber'].dropna().unique().tolist()) if not df_all.empty else ["Всі"], key="filter_field")
    c_val = cols2[1].selectbox("Культура '26", ["Всі"] + sorted(df_all['Crop2026'].dropna().unique().tolist()) if not df_all.empty else ["Всі"], key="filter_crop")

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
    f_done_stay = apply_filters(df_done_stay)
    f_done_out = apply_filters(df_done_out)
    f_done_res = apply_filters(df_done_res)
    f_edit = apply_filters(df_edit)

    st.divider()

    # 5 Вкладок
    tabs = st.tabs([
        f"🆕 Необроблені ({len(f_new)})", 
        f"✅ Залишається ({len(f_done_stay)})", 
        f"❌ Вихід ({len(f_done_out)})", 
        f"⏸️ Резерв ({len(f_done_res)})", 
        f"🔓 На редагування ({len(f_edit)})"
    ])
    
    # 1. Нові
    with tabs[0]:
        if f_new.empty: st.info("Не знайдено договорів.")
        for owner, group in f_new.groupby('CounterpartyName'):
            with st.expander(f"👤 {owner} ({len(group)})"):
                for _, row in group.iterrows(): render_contract_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, "new")

    # 2. Залишається
    with tabs[1]:
        if f_done_stay.empty: st.info("Не знайдено договорів.")
        for owner, group in f_done_stay.groupby('CounterpartyName'):
            with st.expander(f"👤 {owner} (Залишається: {len(group)})"):
                for _, row in group.iterrows(): render_contract_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, "done")

    # 3. Вихід
    with tabs[2]:
        if f_done_out.empty: st.info("Не знайдено договорів.")
        for owner, group in f_done_out.groupby('CounterpartyName'):
            with st.expander(f"👤 {owner} (Вихід: {len(group)})"):
                for _, row in group.iterrows(): render_contract_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, "done")

    # 4. Резерв
    with tabs[3]:
        if f_done_res.empty: st.info("Не знайдено договорів.")
        for owner, group in f_done_res.groupby('CounterpartyName'):
            with st.expander(f"👤 {owner} (Резерв: {len(group)})"):
                for _, row in group.iterrows(): render_contract_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, "done")
                
    # 5. Редагування
    with tabs[4]:
        if f_edit.empty: st.info("Немає договорів, доступних для редагування.")
        for owner, group in f_edit.groupby('CounterpartyName'):
            with st.expander(f"👤 {owner} (Дозволено: {len(group)})"):
                for _, row in group.iterrows(): render_contract_card(row, row['AgreementUID'], row.get('ContractNumber', 'Б/Н'), owner, "edit")