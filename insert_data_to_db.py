import psycopg2
from psycopg2 import Error
import passwords

def exercise_to_db(exercise,choices,right_answer):
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(user="postgres",
                                      # пароль, который указали при установке PostgreSQL
                                      password=passwords.password,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="teaching_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO exercises (EXERCISE, CHOICES, RIGHT_ANSWER) VALUES (%s, %s, %s)"""
        cursor.execute(insert_query,(exercise, choices, right_answer))
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
                                      password=passwords.password,
                                      host="127.0.0.1",
                                      port="5433",
                                      database="teaching_bot_db")
        # Курсор для выполнения операций с базой данных
        cursor = connection.cursor()
        # Распечатать сведения о PostgreSQL
        insert_query = """ INSERT INTO pupils (PUPIL_ID, PUPIL_NAME) VALUES (%s, %s)"""
        cursor.execute(insert_query,(id, name))
        connection.commit()
        cursor.close()
        connection.close()
        print("Соединение с PostgreSQL закрыто")
    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)


'''
print('Введите задание')
exercise=input()
print('Введите варианты ответа через запятую')
choices=input()
print('Введите правильный ответ')
right_answer = input()
print("Успешно")


exercise='question1'
choices='wrong answer1, wrong answer2, wrong answer3, right_answer'
right_answer= 'right_answer'
exercise_to_db(exercise,choices,right_answer)
'''
pupil_to_db(2,'Vova')