import os
import shutil
from asyncio import sleep
from random import shuffle
from aiogram.dispatcher.filters import Text
from passwords import *
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# подгружаем токены и пароли из окружения
# Объект бота
bot = Bot(token=bot_token, parse_mode=types.ParseMode.HTML)
# Диспетчер для бота
storage = MongoStorage(host='localhost', port=27017, db_name='course_bot_db')
dp = Dispatcher(bot, storage=storage)


def sql_conn(sql_request, values: tuple = None):
    """
    Принимает в себя sql запрос и переменные,
    Соединяется с Бд
    Возвращает результат
    """
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
    del_pupil = State()
    add_pupil = State()
    delete_course = State()
    right_answer = State()
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
    choices_add = State()


@dp.message_handler(state='*', commands='cancel')
async def cancel_handler(message: types.Message, state: FSMContext):
    """
    Отмена всех состояний
    """
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.reply('Cancelled.', reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state='*', commands="start")
async def cmd_start(message: types.Message, state: FSMContext):
    """
    Команда start проверяет по id есть ли ученик в БД
    Если есть, то предложит продолжить учебу,
    Если есть активный курс предлагает продолжить его
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
                            FROM public.course WHERE is_active=True
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
async def admin_menu(message: types.Message):
    """
    Админ панель отвечает за создание и управления курсами
    """
    request = """SELECT is_admin, is_teacher FROM PUPILS 
    PUPILS WHERE PUPIL_ID= %s """
    status = sql_conn(request, (message.from_user.id,))
    if status[0][0] or status[0][1]:
        await Form.admin.set()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text=f"Создать новый курс",
            callback_data='add_new'))
        keyboard.add(types.InlineKeyboardButton(
            text=f"Управления курсами",
            callback_data='course_menu_admin'))
        await message.reply('Добро пожаловать в панель Админстратора.', reply_markup=keyboard)


@dp.callback_query_handler(state=Form.admin, text='add_new')
async def add_new_course(call: types.CallbackQuery, state: FSMContext):
    """
    Начинает создание курса
    """
    async with state.proxy() as course_dict:
        course_dict.clear()
    await call.message.answer('Вы находитесь в меню создания курса, внимательно следуйте инструкциям в сообщениях')
    await Form.course_new.set()

    await call.message.answer('Введите название курса')


@dp.message_handler(state=Form.course_new, content_types=['photo', 'text'])
async def new_course_name(message: types.Message, state: FSMContext):
    """
    Ввод краткого описания курса
    """
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
                        await message.photo[-1].download(destination_file=os.path.join(course_dict['course_name'],
                                                                                       course_dict[
                                                                                           'course_name'] + '.jpg'))
                        course_dict['course_image'] = os.path.join(course_dict['course_name'],
                                                                   course_dict['course_name'] + '.jpg')
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


@dp.callback_query_handler(state=Form.course_new, text='save_course')
async def save_course(call: types.CallbackQuery, state: FSMContext):
    """
    Сохраняет курс в БД, проверяет есть ли курс с подобным названием
    """
    async with state.proxy() as course_dict:
        insert_query = """ INSERT INTO course (course_name,course_author,course_description, course_image, course_creator ) VALUES (%s,%s,%s,%s,%s)"""
        try:
            sql_conn(insert_query, (
                course_dict['course_name'], course_dict['course_author'], course_dict['course_description'],
                course_dict['course_image'], call.from_user.id))
            await Form.lesson_add.set()
            await call.message.answer('Введите название урока')
        except:
            await Form.course_new.set()
            del course_dict['course_name']
            await call.message.answer('Курc с таким названием уже существует, выберите другое название')


@dp.message_handler(state=Form.lesson_add, content_types=['text', 'photo', 'audio'])
async def new_lesson(message: types.Message, state: FSMContext):
    """
    Создает новый урок
    """
    async with state.proxy() as course_dict:
        if 'lesson' in course_dict:
            if message.text:
                course_dict['theory'].append(message.text)
            elif message.photo:
                await message.photo[-1].download(
                    destination_file=os.path.join(course_dict['course_name'], course_dict['lesson'], "theory",
                                                  str(message.message_id) + '.jpg'))
                # из ассинхронного характера работы download отдельно добавляем пути к изображениям в БД,
                # беря их из папки загрузки где они в нужном порядке
                dirname = os.path.join(course_dict['course_name'], course_dict['lesson'], "theory")
                for file in os.listdir(dirname):
                    if os.path.isdir(os.path.join(dirname, file)):
                        continue
                    if os.path.join(dirname, file) not in course_dict['theory']:
                        course_dict['theory'].append(os.path.join(dirname, file))
                if message.caption:
                    course_dict['theory'].append(message.caption)
            else:
                await message.answer('Недопустимый формат сообщения возможны текст и фото')
        else:
            if message.text:
                if 'lesson_names' not in course_dict:
                    course_dict['lesson_names'] = []
                if message.text not in course_dict['lesson_names']:
                    course_dict['lesson_names'] = []
                    course_dict['lesson_names'].append(message.text)
                    course_dict['lesson'] = message.text
                    course_dict['theory'] = []
                    course_dict['course_image'] = []
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(
                        text="готово",
                        callback_data="end_messages"))
                    await message.answer(
                        "Теперь введите теорию, ее можно посылать текстом и в картинках, вы можете посылать ее "
                        "несколькими сообщениями,они будут выводится последовательно, когда закончите с вводом ВСЕЙ "
                        "теории нажмите готово",
                        reply_markup=keyboard)
                else:
                    await message.answer('Урок с таким названием уже существует')
            else:
                await message.answer('Недопустимый формат имени урока')


@dp.callback_query_handler(state=Form.lesson_add, text='end_messages')
async def state_end_messages(call: types.CallbackQuery, state: FSMContext):
    await Form.theory_add.set()
    async with state.proxy() as course_dict:
        course_dict['end_message'] = []
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="готово",
        callback_data="show_theory"))
    await call.message.answer('Добавьте сообщения которые будут выводится при успешном прохождения урока '
                              'вы можете посылать их несколькими сообщениями,они будут выводится последовательно, '
                              'когда закончите ВСЕ сообщения нажмите готово',
                              reply_markup=keyboard)


@dp.message_handler(state=Form.theory_add, content_types=['text', 'photo'])
async def add_end_message(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        if message.text:
            course_dict['end_message'].append(message.text)
        elif message.photo:
            await message.photo[-1].download(
                destination_file=os.path.join(course_dict['course_name'], course_dict['lesson'], "end_message",
                                              str(message.message_id) + '.jpg'))
            dirname = os.path.join(course_dict['course_name'], course_dict['lesson'], "end_message")
            for file in os.listdir(dirname):
                if os.path.isdir(os.path.join(dirname, file)):
                    continue
                if os.path.join(dirname, file) not in course_dict['end_message']:
                    course_dict['theory'].append(os.path.join(dirname, file))
            if message.caption:
                course_dict['end_message'].append(message.caption)
        else:
            await message.answer('Недопустимый формат сообщения возможны текст,фото, и аудио')


@dp.callback_query_handler(state=Form.theory_add, text='show_theory')
async def show_theory(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        media = types.MediaGroup()
        i = 0
        for msg in course_dict['theory']:
            if os.path.exists(msg) and not os.path.isdir(msg):
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
        media = types.MediaGroup()
        i = 0
        for msg in course_dict['end_message']:
            if os.path.exists(msg) and not os.path.isdir(msg):
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


@dp.callback_query_handler(state=Form.theory_add, text='save_theory')
async def save_theory(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        insert_data = []
        for key in ('theory', 'end_message'):
            insert_data.append(course_dict.get(key, None))
        insert_query = """ INSERT INTO lesson (LESSON_NAME, THEORY,end_message, COURSE_NAME ) VALUES (%s,%s,%s,%s)"""
        sql_conn(insert_query,
                 (course_dict['lesson'], insert_data[0], insert_data[1], course_dict['course_name']))
        await Form.exercise.set()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="готово",
            callback_data="add_choices"))
        await call.message.answer(
            'Теперь добавьте вопрос он может быть в формате текста или изображения,может содержать несколько '
            'сообщений, как завершите нажмите готово',
            reply_markup=keyboard)


@dp.message_handler(state=Form.exercise, content_types=['text', 'photo'])
async def add_exercise(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        if 'exercise' not in course_dict:
            course_dict['exercise'] = []
        if message.text:
            course_dict['exercise'].append(message.text)
        elif message.photo:
            await message.photo[-1].download(
                destination_file=os.path.join(course_dict['course_name'], course_dict['lesson'], "exercise",
                                              str(message.message_id) + '.jpg'))
            dirname = os.path.join(course_dict['course_name'], course_dict['lesson'], "exercise")
            for file in os.listdir(dirname):
                if os.path.isdir(os.path.join(dirname, file)):
                    continue
                if os.path.join(dirname, file) not in course_dict['exercise']:
                    course_dict['exercise'].append(os.path.join(dirname, file))
            if message.caption:
                course_dict['exercise'].append(message.text)
        else:
            await message.answer('Недопустимый формат сообщения возможны текст,фото, и аудио')


@dp.callback_query_handler(state=Form.exercise, text='add_choices')
async def add_choices(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        course_dict['choices'] = []
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="готово",
            callback_data="add_right_answer"))
        await Form.choices_add.set()
        await call.message.answer(
            'Теперь добавьте варианты ответа, формат текст, не включая правильный, если они нужны, по окончанию нажмите готово',
            reply_markup=keyboard)


@dp.message_handler(state=Form.choices_add)
async def save_choices(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        course_dict['choices'].append(message.text)


@dp.callback_query_handler(state=Form.choices_add, text='add_right_answer')
async def add_right_answer(call: types.CallbackQuery, state: FSMContext):
    await Form.right_answer.set()
    await call.message.answer(
        'Теперь добавьте правильный ответ, формат текст,ЭТОТ ПАРАМЕТР ОБЯЗАТЕЛЕНЕН',
    )


@dp.message_handler(state=Form.right_answer)
async def show_exercise(message: types.Message, state: FSMContext):
    async with state.proxy() as course_dict:
        course_dict["right_answer"] = message.text
        media = types.MediaGroup()
        i = 0
        for msg in course_dict['exercise']:
            if os.path.exists(msg) and not os.path.isdir(msg):
                if i < 10:
                    media.attach_photo(types.InputFile(msg))
                    i += 1
                else:
                    await  message.answer_media_group(media=media)
                    media = types.MediaGroup()
                    i = 0
                    await sleep(0.5)
            else:
                try:
                    await  message.answer_media_group(media=media)
                    media = types.MediaGroup()
                except:
                    pass
                await sleep(0.5)
                await message.answer(msg)
        try:
            await  message.answer_media_group(media=media)
        except:
            pass
        await message.answer(f"Варианты ответа: {course_dict['choices']}\n "
                             f"Правильный ответ: {course_dict['right_answer']}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="Сохранить",
            callback_data="save_exercise"))
        keyboard.add(types.InlineKeyboardButton(
            text=f"Изменить",
            callback_data="delete_exercise"))
        await message.answer((
            f" <b>Проверьте введенные данные. При нажатия изменить вопрос удалиться и его придется вводить заново!!</b>\n"),
            reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(state=Form.right_answer, text='save_exercise')
async def save_exercise(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        sql_request = """ SELECT lesson_id FROM LESSON 
                    WHERE LESSON_NAME=%s """
        lesson_id = sql_conn(sql_request, (course_dict['lesson'],))
        insert_query = """ INSERT INTO exercises (EXERCISE, CHOICES, RIGHT_ANSWER, LESSON_ID) VALUES (%s, %s, %s, %s)"""
        choices = course_dict.get('choices', None)
        sql_conn(insert_query,
                 (course_dict['exercise'], choices, course_dict["right_answer"],
                  lesson_id[0]))
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="добавить еще вопросы",
            callback_data="reset_exercise"))
        keyboard.add(types.InlineKeyboardButton(
            text="закончить",
            callback_data="adding_finished"))
        await call.message.answer(
            'Вопрос успешно сохранен',
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="delete_"), state=Form.theory_add)
async def delete_confirmation(call: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Сохранить",
        callback_data="save_" + call.data[7:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Удалить",
        callback_data="reset_" + call.data[7:]))
    await call.message.answer("Вы уверены?", reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(Text(startswith="adding_finished"), state="*")
async def adding_finished(call: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Добавить еще урок",
        callback_data="reset_lesson"))
    keyboard.add(types.InlineKeyboardButton(
        text="Завершить",
        callback_data="course_menu_admin"))
    await call.message.answer(
        'Поздравляю вы успешно создали свой первый урок, чтобы закончить нажмите, Завершить, по умолчанию курс после '
        'создания имеет статус неактивный, чтоб курс стал активным и отображался в меню курсов, измените его статус в '
        'меню управления курсами, там же вы можете установить будет ли курс бесплатным для всех, или добавить '
        'пользователей имеющих доступ к курсу',
        reply_markup=keyboard)


@dp.callback_query_handler(state='*', text='course_menu')
async def course_menu(call: types.CallbackQuery):
    """
    Отвечает за курсы доступные в БД
    Выводит списки курсов, и предлагает продолжить текущий курс
    """
    sql_request = """SELECT PUPIL_NAME, cur_course
                    FROM public.pupils
                    WHERE pupil_id =%s """
    pupil_info = sql_conn(sql_request, (call.message.chat.id,))
    sql_request = """SELECT COURSE_NAME 
                    FROM public.course
                    WHERE is_active = True
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
            f" Выберите интересующий вас курс",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="reset"), state="*")
