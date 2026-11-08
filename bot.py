import asyncio
import os
import logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

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

# Главное меню
def get_main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Оставить заявку", callback_data="lead_start")]
    ])

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
    await c.message.edit_text(f"Вы выбрали: {service}\n\nКак вас зовут?")
    await state.set_state(LeadForm.name)
    await c.answer()

# Клиент ввел имя
@dp.message(LeadForm.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Отлично! Теперь введите ваш номер телефона для связи:")
    await state.set_state(LeadForm.phone)

# Клиент ввел телефон
@dp.message(LeadForm.phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Есть ли комментарий или удобное время? (Если нет, напишите 'Нет')")
    await state.set_state(LeadForm.comment)

# Клиент ввел комментарий (финал)
@dp.message(LeadForm.comment)
async def process_comment(message: Message, state: FSMContext):
    await state.update_data(comment=message.text)
    data = await state.get_data()
    await state.clear()

    # Сохраняем в базу
    lead_id = database.add_lead(
        user_id=message.from_user.id,
        username=message.from_user.username,
        service=data['service'],
        name=data['name'],
        phone=data['phone'],
        comment=data['comment']
    )

    # Пишем клиенту
    await message.answer(
        f"✅ Спасибо, {data['name']}! Ваша заявка №{lead_id} принята.\n"
        f"Мы свяжемся с вами в ближайшее время.\n"
        f"Наш контакт: {BUSINESS_CONTACT}",
        reply_markup=get_main_kb()
    )

    # Отправляем уведомление тебе (админу)
    admin_text = (
        f"🔔 Новая заявка №{lead_id}!\n\n"
        f"Услуга: {data['service']}\n"
        f"Имя: {data['name']}\n"
        f"Телефон: {data['phone']}\n"
        f"Комментарий: {data['comment']}\n"
        f"От: @{message.from_user.username or 'нет_юзернейма'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу {admin_id}: {e}")

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

# Запуск бота
async def main():
    database.init_db()
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())