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

    connection.commit()
    '''
    Создаём таблицу описывающую струкутура курса,
    в нее входят: название, краткое описание, автор, 
    лого, активен ли курс, является курс бесплатным, ученики имеющие к нему доступ, и id создателя
    '''
    create_table_query = '''CREATE TABLE course
                                    (course_name     TEXT primary key,
                                    course_description      TEXT,
                                    course_author      TEXT,
                                    course_image TEXT,
                                    course_creator      INTEGER,
                                    pupils_accessed TEXT[],
                                    is_active boolean DEFAULT FALSE,
                                    is_free boolean DEFAULT FALSE
                                    ); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    cursor = connection.cursor()
    '''
    Урок включает в себя id, Название, теорию
    Сообщения после прозождения урока, название курса
    '''
    create_table_query = '''CREATE TABLE lesson
                                (LESSON_ID         SERIAL  primary key,
                                LESSON_NAME      TEXT,
                                THEORY TEXT[],
                                END_MESSAGE TEXT[],
                                COURSE_NAME TEXT,
                                FOREIGN KEY (COURSE_NAME) REFERENCES COURSE (COURSE_NAME) ON DELETE SET DEFAULT)
                                ; '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    '''
    Вопросы к теории включают:
    id, вопрос, варианты ответа,правильный ответ, ссылка нв урок
    '''
    # Распечатать сведения о PostgreSQL
    create_table_query = '''CREATE TABLE exercises
                             (EXERCISE_ID         SERIAL  primary key, 
                              EXERCISE           TEXT[]    NOT NULL,
                             CHOICES         TEXT[] ,
                             RIGHT_ANSWER TEXT    NOT NULL,
                             LESSON_ID INTEGER NOT NULL,
                             FOREIGN KEY (LESSON_ID) REFERENCES lesson (LESSON_ID) ON DELETE SET DEFAULT); 
                                                       '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    """
    Ученики включает в себя, id, имя, текущий курс,
    является ли учителем, является ли админом,
    """
    create_table_query = '''CREATE TABLE pupils
                             (PUPIL_ID         INTEGER    NOT NULL  primary key,
                             PUPIL_NAME      TEXT    NOT NULL,
                             CUR_COURSE TEXT,
                             IS_TEACHER boolean DEFAULT FALSE,
                             IS_ADMIN boolean DEFAULT FALSE,  
                             FOREIGN KEY (CUR_COURSE) REFERENCES COURSE (COURSE_NAME) ON DELETE SET DEFAULT); '''
    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    """
    Прогресс ученика , включает: id ученика, последний выполняемый вопрос курса, имя курса
    """
    create_table_query = '''CREATE TABLE PUPIL_PROGRESS 
                            ( PROGRESS_ID         SERIAL  primary key, 
                            PUPIL_ID INTEGER,
                            FOREIGN KEY (PUPIL_ID) REFERENCES pupils (PUPIL_ID) ON DELETE  SET DEFAULT,
                             CUR_EXERCISE INTEGER,
                             FOREIGN KEY (CUR_EXERCISE) REFERENCES exercises (EXERCISE_ID) ON DELETE  SET DEFAULT,
                             COURSE_NAME TEXT,
                             FOREIGN KEY (COURSE_NAME) REFERENCES COURSE (COURSE_NAME) ON DELETE  SET DEFAULT); '''

    # Выполнение команды: это создает новую таблицу
    cursor.execute(create_table_query)
    connection.commit()
    print("Таблицы успешно созданы в PostgreSQL")
    cursor.close()
    connection.close()
    print("Соединение с PostgreSQL закрыто")
except (Exception, Error) as error:
    print("Ошибка при работе с PostgreSQL", error)

