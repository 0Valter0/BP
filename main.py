import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = '7690932396:AAGNxJh8bqw2OezD0soZukQVU1hXNiTRyBE'
bot = telebot.TeleBot(TOKEN)

SHEET_ID = '1Y-rOb3IHMi4yppzWvGN9eu4vOS1hVtXmy3W8Z_GwLmo'
MAIN_SHEET = 'Лист1'
SKILLS_SHEET = 'Навыки'
LIFESTYLE_SHEET = 'Образ жизни'
SPHERE_SHEET = 'Сфера АПК'

# Соответствие листов и их главных столбцов
SHEET_TO_COL = {
    SKILLS_SHEET: 'Навык',
    LIFESTYLE_SHEET: 'Образ жизни',
    SPHERE_SHEET: 'Сфера АПК'
}

scope = [
    "https://spreadsheets.google.com/feeds",
    'https://www.googleapis.com/auth/spreadsheets',
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gs_client = gspread.authorize(creds)

sheet = gs_client.open_by_key(SHEET_ID)
main_ws = sheet.worksheet(MAIN_SHEET)
skills_ws = sheet.worksheet(SKILLS_SHEET)
lifestyle_ws = sheet.worksheet(LIFESTYLE_SHEET)
sphere_ws = sheet.worksheet(SPHERE_SHEET)

COLUMNS = [
    ("Суть профессии", "Суть профессии"),
    ("Хватает ли специалистов на рынке", "Хватает ли специалистов на рынке"),
    ("Перспективы профессии", "Перспективы профессии"),
    ("Зар. плата", "Зар. плата"),
    ("Плюсы и минусы", "Плюсы и минусы"),
    ("Вузы для поступления", "Вузы для поступления"),
]

# Состояния пользователя (chat_id -> state)
user_state = {}
user_filter_data = {}

def get_professions():
    records = main_ws.get_all_records()
    return [row['Профессия'] for row in records if row['Профессия']]

def get_profession_info(name):
    records = main_ws.get_all_records()
    for row in records:
        if row['Профессия'].strip().lower() == name.strip().lower():
            info_lines = []
            for title, col in COLUMNS:
                value = row.get(col, "").strip()
                info_lines.append(f"{title}: {value if value else '—'}")
            return "\n".join(info_lines)
    return 'Профессия не найдена.'

def get_filter_options(sheet):
    col_name = SHEET_TO_COL.get(sheet.title)
    records = sheet.get_all_records()
    return [row[col_name] for row in records if row[col_name]]

def get_professions_by_filter(sheet, filter_value):
    col_name = SHEET_TO_COL.get(sheet.title)
    records = sheet.get_all_records()
    for row in records:
        if row[col_name].strip().lower() == filter_value.strip().lower():
            profs = row['Профессии'].split(',') if row['Профессии'] else []
            return [p.strip() for p in profs]
    return []

def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Общий список профессий", "Фильтр")
    return markup

def filter_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Навыки", "Сфера АПК", "Образ жизни")
    markup.add("Назад")
    return markup

def back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Назад")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_state[message.chat.id] = "MAIN_MENU"
    bot.send_message(message.chat.id, "Привет! Я бот, который поможет узнать о профессиях.\nВыберите действие:", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "Общий список профессий")
def show_professions(message):
    user_state[message.chat.id] = "WAIT_PROFESSION"
    professions_list = "\n".join(get_professions())
    bot.send_message(message.chat.id, f"Список профессий:\n{professions_list}\n\nВведите название профессии для получения подробной информации.", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "Фильтр")
def filter_menu(message):
    user_state[message.chat.id] = "FILTER_MENU"
    bot.send_message(message.chat.id, "Выберите фильтр:", reply_markup=filter_menu_markup())

@bot.message_handler(func=lambda message: message.text in ["Навыки", "Сфера АПК", "Образ жизни"])
def filter_options(message):
    chat_id = message.chat.id
    filter_type = message.text
    user_state[chat_id] = f"FILTER_{filter_type.upper()}"
    # Получаем варианты фильтра
    if filter_type == "Навыки":
        options = get_filter_options(skills_ws)
    elif filter_type == "Сфера АПК":
        options = get_filter_options(sphere_ws)
    elif filter_type == "Образ жизни":
        options = get_filter_options(lifestyle_ws)
    else:
        options = []
    user_filter_data[chat_id] = {"filter_type": filter_type, "options": options}
    options_str = "\n".join(options)
    bot.send_message(chat_id, f"Варианты для фильтра '{filter_type}':\n{options_str}\n\nВведите один из них для просмотра профессий.", reply_markup=back_markup())

@bot.message_handler(func=lambda message: message.text == "Назад")
def go_back(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id, "MAIN_MENU")
    # Логика возврата по состоянию
    if state.startswith("FILTER_"):
        user_state[chat_id] = "FILTER_MENU"
        bot.send_message(chat_id, "Выберите фильтр:", reply_markup=filter_menu_markup())
    elif state == "FILTER_MENU":
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "Главное меню:", reply_markup=main_menu_markup())
    else:
        user_state[chat_id] = "MAIN_MENU"
        bot.send_message(chat_id, "Главное меню:", reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: True)
