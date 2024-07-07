import sqlite3
import csv

# 連接到SQLite資料庫
conn = sqlite3.connect(r'PyCode\bus_delay.db')
cursor = conn.cursor()

# 假設您的資料表名稱為 'your_table'
table_name = 'daily_stats'

# 從資料庫中擷取所有資料
cursor.execute(f"SELECT * FROM {table_name}")
rows = cursor.fetchall()

# 取得資料表的欄位名稱
cursor.execute(f"PRAGMA table_info({table_name})")
columns = [col[1] for col in cursor.fetchall()]

# 指定CSV檔案名稱
csv_file = 'output.csv'

# 將資料寫入CSV檔案
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    csv_writer = csv.writer(f)
    
    # 寫入欄位名稱
    csv_writer.writerow(columns)
    
    # 寫入資料列
    csv_writer.writerows(rows)

print(f"資料已成功匯出到 {csv_file}")

# 關閉連接
conn.close()
