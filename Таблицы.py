import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# === НАСТРОЙКА ===
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1Y-rOb3IHMi4yppzWvGN9eu4vOS1hVtXmy3W8Z_GwLmo"
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# === АВТОРИЗАЦИЯ ===
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_url(SPREADSHEET_URL)

# === Загрузка профессий ===
prof_sheet = sheet.get_worksheet(0)  # Первый лист
prof_df = pd.DataFrame(prof_sheet.get_all_records())
prof_names = prof_df.iloc[:,0].dropna().tolist()

# --- 1. Список профессий по заданию ---

# Определи названия профессий по точному написанию из таблицы!
# Получи их из prof_names для точного соответствия

# Найдём все профессии с "Лаборант" в названии
lab_assistants = [p for p in prof_names if "Лаборант" in p]
# Фермер
fermer = next((p for p in prof_names if "Фермер" in p), None)
# Животновод
zhivotnovod = next((p for p in prof_names if "Животновод" in p), None)
# Специалист по благоустройству растений
spec_blag = next((p for p in prof_names if "Специалист по благоустройству растений" in p), None)

# "Сфера АПК"
sphere_dict = {
    "Растениеводство": [],
    "Животноводство": [],
    "Микробиология": []
}

# "Образ жизни"
lifestyle_dict = {
    "На свежем воздухе": [],
    "В помещениях": [],
    "С частыми командировками": []
}

# "Навык"
skills_dict = {
    "Работа с растениями": [],
    "Работа с животными": [],
    "Экологическая ответственность": []
}

# --- 2. Заполнение сфер ---

# Фермера и Животновода в Животноводство
if fermer: sphere_dict["Животноводство"].append(fermer)
if zhivotnovod: sphere_dict["Животноводство"].append(zhivotnovod)

# В Микробиологию — всех лаборантов
sphere_dict["Микробиология"].extend(lab_assistants)

# В Растениеводство — остальные
ost_prof = [p for p in prof_names if p not in sphere_dict["Животноводство"] + sphere_dict["Микробиология"]]
sphere_dict["Растениеводство"].extend(ost_prof)

# --- 3. Заполнение образа жизни ---

# В помещениях — лаборанты и животновод
lifestyle_dict["В помещениях"].extend(lab_assistants)
if zhivotnovod: lifestyle_dict["В помещениях"].append(zhivotnovod)

# С частыми командировками — специалист по благоустройству растений
if spec_blag: lifestyle_dict["С частыми командировками"].append(spec_blag)

# Остальные — на свежем воздухе
ost_prof_life = [p for p in prof_names if p not in lifestyle_dict["В помещениях"] + lifestyle_dict["С частыми командировками"]]
lifestyle_dict["На свежем воздухе"].extend(ost_prof_life)

# --- 4. Заполнение навыков ---

# Работа с животными — животновод и фермер
if zhivotnovod: skills_dict["Работа с животными"].append(zhivotnovod)
if fermer: skills_dict["Работа с животными"].append(fermer)

# Экологическая ответственность — специалист по благоустройству растений и все лаборанты
if spec_blag: skills_dict["Экологическая ответственность"].append(spec_blag)
skills_dict["Экологическая ответственность"].extend(lab_assistants)

# Работа с растениями — все остальные
ost_prof_skill = [p for p in prof_names if p not in skills_dict["Работа с животными"] + skills_dict["Экологическая ответственность"]]
skills_dict["Работа с растениями"].extend(ost_prof_skill)

# --- 5. Функция для создания датафрейма ---

def dict_to_table(dct, key_name, value_name):
    data = []
    for k, v in dct.items():
        if v:
            data.append([k, ", ".join(sorted(set(v)))])
    return pd.DataFrame(data, columns=[key_name, value_name])

skills_df = dict_to_table(skills_dict, "Навык", "Профессии")
lifestyle_df = dict_to_table(lifestyle_dict, "Образ жизни", "Профессии")
sphere_df = dict_to_table(sphere_dict, "Сфера АПК", "Профессии")

# --- 6. Создание/замена листов в Google Sheets ---

def update_sheet(sheet, title, df):
    try:
        ws = sheet.worksheet(title)
        sheet.del_worksheet(ws)
    except gspread.exceptions.WorksheetNotFound:
        pass
    ws = sheet.add_worksheet(title=title, rows=str(len(df)+1), cols=str(len(df.columns)))
    ws.update([df.columns.values.tolist()] + df.values.tolist())

update_sheet(sheet, "Навыки", skills_df)
update_sheet(sheet, "Образ жизни", lifestyle_df)
update_sheet(sheet, "Сфера АПК", sphere_df)

print("Таблицы успешно обновлены по заданным правилам!")