def text_handler(message):
    chat_id = message.chat.id
    state = user_state.get(chat_id, "MAIN_MENU")
    # 1. Проверяем, был ли выбран фильтр и ожидается ввод значения фильтра
    if state.startswith("FILTER_"):
        filter_type = user_filter_data.get(chat_id, {}).get("filter_type")
        options = user_filter_data.get(chat_id, {}).get("options", [])
        value = message.text.strip()
        if value not in options:
            bot.send_message(chat_id, "Пожалуйста, введите один из предложенных вариантов фильтра или нажмите 'Назад'.", reply_markup=back_markup())
            return
        # Получаем профессии по фильтру
        if filter_type == "Навыки":
            profs = get_professions_by_filter(skills_ws, value)
        elif filter_type == "Сфера АПК":
            profs = get_professions_by_filter(sphere_ws, value)
        elif filter_type == "Образ жизни":
            profs = get_professions_by_filter(lifestyle_ws, value)
        else:
            profs = []
        user_state[chat_id] = "FILTERED_PROFESSIONS"
        user_filter_data[chat_id]["filtered_professions"] = profs
        profs_str = "\n".join(profs) if profs else "Нет профессий по выбранному фильтру."
        bot.send_message(chat_id, f"Профессии по фильтру '{value}':\n{profs_str}\n\nВведите профессию из этого списка для подробной информации или нажмите 'Назад'.", reply_markup=back_markup())
        return
    # 2. Если ждем подробную информацию о профессии из фильтрованного списка
    if state == "FILTERED_PROFESSIONS":
        profs = user_filter_data.get(chat_id, {}).get("filtered_professions", [])
        if message.text.strip() not in profs:
            bot.send_message(chat_id, "Пожалуйста, введите профессию из предложенного списка или нажмите 'Назад'.", reply_markup=back_markup())
            return
        info = get_profession_info(message.text)
        bot.send_message(chat_id, f"Информация о профессии {message.text}:\n{info}", reply_markup=back_markup())
        return
    # 3. Если ждем подробную информацию о профессии из полного списка
    if state == "WAIT_PROFESSION":
        professions = get_professions()
        if message.text.strip() not in professions:
            bot.send_message(chat_id, "Пожалуйста, введите профессию из полного списка или выберите действие.", reply_markup=main_menu_markup())
            return
        info = get_profession_info(message.text)
        bot.send_message(chat_id, f"Информация о профессии {message.text}:\n{info}", reply_markup=main_menu_markup())
        return
    # 4. По умолчанию — повтор главного меню
    user_state[chat_id] = "MAIN_MENU"
    bot.send_message(chat_id, "Пожалуйста, выберите действие с помощью кнопок.", reply_markup=main_menu_markup())

if __name__ == "__main__":
    bot.polling(none_stop=True)

print('hello')