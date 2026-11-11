import gspread
import os
import json
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def add_lead_to_sheet(lead_data):
    try:
        # Проверяем, запущены ли мы на Railway (там ключ в переменной) или локально (в файле)
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        
        if creds_json:
            # Для Railway
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            # Для локального запуска (читает файл credentials.json из папки)
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

        client = gspread.authorize(creds)

        # ВСТАВЬ СЮДА СВОЙ ID ТАБЛИЦЫ
        SHEET_ID = "1YtJCmNQpIwoGVffTnELujznfrEyqT2WCZfapyNqv0Zc"
        
        sheet = client.open_by_key(SHEET_ID).sheet1
        sheet.append_row(lead_data)
        print(f"Заявка добавлена в Google Sheets: {lead_data}")

    except Exception as e:
        print(f"Ошибка при записи в Google Sheets: {e}")