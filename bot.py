from asyncio import sleep
from random import shuffle

from aiogram.dispatcher.filters import Text

from passwords import *
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from os import getenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# подгружаем токены и пароли из окружения
# Объект бота
bot = Bot(token=bot_token)
# Диспетчер для бота
storage = MongoStorage(host='localhost', port=27017, db_name='course_bot_db')
dp = Dispatcher(bot, storage=storage)


def sql_conn(sql_request, values: tuple = None):
    '''
    Принимает в себя sql запрос и перемнные,
    Соединяется с Бд
    Возвращает результат
    '''
    connection = psycopg2.connect(user="postgres",
                                  # пароль, который указали при установке PostgreSQL
                                  password=password_bd,
                                  host="127.0.0.1",
                                  port="5433",
                                  database="course_bot_db")
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # Курсор для выполнения операций с базой данных
    cursor = connection.cursor()
    cursor.execute(sql_request, values)
    # Заглушка на случай если sql запрос ничего не возвращает
    try:
        sql_result = cursor.fetchall()
    except:
        sql_result = None
    finally:
        cursor.close()
        connection.close()
    return sql_result


# получаем номер последнего урока чтобы

class Form(StatesGroup):
    """
    Класс состояний для реализации конечных автоматов
    """
    name = State()
    lesson = State()
    answer = State()
    finished = State()
    waiting_check = State()
    course = State()


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

    sql_request = """SELECT PUPIL_NAME, cur_course
                FROM public.pupils
                WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    if pupil_info:
        print(pupil_info)
        if pupil_info[0][1]:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="Перейти в меню курсов",
                callback_data="course_menu"))
            keyboard.add(types.InlineKeyboardButton(
                text=f"продолжить учебу в {pupil_info[0][1]}",
                callback_data="lesson_" + pupil_info[0][1]))
            await message.answer(
                f"Здравствуйте {pupil_info[0][0]}!\n Хотите продолжить учебу в {pupil_info[0][1]} или выбрать другой курс?",
                reply_markup=keyboard)
        else:
            sql_request = """SELECT COURSE_NAME 
                            FROM public.course
                            """
            course_info = sql_conn(sql_request)
            keyboard = types.InlineKeyboardMarkup()
            for course in course_info:
                keyboard.add(types.InlineKeyboardButton(
                    text=course[0],
                    callback_data='course_' + course[0]))
            await message.answer(
                f"Здравствуйте {pupil_info[0][0]}!\n Выберите интересующий вас курс",
                reply_markup=keyboard)
    else:
        await Form.name.set()
        await message.answer("Добро пожаловать! Как вас зовут?")


@dp.callback_query_handler(state='*', text='course_menu')
async def course_menu(call: types.CallbackQuery):
    sql_request = """SELECT PUPIL_NAME, cur_course
                    FROM public.pupils
                    WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (call.message.chat.id,))
    sql_request = """SELECT COURSE_NAME 
                    FROM public.course
                    """
    course_info = sql_conn(sql_request)
    keyboard = types.InlineKeyboardMarkup()
    for course in course_info:
        keyboard.add(types.InlineKeyboardButton(
            text=course[0],
            callback_data='course_' + course[0]))
    if pupil_info[0][1]:
        keyboard.add(types.InlineKeyboardButton(
            text=f"продолжить учебу в {pupil_info[0][1]}",
            callback_data="create_" + pupil_info[0][1]))
        await call.message.answer(
            f"Здравствуйте {pupil_info[0][0]}!\n Хотите продолжить учебу в {pupil_info[0][1]} или выбрать другой курс?",
            reply_markup=keyboard)
    else:
        await call.message.answer(
            f"Здравствуйте {pupil_info[0][0]}!\n Выберите интересующий вас курс",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="course_"), state='*')
async def course_detailed(call: types.CallbackQuery):
    sql_request = """SELECT COURSE_NAME, COURSE_AUTHOR, COURSE_DESCRIPTION, COURSE_IMAGE
                    FROM course WHERE COURSE_NAME=%s
                    """
    course_info = sql_conn(sql_request, (call.data[7:],))[0]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text=f"Начать учебу в {call.data[7:]}",
        callback_data="create_" + call.data[7:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Назад",
        callback_data="course_menu"))
    if course_info[3]:
        await call.message.answer_photo(types.InputFile(course_info[3]), caption=(f"Название: {course_info[0]}\n"
                                                                                  f"Автор: {course_info[1]}\n"
                                                                                  f"Краткое орисание:\n{course_info[2]}"),
                                        reply_markup=keyboard)
    else:
        await call.message.answer(
            f"Название: {course_info[0]}\n"                                                                                  f"Автор: {course_info[1]}\n"                                                                                  f"Краткое орисание:\n{course_info[2]}",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="create_"), state='*', )
