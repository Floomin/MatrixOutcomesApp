import streamlit as st
from core.auth import login_user, update_password

# Настройка страницы (должна быть первой командой Streamlit)
st.set_page_config(page_title="Матриця виходів", page_icon="📋", layout="centered")

# Инициализация базовых переменных сессии
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'must_change_password' not in st.session_state:
    st.session_state['must_change_password'] = False

def logout():
    """Очистка сессии при выходе."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]

# === ЭКРАН 1: АВТОРИЗАЦИЯ ===
if not st.session_state['logged_in']:
    st.title("🔐 Вход в систему")
    st.markdown("Добро пожаловать в приложение **«Матриця виходів»**.")
    
    with st.form("login_form"):
        username = st.text_input("Логин (напр. bashchenko_n)")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Увійти")
        
        if submit:
            if username and password:
                if login_user(username, password):
                    st.rerun() # Перезагружаем интерфейс после успешного входа
                else:
                    st.error("Неверный логин или пароль, либо доступ закрыт.")
            else:
                st.warning("Пожалуйста, введите логин и пароль.")

# === ЭКРАН 2: ПРИНУДИТЕЛЬНАЯ СМЕНА ПАРОЛЯ ===
elif st.session_state['must_change_password']:
    st.title("🛡️ Смена пароля")
    st.warning("Вы используете временный пароль. В целях безопасности придумайте новый.")
    
    with st.form("change_pass_form"):
        new_pass = st.text_input("Новый пароль", type="password")
        new_pass_confirm = st.text_input("Подтвердите пароль", type="password")
        submit_pass = st.form_submit_button("Зберегти пароль")
        
        if submit_pass:
            if len(new_pass) < 6:
                st.error("Пароль должен содержать минимум 6 символов.")
            elif new_pass != new_pass_confirm:
                st.error("Пароли не совпадают.")
            else:
                update_password(st.session_state['user_id'], new_pass)
                st.session_state['must_change_password'] = False
                st.success("Пароль успешно изменен!")
                st.rerun()

# === ЭКРАН 3: ГЛАВНАЯ СТРАНИЦА (ДОСТУП ОТКРЫТ) ===
else:
    # Настройка боковой панели
    st.sidebar.title("Меню користувача")
    st.sidebar.markdown(f"👤 **ПІБ:** {st.session_state.get('user_name', '')}")
    st.sidebar.markdown(f"🏷️ **Роль:** {st.session_state.get('user_role', '')}")
    st.sidebar.button("Вийти", on_click=logout, use_container_width=True)
    
    # Приветствие в основной зоне
    st.title(f"Вітаємо, {st.session_state.get('user_name', '').split(' ')[0]}! 👋")
    st.info("👈 Виберіть потрібний розділ у боковому меню ліворуч.")
    
    # Небольшой дашборд для красоты (позже можно заменить на реальную статистику)
    st.write("---")
    st.write("### Коротке зведення (Демо)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Договорів у роботі", "124")
    col2.metric("Оброблено", "38")
    col3.metric("Резерв", "12")