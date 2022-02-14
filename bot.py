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


# получаем номер последнего урока чтобы

class Form(StatesGroup):
    """
    Класс состояний для реализации конечных автоматов
    """
    waiting_for_name = State()
    waiting_for_answer = State()
    finished = State()
    waiting_check=State()


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
        await Form.waiting_for_answer.set()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
        await message.answer("Хотите продолжить учебу?", reply_markup=keyboard)

    else:
        await Form.waiting_for_name.set()
        await message.answer("Добро пожаловать! Как вас зовут?")


@dp.message_handler(state=Form.waiting_for_answer)
async def send_answer(message: types.CallbackQuery, state: FSMContext):
    """
    Отправляет вопрос ученику
    """
    sql_request = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER, EXERCISE_ID, LESSON 
                   FROM public.exercises
                   JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                   WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    keyboard = types.InlineKeyboardMarkup()
    # задаем глобальные перемнные для уменьшения количества sql запросов
    global name, right_answer, lesson, exercise_id
    name, question, choices, right_answer, exercise_id, lesson = [x for x in pupil_info[0:6]]
    choices += right_answer
    choices = choices.split(';')
    await message.answer(question)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*choices)
    await message.answer(choices, reply_markup=keyboard)
    await Form.waiting_check.set()


@dp.message_handler(state=Form.waiting_check)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ
    """
    if message.text == right_answer:

        await message.answer(f"Верно, Красава {name}!", reply_markup=types.ReplyKeyboardRemove())
        sql_request = """SELECT MAX(EXERCISE_ID) FROM public.exercises
                                        GROUP BY LESSON
                                        HAVING LESSON = %s"""
        last_exersize = sql_conn(sql_request, (lesson,))
        if last_exersize[0] != exercise_id:
            sql_request = """ UPDATE pupils 
                                SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                                WHERE pupil_id = %s"""
            sql_conn(sql_request, (message.from_user.id,))
            await Form.waiting_for_answer.set()
        else:
            # получаем номер последнего урока и проверяем есть ли еще уроки
            sql_request = """SELECT MAX(LESSON) FROM public.exercises"""
            last_lesson = sql_conn(sql_request)
            if last_lesson[0] != lesson:
                sql_request = """ UPDATE pupils 
                                                SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                                                WHERE pupil_id = %s"""
                sql_conn(sql_request, (message.from_user.id,))
                await Form.waiting_for_answer.set()
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="send_answer"))
                await message.answer(f"Молодец! Урок {lesson} успешно пройден\n Готовы перейти к следующему уроку?",
                                     reply_markup=keyboard)
            else:
                await state.finish()
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(text="Да", callback_data="reset_user"))
                await message.answer(
                    "Поздравляю вы закончили наш курс, надеюсь вамв понравилось!!!\nХотите сбросить прогресс и начать "
                    "курс заново?",
                    reply_markup=keyboard)
    else:
        await message.answer(f"Неверно, ну ты и дон-дон {name}!")


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


@dp.callback_query_handler(state=Form.finished)
@dp.callback_query_handler(text="reset_user")
async def reset_user(call: types.CallbackQuery, state: FSMContext):
    sql_request = """ UPDATE pupils 
                        SET CUR_EXERCISE = 1
                        WHERE pupil_id = %s"""
    sql_conn(sql_request, (call.from_user.id,))
    await call.message.answer("Нажмите /start чтобы начать учебу")


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
