from random import shuffle

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def exercise_for_pupil(exercise):
    """
    Получает exercise содеражщий
    вопрос , варианты ответа и правильный ответ,
    Сравнивает их с правильным возвращает True, False
    """
    question, choices, right_answer = exercise[0], exercise[1], exercise[2]
    print(choices)
    #shuffle(choices)
    print(question, choices, right_answer)

    answer = input()
    return answer == right_answer


def get_exercise_from_db(pupil_id):
    """
    Получает задание для ученика из БД по его id,
    Возвращает вопрос, варианты ответа, правильный ответ
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
    sql_get_data = """SELECT EXERCISE, CHOICES, RIGHT_ANSWER FROM public.exercises
                    JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                    WHERE pupil_id =%s 
                    """
    cursor.execute(sql_get_data, (pupil_id,))
    exercise = cursor.fetchone()
    cursor.close()
    connection.close()
    print(exercise)
    return exercise


