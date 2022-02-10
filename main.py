from random import shuffle

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import passwords


def exercise_for_pupil(exercise):
    """
    Получает exercise содержащий
    вопрос , варианты ответа и правильный ответ,
    Сравнивает их с правильным возвращает True, False
    """
    question, choices, right_answer = [x for x in exercise]
    print(choices)
    #shuffle(choices)
    print(choices, right_answer)

    answer = input()
    return answer == right_answer


def get_pupil_from_db(pupil_id):
    """
    Получает задание для ученика из БД по его id,
    Возвращает имя ученика, вопрос, варианты ответа, правильный ответ
    :return exercise
    """
    connection = psycopg2.connect(user="postgres",
                                  # пароль, который указали при установке PostgreSQL
                                  password="453800",
                                  host="127.0.0.1",
                                  port="5433",
                                  database="teaching_bot_db")
    connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    # Курсор для выполнения операций с базой данных
    cursor = connection.cursor()
    sql_get_data = """SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER FROM public.exercises
                    JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                    WHERE pupil_id =%s 
                    """
    cursor.execute(sql_get_data, (pupil_id,))
    pupil_info = cursor.fetchone()
    cursor.close()
    connection.close()

    if pupil_info != None:
        print('Пользователь в базе')
        return pupil_info
    else:
        return False


def pupil_to_db(id, name):
    '''
    Записавыает нового ученик в БД
    '''
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=passwords.password,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="teaching_bot_db")
        cursor = connection.cursor()
        insert_query = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
        cursor.execute(insert_query, (id, name))
        connection.commit()
        cursor.close()
        connection.close()
        print("Пользователь успешно создан")
    except (Exception) as error:
        print("Ошибка на сервере попроюуйте позже", error)
    finally:
        cursor.close()
        connection.close()


def update_progres(id):
    '''
    Увеличаети прогресс ученика на 1
    '''
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=passwords.password,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="teaching_bot_db")
        cursor = connection.cursor()
        insert_query = """ UPDATE pupils 
                SET CUR_EXERCISE = CUR_EXERCISE + 1, ANSWERED = current_timestamp
                WHERE pupil_id = %s"""
        cursor.execute(insert_query, (id,))
        connection.commit()
        cursor.close()
        connection.close()
        print("Значение увеличено")
    except (Exception) as error:
        print("Ошибка на сервере попроюуйте позже", error)
    finally:
        cursor.close()
        connection.close()


sql = """ UPDATE vendors
                SET vendor_name = %s
                WHERE vendor_id = %s"""

#print(exercise_for_pupil(get_exercise_from_db(111111)))

