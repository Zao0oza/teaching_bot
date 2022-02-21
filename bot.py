from asyncio import sleep

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from os import getenv
import psycopg2
from aiogram.types import BotCommand
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
storage = MongoStorage(host='localhost', port=27017, db_name='teaching_bot')
dp = Dispatcher(bot, storage=storage)


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
    name = State()
    answer = State()
    finished = State()
    waiting_check = State()


@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state='*', commands="start")
async def cmd_start(message: types.Message, state: FSMContext):
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
        await Form.answer.set()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add('Да')
        await message.answer(f"Здравствуйте {pupil_info[0]}!\n Готовы начать учится?", reply_markup=keyboard)

    else:
        await Form.name.set()
        await message.answer("Добро пожаловать! Как вас зовут?")


@dp.message_handler(state=Form.answer)
async def send_answer(message: types.CallbackQuery, state: FSMContext):
    print(message, state)
    """
    Отправляет вопрос ученику
    """
    sql_request = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER, EXERCISE_ID, LESSON 
                   FROM public.exercises
                   JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                   WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    name, question, choices, right_answer, exercise_id, lesson = [x for x in pupil_info[0:6]]
    async with state.proxy() as data:
        data['answer'] = {'name': name, 'right_answer': right_answer, 'lesson': lesson, 'exercise_id': exercise_id}
    choices += right_answer
    choices = choices.split(';')
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*choices)
    await message.answer(str(question)+'\n'+str(choices), reply_markup=keyboard)
    await Form.waiting_check.set()


@dp.message_handler(state=Form.waiting_check)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ
    """
    async with state.proxy() as data:
        if message.text == data['answer']['right_answer']:
            await message.answer(f"Верно, Красава {data['answer']['name']}!", reply_markup=types.ReplyKeyboardRemove())
            sql_request = """SELECT MAX(EXERCISE_ID) FROM public.exercises
                                            GROUP BY LESSON
                                            HAVING LESSON = %s"""
            last_exersize = sql_conn(sql_request, (data['answer']['lesson'],))
            if last_exersize[0] != data['answer']['exercise_id']:
                sql_request = """ UPDATE pupils 
                                    SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                                    WHERE pupil_id = %s"""
                sql_conn(sql_request, (message.from_user.id,))
                await send_answer(message, state)

            else:
                # получаем номер последнего урока и проверяем есть ли еще уроки
                sql_request = """SELECT MAX(LESSON) FROM public.exercises"""
                last_lesson = sql_conn(sql_request)
                if last_lesson[0] != data['answer']['lesson']:
                    sql_request = """ UPDATE pupils 
                                                    SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                                                    WHERE pupil_id = %s"""
                    sql_conn(sql_request, (message.from_user.id,))
                    await Form.answer.set()
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add('Да')
                    await message.answer(
                        f"Молодец! Урок {data['answer']['lesson']} успешно пройден\n Готовы перейти к следующему уроку?",
                        reply_markup=keyboard)
                else:
                    await Form.finished.set()
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    keyboard.add('Да')
                    return await message.answer(
                        '''Поздравляю вы успешно закончили наш курс, 
                        надеюсь вам понравилось!!!
                        Хотите сбросить прогресс и начать курс заново?''',
                        reply_markup=keyboard)
        else:
            await message.answer(f"Неверно, ну ты и дон-дон {data['answer']['name']}!\n Повтори материал и попробуй еще раз")

@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Создает нового ученика
    """
    sql_request = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
    sql_conn(sql_request, (message.from_user.id, message.text,))
    await state.finish()
    sql_request = """SELECT PUPIL_NAME 
                   FROM public.exercises
                   JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                   WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    await message.answer(f"Добро пожаловать {pupil_info[0]}!")
    await Form.answer.set()
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Да')
    await message.answer("Хотите начать учебу?", reply_markup=keyboard)


@dp.message_handler(text="Да", state=Form.finished)
async def reset_user(message: types.Message, state: FSMContext):
    '''
    Сбрасывает прогресс ученика
    '''
    sql_request = """ UPDATE pupils 
                        SET CUR_EXERCISE = 1
                        WHERE pupil_id = %s"""
    sql_conn(sql_request, (message.from_user.id,))
    await cmd_start(message, state)


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
