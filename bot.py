import asyncio
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import phonenumbers
import datetime
import database

# Загружаем настройки из файла .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS").split(",")]
BUSINESS_NAME = os.getenv("BUSINESS_NAME")
BUSINESS_CONTACT = os.getenv("BUSINESS_CONTACT")

# Включаем логирование (чтобы видеть, что происходит)
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Состояния (шаги), которые проходит клиент
class LeadForm(StatesGroup):
    service = State()
    name = State()
    phone = State()
    comment = State()

# Кнопки выбора услуг
def get_services_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Стрижка", callback_data="svc:Стрижка")],
        [InlineKeyboardButton(text="Борода", callback_data="svc:Борода")],
        [InlineKeyboardButton(text="Стрижка + борода", callback_data="svc:Комбо")]
    ])

def get_date_kb():
    today = datetime.date.today()
    dates = [today + datetime.timedelta(days=i) for i in range(7)]
    keyboard = []
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    for i, d in enumerate(dates):
        day_str = d.strftime("%d.%m")
        wd = weekdays[d.weekday()]
        btn_text = f"{day_str} ({wd})"
        if i == 0: btn_text = f"Сегодня, {day_str}"
        elif i == 1: btn_text = f"Завтра, {day_str}"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"date:{d.isoformat()}")])
    
    # Кнопки навигации
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_phone_from_date")])
    keyboard.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_lead")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_time_kb():
    hours = [f"{h:02d}:00" for h in range(10, 20)]
    keyboard = []
    for i in range(0, len(hours), 3):
        row = [InlineKeyboardButton(text=h, callback_data=f"time:{h}") for h in hours[i:i+3]]
        keyboard.append(row)
    # Кнопки навигации
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_date")])
    keyboard.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_lead")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Главное меню
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Оставить заявку", callback_data="lead_start")]
    ])

def get_nav_kb(back_callback=None):
    buttons = []
    if back_callback:
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)])
    buttons.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_lead")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"👋 Добро пожаловать в {BUSINESS_NAME}!\n\n"
        f"Здесь вы можете оставить заявку. Мы свяжемся с вами.",
        reply_markup=get_main_kb()
    )