async def reset_data(call: types.CallbackQuery, state: FSMContext):
    """
    Сбрасывает введенные данные, в зависимости откуда вызвано
    """
    async with state.proxy() as course_dict:
        if call.data[6:] == 'course':
            for key in ('course_name', 'course_author', 'course_description', 'course_image'):
                course_dict.pop(key, None)
            await Form.course_new.set()
            await call.message.answer('Введите название курса')
        elif call.data[6:] == 'theory':
            for key in ('lesson', 'theory', 'end_message'):
                course_dict.pop(key, None)
            dirname = os.path.join(course_dict['course_name'], course_dict['lesson'], "theory")
            shutil.rmtree(dirname)
            await Form.lesson_add.set()
            await call.message.answer('Введите название урока')
        elif call.data[6:] == 'exercise':
            for key in ('exercise', 'choices', 'right_answer'):
                course_dict.pop(key, None)
            await Form.exercise.set()
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="готово",
                callback_data="add_choices"))
            await call.message.answer(
                'Теперь добавьте вопросы они могут в формате текста или изображения, по окончанию добавления нажмите готово',
                reply_markup=keyboard)
        elif call.data[6:] == 'lesson':
            for key in ('exercise', 'choices', 'right_answer', 'lesson', 'theory', 'end_message'):
                course_dict.pop(key, None)
                await Form.lesson_add.set()


