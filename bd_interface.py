import psycopg2
from psycopg2 import Error

try:
    # Подключение к существующей базе данных
    connection = psycopg2.connect(user="postgres",
                                  # пароль, который указали при установке PostgreSQL
                                  password="453800",
                                  host="127.0.0.1",
                                  port="5433",
                                  database="teach_chinese_bot_db")

    # Курсор для выполнения операций с базой данных
    cursor = connection.cursor()
    create_table_query = '''CREATE TABLE lesson
                                (LESSON_ID         INTEGER    NOT NULL  primary key,
                                LESSON_NAME      TEXT,
                                START_MESSAGES      TEXT[],
                                END_MESSAGES      TEXT[]
                                ); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    create_table_query = '''CREATE TABLE images
                                (IMAGE_ID         SERIAL  primary key, 
                                START_IMAGE boolean NOT NULL,
                                IMAGE TEXT NOT NULL,
                                LESSON INTEGER NOT NULL,
                                FOREIGN KEY (LESSON) REFERENCES lesson (LESSON_ID) ON DELETE SET DEFAULT); 
                                                          '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    # Распечатать сведения о PostgreSQL
    create_table_query = '''CREATE TABLE exercises
                             (EXERCISE_ID         SERIAL  primary key, 
                              EXERCISE           TEXT[]    NOT NULL,
                             CHOICES         TEXT[] ,
                             RIGHT_ANSWER TEXT    NOT NULL,
                             LESSON INTEGER NOT NULL,
                             FOREIGN KEY (LESSON) REFERENCES lesson (LESSON_ID) ON DELETE SET DEFAULT); 
                                                       '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    create_table_query = '''CREATE TABLE pupils
                             (PUPIL_ID         INTEGER    NOT NULL  primary key,
                             PUPIL_NAME      TEXT    NOT NULL,
                             CUR_EXERCISE INTEGER DEFAULT 1,
                             REGISTER_TIME timestamp default current_timestamp,
                             ANSWERED timestamp,
                             FOREIGN KEY (CUR_EXERCISE) REFERENCES exercises (EXERCISE_ID) ON DELETE SET DEFAULT); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблица успешно создана в PostgreSQL")
    cursor.close()
    connection.close()
    print("Соединение с PostgreSQL закрыто")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)