# Нажатие на кнопку "Оставить заявку"
@dp.callback_query(F.data == "lead_start")
async def start_lead(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text("Выберите услугу:", reply_markup=get_services_kb())
    await state.set_state(LeadForm.service)
    await c.answer()

# Клиент выбрал услугу
@dp.callback_query(LeadForm.service, F.data.startswith("svc:"))
async def process_service(c: CallbackQuery, state: FSMContext):
    service = c.data.split(":")[1]
    await state.update_data(service=service)
    await c.message.edit_text(f"Вы выбрали: {service}\n\nКак вас зовут?", reply_markup=get_nav_kb("back_to_service"))
    await state.set_state(LeadForm.name)
    await c.answer()

# Клиент ввел имя
@dp.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте ваше имя текстом.")
        return
        
    name_text = message.text.strip()
    
    # Проверка 1: Имя не слишком короткое
    if len(name_text) < 2:
        await message.answer("Имя слишком короткое. Пожалуйста, введите ваше имя.")
        return
        
    # Проверка 2: В имени должны быть буквы (а не только цифры)
    # Мы проверяем, есть ли хотя бы одна буква в тексте
    if not any(char.isalpha() for char in name_text):
        await message.answer("Имя должно содержать буквы. Пожалуйста, введите ваше имя (например, Иван).")
        return
        
    await state.update_data(name=name_text)
    await message.answer("Отлично! Теперь введите ваш номер телефона для связи:", reply_markup=get_nav_kb("back_to_service"))
    await state.set_state(LeadForm.phone)

# Клиент ввел телефон
@dp.message(LeadForm.phone)
async def process_phone(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, отправьте номер телефона текстом.")
        return
        
    raw_text = message.text.strip()
    digits = "".join(filter(str.isdigit, raw_text)) # Оставляем только цифры

    try:
        # Если номер начинается с плюса, парсим как есть
        if raw_text.startswith("+"):
            parsed_number = phonenumbers.parse(raw_text, None)
        
        # Если написали с 80 (например, 8029...), меняем на +7 (или +375, если хотите)
        elif digits.startswith("80"):
            parsed_number = phonenumbers.parse("+7" + digits[2:], None)
            
        # Если написали код страны без плюса (375..., 7..., 234...)
        elif digits.startswith(("375", "7", "234")):
            parsed_number = phonenumbers.parse("+" + digits, None)
            
        # Если написали просто местный номер (например, 291234567)
        else:
            # Указываем регион по умолчанию (BY - Беларусь, можно поменять на RU или KZ)
            parsed_number = phonenumbers.parse(digits, "BY")
            
        # Проверяем, существует ли такой номер в мире
        if not phonenumbers.is_valid_number(parsed_number):
            raise ValueError
            
        # Делаем номер красивым (международный формат)
        formatted_phone = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        
        await state.update_data(phone=formatted_phone)
        await message.answer("Отлично! Выберите удобную дату для записи:", reply_markup=get_date_kb())
        await state.set_state(LeadForm.comment) 

    except phonenumbers.NumberParseException:
        await message.answer("Не похоже на номер телефона. Пожалуйста, введите номер, например:\n+375291234567 (Беларусь)\n+79101234567 (Россия)")
        return
    except ValueError:
        await message.answer("Такого номера не существует. Пожалуйста, проверьте номер и введите снова.")
        return

# Обработка выбора даты
@dp.callback_query(F.data.startswith("date:"), LeadForm.comment)
async def process_date(c: CallbackQuery, state: FSMContext):
    chosen_date = c.data.split(":", 1)[1] # Получаем дату в формате 2026-11-11
    await state.update_data(chosen_date=chosen_date)
    # Показываем кнопки времени
    await c.message.edit_text(f"Дата: {chosen_date}\n\nТеперь выберите удобное время:", reply_markup=get_time_kb())
    await c.answer()

# Обработка выбора времени
@dp.callback_query(F.data.startswith("time:"), LeadForm.comment)
async def process_time(c: CallbackQuery, state: FSMContext):
    chosen_time = c.data.split(":", 1)[1] # <--- ИСПРАВЛЕНИЕ БАГА: берем "18:00" целиком!
    data = await state.get_data()
    chosen_date = data.get('chosen_date', 'Дата не указана')
    
    # Склеиваем дату и время для сохранения
    full_datetime = f"{chosen_date} в {chosen_time}"
    await state.update_data(comment=full_datetime)
    
    # Заново получаем данные (уже с комментарием)
    final_data = await state.get_data()
    await state.clear()

    # Сохраняем в базу
    lead_id = database.add_lead(
        user_id=c.from_user.id,
        username=c.from_user.username,
        service=final_data['service'],
        name=final_data['name'],
        phone=final_data['phone'],
        comment=final_data['comment']
    )

    # Пишем клиенту
    await c.message.edit_text(
        f"✅ Спасибо, {final_data['name']}! Ваша заявка №{lead_id} принята на {full_datetime}.\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Наш контакт: {BUSINESS_CONTACT}"
    )

    # Отправляем уведомление тебе (админу)
    admin_text = (
        f"🔔 Новая заявка №{lead_id}!\n\n"
        f"Услуга: {final_data['service']}\n"
        f"Имя: {final_data['name']}\n"
        f"Телефон: {final_data['phone']}\n"
        f"Дата и время: {full_datetime}\n"
        f"От: @{c.from_user.username or 'нет_юзернейма'}"
    )
    
    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Взять в работу", callback_data=f"adm_status:{lead_id}:in_progress"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_status:{lead_id}:cancelled")
        ]
    ])

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=admin_kb)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")
            
    await c.answer()

# Возврат с шага времени на шаг выбора даты
@dp.callback_query(F.data == "back_to_date", LeadForm.comment)
async def back_to_date(c: CallbackQuery, state: FSMContext):
    await c.message.edit_text(
        "Выберите удобную дату для записи:", 
        reply_markup=get_date_kb()
    )
    await c.answer()

# Возврат с шага выбора даты на шаг ввода телефона
@dp.callback_query(F.data == "back_to_phone_from_date", LeadForm.comment)
async def back_to_phone_from_date(c: CallbackQuery, state: FSMContext):
    await state.set_state(LeadForm.phone)
    # Используем ту кнопку отмены, которая у тебя уже есть в коде
    await c.message.edit_text(
        "Введите ваш номер телефона для связи:", 
        reply_markup=get_nav_kb()
    )
    await c.answer()

