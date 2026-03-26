import bcrypt
from database.connection import get_connection

def create_test_manager():
    conn = get_connection()
    if not conn:
        print("❌ Помилка підключення до БД")
        return
        
    cursor = conn.cursor()
    
    # 1. Простіший пароль для тестів
    test_password = "test"
    hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # 2. Перевіряємо, чи немає його вже в базі, щоб уникнути дублів
    cursor.execute("SELECT UserID FROM tbl_Users WHERE Username = 'test_manager'")
    existing = cursor.fetchone()
    
    if existing:
        print("⚠️ Тестовий менеджер вже існує!")
        conn.close()
        return

    # 3. Створюємо користувача (RequirePasswordChange = 0, щоб заходити відразу)
    cursor.execute("""
        INSERT INTO tbl_Users (FullName, Username, PasswordHash, Role, Cluster, BrigadeName, BrigadierName, IsActive, RequirePasswordChange)
        OUTPUT INSERTED.UserID
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ('Тестовий Менеджер', 'test_manager', hashed, 'Manager', 'Тестова філія', 'Тестова бригада', 'Floomin', 1, 0))
    
    user_id = cursor.fetchone()[0]
    
    # 4. Прив'язуємо до тестових сіл
    test_villages = ['Комарівка', 'Борсуки', 'Даньківка']
    for village in test_villages:
        cursor.execute("INSERT INTO tbl_User_Villages (UserID, VillageName) VALUES (?, ?)", (user_id, village))
        
    conn.commit()
    conn.close()
    
    print("✅ Тестовий менеджер успішно створений!")
    print("Логін: test_manager")
    print("Пароль: test")
    print(f"Прив'язані села: {', '.join(test_villages)}")

if __name__ == "__main__":
    create_test_manager()