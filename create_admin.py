from getpass import getpass

from werkzeug.security import generate_password_hash
from app import get_connection

full_name = input("ПІБ адміністратора: ").strip()
login = input("Логін адміністратора: ").strip()
password = getpass("Пароль адміністратора: ")
password_confirm = getpass("Повторіть пароль: ")

if not full_name or not login or not password:
    raise SystemExit("Усі поля обов'язкові.")

if password != password_confirm:
    raise SystemExit("Паролі не збігаються.")

if len(password) < 10:
    raise SystemExit("Пароль має містити щонайменше 10 символів.")

conn = get_connection()

try:
    cur = conn.cursor()

    cur.execute("SELECT RoleID FROM Roles WHERE RoleName = ?", ("Адміністратор",))
    role = cur.fetchone()

    if role is None:
        raise RuntimeError("Роль «Адміністратор» не знайдена в таблиці Roles.")

    cur.execute("SELECT UserID FROM Users WHERE Login = ?", (login,))
    if cur.fetchone():
        raise RuntimeError("Такий логін уже існує.")

    cur.execute(
        """
        INSERT INTO Users
            (RoleID, FullName, Login, IsActive, PasswordHash)
        VALUES (?, ?, ?, 1, ?)
        """,
        (role[0], full_name, login, generate_password_hash(password)),
    )

    conn.commit()
    print("Адміністратора успішно створено.")
    print("Логін:", login)
    print("Тепер увійдіть через сторінку /login.")

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()
