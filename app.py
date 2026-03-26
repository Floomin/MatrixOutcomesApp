import streamlit as st
import bcrypt
from database.connection import execute_query
from navigation import show_nav

# Налаштування сторінки має бути найпершим викликом Streamlit
st.set_page_config(page_title="Land Audit App", page_icon="🏢", layout="wide")

# Викликаємо нашу кастомну навігацію (вона сховає стандартне меню і намалює своє)
show_nav()

# Ініціалізація змінних сесії, якщо їх ще немає
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login():
    st.title("🔐 Вхід у систему")
    
    # Використовуємо st.form, щоб логін відбувався по натисканню Enter
    with st.form("login_form"):
        username = st.text_input("Логін")
        password = st.text_input("Пароль", type="password")
        submit = st.form_submit_button("Увійти", type="primary", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.warning("Будь ласка, введіть логін та пароль.")
                return
                
            # Оновлений запит: витягуємо також SubRole та IsActive
            query = """
                SELECT UserID, PasswordHash, Role, FullName, RequirePasswordChange, SubRole, IsActive 
                FROM tbl_Users 
                WHERE Username = ?
            """
            result = execute_query(query, (username,))
            
            if result:
                user = result[0]
                
                # Перевірка, чи не заблокований користувач адміністратором
                if not user.get('IsActive', 1):
                    st.error("Ваш обліковий запис заблоковано. Зверніться до адміністратора.")
                    return
                
                stored_hash = user['PasswordHash']
                
                # Перевірка пароля
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    # Зберігаємо всі необхідні дані в сесію
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user['UserID']
                    st.session_state['user_role'] = user['Role']
                    st.session_state['user_subrole'] = user.get('SubRole') # <--- Наша нова колонка
                    st.session_state['full_name'] = user['FullName']
                    st.session_state['require_password_change'] = user['RequirePasswordChange']
                    
                    st.success("Успішний вхід!")
                    st.rerun() # Перезавантажуємо сторінку, щоб застосувати стан
                else:
                    st.error("Невірний логін або пароль.")
            else:
                st.error("Невірний логін або пароль.")

def change_password():
    st.title("🔒 Зміна пароля")
    st.warning("Оскільки це ваш перший вхід (або ваш пароль було скинуто), ви повинні встановити новий надійний пароль.")
    
    with st.form("change_password_form"):
        new_password = st.text_input("Новий пароль", type="password")
        confirm_password = st.text_input("Підтвердіть новий пароль", type="password")
        submit = st.form_submit_button("Зберегти пароль", type="primary")
        
        if submit:
            if not new_password or not confirm_password:
                st.error("Будь ласка, заповніть всі поля.")
            elif new_password != confirm_password:
                st.error("Паролі не співпадають!")
            elif len(new_password) < 6:
                st.error("Пароль має містити мінімум 6 символів.")
            else:
                # Хешуємо новий пароль і записуємо в базу
                hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                user_id = st.session_state['user_id']
                
                query = "UPDATE tbl_Users SET PasswordHash = ?, RequirePasswordChange = 0 WHERE UserID = ?"
                execute_query(query, (hashed, user_id), fetch=False)
                
                # Знімаємо прапорець вимоги в сесії
                st.session_state['require_password_change'] = 0
                st.success("✅ Пароль успішно змінено!")
                st.rerun()

# === ОСНОВНА ЛОГІКА РОУТИНГУ ===
if not st.session_state['logged_in']:
    login()
else:
    # Якщо користувач увійшов, але має змінити пароль - не пускаємо його далі
    if st.session_state.get('require_password_change'):
        change_password()
    else:
        # Головний екран для авторизованих користувачів
        st.title(f"👋 Вітаємо, {st.session_state['full_name']}!")
        
        st.write("---")
        st.write("Ви успішно увійшли до системи **Land Audit App**.")
        
        role = st.session_state.get('user_role')
        subrole = st.session_state.get('user_subrole')
        
        # Відображаємо підказку залежно від ролі
        if role == 'Admin':
            st.info("Ви маєте права **Адміністратора**. Використовуйте бокове меню для доступу до всіх розділів системи.")
        elif role == 'Manager':
            st.info("Ваша роль: **Менеджер**. Перейдіть до розділу 'Робоче місце' у боковому меню, щоб почати обробку договорів.")
        elif role == 'Brigadier':
            st.info("Ваша роль: **Бригадир**. Перейдіть до розділу 'Дашборд Бригадира' у боковому меню для перегляду аналітики.")
        elif role == 'Landman':
            subrole_display = f" (Тип: {subrole})" if subrole else ""
            st.info(f"Ваша роль: **Фахівець земельної служби**{subrole_display}. Перейдіть до розділу 'Земельна служба' у боковому меню.")
            
        st.markdown("### 👈 Оберіть потрібний розділ у меню ліворуч для початку роботи.")