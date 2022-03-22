import os
from random import random, randint

import psycopg2
from psycopg2 import Error
from passwords import *


def exercise_to_db(exercise, choices, right_answer, lesson):
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=password_bd,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="course_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO exercises (EXERCISE, CHOICES, RIGHT_ANSWER, LESSON) VALUES (%s, %s, %s, %s)"""
        cursor.execute(insert_query, (exercise, choices, right_answer, lesson))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


def pupil_to_db(id, name):
    try:

        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=password_bd,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="course_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
        cursor.execute(insert_query, (id, name))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


def course_to_db(course_name, course_description, course_author, course_image):
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=password_bd,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="course_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO course (course_name,course_description,course_author, course_image ) VALUES (%s,%s,%s,%s)"""
        cursor.execute(insert_query, (course_name, course_description, course_author, course_image))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


def lesson_to_db(id, name, theory,end_message, course_name):
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=password_bd,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="course_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO lesson (LESSON_ID,LESSON_NAME, THEORY,end_message, COURSE_NAME ) VALUES (%s,%s,%s,%s,%s)"""
        cursor.execute(insert_query, (id, name, theory,end_message, course_name))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


def image_to_db(image, lesson_id, start_image=False):
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=password_bd,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="course_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO images (image,start_image , lesson ) VALUES (%s,%s,%s)"""
        cursor.execute(insert_query, (image, start_image, lesson_id))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


def insert_for_db():
    exercise = ['question' + str(x) for x in range(0, 5)]
    right_answer = 'right_answer'
    lesson = [1, 1, 1, 2, 2]
    for i in [1, 2]:
        lesson_to_db(i, i, ['start_message1', 'start_message2'], ['end_message1', 'end_message2'])
    dirname = 'images/'
    files = os.listdir(dirname)
    for i in range(0, 5):
        choices = ['wrong_answer'] * randint(0, 4)
        exercise_to_db([exercise[i], exercise[i]], choices, right_answer, lesson[i])
    # pupil_to_db(1, 'test_pupil')


def insert_for_chinese_db():
    theory = ['Давай сегодня поработаем как следует и разберёмся с одной из тех грамматических тем, которые не '
              'дают покоя студентам всех уровней! А именно - комплементы направления.', 'С этой темой обычно '
                                                                                        'возникает две '
                                                                                        'сложности: не всегда '
                                                                                        'ясно, куда поставить '
                                                                                        'комплемент направления '
                                                                                        'в предложении, '
                                                                                        'и стоит ли его '
                                                                                        'использовать вообще. '
                                                                                        'Тут важно запомнить, '
                                                                                        'что мы используем '
                                                                                        'комплементы направления '
                                                                                        'только в том случае, '
                                                                                        'когда нам важно сказать '
                                                                                        'о характере движения: '
                                                                                        'например, с какой целью '
                                                                                        'оно совершается или '
                                                                                        'кто/что переместилось и '
                                                                                        'в каком направлении.',
              'Сегодня предлагаю тебе сделать ещё одну попытку разобраться в это непростой для нас теме! В '
              'следующем сообщении ты найдёшь два файла с теорией: первый рассказывает о базовых принципах '
              'использования комплемента направления, а во втором даются дополнительные значения сложных '
              'комплементов. Второй файл будет полезен для тех, кто хочет полностью разобраться в этой теме🤓'
              ]
    import os
    dirname = 'chinese/lesson1/'
    files = os.listdir(dirname)
    for file in files:
        if os.path.isdir(os.path.join(dirname, file)):
            continue
        theory.append(os.path.join(dirname, file))
    end_message=['Отлично😍 Ты со всем справился! Теперь можно и отдохнуть✨','Кстати, завтра не будет никакой грамматики, обещаю!']
    course_to_db('chinese_for_lamers', 'просто непонятное описание  и картинка', 'esther',
                 'chinese/course_image/1545000059_glavnuyu.jpg')
    lesson_to_db(1, 'Комплементы направления', theory,end_message,
                 'chinese_for_lamers')



    exercise_1 = [
        'Первое задание совсем простое, но оно поможет тебе понять логику, по которой китайцы используют комплементы направления: ',
        'Определите, где находится говорящий в следующих предложениях: 例：你要走下去。说话人在：上边。', '1. 他们爬上山来了。说话人在：']
    exercise_to_db(exercise_1, ['下边'], '上边', 1)
    exercise_to_db(['2. 她带回来了一封信。说话人在：'], ['回去'], '回来', 1)
    exercise_to_db(['3. 老师发过去了一个传真。说话人在：'], ['回来'], '回去', 1)
    exercise_to_db(['4. 一个包裹妹妹从邮局取回来了。说话人在：'], ['进去'], '进来', 1)
    exercise_to_db(['大衣从楼上掉下来了。说话人在：'], ['上边'], '下边', 1)
    exercise_to_db(
        ['Второе задание немного сложнее, но если ты прочитал дополнительную грамматику, то сможешь его выполнить!',
         '1. 这个电视剧太精彩了，我再困也要坚持看'], ['起来', '过去', '下来'], '下去', 1)
    exercise_to_db(['2. 这个孩子看______缺乏营养，面黃肌瘦的。'], ['上来', '下来', '下去'], '上去', 1)


insert_for_chinese_db()
