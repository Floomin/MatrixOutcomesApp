import pyodbc
import streamlit as st

def get_connection():
    """Создает подключение к MS SQL, используя секреты Streamlit."""
    try:
        # Берем данные из .streamlit/secrets.toml
        conn_str = (
            f"DRIVER={{{st.secrets['connections']['sql']['driver']}}};"
            f"SERVER={st.secrets['connections']['sql']['server']};"
            f"DATABASE={st.secrets['connections']['sql']['database']};"
            f"UID={st.secrets['connections']['sql']['username']};"
            f"PWD={st.secrets['connections']['sql']['password']};"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        st.error(f"Ошибка подключения к БД: {e}")
        return None

def execute_query(query, params=None, fetch=True):
    """Универсальная функция для выполнения запросов."""
    conn = get_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch:
            columns = [column[0] for column in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
        else:
            conn.commit()
            return True
    except Exception as e:
        st.error(f"Ошибка выполнения запроса: {e}")
        return None
    finally:
        conn.close()