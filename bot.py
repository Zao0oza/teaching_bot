from asyncio import sleep

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from os import getenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# подгружаем токены и пароли из окружения
bot_token = getenv("BOT_TOKEN")
if not bot_token:
    exit("Error: no token provided")
postgress_password = getenv("postgress_password")
if not bot_token:
    exit("Error: no postgress_password provided")

# Объект бота
bot = Bot(token=bot_token)
# Диспетчер для бота
dp = Dispatcher(bot, storage=MemoryStorage())


def sql_conn(sql_request, values: tuple = None):
    '''
    Принимает в себя sql запрос и перемнные,
    Соединяется с Бд
    Возвращает результат
    '''
    connection = psycopg2.connect(user="postgres",
                                  # пароль, который указали при установке PostgreSQL
                                  password=postgress_password,
                                  host="127.0.0.1",
                                  port="5433",
                                  database="teaching_bot_db")
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # Курсор для выполнения операций с базой данных
    cursor = connection.cursor()
    cursor.execute(sql_request, values)
    # Заглушка на случай если sql запрос ничего не возвращает
    try:
        sql_result = cursor.fetchone()
    except:
        sql_result = None
    cursor.close()
    connection.close()
    return sql_result


class Form(StatesGroup):
    """
    Класс состояний для реализации конечных автоматов
    """
    waiting_for_name = State()
    waiting_for_answer = State()
    finished = State()


@dp.message_handler(commands="start")
async def cmd_start(message: types.Message):
    """
    Комнада start проверяет по id есть ли ученик в БД
    Если есть, то предложит продолжить учебу,
    Нет, спросит имя ученика и перейдет к добавлению нового ученика в БД
    """
    sql_request = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER 
                FROM public.exercises
                JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    if pupil_info:
        await message.answer(f"С возвращением {pupil_info[0]}!", reply_markup=types.ReplyKeyboardRemove())
        await sleep(1)
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
        await message.answer("Хотите продолжить учебу?", reply_markup=keyboard)
    else:
        await Form.waiting_for_name.set()
        await message.answer("Добро пожаловать! Как вас зовут?")


@dp.callback_query_handler(text="send_answer")
async def send_answer(call: types.CallbackQuery):
    """
    Отправляет вопрос ученику
    """
    sql_request = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER 
                   FROM public.exercises
                   JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                   WHERE pupil_id =%s """
    try:
        pupil_info = sql_conn(sql_request, (call.from_user.id,))
    except:
        await Form.finshed.set()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="reset_user"))
        await call.answer(
            "Поздравляю вы закончили наш курс, надеюсь вамвпонравилось!!!/nХотите сбросить прогресс и начать курс заново?",
            reply_markup=keyboard)

    # задаем глобальные перемнные для уменьшения количества sql запросов
    global name, question, choices, right_answer
    name, question, choices, right_answer = [x for x in pupil_info[0:4]]
    choices = choices.split(',')
    await call.message.answer(question)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*choices)
    await call.message.answer(choices, reply_markup=keyboard)
    await Form.waiting_for_answer.set()


@dp.message_handler(state=Form.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ
    """
    try:
        if message.text == right_answer:
            await message.answer(f"Верно, Красава {name}!", reply_markup=types.ReplyKeyboardRemove())
            sql_request = """ UPDATE pupils 
                            SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                            WHERE pupil_id = %s"""
            pupil_info = sql_conn(sql_request, (message.from_user.id,))
            await state.finish()
            await sleep(1)
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
            await message.answer("Следующее задание", reply_markup=keyboard)
        else:
            await message.answer(f"Неверно, ну ты и дон-дон {name}!")
    except:
        await state.finish()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="reset_user"))
        await message.answer(
            "Поздравляю вы закончили наш курс, надеюсь вамвпонравилось!!!/nХотите сбросить прогресс и начать курс заново?",
            reply_markup=keyboard)


@dp.message_handler(state=Form.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Создает нового ученика
    """
    sql_request = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
    sql_conn(sql_request, (message.from_user.id, message.text,))
    await state.finish()
    sql_request = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER 
                   FROM public.exercises
                   JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                   WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    await message.answer(f"Добро пожаловать {pupil_info[0]}!")
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
    await message.answer("Хотите начать учебу?", reply_markup=keyboard)


@dp.callback_query_handler(text="reset_user")
async def reset_user(call: types.Message, state: FSMContext):
    sql_request = """ UPDATE pupils 
                        SET CUR_EXERCISE = 1
                        WHERE pupil_id = %s"""
    sql_conn(sql_request, (call.from_user.id,))
    await call.message.answer("Нажмите /start чтобы начать учебу")


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
