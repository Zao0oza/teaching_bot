import io
import os
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
    admin = State()
    course_new = State()
    theory_add = State()
    exercise = State()
    lesson_add = State()


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
    Если есть активгый курс предалагает продолжить его
    Если ученика нет в базе, спросит имя ученика и перейдет к добавлению нового ученика в БД
    """
    await state.finish()
    sql_request = """SELECT PUPIL_NAME, cur_course
                FROM public.pupils
                WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (message.from_user.id,))
    if pupil_info:
        async with state.proxy() as data:
            data['pupil_name'] = pupil_info[0][0]
        if pupil_info[0][1]:  # проверяет есть ли активные курсы у ученика
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="Перейти в меню курсов",
                callback_data="course_menu"))
            keyboard.add(types.InlineKeyboardButton(
                text=f"продолжить учебу в {pupil_info[0][1]}",
                callback_data="lesson_" + pupil_info[0][1]))
            await message.answer(
                f"Здравствуйте {data['pupil_name']}!\n Хотите продолжить учебу в {pupil_info[0][1]} или выбрать другой курс?",
                reply_markup=keyboard)
        else:  # отправляет доступные курсы
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


@dp.message_handler(state='*', commands='admin')
async def admin_menu(message: types.Message, state: FSMContext):
    await Form.admin.set()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text=f"Создать новый курс",
        callback_data='add_new'))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Назад",
        callback_data='course_menu'))
    await message.reply('Добро пожаловать в панель Админстратора.', reply_markup=keyboard)


@dp.callback_query_handler(state=Form.admin, text='add_new')
async def add_new_course(call: types.CallbackQuery):
    '''
    иницилизирует создание курса
    '''
    await call.message.answer('Вы находитесь в меню создания курса, внимательно следуйте интсрукциям в сообщениях')
    await Form.course_new.set()
    await call.message.answer('Введите название курса')


