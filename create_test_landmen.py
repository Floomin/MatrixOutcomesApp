import bcrypt
from database.connection import get_connection

def create_test_landmen():
    conn = get_connection()
    if not conn:
        print("❌ Помилка підключення до БД")
        return
        
    cursor = conn.cursor()
    test_password = "test"
    hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Список користувачів: (ПІБ, Логін, SubRole)
    landmen = [
        ('Земельник Оформлення', 'test_landman1', 'Type1'),
        ('Земельник Польовий', 'test_landman2', 'Type2'),
        ('Земельник 1С', 'test_landman3', 'Type3')
    ]
    
    for name, username, subrole in landmen:
        cursor.execute("SELECT UserID FROM tbl_Users WHERE Username = ?", (username,))
        if cursor.fetchone():
            print(f"⚠️ Користувач {username} вже існує!")
            continue
            
        # Додаємо користувача з вказанням Role = 'Landman' та SubRole
        cursor.execute("""
            INSERT INTO tbl_Users (FullName, Username, PasswordHash, Role, SubRole, IsActive, RequirePasswordChange)
            OUTPUT INSERTED.UserID
            VALUES (?, ?, ?, 'Landman', ?, 1, 0)
        """, (name, username, hashed, subrole))
        
        user_id = cursor.fetchone()[0]
        
        # Прив'язуємо до тестових сіл
        test_villages = ['Комарівка', 'Борсуки', 'Даньківка']
        for village in test_villages:
            cursor.execute("INSERT INTO tbl_User_Villages (UserID, VillageName) VALUES (?, ?)", (user_id, village))
            
        print(f"✅ Створено: {name} | Логін: {username} | SubRole: {subrole}")

    conn.commit()
    conn.close()
    print("🎉 Всіх тестових земельників успішно створено (Пароль у всіх: test)!")

if __name__ == "__main__":
    create_test_landmen()