async def create_lesson(call: types.CallbackQuery, state: FSMContext):
    sql_request = """ SELECT CUR_EXERCISE FROM PUPIL_PROGRESS 
            WHERE PUPIL_ID = %s and COURSE_NAME=%s """
    pupil_progress = sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    if pupil_progress:
        await start_lesson(call, state)
    else:
        sql_request = """ SELECT MIN(EXERCISE_ID) FROM EXERCISES JOIN 
        lesson on lesson.lesson_id=exercises.lesson
         GROUP BY LESSON_NAME=%s """
        exercise = sql_conn(sql_request, (call.data[7:],))
        sql_request = """ INSERT INTO PUPIL_PROGRESS (PUPIL_ID, COURSE_NAME,CUR_EXERCISE) VALUES (%s, %s, %s) """
        sql_conn(sql_request, (call.message.chat.id, call.data[7:], exercise[0][0],))
        sql_request = """ UPDATE pupils SET CUR_COURSE = %s  
                        WHERE pupil_id = %s """
        sql_conn(sql_request, (call.data[7:], call.message.chat.id,))
        await start_lesson(call, state)


@dp.callback_query_handler(Text(startswith="lesson_"), state='*')
async def start_lesson(call: types.CallbackQuery, state: FSMContext = FSMContext):
    """ Оптравляет теорию ученику, сначала получает ее из БД, после сохраняет в словарь
        Снчаал посылает приветсвенные сообщения, после стартовую картинку если есть,
        после теорию в формате картинок
    """
    sql_request = """SELECT PUPIL_NAME, LESSON_NAME, START_MESSAGES, 
    END_MESSAGES, LESSON_ID FROM exercises JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id JOIN 
    lesson on lesson.lesson_id=exercises.lesson JOIN pupils on pupil_progress.pupil_id=pupils.pupil_id WHERE pupils.pupil_id =%s and pupil_progress.course_name=%s"""
    pupil_info = sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    async with state.proxy() as data:
        data['lesson'] = {keys: value for keys, value in
                          zip(['name', 'lesson_name', 'start_messages', 'end_messages', 'lesson_id'], pupil_info[0])}
        data['lesson']['course_name'] = call.data[7:]
        for mes in data['lesson']['start_messages']:
            await sleep(0.5)
            await call.message.answer(mes)
        sql_request = """SELECT IMAGE  
                           FROM IMAGES
                            WHERE LESSON = %s and START_IMAGE = TRUE"""
        images = sql_conn(sql_request, (data['lesson']['lesson_id'],))
        media = types.MediaGroup()
        ""
        while len(images) > 10:
            for image in images[:10]:
                media.attach_photo(types.InputFile(image[0]))
            await sleep(0.5)
            await call.message.answer_media_group(media=media)
            images = images[10:]
            media = types.MediaGroup()
        else:
            media = types.MediaGroup()
            for image in images:
                media.attach_photo(types.InputFile(image[0]))
            await sleep(0.5)
            await call.message.answer_media_group(media=media)
        sql_request = """SELECT IMAGE  
                           FROM IMAGES
                            WHERE LESSON = %s and START_IMAGE = FALSE"""
        images = sql_conn(sql_request, (data['lesson']['lesson_id'],))
        media = types.MediaGroup()
        '''
        Так как media_group не может посылать больше 10 сообщений за раз, 
        разбиваем сообщения на группы по 10
        '''
        while len(images) > 10:
            for image in images[:10]:
                media.attach_photo(types.InputFile(image[0]))
            await sleep(0.5)
            await call.message.answer_media_group(media=media)
            images = images[10:]
            media = types.MediaGroup()
        else:
            media = types.MediaGroup()
            for image in images:
                media.attach_photo(types.InputFile(image[0]))
            await sleep(0.5)
            await call.message.answer_media_group(media=media)
        await Form.answer.set()
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add('Да, готов проверить свои знания на практике!')
        await call.message.answer('Ну что, как успехи с нашей теорией? Ты все изучил?', reply_markup=keyboard)


