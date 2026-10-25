import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

driver = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
server = os.getenv("DB_SERVER", ".")
database = os.getenv("DB_NAME", "ForestMonitoringDB")
username = os.getenv("DB_USER", "")
password = os.getenv("DB_PASSWORD", "")
encrypt = os.getenv("DB_ENCRYPT", "no")
trust = os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")

if username:
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};DATABASE={database};"
        f"UID={username};PWD={password};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust};"
    )
else:
    connection_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust};"
    )

try:
    with pyodbc.connect(connection_string, timeout=5) as connection:
        cursor = connection.cursor()

        cursor.execute("SELECT DB_NAME(), USER_NAME()")
        database_name, database_user = cursor.fetchone()

        print("ПІДКЛЮЧЕННЯ УСПІШНЕ")
        print("База даних:", database_name)
        print("Користувач SQL Server:", database_user)

        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        print("Кількість таблиць:", len(tables))
        print("Таблиці:", ", ".join(tables))

except Exception as error:
    print("ПОМИЛКА ПІДКЛЮЧЕННЯ")
    print(type(error).__name__, error)