@dp.callback_query_handler(state='*', text='course_menu_admin')
async def course_menu_admin(call: types.CallbackQuery):
    """
    Админ панель для курсов, выводит все доступные курсы? если пользователь администратор,
    если учитель, то только курсы созданные пользователем
    """
    request = """SELECT is_admin FROM PUPILS 
    PUPILS WHERE PUPIL_ID= %s """
    is_admin = sql_conn(request, (call.from_user.id,))
    if is_admin[0][0]:
        sql_request = """SELECT COURSE_NAME,is_active
                        FROM public.course
                        """
        course_info = sql_conn(sql_request)
    else:
        sql_request = """SELECT COURSE_NAME,is_active
                        FROM public.course WHERE course_creator =%s
                        """
        course_info = sql_conn(sql_request, (call.from_user.id,))
    keyboard = types.InlineKeyboardMarkup()
    for course in course_info:
        status = 'активен' if course[1] else 'не активен'
        keyboard.add(types.InlineKeyboardButton(
            text=f'{course[0]} - {status}',
            callback_data='admin_course_' + course[0]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Назад",
        callback_data='admin_menu'))
    await call.message.answer(
        f" Выберите интересующий вас курс",
        reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(Text(startswith="admin_course_"), state='*')
async def course_detailed_admin(call: types.CallbackQuery):
    """
    Показывает детальную информацию о курсе
    Название, автора, краткое описание, логотип если есть
    """
    await Form.admin.set()
    sql_request = """SELECT COURSE_NAME, COURSE_AUTHOR, COURSE_DESCRIPTION, COURSE_IMAGE, is_active, is_free
                    FROM course WHERE COURSE_NAME=%s
                    """
    course_info = sql_conn(sql_request, (call.data[13:],))[0]
    sql_request = """SELECT LESSON_NAME, LESSON_ID
                                   FROM LESSON
                                    WHERE COURSE_NAME = %s """
    lessons = sql_conn(sql_request, (call.data[13:],))
    keyboard = types.InlineKeyboardMarkup()
    is_free = "бесплатным" if course_info[5] else "платным"
    for lesson in lessons:
        keyboard.add(types.InlineKeyboardButton(
            text=f"Урок: {lesson[0]}",
            callback_data="admin_view_" + str(lesson[1])))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Изменить статус",
        callback_data="admin_status_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Сделать {is_free}",
        callback_data="admin_isfree_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Меню управления учениками",
        callback_data="admin_access_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Добавить урок",
        callback_data="admin_change_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Удалить курс",
        callback_data="admin_delete_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Назад",
        callback_data="course_menu_admin"))
    if course_info[3]:  # проверка есть ли лого
        await call.message.answer_photo(types.InputFile(course_info[3]),
                                        caption=(f"Название: {course_info[0]}\n"
                                                 f"Бесплатный: {course_info[5]}\n"
                                                 f"Автор: {course_info[1]}\n"
                                                 f"Краткое описание:\n{course_info[2]}\n"
                                                 f"Статус: <b>{course_info[4]}</b>\n"),
                                        reply_markup=keyboard, parse_mode=types.ParseMode.HTML)
    else:
        await call.message.answer(
            f"Название: {course_info[0]}\n"
            f"Бесплатный: {course_info[5]}\n"
            f"Автор: {course_info[1]}\n"
            f"Краткое описание:\n{course_info[2]}"
            f"Статус: <b>{course_info[4]}</b>\n",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="admin_status"), state='*')
