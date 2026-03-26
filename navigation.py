import streamlit as st

def show_nav():
    # Приховуємо стандартне меню Streamlit за допомогою CSS
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("### 🧭 Навігація")
        
        # Головна сторінка доступна всім (там форма логіну або профіль)
        st.page_link("app.py", label="Головна", icon="🏠")
        
        # Якщо користувач авторизований, малюємо меню залежно від ролі
        if st.session_state.get('logged_in'):
            role = st.session_state.get('user_role')
            
            if role in ['Manager', 'Admin']:
                st.page_link("pages/1_Менеджер.py", label="Робоче місце", icon="💼")
                
            if role in ['Brigadier', 'Admin']:
                st.page_link("pages/2_Бригадир.py", label="Дашборд Бригадира", icon="📊")
                
            if role == 'Admin':
                st.page_link("pages/0_Адміністрування.py", label="Адміністрування", icon="⚙️")
                
            st.markdown("---")
            if st.button("🚪 Вийти з системи", use_container_width=True):
                st.session_state.clear()
                st.rerun()