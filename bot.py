from asyncio import sleep

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from os import getenv
from main import *

# Объект бота
bot_token = getenv("BOT_TOKEN")
if not bot_token:
    exit("Error: no token provided")

bot = Bot(token=bot_token)
# Диспетчер для бота
dp = Dispatcher(bot, storage=MemoryStorage())


class Form(StatesGroup):
    """
    Класс состояний для реализации конечных автоматов
    """
    waiting_for_name = State()
    waiting_for_answer = State()


@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    """
    Комнада start проверяет по id есть ли ученик в БД
    Если есть, то предложит продолжить учебу,
    Нет, спросит имя ученика и перейдет к добавлению нового ученика в БД
    """
    pupil_info = get_pupil_from_db(message.from_user.id)
    if pupil_info:
        await message.answer(f"С возвращением {pupil_info[0]}!")
        await sleep(1)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
        await message.answer("Хотите продолжить учебу?", reply_markup=keyboard)
    else:
        await Form.waiting_for_name.set()
        await message.answer("Добро пожаловать! Как вас зовут?")


@dp.message_handler(state=Form.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ
    """
    if message.text == right_answer:
        await message.answer(f"Верно, Красава {name}!")
        update_progres(message.from_user.id)
        await state.finish()
        await sleep(1)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
        await message.answer("Следующее задание", reply_markup=keyboard)
    else:
        await message.answer(f"Неверно, ну ты и дон-дон {name}!")


@dp.message_handler(state=Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Создает нового ученика
    """
    pupil_to_db(message.from_user.id, message.text)
    await Form.next()
    pupil_info = get_pupil_from_db(message.from_user.id)
    await message.answer(f"Добро пожаловать {pupil_info[0]}!")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
    await message.answer("Хотите начать учебу?", reply_markup=keyboard)



@dp.callback_query_handler(text="send_answer")
async def send_answer(call: types.CallbackQuery):
    """
    Отправляет вопрос ученику
    """
    pupil_info = get_pupil_from_db(call.from_user.id)
    global name, question, choices, right_answer
    name, question, choices, right_answer = [x for x in pupil_info[0:4]]
    choices = choices.split(',')
    await call.message.answer(question)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*choices)
    await call.message.answer(choices, reply_markup=keyboard)
    await Form.waiting_for_answer.set()


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