@dp.message_handler(state=Form.answer, text=("Да", 'Да, готов проверить свои знания на практике!'))
async def send_answer(message: types.CallbackQuery, state: FSMContext):
    """
    Отправляет вопрос ученику
    """
    sql_request = """SELECT EXERCISE, CHOICES, RIGHT_ANSWER, EXERCISE_ID
        FROM public.exercises JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id  WHERE pupil_id =%s """
    exercise_info = sql_conn(sql_request, (message.from_user.id,))
    async with state.proxy() as data:
        data['answer'] = {keys: value for keys, value in
                          zip(['exercise', 'choices', 'right_answer', 'exercise_id'], exercise_info[0])}
        await Form.waiting_check.set()
        choices = data['answer']['choices']
        choices.append(data['answer']['right_answer'])
        shuffle(choices)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(*choices)
        for mes in data['answer']['exercise']:
            await sleep(0.5)
            await message.answer(mes, reply_markup=keyboard)


@dp.message_handler(state=Form.waiting_check)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ
    """
    async with state.proxy() as data:
        if message.text == data['answer']['right_answer']:
            await message.answer(f"Верно, Молодец {data['lesson']['name']}!", reply_markup=types.ReplyKeyboardRemove())
            sql_request = """SELECT EXERCISE_ID FROM public.exercises
                               WHERE LESSON = %s AND EXERCISE_ID>%s"""
            exersizes = sql_conn(sql_request, (data['lesson']['lesson_id'],
                                               data['answer']['exercise_id']))
            if exersizes:
                sql_request = """ UPDATE pupil_progress 
                                    SET CUR_EXERCISE = %s
                                    WHERE pupil_id = %s"""
                sql_conn(sql_request, (exersizes[0][0], message.from_user.id))
                await send_answer(message, state)
            else:
                # получаем номер последнего урока и проверяем есть ли еще уроки
                sql_request = """SELECT MAX(LESSON) FROM public.exercises"""
                last_lesson = sql_conn(sql_request)
                if last_lesson[0][0] != data['lesson']['lesson_id']:
                    sql_request = """UPDATE pupil_progress SET cur_exercise = (SELECT MIN(EXERCISE_ID) FROM public.exercises 
                    WHERE LESSON=%s), WHERE pupil_id = %s """
                    sql_conn(sql_request, (data['lesson']['lesson_id'] + 1, message.from_user.id))

                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    for mes in data['lesson']['end_messages']:
                        await message.answer(mes)
                    await Form.lesson.set()
                    keyboard.add('Да')
                    await message.answer(
                        "Нажмите да как только будете готовы к следующему уроку",
                        reply_markup=keyboard)
                else:
                    await Form.finished.set()
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(
                        text=f"Начать заново {data['lesson']['course_name']}",
                        callback_data="clear__" + data['lesson']['course_name']))
                    keyboard.add(types.InlineKeyboardButton(
                        text=f"В меню",
                        callback_data="course_menu"))
                    return await message.answer(
                        '''Поздравляю вы успешно закончили наш курс, 
                        надеюсь вам понравилось!!!
                        Хотите сбросить прогресс и начать курс заново?''',
                        reply_markup=keyboard)
        else:
            await message.answer(
                f"Неверно, {data['lesson']['name']}!\n Повтори материал и попробуй еще раз")


@dp.message_handler(state=Form.name)
async def process_name(message: types.Message, state: FSMContext):
    """
    Создает нового ученика
    """
    sql_request = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
    sql_conn(sql_request, (message.from_user.id, message.text,))
    await state.finish()
    sql_request = """SELECT PUPIL_NAME 
                   FROM pupils
                   WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    sql_request = """SELECT COURSE_NAME 
                                FROM public.course
                                """
    course_info = sql_conn(sql_request)
    keyboard = types.InlineKeyboardMarkup()
    for course in course_info:
        keyboard.add(types.InlineKeyboardButton(
            text=course[0],
            callback_data='course_' + course[0]))
    await message.answer(
        f"Добро пожаловать {pupil_info[0][0]}!\n Выберите интересующий вас курс",
        reply_markup=keyboard)

@dp.callback_query_handler(Text(startswith="clear__"), state='*')
async def reset_user(call: types.CallbackQuery, state: FSMContext):
    '''
    Сбрасывает прогресс ученика
    '''
    sql_request = """ DELETE FROM pupil_progress 
                    WHERE pupil_id = %s AND COURSE_NAME = %s"""
    sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    sql_request = """ UPDATE pupils SET CUR_COURSE = NULL  
                    WHERE pupil_id = %s """
    sql_conn(sql_request, (call.message.chat.id, ))
    await course_menu(call)


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
