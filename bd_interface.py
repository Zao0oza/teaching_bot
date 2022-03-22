import psycopg2
from psycopg2 import Error
from passwords import *

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

    create_table_query = '''CREATE TABLE course
                                    (course_name     TEXT primary key,
                                    course_description      TEXT,
                                    course_author      TEXT,
                                    course_image TEXT
                                    ); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    cursor = connection.cursor()
    create_table_query = '''CREATE TABLE lesson
                                (LESSON_ID         INTEGER    NOT NULL  primary key,
                                LESSON_NAME      TEXT,
                                THEORY TEXT[],
                                END_MESSAGE TEXT[],
                                COURSE_NAME TEXT,
                                FOREIGN KEY (COURSE_NAME) REFERENCES COURSE (COURSE_NAME) ON DELETE CASCADE)
                                ; '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    """
    create_table_query = '''CREATE TABLE images
                                (IMAGE_ID         SERIAL  primary key, 
                                START_IMAGE boolean NOT NULL,
                                IMAGE TEXT NOT NULL,
                                LESSON INTEGER NOT NULL,
                                FOREIGN KEY (LESSON) REFERENCES lesson (LESSON_ID) ON DELETE SET NULL); 
                                                          '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")"""
    # Распечатать сведения о PostgreSQL
    create_table_query = '''CREATE TABLE exercises
                             (EXERCISE_ID         SERIAL  primary key, 
                              EXERCISE           TEXT[]    NOT NULL,
                             CHOICES         TEXT[] ,
                             RIGHT_ANSWER TEXT    NOT NULL,
                             LESSON INTEGER NOT NULL,
                             FOREIGN KEY (LESSON) REFERENCES lesson (LESSON_ID) ON DELETE CASCADE); 
                                                       '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    create_table_query = '''CREATE TABLE pupils
                             (PUPIL_ID         INTEGER    NOT NULL  primary key,
                             PUPIL_NAME      TEXT    NOT NULL,
                             CUR_COURSE TEXT,
                             FOREIGN KEY (CUR_COURSE) REFERENCES COURSE (COURSE_NAME) ON DELETE SET DEFAULT); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()

    print("Таблица успешно создана в PostgreSQL")
    create_table_query = '''CREATE TABLE PUPIL_PROGRESS 
                            ( PUPIL_ID INTEGER,
                            FOREIGN KEY (PUPIL_ID) REFERENCES pupils (PUPIL_ID) ON DELETE  SET NULL,
                             CUR_EXERCISE INTEGER,
                             FOREIGN KEY (CUR_EXERCISE) REFERENCES exercises (EXERCISE_ID) ON DELETE  SET NULL,
                             COURSE_NAME TEXT,  
                             FOREIGN KEY (COURSE_NAME) REFERENCES COURSE (COURSE_NAME) ON DELETE  SET NULL); '''

    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    cursor.close()
    connection.close()
    print("Соединение с PostgreSQL закрыто")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)

