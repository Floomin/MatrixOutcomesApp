import bcrypt
from database.connection import get_connection

DEFAULT_PASSWORD = "Password2026!"

def setup_system():
    # Хэшируем пароль
    hashed_default = bcrypt.hashpw(DEFAULT_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_connection()
    if conn:
        cursor = conn.cursor()
        
        # 1. Обновляем пароли всем менеджерам и ставим флаг смены пароля
        cursor.execute("UPDATE tbl_Users SET PasswordHash = ?, RequirePasswordChange = 1", (hashed_default,))
        
        # 2. Создаем или обновляем пользователя Floomin
        cursor.execute("SELECT UserID FROM tbl_Users WHERE Username = 'Floomin'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO tbl_Users (FullName, Username, PasswordHash, Role, IsActive, RequirePasswordChange)
                VALUES (?, ?, ?, ?, ?, ?)
            """, ('Адміністратор (Floomin)', 'Floomin', hashed_default, 'Admin', 1, 1))
            print("✅ Администратор Floomin успешно создан.")
        else:
            cursor.execute("UPDATE tbl_Users SET Role = 'Admin', IsActive = 1 WHERE Username = 'Floomin'")
            print("✅ Права администратора для Floomin обновлены.")
            
        conn.commit()
        conn.close()
        print(f"\n🚀 СИСТЕМА ГОТОВА")
        print(f"Логин админа: Floomin")
        print(f"Временный пароль для всех: {DEFAULT_PASSWORD}")

if __name__ == "__main__":
    setup_system()