import sqlite3
import psycopg2
from psycopg2 import sql

# SQLite database
sqlite_db = r'PyCode\bus_delay.db'
sqlite_conn = sqlite3.connect(sqlite_db)
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL database connection details
pg_host = 'postgres-data'
pg_port = 5432
pg_dbname = 'dashboard'
pg_user = 'postgres'
pg_password = '!Kenchou2006'

# Connect to PostgreSQL database
try:
    pg_conn = psycopg2.connect(
        host=pg_host,
        port=pg_port,
        dbname=pg_dbname,
        user=pg_user,
        password=pg_password
    )
except psycopg2.Error as e:
    print(f"Error connecting to PostgreSQL database: {e}")
    exit(1)

pg_cursor = pg_conn.cursor()

# Define SQLite table name
sqlite_table = 'daily_stats'

# Fetch table schema from SQLite
sqlite_cursor.execute(f"PRAGMA table_info({sqlite_table})")
table_info = sqlite_cursor.fetchall()
column_names = [col[1] for col in table_info]

# Create table in PostgreSQL if not exists
create_table_query = sql.SQL("""
CREATE TABLE IF NOT EXISTS daily_stats (
    date TEXT,
    route_name TEXT,
    delayed_count INTEGER,
    on_time_count INTEGER,
    PRIMARY KEY (date, route_name)
)
""")
pg_cursor.execute(create_table_query)
pg_conn.commit()

# Fetch data from SQLite table
sqlite_cursor.execute(f"SELECT * FROM {sqlite_table}")
rows = sqlite_cursor.fetchall()

# Insert data into PostgreSQL table
insert_query = sql.SQL("""
    INSERT INTO daily_stats ({})
    VALUES ({})
""").format(
    sql.SQL(', ').join(map(sql.Identifier, column_names)),
    sql.SQL(', ').join(sql.Placeholder() * len(column_names))
)

for row in rows:
    # Handle None values in SQLite data
    row = tuple(None if value is None else value for value in row)
    pg_cursor.execute(insert_query, row)

pg_conn.commit()

# Close all connections
sqlite_cursor.close()
sqlite_conn.close()
pg_cursor.close()
pg_conn.close()

print("Data migration completed successfully.")
