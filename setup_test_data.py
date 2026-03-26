import random
from database.connection import get_connection

# Берем реальные филиалы и села из нашего списка, чтобы фильтры сработали
LOCATIONS = [
    ('Кунянська філія', 'Комарівка'),
    ('Кунянська філія', 'Мала Севастьянівка'),
    ('Маломочульська філія', 'Борсуки'),
    ('Немирівська філія', 'Даньківка'),
    ('Погребищенська філія', 'Адамівка( Погребище)')
]

LAST_NAMES = ['Іваненко', 'Петренко', 'Сидоренко', 'Коваленко', 'Ткаченко', 'Шевченко', 'Бойко', 'Мельник']
INITIALS = ['І.І.', 'П.П.', 'С.С.', 'В.В.', 'О.О.', 'М.М.', 'Т.Т.', 'Г.Г.']
CROPS = ['Пшениця озима', 'Кукурудза', 'Соняшник', 'Соя', 'Ріпак']

def generate_test_data(count=20):
    conn = get_connection()
    if not conn:
        print("❌ Ошибка подключения к БД")
        return
    
    cursor = conn.cursor()
    records_added = 0
    
    print("⏳ Генерация тестовых данных...")
    
    for _ in range(count):
        cluster, village = random.choice(LOCATIONS)
        contract_num = f"Д-{random.randint(1000, 9999)}"
        # Генерируем похожий на правду кадастровый номер (Винницкая область обычно начинается на 05)
        cadastral = f"052{random.randint(10,99)}8{random.randint(100,999)}00:0{random.randint(1,9)}:00{random.randint(1,9)}:{random.randint(1000,9999)}"
        
        uid = f"{cadastral}_{contract_num}" # Наш двойной ключ
        owner = f"{random.choice(LAST_NAMES)} {random.choice(INITIALS)}"
        area = round(random.uniform(1.5, 4.5), 4)
        expiry = '2026-12-31'
        crop25 = random.choice(CROPS)
        crop26 = random.choice(CROPS)
        field = f"Поле №{random.randint(1, 15)}"
        
        query = """
            INSERT INTO tbl_MainRegistry 
            (AgreementUID, Cluster, Village, ContractNumber, ExpiryDate, ContractType, LessorType, 
             LandPlotType, CounterpartyName, CadastralNumber, Area, ShareCount, PlotNumber, 
             FieldNumber, Crop2025, Crop2026, Condition, PlotStatus)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        try:
            cursor.execute(query, (
                uid, cluster, village, contract_num, expiry, 'Оренда землі', 'Фізична особа',
                'Пай', owner, cadastral, area, 1.0, f"Діл-{random.randint(1, 100)}",
                field, crop25, crop26, 'Діючий', 'В обробітку'
            ))
            records_added += 1
        except Exception as e:
            # Игнорируем дубликаты, если случайно сгенерируется одинаковый UID
            pass
            
    conn.commit()
    conn.close()
    print(f"✅ Успешно добавлено {records_added} тестовых записей в реестр!")

if __name__ == "__main__":
    generate_test_data(30) # Создадим 30 записей