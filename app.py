import os
from datetime import datetime
from functools import wraps

import pyodbc
from dotenv import load_dotenv
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    abort,
)
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-development-secret-key",
)

TABLES = {
    "forestry-units": {
        "table": "ForestryUnits",
        "pk": "ForestryUnitID",
        "title": "Лісництва",
        "icon": "🌲",
        "fields": [
            ("Name", "Назва", "text", True),
            ("Region", "Регіон", "text", True),
            ("Address", "Адреса", "text", False),
            ("AreaHectares", "Площа, га", "number", False),
            ("ContactPhone", "Контактний телефон", "text", False),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "forest-plots": {
        "table": "ForestPlots",
        "pk": "PlotID",
        "title": "Лісові ділянки",
        "icon": "🗺️",
        "fields": [
            (
                "ForestryUnitID",
                "Лісництво",
                "fk:ForestryUnits:ForestryUnitID:Name",
                True,
            ),
            ("PlotNumber", "Номер ділянки", "text", True),
            ("AreaHectares", "Площа, га", "number", True),
            ("Latitude", "Широта", "number", False),
            ("Longitude", "Довгота", "number", False),
            ("ForestCondition", "Стан лісу", "text", False),
            (
                "RiskLevel",
                "Рівень ризику",
                "select:Низький|Середній|Високий|Критичний",
                False,
            ),
        ],
    },
    "tree-species": {
        "table": "TreeSpecies",
        "pk": "SpeciesID",
        "title": "Породи дерев",
        "icon": "🍃",
        "fields": [
            ("Name", "Назва породи", "text", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "forest-stands": {
        "table": "ForestStands",
        "pk": "StandID",
        "title": "Лісові насадження",
        "icon": "🌳",
        "fields": [
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", True),
            ("SpeciesID", "Порода", "fk:TreeSpecies:SpeciesID:Name", True),
            ("AgeYears", "Вік, років", "number", True),
            ("AverageHeightMeters", "Середня висота, м", "number", False),
            ("AverageDiameterCm", "Середній діаметр, см", "number", False),
            ("DensityPercent", "Щільність, %", "number", False),
            ("HealthCondition", "Стан насаджень", "text", False),
        ],
    },
    "towers": {
        "table": "ObservationTowers",
        "pk": "TowerID",
        "title": "Спостережні вежі",
        "icon": "📡",
        "fields": [
            (
                "ForestryUnitID",
                "Лісництво",
                "fk:ForestryUnits:ForestryUnitID:Name",
                True,
            ),
            ("TowerName", "Назва вежі", "text", True),
            ("Latitude", "Широта", "number", True),
            ("Longitude", "Довгота", "number", True),
            ("HeightMeters", "Висота, м", "number", False),
            ("Status", "Статус", "select:Працює|На обслуговуванні|Не працює", True),
        ],
    },
    "cameras": {
        "table": "Cameras",
        "pk": "CameraID",
        "title": "Камери",
        "icon": "📷",
        "fields": [
            ("TowerID", "Вежа", "fk:ObservationTowers:TowerID:TowerName", True),
            ("CameraName", "Назва камери", "text", True),
            ("CameraType", "Тип камери", "text", False),
            ("InstallationDate", "Дата встановлення", "date", False),
            ("Status", "Статус", "select:Працює|На обслуговуванні|Не працює", True),
            ("IPAddress", "IP-адреса", "text", False),
        ],
    },
    "coverage-zones": {
        "table": "CoverageZones",
        "pk": "CoverageZoneID",
        "title": "Зони покриття",
        "icon": "📶",
        "fields": [
            ("CameraID", "Камера", "fk:Cameras:CameraID:CameraName", True),
            ("ZoneName", "Назва зони", "text", True),
            ("RadiusMeters", "Радіус, м", "number", False),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "signal-sources": {
        "table": "SignalSources",
        "pk": "SignalSourceID",
        "title": "Джерела сигналів",
        "icon": "🔔",
        "fields": [
            ("SourceName", "Назва джерела", "text", True),
            ("SourceType", "Тип джерела", "text", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "suspicions": {
        "table": "FireSuspicions",
        "pk": "SuspicionID",
        "title": "Підозри щодо займань",
        "icon": "⚠️",
        "fields": [
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", False),
            (
                "SignalSourceID",
                "Джерело сигналу",
                "fk:SignalSources:SignalSourceID:SourceName",
                True,
            ),
            (
                "CreatedByUserID",
                "Створив користувач",
                "fk:Users:UserID:FullName",
                False,
            ),
            ("Latitude", "Широта", "number", False),
            ("Longitude", "Довгота", "number", False),
            ("Description", "Опис", "textarea", False),
            (
                "Priority",
                "Пріоритет",
                "select:Низький|Середній|Високий|Критичний",
                True,
            ),
            (
                "Status",
                "Статус",
                "select:Нова|На перевірці|Підтверджена|Відхилена",
                True,
            ),
        ],
    },
    "uavs": {
        "table": "UAVs",
        "pk": "UAVID",
        "title": "Безпілотні апарати",
        "icon": "🛩️",
        "fields": [
            ("Name", "Назва", "text", True),
            ("Model", "Модель", "text", False),
            ("SerialNumber", "Серійний номер", "text", False),
            ("MaximumFlightMinutes", "Максимальний час польоту, хв", "number", False),
            ("CameraType", "Тип камери", "text", False),
            (
                "Status",
                "Статус",
                "select:Готовий|У польоті|На обслуговуванні|Недоступний",
                True,
            ),
        ],
    },
    "missions": {
        "table": "UAVMissions",
        "pk": "MissionID",
        "title": "Польотні завдання",
        "icon": "🧭",
        "fields": [
            (
                "SuspicionID",
                "Підозра",
                "fk:FireSuspicions:SuspicionID:Description",
                False,
            ),
            ("UAVID", "БПЛА", "fk:UAVs:UAVID:Name", True),
            ("AssignedUserID", "Оператор", "fk:Users:UserID:FullName", False),
            ("StartLatitude", "Широта старту", "number", False),
            ("StartLongitude", "Довгота старту", "number", False),
            ("TargetLatitude", "Широта цілі", "number", False),
            ("TargetLongitude", "Довгота цілі", "number", False),
            ("RouteDescription", "Опис маршруту", "textarea", False),
            (
                "Status",
                "Статус",
                "select:Заплановано|Виконується|Завершено|Скасовано",
                True,
            ),
            ("Result", "Результат", "textarea", False),
        ],
    },
    "inspections": {
        "table": "Inspections",
        "pk": "InspectionID",
        "title": "Перевірки підозр",
        "icon": "🔎",
        "fields": [
            (
                "SuspicionID",
                "Підозра",
                "fk:FireSuspicions:SuspicionID:SuspicionID",
                True,
            ),
            (
                "MissionID",
                "Польотне завдання",
                "fk:UAVMissions:MissionID:MissionID",
                False,
            ),
            ("InspectorUserID", "Інспектор", "fk:Users:UserID:FullName", False),
            ("Result", "Результат", "text", True),
            ("Description", "Опис", "textarea", False),
            ("FireConfirmed", "Пожежу підтверджено", "select:0|1", True),
        ],
    },
    "severity-classes": {
        "table": "FireSeverityClasses",
        "pk": "SeverityClassID",
        "title": "Класи складності пожеж",
        "icon": "🔥",
        "fields": [
            ("ClassName", "Назва класу", "text", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "fires": {
        "table": "Fires",
        "pk": "FireID",
        "title": "Підтверджені пожежі",
        "icon": "🔥",
        "fields": [
            (
                "SuspicionID",
                "Підозра",
                "fk:FireSuspicions:SuspicionID:SuspicionID",
                False,
            ),
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", False),
            (
                "SeverityClassID",
                "Клас складності",
                "fk:FireSeverityClasses:SeverityClassID:ClassName",
                True,
            ),
            ("ConfirmedAt", "Час підтвердження", "datetime-local", False),
            ("LocalizedAt", "Час локалізації", "datetime-local", False),
            ("ExtinguishedAt", "Час ліквідації", "datetime-local", False),
            ("Latitude", "Широта", "number", False),
            ("Longitude", "Довгота", "number", False),
            ("AreaHectares", "Площа, га", "number", False),
            ("Cause", "Причина", "text", False),
            ("Status", "Статус", "select:Активна|Локалізована|Ліквідована", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "fire-stages": {
        "table": "FireSuppressionStages",
        "pk": "StageID",
        "title": "Етапи реагування",
        "icon": "🚒",
        "fields": [
            ("FireID", "Пожежа", "fk:Fires:FireID:FireID", True),
            ("StageName", "Назва етапу", "text", True),
            ("StartTime", "Початок", "datetime-local", True),
            ("EndTime", "Завершення", "datetime-local", False),
            ("Description", "Опис", "textarea", False),
            ("Result", "Результат", "textarea", False),
        ],
    },
    "resources": {
        "table": "ResponseResources",
        "pk": "ResourceID",
        "title": "Ресурси реагування",
        "icon": "🚒",
        "fields": [
            ("ResourceType", "Тип ресурсу", "text", True),
            ("ResourceName", "Назва ресурсу", "text", True),
            ("Organization", "Організація", "text", False),
            ("Quantity", "Кількість", "number", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "illegal-logging": {
        "table": "IllegalLogging",
        "pk": "LoggingID",
        "title": "Незаконні рубки",
        "icon": "🪵",
        "fields": [
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", True),
            (
                "DetectedByUserID",
                "Виявив користувач",
                "fk:Users:UserID:FullName",
                False,
            ),
            ("Latitude", "Широта", "number", False),
            ("Longitude", "Довгота", "number", False),
            ("EstimatedAreaHectares", "Орієнтовна площа, га", "number", False),
            ("EstimatedDamage", "Орієнтовні збитки", "number", False),
            ("Status", "Статус", "select:Нове|На перевірці|Підтверджено|Закрито", True),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "illegal-dumps": {
        "table": "IllegalDumpSites",
        "pk": "DumpSiteID",
        "title": "Сміттєзвалища",
        "icon": "♻️",
        "fields": [
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", True),
            (
                "DetectedByUserID",
                "Виявив користувач",
                "fk:Users:UserID:FullName",
                False,
            ),
            ("Latitude", "Широта", "number", False),
            ("Longitude", "Довгота", "number", False),
            ("EstimatedAreaM2", "Орієнтовна площа, м²", "number", False),
            ("WasteType", "Тип відходів", "text", False),
            (
                "Status",
                "Статус",
                "select:Нове|На перевірці|Підтверджено|Ліквідовано",
                True,
            ),
            ("Description", "Опис", "textarea", False),
        ],
    },
    "risk-assessments": {
        "table": "FireRiskAssessments",
        "pk": "RiskAssessmentID",
        "title": "Оцінювання пожежного ризику",
        "icon": "🌡️",
        "fields": [
            ("PlotID", "Ділянка", "fk:ForestPlots:PlotID:PlotNumber", True),
            ("TemperatureC", "Температура, °C", "number", False),
            ("HumidityPercent", "Вологість, %", "number", False),
            ("WindSpeedMs", "Швидкість вітру, м/с", "number", False),
            ("PrecipitationMm", "Опади, мм", "number", False),
            (
                "RiskLevel",
                "Рівень ризику",
                "select:Низький|Середній|Високий|Критичний",
                True,
            ),
            ("RiskScore", "Оцінка ризику", "number", False),
            ("Recommendation", "Рекомендація", "textarea", False),
        ],
    },
}

TABLES.update(
    {
        "roles": {
            "table": "Roles",
            "pk": "RoleID",
            "title": "Ролі",
            "icon": "🛡️",
            "fields": [
                ("RoleName", "Назва ролі", "text", True),
                ("Description", "Опис", "textarea", False),
            ],
        },
        "users": {
            "table": "Users",
            "pk": "UserID",
            "title": "Користувачі",
            "icon": "👥",
            "fields": [
                ("RoleID", "Роль", "fk:Roles:RoleID:RoleName", True),
                ("FullName", "ПІБ", "text", True),
                ("Login", "Логін", "text", True),
                ("Email", "Email", "email", False),
                ("Phone", "Телефон", "text", False),
                ("IsActive", "Активний (0/1)", "select:0|1", True),
                ("Password", "Пароль", "password", True),
            ],
        },
        "fire-resources": {
            "table": "FireResources",
            "pk": "FireResourceID",
            "title": "Ресурси на пожежах",
            "icon": "🧰",
            "fields": [
                ("FireID", "Пожежа", "fk:Fires:FireID:FireID", True),
                (
                    "ResourceID",
                    "Ресурс",
                    "fk:ResponseResources:ResourceID:ResourceName",
                    True,
                ),
                ("QuantityUsed", "Використана кількість", "number", True),
            ],
        },
        "inspection-acts": {
            "table": "InspectionActs",
            "pk": "ActID",
            "title": "Акти інспекцій",
            "icon": "📄",
            "fields": [
                ("ActNumber", "Номер акта", "text", True),
                ("CreatedByUserID", "Створив", "fk:Users:UserID:FullName", True),
                (
                    "LoggingID",
                    "Незаконна рубка",
                    "fk:IllegalLogging:LoggingID:LoggingID",
                    False,
                ),
                (
                    "DumpSiteID",
                    "Сміттєзвалище",
                    "fk:IllegalDumpSites:DumpSiteID:DumpSiteID",
                    False,
                ),
                ("Description", "Опис", "textarea", False),
                ("Decision", "Рішення", "textarea", False),
            ],
        },
    }
)

DIRECTORY_MODULES = {
    "forestry-units",
    "forest-plots",
    "tree-species",
    "forest-stands",
    "towers",
    "cameras",
    "coverage-zones",
    "signal-sources",
    "uavs",
    "severity-classes",
    "resources",
    "risk-assessments",
    "roles",
    "users",
}

EVENT_MODULES = {
    "suspicions",
    "missions",
    "inspections",
    "fires",
    "fire-stages",
    "fire-resources",
    "illegal-logging",
    "illegal-dumps",
    "inspection-acts",
}

ROLE_MODULES = {
    "Черговий диспетчер": {
        "view": {
            "forest-plots",
            "signal-sources",
            "suspicions",
            "uavs",
            "missions",
            "inspections",
            "fires",
            "fire-stages",
            "severity-classes",
            "resources",
            "fire-resources",
            "risk-assessments",
        },
        "create": {
            "suspicions",
            "missions",
            "fires",
            "fire-stages",
            "fire-resources",
        },
        "edit": {
            "suspicions",
            "missions",
            "fires",
            "fire-stages",
            "fire-resources",
        },
    },
    "Лісничий": {
        "view": {
            "forestry-units",
            "forest-plots",
            "tree-species",
            "forest-stands",
            "towers",
            "cameras",
            "coverage-zones",
            "illegal-logging",
            "illegal-dumps",
            "risk-assessments",
        },
        "create": {
            "forest-plots",
            "forest-stands",
            "illegal-logging",
            "illegal-dumps",
            "risk-assessments",
        },
        "edit": {
            "forest-plots",
            "forest-stands",
            "illegal-logging",
            "illegal-dumps",
            "risk-assessments",
        },
    },
    "Інспектор": {
        "view": {
            "forest-plots",
            "suspicions",
            "missions",
            "inspections",
            "illegal-logging",
            "illegal-dumps",
            "inspection-acts",
            "fires",
            "severity-classes",
        },
        "create": {
            "inspections",
            "illegal-logging",
            "illegal-dumps",
            "inspection-acts",
        },
        "edit": {
            "inspections",
            "illegal-logging",
            "illegal-dumps",
            "inspection-acts",
        },
    },
    "Керівник": {
        "view": set(TABLES.keys()) - {"roles", "users"},
        "create": set(),
        "edit": set(),
    },
}


PAGE_ROLES = {
    "dashboard": {
        "Черговий диспетчер",
        "Лісничий",
        "Інспектор",
        "Керівник",
        "Адміністратор",
    },
    "map": {
        "Черговий диспетчер",
        "Лісничий",
        "Інспектор",
        "Керівник",
        "Адміністратор",
    },
    "reports": {
        "Черговий диспетчер",
        "Інспектор",
        "Керівник",
        "Адміністратор",
    },
}


def current_role():
    return session.get("role", "")


def can_view_module(slug):
    role = current_role()

    if role == "Адміністратор":
        return slug in TABLES

    return slug in ROLE_MODULES.get(role, {}).get("view", set())


def can_create_module(slug):
    role = current_role()

    if role == "Адміністратор":
        return slug in TABLES

    return slug in ROLE_MODULES.get(role, {}).get("create", set())


def can_edit_module(slug):
    role = current_role()

    if role == "Адміністратор":
        return slug in TABLES

    return slug in ROLE_MODULES.get(role, {}).get("edit", set())


def can_delete_module(slug):
    return current_role() == "Адміністратор" and slug in TABLES


def can_access_page(page):
    role = current_role()

    return role == "Адміністратор" or role in PAGE_ROLES.get(page, set())


def get_connection():
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
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Encrypt={encrypt};"
            f"TrustServerCertificate={trust};"
        )
    else:
        connection_string = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
            f"Encrypt={encrypt};"
            f"TrustServerCertificate={trust};"
        )

    return pyodbc.connect(connection_string, timeout=5)


def query(sql, params=(), one=False):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)

        if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            connection.commit()
            return None

        columns = (
            [column[0] for column in cursor.description] if cursor.description else []
        )
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()] if columns else []

        if one:
            return rows[0] if rows else None

        return rows
    finally:
        connection.close()


def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))

        return function(*args, **kwargs)

    return wrapped


def roles_required(*roles):
    def decorator(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                return redirect(url_for("login", next=request.path))

            if session.get("role") not in roles:
                abort(403)

            return function(*args, **kwargs)

        return wrapped

    return decorator


@app.context_processor
def inject_globals():
    visible_tables = {
        slug: config for slug, config in TABLES.items() if can_view_module(slug)
    }

    return {
        "nav_tables": visible_tables,
        "directory_tables": {
            slug: config
            for slug, config in visible_tables.items()
            if slug in DIRECTORY_MODULES
        },
        "event_tables": {
            slug: config
            for slug, config in visible_tables.items()
            if slug in EVENT_MODULES
        },
        "current_year": datetime.now().year,
        "can_view_module": can_view_module,
        "can_create_module": can_create_module,
        "can_edit_module": can_edit_module,
        "can_delete_module": can_delete_module,
        "can_access_page": can_access_page,
    }


@app.route("/")
@login_required
def index():
    stats = {
        "plots": "—",
        "suspicions": "—",
        "fires": "—",
        "uavs": "—",
    }

    stat_queries = {
        "plots": "SELECT COUNT(*) n FROM ForestPlots",
        "suspicions": (
            "SELECT COUNT(*) n FROM FireSuspicions "
            "WHERE Status NOT IN (N'Відхилена')"
        ),
        "fires": (
            "SELECT COUNT(*) n FROM Fires " "WHERE Status NOT IN (N'Ліквідована')"
        ),
        "uavs": "SELECT COUNT(*) n FROM UAVs",
    }

    for key, sql in stat_queries.items():
        try:
            result = query(sql, one=True)
            stats[key] = result["n"] if result else 0
        except Exception:
            app.logger.exception(
                "Не вдалося завантажити показник dashboard: %s",
                key,
            )

    latest = []

    try:
        latest = query("""
            SELECT TOP 6
                s.SuspicionID,
                s.DetectedAt,
                s.Priority,
                s.Status,
                s.Description,
                p.PlotNumber,
                ss.SourceName
            FROM FireSuspicions s
            LEFT JOIN ForestPlots p ON p.PlotID = s.PlotID
            INNER JOIN SignalSources ss
                ON ss.SignalSourceID = s.SignalSourceID
            ORDER BY s.DetectedAt DESC
        """)
    except Exception:
        app.logger.exception("Не вдалося завантажити останні сигнали dashboard")

    return render_template(
        "dashboard.html",
        stats=stats,
        latest=latest,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_name = request.form.get("login", "").strip()
        password = request.form.get("password", "")

        try:
            user = query(
                """
                SELECT
                    u.UserID,
                    u.FullName,
                    u.Login,
                    u.PasswordHash,
                    u.IsActive,
                    r.RoleName
                FROM Users u
                INNER JOIN Roles r ON r.RoleID = u.RoleID
                WHERE u.Login = ?
            """,
                (login_name,),
                one=True,
            )

            if (
                user
                and user["IsActive"]
                and user["PasswordHash"]
                and check_password_hash(user["PasswordHash"], password)
            ):
                session.clear()
                session.update(
                    user_id=user["UserID"],
                    full_name=user["FullName"],
                    login=user["Login"],
                    role=user["RoleName"],
                )

                flash("Вхід виконано успішно.", "success")
                return redirect(request.args.get("next") or url_for("index"))

            flash(
                "Неправильний логін/пароль або обліковий запис неактивний.",
                "danger",
            )
        except Exception:
            app.logger.exception("Помилка входу")
            flash(
                "Не вдалося перевірити обліковий запис. "
                "Перевірте налаштування БД і структуру таблиці Users.",
                "danger",
            )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Ви вийшли із системи.", "info")
    return redirect(url_for("login"))


@app.route("/module/<slug>")
@login_required
def module(slug):
    config = TABLES.get(slug)

    if not config:
        abort(404)

    if not can_view_module(slug):
        abort(403)

    search = request.args.get("q", "").strip()

    try:
        sql = f"SELECT TOP 300 * FROM [{config['table']}]"
        params = []

        if search:
            searchable = [
                field[0]
                for field in config["fields"]
                if field[2] in ("text", "email", "textarea")
            ]

            if searchable:
                sql += " WHERE " + " OR ".join(
                    f"CAST([{column}] AS NVARCHAR(MAX)) LIKE ?" for column in searchable
                )
                params = [f"%{search}%"] * len(searchable)

        sql += f" ORDER BY [{config['pk']}] DESC"

        rows = query(sql, params)

        if rows:
            columns = list(rows[0].keys())
        else:
            columns = [config["pk"]] + [field[0] for field in config["fields"]]

        error = None

    except Exception:
        app.logger.exception("Помилка завантаження модуля %s", slug)
        rows, columns = [], []
        error = True

    return render_template(
        "module.html",
        slug=slug,
        cfg=config,
        rows=rows,
        columns=columns,
        search=search,
        db_error=error,
    )


def field_options(field_type):
    parts = field_type.split(":")

    if parts[0] != "fk":
        return []

    table_name, primary_key, label_column = parts[1], parts[2], parts[3]

    return query(f"""
        SELECT
            [{primary_key}] AS id,
            CAST([{label_column}] AS NVARCHAR(250)) AS label
        FROM [{table_name}]
        ORDER BY [{primary_key}] DESC
        """)


def parse_value(value, kind):
    if value == "":
        return None

    if kind == "select:0|1":
        return int(value)

    if kind.startswith("fk:"):
        return int(value)

    if kind == "number":
        return float(value)

    if kind == "date":
        return value

    if kind == "datetime-local":
        return value.replace("T", " ") if value else None

    return value.strip()


def load_options(config):
    result = {}

    for column, label, kind, required in config["fields"]:
        if kind.startswith("fk:"):
            try:
                result[column] = field_options(kind)
            except Exception:
                app.logger.exception(
                    "Не вдалося завантажити варіанти для %s",
                    column,
                )
                result[column] = []

    return result


@app.route("/module/<slug>/new", methods=["GET", "POST"])
@login_required
def create_record(slug):
    config = TABLES.get(slug)

    if not config:
        abort(404)

    if not can_create_module(slug):
        abort(403)

    if request.method == "POST":
        try:
            names = []
            values = []

            for column, label, kind, required in config["fields"]:
                raw_value = request.form.get(column, "")

                if required and not raw_value.strip():
                    raise ValueError(f"Поле «{label}» є обов'язковим.")

                if config["table"] == "Users" and column == "Password":
                    names.append("[PasswordHash]")
                    values.append(generate_password_hash(raw_value))
                else:
                    names.append(f"[{column}]")
                    values.append(parse_value(raw_value, kind))

            placeholders = ",".join("?" for _ in names)

            query(
                f"""
                INSERT INTO [{config['table']}]
                    ({','.join(names)})
                VALUES ({placeholders})
                """,
                values,
            )

            flash("Запис створено.", "success")
            return redirect(url_for("module", slug=slug))

        except Exception as error:
            app.logger.exception("Помилка створення запису в %s", slug)
            flash(f"Не вдалося створити запис: {error}", "danger")

    return render_template(
        "record_form.html",
        cfg=config,
        slug=slug,
        record={},
        options=load_options(config),
        mode="new",
    )


@app.route("/module/<slug>/<int:record_id>/edit", methods=["GET", "POST"])
@login_required
def edit_record(slug, record_id):
    config = TABLES.get(slug)

    if not config:
        abort(404)

    if not can_edit_module(slug):
        abort(403)

    record = query(
        f"""
        SELECT *
        FROM [{config['table']}]
        WHERE [{config['pk']}] = ?
        """,
        (record_id,),
        one=True,
    )

    if not record:
        abort(404)

    if request.method == "POST":
        try:
            assignments = []
            values = []

            for column, label, kind, required in config["fields"]:
                raw_value = request.form.get(column, "")

                if config["table"] == "Users" and column == "Password":
                    if raw_value.strip():
                        assignments.append("[PasswordHash] = ?")
                        values.append(generate_password_hash(raw_value))
                    continue

                if required and not raw_value.strip():
                    raise ValueError(f"Поле «{label}» є обов'язковим.")

                assignments.append(f"[{column}] = ?")
                values.append(parse_value(raw_value, kind))

            values.append(record_id)

            query(
                f"""
                UPDATE [{config['table']}]
                SET {','.join(assignments)}
                WHERE [{config['pk']}] = ?
                """,
                values,
            )

            flash("Зміни збережено.", "success")
            return redirect(url_for("module", slug=slug))

        except Exception as error:
            app.logger.exception("Помилка редагування запису %s", slug)
            flash(f"Не вдалося зберегти зміни: {error}", "danger")
            record = {**record, **request.form}

    return render_template(
        "record_form.html",
        cfg=config,
        slug=slug,
        record=record,
        options=load_options(config),
        mode="edit",
    )


@app.route("/module/<slug>/<int:record_id>/delete", methods=["POST"])
@roles_required("Адміністратор")
def delete_record(slug, record_id):
    config = TABLES.get(slug)

    if not config:
        abort(404)

    try:
        query(
            f"""
            DELETE FROM [{config['table']}]
            WHERE [{config['pk']}] = ?
            """,
            (record_id,),
        )
        flash(
            "Запис видалено, якщо він не використовується пов'язаними записами.",
            "success",
        )
    except Exception as error:
        app.logger.exception("Помилка видалення запису %s", slug)
        flash(
            "Не вдалося видалити запис. Можливо, на нього посилаються "
            f"інші таблиці. Деталі: {error}",
            "danger",
        )

    return redirect(url_for("module", slug=slug))


@app.route("/map")
@login_required
def map_view():
    if not can_access_page("map"):
        abort(403)

    try:
        plots = query("""
            SELECT PlotID, PlotNumber, Latitude, Longitude, RiskLevel
            FROM ForestPlots
            WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
        """)

        fires = query("""
            SELECT FireID, Latitude, Longitude, Status, AreaHectares
            FROM Fires
            WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
        """)

        suspicions = query("""
            SELECT SuspicionID, Latitude, Longitude, Priority, Status
            FROM FireSuspicions
            WHERE Latitude IS NOT NULL AND Longitude IS NOT NULL
        """)

    except Exception:
        app.logger.exception("Помилка завантаження карти")
        plots, fires, suspicions = [], [], []
        flash(
            "Не вдалося завантажити координати. Перевірте дані.",
            "warning",
        )

    return render_template(
        "map.html",
        plots=plots,
        fires=fires,
        suspicions=suspicions,
    )


@app.route("/reports")
@login_required
def reports():
    if not can_access_page("reports"):
        abort(403)

    data = {}

    try:
        data["fires_by_status"] = query("""
            SELECT Status, COUNT(*) AS Total
            FROM Fires
            GROUP BY Status
            ORDER BY Total DESC
        """)

        data["suspicions_by_priority"] = query("""
            SELECT Priority, COUNT(*) AS Total
            FROM FireSuspicions
            GROUP BY Priority
            ORDER BY Total DESC
        """)

        data["risk_by_level"] = query("""
            SELECT RiskLevel, COUNT(*) AS Total
            FROM FireRiskAssessments
            GROUP BY RiskLevel
            ORDER BY Total DESC
        """)

        data["response"] = query("""
            SELECT TOP 20
                FireID,
                DetectedAt,
                ConfirmedAt,
                LocalizedAt,
                ExtinguishedAt,
                Status,
                AreaHectares
            FROM Fires
            ORDER BY DetectedAt DESC
        """)

    except Exception:
        app.logger.exception("Помилка завантаження звітів")
        flash(
            "Звіти недоступні. Перевірте структуру таблиць.",
            "warning",
        )

        data = {
            "fires_by_status": [],
            "suspicions_by_priority": [],
            "risk_by_level": [],
            "response": [],
        }

    return render_template("reports.html", data=data)


@app.errorhandler(403)
def forbidden(_error):
    return (
        render_template(
            "error.html",
            code=403,
            message="Недостатньо прав для цієї дії.",
        ),
        403,
    )


@app.errorhandler(404)
def not_found(_error):
    return (
        render_template(
            "error.html",
            code=404,
            message="Сторінку або запис не знайдено.",
        ),
        404,
    )


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
