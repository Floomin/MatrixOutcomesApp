import bcrypt
import streamlit as st
from database.connection import execute_query

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login_user(username, password):
    query = """
        SELECT UserID, FullName, Role, PasswordHash, RequirePasswordChange 
        FROM tbl_Users 
        WHERE Username = ? AND IsActive = 1
    """
    user_data = execute_query(query, (username,))
    
    if user_data:
        user = user_data[0]
        if check_password(password, user['PasswordHash']):
            # Сохраняем данные в сессию
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = user['UserID']
            st.session_state['user_name'] = user['FullName']
            st.session_state['user_role'] = user['Role']
            st.session_state['must_change_password'] = bool(user['RequirePasswordChange'])
            return True
    return False

def update_password(user_id, new_password):
    """Смена пароля самим пользователем."""
    new_hash = hash_password(new_password)
    query = "UPDATE tbl_Users SET PasswordHash = ?, RequirePasswordChange = 0 WHERE UserID = ?"
    return execute_query(query, (new_hash, user_id), fetch=False)