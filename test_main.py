import pytest
from bot import *
from unittest.mock import AsyncMock


def test_get_pupil_from_db():
    exercise = ('test_pupil','question','wrong answer;wrong answer;wrong answer;wrong answer;','right_answer')
    assert exercise == sql_conn("""SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER FROM public.exercises
                    JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                    WHERE pupil_id =%s 
                    """, (1,))

def test_last_answer_for_lesson_from_db():
    exercise = ('test_pupil','question','wrong answer;wrong answer;wrong answer;wrong answer;','right_answer')
    assert (4,) == sql_conn("""SELECT MAX(EXERCISE_ID) FROM public.EXERCISEs
                                GROUP BY LESSON
                                HAVING LESSON  =%s 
                                """, (1,))


