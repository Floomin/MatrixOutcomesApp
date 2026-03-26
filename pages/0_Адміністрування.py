import streamlit as st
from navigation import show_nav
show_nav()
import pandas as pd
import bcrypt
from database.connection import execute_query

# === 1. ЗАХИСТ СТОРІНКИ ===
if not st.session_state.get('logged_in') or st.session_state.get('user_role') != 'Admin':
    st.error("🚫 Доступ заборонено.")
    st.stop()

# === 2. ФУНКЦІЇ БАЗИ ДАНИХ ===
def get_pending_requests():
    query = """
        SELECT eq.RequestID, eq.ResultID, m.ContractNumber, m.CounterpartyName, 
               u.FullName AS ManagerName, eq.RequestDate, eq.RequestReason, m.Village
        FROM tbl_EditRequests eq
        INNER JOIN tbl_Manager_Results r ON eq.ResultID = r.ResultID
        INNER JOIN tbl_MainRegistry m ON r.AgreementUID = m.AgreementUID
        INNER JOIN tbl_Users u ON eq.ManagerID = u.UserID
        WHERE eq.Status = 'Pending'
        ORDER BY eq.RequestDate DESC
    """
    data = execute_query(query)
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_request_history():
    query = """
        SELECT eq.RequestID, m.ContractNumber, u.FullName AS ManagerName, 
               eq.RequestReason, eq.Status, eq.AdminComment, eq.ProcessedDate
        FROM tbl_EditRequests eq
        INNER JOIN tbl_Manager_Results r ON eq.ResultID = r.ResultID
        INNER JOIN tbl_MainRegistry m ON r.AgreementUID = m.AgreementUID
        INNER JOIN tbl_Users u ON eq.ManagerID = u.UserID
        WHERE eq.Status != 'Pending'
        ORDER BY eq.ProcessedDate DESC
    """
    data = execute_query(query)
    return pd.DataFrame(data) if data else pd.DataFrame()

def get_all_users():
    query = "SELECT UserID, Username, FullName, Role, IsActive FROM tbl_Users ORDER BY FullName"
    data = execute_query(query)
    return pd.DataFrame(data) if data else pd.DataFrame()

def process_edit_request(request_id, result_id, admin_id, status, comment=None):
    # Оновлюємо статус самого запиту в реєстрі
    q_req = "UPDATE tbl_EditRequests SET Status = ?, AdminID = ?, AdminComment = ?, ProcessedDate = GETDATE() WHERE RequestID = ?"
    execute_query(q_req, (status, admin_id, comment, request_id), fetch=False)
    
    # Оновлюємо статус договору для менеджера
    is_locked = 0 if status == 'Approved' else 1
    q_res = "UPDATE tbl_Manager_Results SET IsLocked = ?, ProcessingStatus = 'Submitted' WHERE ResultID = ?"
    execute_query(q_res, (is_locked, result_id), fetch=False)
    
    st.toast(f"✅ Запит {status.lower()}!")

def reset_user_password(user_id, new_password):
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    query = "UPDATE tbl_Users SET PasswordHash = ?, RequirePasswordChange = 1 WHERE UserID = ?"
    execute_query(query, (hashed, user_id), fetch=False)

# === 3. ІНТЕРФЕЙС ===
st.title("⚙️ Панель Адміністратора")

tab_req, tab_hist, tab_users = st.tabs(["🔔 Нові запити", "🗄️ Реєстр запитів", "👥 Користувачі"])

with tab_req:
    st.subheader("Очікують рішення")
    df_req = get_pending_requests()
    
    if df_req.empty:
        st.success("🎉 Немає нових запитів на розблокування.")
    else:
        for _, row in df_req.iterrows():
            with st.container(border=True):
                st.markdown(f"**Менеджер:** :blue[{row['ManagerName']}] | **Пайовик:** {row['CounterpartyName']} | **Договір:** {row['ContractNumber']}")
                st.info(f"**Причина запиту:** {row['RequestReason']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Схвалити (Дозволити редагування)", key=f"app_{row['RequestID']}", type="primary", use_container_width=True):
                        process_edit_request(row['RequestID'], row['ResultID'], st.session_state['user_id'], 'Approved')
                        st.rerun()
                
                with col2:
                    # Кнопка відхилення відкриває поле для вводу причини
                    if st.button("❌ Відхилити", key=f"rej_btn_{row['RequestID']}", use_container_width=True):
                        st.session_state[f'rejecting_{row["RequestID"]}'] = True
                
                if st.session_state.get(f'rejecting_{row["RequestID"]}'):
                    admin_reason = st.text_input("Вкажіть причину відмови:", key=f"rej_reason_{row['RequestID']}")
                    if st.button("Підтвердити відхилення", key=f"confirm_rej_{row['RequestID']}", type="primary"):
                        if not admin_reason:
                            st.error("Причина відмови обов'язкова!")
                        else:
                            process_edit_request(row['RequestID'], row['ResultID'], st.session_state['user_id'], 'Rejected', admin_reason)
                            del st.session_state[f'rejecting_{row["RequestID"]}']
                            st.rerun()

with tab_hist:
    st.subheader("Реєстр оброблених запитів")
    df_hist = get_request_history()
    if not df_hist.empty:
        st.dataframe(df_hist, hide_index=True, use_container_width=True)
    else:
        st.info("Історія порожня.")

with tab_users:
    df_users = get_all_users()
    if not df_users.empty:
        user_options = {f"{row['FullName']} ({row['Username']}) - Роль: {row['Role']}": row['UserID'] for _, row in df_users.iterrows()}
        selected_user_label = st.selectbox("Скидання пароля користувачу:", [""] + list(user_options.keys()))
        
        if selected_user_label:
            temp_password = st.text_input("Тимчасовий пароль", value="123456")
            if st.button("🔄 Скинути пароль", type="primary"):
                reset_user_password(user_options[selected_user_label], temp_password)
                st.success(f"✅ Пароль змінено на: **{temp_password}**")
        st.write("---")
        st.dataframe(df_users, hide_index=True, use_container_width=True)