@dp.message_handler(state=Form.course_new, content_types=['photo', 'text'])
async def new_course_name(message: types.Message, state: FSMContext):
    '''
    Ввод краткого описания курса
    '''
    async with state.proxy() as course_dict:
        if 'course_name' not in course_dict:
            course_dict['course_name'] = message.text
            if 'course_author' and 'course_description' in course_dict:
                '''
                Для случая когда имя курса повторилось в бд
                '''
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(
                    text="Сохранить",
                    callback_data="new_theory"))
                keyboard.add(types.InlineKeyboardButton(
                    text=f"Изменить",
                    callback_data="reset"))
                if course_dict['course_image']:
                    await message.answer_photo(types.InputFile(course_dict['course_image']),
                                               caption=(f"Проверьте введенные данные\033[1m\n"
                                                        f"Название: {course_dict['course_name']}\n"
                                                        f"Автор: {course_dict['course_author']}\n"
                                                        f"Краткое описание:\n{course_dict['course_description']}"),
                                               reply_markup=keyboard)
                else:
                    await message.answer((f" <b>Проверьте введенные данные</b>\n\n"
                                          f"Название: {course_dict['course_name']}\n"
                                          f"Автор: {course_dict['course_author']}\n"
                                          f"Краткое орисание:\n{course_dict['course_description']}"),
                                         reply_markup=keyboard, parse_mode=types.ParseMode.HTML)
            else:
                await message.answer('Введите автора курса')
        else:
            if 'course_author' not in course_dict:
                course_dict['course_author'] = message.text
                await message.answer('Введите краткое описание курса')
            else:
                if 'course_description' not in course_dict:
                    course_dict['course_description'] = message.text
                    await message.answer(
                        'Если хотите добавить логотип курса отправьте его картинкой, если нет напишите нет')
                else:
                    if message.photo:
                        await message.photo[-1].download(
                            destination_file=course_dict['course_name'] + '\\' + course_dict[
                                'course_name'] + '.jpg')
                        course_dict['course_image'] = course_dict['course_name'] + '\\' + course_dict[
                            'course_name'] + '.jpg'
                    else:
                        course_dict['course_image'] = None
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(
                        text="Сохранить",
                        callback_data="save_course"))
                    keyboard.add(types.InlineKeyboardButton(
                        text=f"Изменить",
                        callback_data="reset_course"))
                    if course_dict['course_image']:
                        await message.answer_photo(types.InputFile(course_dict['course_image']),
                                                   caption=(f" <b>Проверьте введенные данные</b>\n\n"
                                                            f"Название: {course_dict['course_name']}\n"
                                                            f"Автор: {course_dict['course_author']}\n"
                                                            f"Краткое описание:\n{course_dict['course_description']}"),
                                                   parse_mode=types.ParseMode.HTML, reply_markup=keyboard)
                    else:
                        await message.answer((f" <b>Проверьте введенные данные</b>\n\n"
                                              f"Название: {course_dict['course_name']}\n"
                                              f"Автор: {course_dict['course_author']}\n"
                                              f"Краткое орисание:\n{course_dict['course_description']}"),
                                             reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(Text(startswith="reset"), state="*")
async def change_data(call: types.CallbackQuery, state: FSMContext):
    """Сбрасывает введенные данные"""
    async with state.proxy() as course_dict:
        if call.data[6:] == 'course':
            for key in ('course_name', 'course_author', 'course_description', 'course_image'):
                course_dict.pop(key, None)
            await Form.course_new.set()
            await call.message.answer('Введите название курса')
        if call.data[6:] == 'theory':
            for key in ('lesson', 'theory', 'end_message'):
                course_dict.pop(key, None)
            await Form.lesson_add.set()
            await call.message.answer('Введите название урока')


@dp.callback_query_handler(state=Form.course_new, text='save_course')
async def save_course(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        insert_query = """ INSERT INTO course (course_name,course_author,course_description, course_image ) VALUES (%s,%s,%s,%s)"""
        try:
            sql_conn(insert_query, (
                course_dict['course_name'], course_dict['course_author'], course_dict['course_description'],
                course_dict['course_image']))
            await Form.lesson_add.set()
            await call.message.answer('Введите название урока')
        except:
            del course_dict['course_name']
            await call.message.answer('Курc с таким названием уже существует, выберите другое название')


@dp.message_handler(state=Form.lesson_add, content_types=['text', 'photo', 'audio'])
async def new_lesson(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        if 'lesson' in course_dict:
            if message.text:
                course_dict['theory'].append(message.text)
            elif message.photo:
                await message.photo[-1].download(
                    destination_dir=course_dict['course_name'] + "\\" + course_dict['lesson'])
                course_dict['theory'].append(course_dict['course_name'] + '\\' + course_dict[
                    'lesson'] + '.jpg')
            elif message.audio:
                await message.audio[-1].download(
                    destination_dir=course_dict['course_name'] + "\\" + course_dict['lesson'])
                course_dict['theory'].append(course_dict['course_name'] + '\\' + course_dict[
                    'lesson'] + '.mp3')
            else:
                await message.answer('Недопустимый формат сообщения возможны текст,фото, и аудио')
        else:
            if message.text:
                course_dict['lesson'] = message.text
                course_dict['theory'] = []
                course_dict['course_image'] = []
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(types.InlineKeyboardButton(
                    text="готово",
                    callback_data="end_messages"))
                await message.answer(
                    "Теперь введите теорию, ее можно посылать текстом в картинках и и аудио,вы можете посылать ее несколькими сообщениями,они будут выводится последовательно, когда закончите с вводом ВСЕЙ теории нажмите готово",
                    reply_markup=keyboard)
            else:
                await message.answer('Недопустимый формат имени урока')


@dp.callback_query_handler(state=Form.lesson_add, text='end_messages')
async def state_end_messages(call: types.CallbackQuery, state: FSMContext):
    await Form.theory_add.set()
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="готово",
        callback_data="show_theory"))
    await call.message.answer('Добавьте сообщения которые будут выводится при успешном прохождения урока'
                              'вы можете посылать их несколькими сообщениями,они будут выводится последовательно, когда закончите ВСЕ сообщения нажмите готово',
                              reply_markup=keyboard)


@dp.message_handler(state=Form.theory_add, content_types=['text', 'photo', 'audio'])
async def add_end_message(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        if message.text:
            course_dict['end_message'].append(message.text)
        elif message.photo:
            await message.photo[-1].download(
                destination_dir=course_dict['course_name'] + "\\" + course_dict['lesson'] + "\\end_message")
            course_dict['end_message'].append(
                course_dict['course_name'] + '\\' + course_dict['lesson'] + "\\end_message" + '.jpg')
        elif message.audio:
            await message.audio[-1].download(
                destination_dir=course_dict['course_name'] + '\\' + course_dict['lesson'] + "\\end_message")
            course_dict['end_message'].append(
                course_dict['course_name'] + '\\' + course_dict['lesson'] + "\\end_message" + '.mp3')
        else:
            await message.answer('Недопустимый формат сообщения возможны текст,фото, и аудио')


@dp.callback_query_handler(state=[Form.theory_add, Form.theory_add], text='show_theory')
async def show_theory(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        for msg in course_dict['theory']:
            if os.path.exists(msg):
                if i < 10:
                    media.attach_photo(types.InputFile(msg))
                    i += 1
                else:
                    await  call.message.answer_media_group(media=media)
                    media = types.MediaGroup()
                    i = 0
                    await sleep(0.5)
            else:
                try:
                    await  call.message.answer_media_group(media=media)
                    media = types.MediaGroup()
                except:
                    pass
                await sleep(0.5)
                await call.message.answer(msg)
        try:
            await  call.message.answer_media_group(media=media)
        except:
            pass
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="Сохранить",
            callback_data="save_theory"))
        keyboard.add(types.InlineKeyboardButton(
            text=f"Изменить",
            callback_data="delete_theory"))
        await call.message.answer((
            f" <b>Проверьте введенные данные. При нажатия изменить сброситься вся теория и ее придется вводить заново!!</b >\n\n"
        ),
            reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(state=[Form.theory_add, Form.theory_add], text='delete_theory')
async def delete_theory(call: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Сохранить",
        callback_data="save_theory"))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Удалить",
        callback_data="reset_theory"))
    await call.message.answer("Вы уверены?", reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(state=Form.theory_add, text='save_theory')
async def save_theory(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        insert_data=[]
        for key in ( 'theory', 'end_message'):
            insert_data.append(course_dict.pop(key, None))
        insert_query = """ INSERT INTO lesson (LESSON_NAME, THEORY,end_message, COURSE_NAME ) VALUES (%s,%s,%s,%s)"""
        sql_conn(insert_query,
                 (course_dict['lesson'],insert_data[0],insert_data[1],course_dict['course_name']))
        await call.message.answer('Недопустимый формат сообщения возможны текст,фото, и аудио')


@dp.callback_query_handler(state='*', text='course_menu')
async def course_menu(call: types.CallbackQuery):
    '''
    Отвечает за курсы доступные в БД
    Выводит списки курсов, и предлагет продолжить текущий курс
    '''
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
    """
    Показывет детальную информацию о курсе
    Название, автора, краткое описание, логотип если есть
    """
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
    if course_info[3]:  # проверка есть ли лого
        await call.message.answer_photo(types.InputFile(course_info[3]),
                                        caption=(f"Название: {course_info[0]}\n"
                                                 f"Автор: {course_info[1]}\n"
                                                 f"Краткое описание:\n{course_info[2]}"),
                                        reply_markup=keyboard)
    else:
        await call.message.answer(
            f"Название: {course_info[0]}\n"
            f"Автор: {course_info[1]}\n"
            f"Краткое орисание:\n{course_info[2]}",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="create_"), state='*', )
async def create_lesson(call: types.CallbackQuery, state: FSMContext):
    '''
    Создает начальный прогресс курса, если его нет,
    Устанавливает ученику текущее упражнение первым из курса,
    Обновляет значение активного курса ученика на текущий
    '''
    sql_request = """ SELECT CUR_EXERCISE FROM PUPIL_PROGRESS 
            WHERE PUPIL_ID = %s and COURSE_NAME=%s """
    pupil_progress = sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    if pupil_progress:
        await start_lesson(call, state)
    else:
        sql_request = """ SELECT MIN(EXERCISE_ID) FROM EXERCISES JOIN 
        lesson on lesson.lesson_id=exercises.lesson_id
        WHERE COURSE_NAME = %s
        GROUP BY LESSON_NAME """
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
        После теорию
    """
    sql_request = """SELECT LESSON_NAME, exercises.LESSON_ID , END_MESSAGE FROM exercises 
    JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id 
    JOIN lesson on lesson.lesson_id=exercises.lesson_id 
    WHERE pupil_progress.pupil_id =%s and pupil_progress.course_name=%s"""
    pupil_info = sql_conn(sql_request, (call.message.chat.id, call.data[7:]))

    async with state.proxy() as data:
        data['lesson_id'] = pupil_info[0][1]
        data['end_message'] = pupil_info[0][2]
        data['course_name'] = call.data[7:]
        data['course_name'] = call.data[7:]
        sql_request = """SELECT THEORY  
                           FROM LESSON
                            WHERE LESSON_ID = %s """
        theory = sql_conn(sql_request, (data['lesson_id'],))

        media = types.MediaGroup()
        i = 0
        '''
        Проверяем является ли сообщение изображением,
        Так как media_group не может посылать больше 10 сообщений за раз, 
        разбиваем сообщения на группы по 10
        '''
        for msg in theory[0][0]:
            if os.path.exists(msg):
                if i < 10:
                    media.attach_photo(types.InputFile(msg))
                    i += 1
                else:
                    await  call.message.answer_media_group(media=media)
                    media = types.MediaGroup()
                    i = 0
                    await sleep(0.5)
            else:
                try:
                    await  call.message.answer_media_group(media=media)
                    media = types.MediaGroup()
                except:
                    pass
                await sleep(0.5)
                await call.message.answer(msg)
        try:
            await  call.message.answer_media_group(media=media)
        except:
            pass
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
        FROM public.exercises JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id  
        WHERE pupil_id =%s """
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
    Получает и проверяет ответ,
    """
    async with state.proxy() as data:
        if message.text == data['answer']['right_answer']:
            await message.answer(f"Верно, Молодец {data['pupil_name']}!", reply_markup=types.ReplyKeyboardRemove())
            sql_request = """SELECT EXERCISE_ID FROM public.exercises
                               WHERE LESSON = %s AND EXERCISE_ID>%s LIMIT 1"""
            exersizes = sql_conn(sql_request, (data['lesson_id'],
                                               data['answer']['exercise_id']))
            if exersizes:  # Проверяет есть ли еще вопросы, если нет то проверяет остались ли уроки
                sql_request = """ UPDATE pupil_progress 
                                    SET CUR_EXERCISE = %s
                                    WHERE pupil_id = %s"""
                sql_conn(sql_request, (exersizes[0][0], message.from_user.id))
                await send_answer(message, state)
            else:
                # получаем номер последнего урока и проверяем есть ли еще уроки
                for mes in data['end_message']:
                    await message.answer(mes)
                sql_request = """SELECT MAX(LESSON) FROM public.exercises"""
                last_lesson = sql_conn(sql_request)
                if last_lesson[0][0] != data['lesson_id']:
                    sql_request = """SELECT LESSON_ID  
                                           FROM LESSON
                                            WHERE COURSE_NAME = %s AND LESSON_ID>%s LIMIT 1"""
                    lessons = sql_conn(sql_request, (data['course_name'],))
                    data['lesson_id'] = lessons[0][0]
                    sql_request = """UPDATE pupil_progress SET cur_exercise = (SELECT MIN(EXERCISE_ID) FROM public.exercises 
                    WHERE LESSON=%s), WHERE pupil_id = %s """
                    sql_conn(sql_request, (data['lesson_id'], message.from_user.id))
                    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    await Form.lesson.set()
                    keyboard.add('Да')
                    await message.answer(
                        "Нажмите да как только будете готовы к следующему уроку",
                        reply_markup=keyboard)
                else:
                    await Form.finished.set()
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(
                        text=f"Начать заново {data['course_name']}",
                        callback_data="clear__" + data['course_name']))
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
                f"Неверно, {data['pupil_name']}!\n Повтори материал и попробуй еще раз")


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
    async with state.proxy() as data:
        data['pupil_name'] = pupil_info[0][0]
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
    Сбрасывает прогресс ученика в пройденном курсе,
    устанавливет активный курс Null
    '''
    sql_request = """ DELETE FROM pupil_progress 
                    WHERE pupil_id = %s AND COURSE_NAME = %s"""
    sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    sql_request = """ UPDATE pupils SET CUR_COURSE = NULL  
                    WHERE pupil_id = %s """
    sql_conn(sql_request, (call.message.chat.id,))
    await course_menu(call)


if __name__ == "__main__":
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
