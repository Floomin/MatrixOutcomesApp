import bcrypt
from database.connection import get_connection

def create_test_brigadier():
    conn = get_connection()
    if not conn:
        print("❌ Помилка підключення до БД")
        return
        
    cursor = conn.cursor()
    
    # 1. Пароль для тестів
    test_password = "test"
    hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 2. Перевіряємо, чи немає його вже в базі
    cursor.execute("SELECT UserID FROM tbl_Users WHERE Username = 'test_brigadier'")
    if cursor.fetchone():
        print("⚠️ Тестовий бригадир вже існує!")
        conn.close()
        return

    # 3. Створюємо користувача. 
    # ВАЖЛИВО: прив'язуємо його до 'Тестова бригада' (туди ж, куди й нашого test_manager)
    cursor.execute("""
        INSERT INTO tbl_Users (FullName, Username, PasswordHash, Role, BrigadeName, IsActive, RequirePasswordChange)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, ('Тестовий Бригадир', 'test_brigadier', hashed, 'Brigadier', 'Тестова бригада', 1, 0))
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовий бригадир успішно створений!")
    print("Логін: test_brigadier")
    print("Пароль: test")
    print("Бригада: Тестова бригада")

if __name__ == "__main__":
    create_test_brigadier()