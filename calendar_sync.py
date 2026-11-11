import os
import json
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def add_event_to_calendar(date_str, time_str, name, phone, service):
    try:
        # Авторизация
        creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if creds_json:
            creds_dict = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

        service_api = build('calendar', 'v3', credentials=creds)

        # ВСТАВЬ СЮДА СВОЙ ID КАЛЕНДАРЯ (тот, что ты нашел)
        CALENDAR_ID = "alexej.kuzmitskij3748@gmail.com"

        # Формируем время (длительность 1 час)
        start_datetime = f"{date_str}T{time_str}:00+03:00" 
        end_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") + datetime.timedelta(hours=1)
        end_datetime = end_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")

        event = {
            'summary': f'{service} - {name}',
            'description': f'Телефон: {phone}\nУслуга: {service}',
            'start': {'dateTime': start_datetime, 'timeZone': 'Europe/Minsk'},
            'end': {'dateTime': end_datetime, 'timeZone': 'Europe/Minsk'},
        }

        service_api.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"Событие добавлено в календарь: {name} на {date_str} {time_str}")

    except Exception as e:
        print(f"Ошибка при записи в Календарь: {e}")