async def admin_change_status(call: types.CallbackQuery):
    """меняет статус курса на противоположный"""
    sql_request = """ UPDATE course SET is_active = NOT is_active  
                    WHERE COURSE_NAME = %s """
    sql_conn(sql_request, (call.data[13:],))
    await course_detailed_admin(call)


@dp.callback_query_handler(Text(startswith="admin_isfree_"), state='*')
async def admin_change_is_free(call: types.CallbackQuery):
    """Делает курсы платным или бесплатным"""
    sql_request = """ UPDATE course SET is_free = NOT is_free  
                    WHERE COURSE_NAME = %s """
    sql_conn(sql_request, (call.data[13:],))
    await course_detailed_admin(call)


@dp.callback_query_handler(Text(startswith="admin_access_"), state='*')
async def admin_course_access(call: types.CallbackQuery):
    """Управляет доступом к курсу, добавляет учеников, выводит список учеников курса"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text=f"Список учеников",
        callback_data="pupil_list" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text=f"Добавить ученика",
        callback_data="add_pupil" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="admin_course_" + call.data[13:]))
    await call.message.answer("Меню управления учениками", reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="add_pupil"), state='*')
async def admin_add_pupil(call: types.CallbackQuery, state):
    await Form.add_pupil.set()
    async with state.proxy() as course_name:
        course_name['name'] = call.data[9:]
        await call.message.answer("введите telegram id ученика которого хотите добавить ")


@dp.message_handler(state=Form.add_pupil)
async def admin_save_pupil(message: types.Message, state):
    if message.text.isnumeric():
        async with state.proxy() as course_name:
            name = course_name['name']
            sql_request = """ UPDATE course SET pupils_accessed =array_append (pupils_accessed,%s)  
                                WHERE COURSE_NAME = %s """
            sql_conn(sql_request, (message.text, course_name['name'],))
            await Form.admin.set()
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="admin_access_" + name))
            await message.answer("ученик успешно добавлен", reply_markup=keyboard)

    else:
        await message.answer("неверный формат id")


@dp.callback_query_handler(Text(startswith="pupil_list"), state='*')
async def admin_pupli_list(call: types.CallbackQuery, state):
    await Form.admin.set()
    """
    Список учеников курса
    """
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Удалить ученика",
        callback_data="del_pupil" + call.data[10:]))
    keyboard.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="admin_course_" + call.data[10:]))
    sql_request = """ SELECT pupils_accessed FROM course  
                        WHERE COURSE_NAME = %s """
    pupils = sql_conn(sql_request, (call.data[10:],))
    await  call.message.answer(text=("Список учеников имеющих доступ к курсу:", pupils), reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="del_pupil"), state='*')
async def admin_delete_pupil(call: types.CallbackQuery, state):
    """
    Удаляет ученика по id
    """
    await Form.del_pupil.set()
    async with state.proxy() as course_name:
        course_name['name'] = call.data[9:]
        await call.message.answer("введите telegram id ученика которого удалить ")


@dp.message_handler(state=Form.del_pupil)
async def admin_del_pupil(message: types.Message, state):
    async with state.proxy() as course_name:
        name = course_name['name']
    sql_request = """ SELECT pupils_accessed FROM course  
                        WHERE COURSE_NAME = %s """
    pupils = sql_conn(sql_request, (course_name['name'],))
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="admin_access_" + name))
    if message.text in pupils[0][0]:
        sql_request = """ UPDATE course SET pupils_accessed =array_remove (pupils_accessed,%s)  
                            WHERE COURSE_NAME = %s """
        sql_conn(sql_request, (message.text, course_name['name'],))
        await Form.admin.set()

        await message.answer("ученик успешно удален", reply_markup=keyboard)

    else:
        await message.answer("такого ученика нет", reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="admin_change"), state='*')
async def admin_change_course(call: types.CallbackQuery, state):
    """
    Добавление нового урока
    """
    async with state.proxy() as course_dict:
        course_dict['course_name'] = call.data[13:]
        await Form.lesson_add.set()
        await call.message.answer('Введите название урока')


@dp.callback_query_handler(Text(startswith="admin_view"), state='*')
async def admin_view_lesson(call: types.CallbackQuery):
    """
    Детализированный просмотр урока
    """
    sql_request = """SELECT THEORY,COURSE_NAME,END_MESSAGE TEXT  
                               FROM LESSON
                                WHERE LESSON_ID = %s """
    theory = sql_conn(sql_request, (call.data[11:],))
    sql_request = """SELECT EXERCISE, CHOICES, RIGHT_ANSWER, EXERCISE_ID
                FROM public.exercises 
                WHERE LESSON_ID =%s """
    exercise_info = sql_conn(sql_request, (call.data[11:],))
    media = types.MediaGroup()
    i = 0
    '''
    Проверяем является ли сообщение изображением,
    Так как media_group не может посылать больше 10 сообщений за раз, 
    разбиваем сообщения на группы по 10
    '''
    for msg in theory[0][0]:
        if os.path.exists(msg) and not os.path.isdir(msg):
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
    media = types.MediaGroup()
    i = 0
    for exersice in exercise_info:
        for msg in exersice[0]:
            if os.path.exists(msg) and not os.path.isdir(msg):
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
        await call.message.answer(f"Варианты ответа: {exersice[1]}\n "
                                  f"Правильный ответ: {exersice[2]}")
    for msg in theory[0][2]:
        if os.path.exists(msg) and not os.path.isdir(msg):
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
        text="Назад",
        callback_data="admin_course_" + theory[0][1]))
    await  call.message.answer("Конец урока", reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="admin_delete"), state='*')
async def admin_delete_course(call: types.CallbackQuery):
    # удаление курса
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text=f"Удалить",
        callback_data="confirm_delete_" + call.data[13:]))
    keyboard.add(types.InlineKeyboardButton(
        text="Назад",
        callback_data="admin_course_" + call.data[13:]))
    await call.message.answer("Вы уверены?", reply_markup=keyboard, parse_mode=types.ParseMode.HTML)


@dp.callback_query_handler(Text(startswith="confirm_delete_"), state='*')
async def admin_delete_confirmation(call: types.CallbackQuery, state: FSMContext):
    async with state.proxy() as course_dict:
        course_dict['confirm_delete'] = call.data[15:]
        await Form.delete_course.set()
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="Назад",
            callback_data="admin_course_" + course_dict['confirm_delete']))
        await  call.message.answer("Напишите название курса для подтверждения", reply_markup=keyboard)


@dp.message_handler(state=Form.delete_course)
async def admin_delete_confirmed(message: types.Message, state: FSMContext):
    """ запрашиваем подтверждения удаления"""
    async with state.proxy() as course_dict:
        if message.text == course_dict['confirm_delete']:
            sql_request = """ DELETE FROM exercises  
                            WHERE LESSON_ID = (SELECT LESSON_ID FROM lesson WHERE COURSE_NAME  = %s)"""
            sql_conn(sql_request, (course_dict['confirm_delete'],))
            sql_request = """ DELETE FROM lesson  
                            WHERE COURSE_NAME = %s """
            sql_conn(sql_request, (course_dict['confirm_delete'],))
            sql_request = """ DELETE FROM course  
                            WHERE COURSE_NAME = %s """
            sql_conn(sql_request, (course_dict['confirm_delete'],))
            await Form.admin.set()
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="course_menu_admin"))
            await  message.answer("Курс удален", reply_markup=keyboard)
        else:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(
                text="Назад",
                callback_data="course_menu_admin" + course_dict['confirm_delete']))
            await message.answer("Неверно, попоробуйте снова", reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="course_"), state='*')
async def course_detailed(call: types.CallbackQuery):
    """
    Показывает детальную информацию о курсе
    Название, автора, краткое описание, логотип если есть,
    Проверяет есть ли у ученика доступ к курсу,
    """
    sql_request = """SELECT COURSE_NAME, COURSE_AUTHOR, COURSE_DESCRIPTION, COURSE_IMAGE,is_free,pupils_accessed
                    FROM course WHERE COURSE_NAME=%s
                    """
    course_info = sql_conn(sql_request, (call.data[7:],))[0]
    keyboard = types.InlineKeyboardMarkup()
    aviable = 'Да'
    if course_info[4]:
        keyboard.add(types.InlineKeyboardButton(
            text=f"Начать учебу в {call.data[7:]}",
            callback_data="create_" + call.data[7:]))
    elif call.from_user.id in course_info[5]:
        keyboard.add(types.InlineKeyboardButton(
            text=f"Начать учебу в {call.data[7:]}",
            callback_data="create_" + call.data[7:]))
    else:
        aviable = 'Нет'
    keyboard.add(types.InlineKeyboardButton(
        text=f"Назад",
        callback_data="course_menu"))
    if course_info[3]:  # проверка есть ли лого
        await call.message.answer_photo(types.InputFile(course_info[3]),
                                        caption=(f"Название: {course_info[0]}\n"
                                                 f"Доступен: {aviable}\n"
                                                 f"Автор: {course_info[1]}\n"
                                                 f"Краткое описание:\n{course_info[2]}"),
                                        reply_markup=keyboard)
    else:
        await call.message.answer(
            f"Название: {course_info[0]}\n"
            f"Доступен: {aviable}\n"
            f"Автор: {course_info[1]}\n"
            f"Краткое орисание:\n{course_info[2]}",
            reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="create_"), state='*', )
async def create_lesson(call: types.CallbackQuery, state: FSMContext):
    """
    Создает начальный прогресс курса, если его нет,
    Устанавливает ученику текущее упражнение первым из курса,
    Обновляет значение активного курса ученика на текущий
    """
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
        await start_lesson(call, state)


@dp.callback_query_handler(Text(startswith="lesson_"), state='*')
async def start_lesson(call: types.CallbackQuery, state: FSMContext = FSMContext):
    """
    Оправляет теорию ученику, сначала получает ее из БД, после сохраняет в словарь
    """

    sql_request = """ UPDATE pupils SET CUR_COURSE = %s  
                    WHERE pupil_id = %s """
    sql_conn(sql_request, (call.data[7:], call.message.chat.id,))
    sql_request = """SELECT LESSON_NAME, exercises.LESSON_ID , END_MESSAGE FROM exercises 
    JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id 
    JOIN lesson on lesson.lesson_id=exercises.lesson_id 
    WHERE pupil_progress.pupil_id =%s and pupil_progress.course_name=%s"""
    pupil_info = sql_conn(sql_request, (call.message.chat.id, call.data[7:]))
    async with state.proxy() as data:
        data['lesson_id'] = pupil_info[0][1]
        data['end_message'] = pupil_info[0][2]
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
            if os.path.exists(msg) and not os.path.isdir(msg):
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
async def send_answer(message: types.Message, state: FSMContext):
    """
    Отправляет вопрос ученику
    """
    async with state.proxy() as data:
        sql_request = """SELECT EXERCISE, CHOICES, RIGHT_ANSWER, EXERCISE_ID
            FROM public.exercises JOIN pupil_progress on pupil_progress.cur_exercise=exercises.exercise_id  
            WHERE pupil_id =%s and COURSE_NAME =%s"""
        exercise_info = sql_conn(sql_request, (message.from_user.id, data['course_name']))
        data['answer'] = {keys: value for keys, value in
                          zip(['exercise', 'choices', 'right_answer', 'exercise_id'], exercise_info[0])}
        await Form.waiting_check.set()
        keyboard = types.ReplyKeyboardRemove()
        if data['answer']['choices']:
            choices = data['answer']['choices']
            choices.append(data['answer']['right_answer'])
            shuffle(choices)
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            keyboard.add(*choices)
        for msg in data['answer']['exercise']:
            if os.path.exists(msg) and not os.path.isdir(msg):
                await message.answer_photo(types.InputFile(msg), reply_markup=keyboard)
            else:
                await message.answer(msg, reply_markup=keyboard)


@dp.message_handler(state=Form.waiting_check)
async def check_answer(message: types.Message, state: FSMContext):
    """
    Получает и проверяет ответ,
    """
    async with state.proxy() as data:
        if message.text == data['answer']['right_answer']:
            await message.answer(f"Верно, Молодец {data['pupil_name']}!", reply_markup=types.ReplyKeyboardRemove())
            sql_request = """SELECT EXERCISE_ID FROM public.exercises
                               WHERE LESSON_ID = %s AND EXERCISE_ID>%s LIMIT 1"""
            exersizes = sql_conn(sql_request, (data['lesson_id'],
                                               data['answer']['exercise_id']))
            if exersizes:  # Проверяет есть ли еще вопросы, если нет то проверяет остались ли уроки
                sql_request = """ UPDATE pupil_progress 
                                    SET CUR_EXERCISE = %s
                                    WHERE pupil_id = %s and COURSE_NAME= %s"""
                sql_conn(sql_request, (exersizes[0][0], message.from_user.id, data['course_name'],))
                await send_answer(message, state)
            else:
                media = types.MediaGroup()
                i = 0
                for msg in data['end_message']:
                    if os.path.exists(msg) and not os.path.isdir(msg):
                        if i < 10:
                            media.attach_photo(types.InputFile(msg))
                            i += 1
                        else:
                            await  message.answer_media_group(media=media)
                            media = types.MediaGroup()
                            i = 0
                            await sleep(0.5)
                    else:
                        try:
                            await  message.answer_media_group(media=media)
                            media = types.MediaGroup()
                        except:
                            pass
                        await sleep(0.5)
                        await message.answer(msg)
                try:
                    await message.answer_media_group(media=media)
                except:
                    pass
                # получаем номер последнего урока и проверяем есть ли еще уроки
                sql_request = """SELECT MAX(LESSON_ID) FROM public.exercises"""
                last_lesson = sql_conn(sql_request)
                if last_lesson[0][0] != data['lesson_id']:
                    sql_request = """SELECT LESSON_ID  
                                           FROM LESSON
                                            WHERE COURSE_NAME = %s AND LESSON_ID>%s LIMIT 1"""
                    lessons = sql_conn(sql_request, (data['course_name'], data['lesson_id']))
                    data['lesson_id'] = lessons[0][0]
                    sql_request = """UPDATE pupil_progress SET cur_exercise = (SELECT MIN(EXERCISE_ID) FROM public.exercises 
                    WHERE lesson_id = %s )"""
                    sql_conn(sql_request, (data['lesson_id'],))
                    keyboard = types.InlineKeyboardMarkup()
                    keyboard.add(types.InlineKeyboardButton(
                        text=f"Да",
                        callback_data="lesson_" + data['course_name']))
                    await Form.lesson.set()
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
                        '''Поздравляю вы успешно закончили курс,надеюсь вам понравилось!!! Хотите сбросить прогресс и 
                        для того чтобы начать курс заново?''',
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
    async with state.proxy() as data:
        data['pupil_name'] = pupil_info[0][0]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="Муню курсов",
        callback_data="course_menu"))
    await message.answer(
        f"Добро пожаловать {pupil_info[0][0]}!, вы успешно зарегистрировались, перейдите в меню курсов чтобы выбрать интересующий вас курс",
        reply_markup=keyboard)


@dp.callback_query_handler(Text(startswith="clear__"), state='*')
async def reset_user(call: types.CallbackQuery, state: FSMContext):
    """
    Сбрасывает прогресс ученика в пройденном курсе,
    устанавливает активный курс Null
    """
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