# Команда /leads (только для админа)
@dp.message(Command("leads"))
async def cmd_leads(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    leads = database.get_recent_leads(10)
    if not leads:
        await message.answer("Заявок пока нет.")
        return

    text = "📋 Последние 10 заявок:\n\n"
    for lead in leads:
        text += f"№{lead[0]} | {lead[1]} | {lead[2]} | {lead[3]} | {lead[4]}\n"
    
    await message.answer(text)

@dp.callback_query(F.data == "cancel_lead")
async def cancel_lead(c: CallbackQuery, state: FSMContext):
    await state.clear()
    await c.message.edit_text(
        "❌ Заявка отменена. Вы вернулись в главное меню.",
        reply_markup=get_main_kb()
    )
    await c.answer()

@dp.callback_query(F.data == "back_to_service")
async def back_to_service(c: CallbackQuery, state: FSMContext):
    # Сбрасываем состояние на выбор услуги
    await state.set_state(LeadForm.service)
    await c.message.edit_text("Выберите услугу:", reply_markup=get_services_kb())
    await c.answer()

@dp.callback_query(F.data == "back_to_name")
async def back_to_name(c: CallbackQuery, state: FSMContext):
    # Возвращаемся к вводу имени
    await state.set_state(LeadForm.name)
    await c.message.edit_text("Как вас зовут?", reply_markup=get_nav_kb("back_to_service"))
    await c.answer()

@dp.callback_query(F.data == "back_to_phone")
async def back_to_phone(c: CallbackQuery, state: FSMContext):
    # Возвращаемся к вводу телефона
    await state.set_state(LeadForm.phone)
    await c.message.edit_text("Введите ваш номер телефона для связи:", reply_markup=get_nav_kb("back_to_name"))
    await c.answer()

# --- АДМИН ПАНЕЛЬ ---

def get_admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🆕 Новые заявки", callback_data="adm_view:new")],
        [InlineKeyboardButton(text="⏳ В работе", callback_data="adm_view:in_progress")],
        [InlineKeyboardButton(text="✅ Завершенные", callback_data="adm_view:done")]
    ])

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("🛠 <b>Панель управления заявками</b>\nВыберите категорию:", reply_markup=get_admin_menu_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("adm_view:"))
async def view_leads(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        return
        
    status = c.data.split(":")[1]
    status_names = {"new": "🆕 Новые", "in_progress": "⏳ В работе", "done": "✅ Завершенные"}
    leads = database.get_leads_by_status(status, limit=5)
    
    if not leads:
        await c.message.edit_text(f"{status_names[status]}\n\nЗдесь пока пусто.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="adm_menu")]]), parse_mode="HTML")
        return
        
    await c.message.edit_text(f"{status_names[status]} (последние 5):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data="adm_menu")]]))
    
    for lead in leads:
        lead_id, date, service, name, phone, comment, username = lead
        
        kb_buttons = []
        if status == "new":
            kb_buttons.append([InlineKeyboardButton(text="✅ В работу", callback_data=f"adm_status:{lead_id}:in_progress"), InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_status:{lead_id}:cancelled")])
        elif status == "in_progress":
            kb_buttons.append([InlineKeyboardButton(text="🏁 Завершить", callback_data=f"adm_status:{lead_id}:done")])
            
        kb = InlineKeyboardMarkup(inline_keyboard=kb_buttons) if kb_buttons else None
        
        text = (f"<b>Заявка №{lead_id}</b> ({date})\n"
                f"Услуга: {service}\n"
                f"Имя: {name}\n"
                f"Телефон: {phone}\n"
                f"Комментарий: {comment}\n"
                f"От: @{username or 'скрыт'}")
        await c.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data == "adm_menu")
async def back_to_adm_menu(c: CallbackQuery):
    await c.message.edit_text("🛠 <b>Панель управления заявками</b>\nВыберите категорию:", reply_markup=get_admin_menu_kb())
    await c.answer()

@dp.callback_query(F.data.startswith("adm_status:"))
async def change_status(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        return
        
    _, lead_id, new_status = c.data.split(":")
    lead_id = int(lead_id)
    
    database.update_lead_status(lead_id, new_status)
    
    new_text = c.message.text + f"\n\n🔄 <b>Статус изменен на: {new_status}</b>"
    await c.message.edit_text(new_text, reply_markup=None, parse_mode="HTML") 
    await c.answer("Статус обновлен!")

# Запуск бота
async def main():
    database.init_db()
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())