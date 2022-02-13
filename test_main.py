import pytest
from bot import *
from unittest.mock import AsyncMock


def test_get_pupil_from_db():
    exercise = ('Andrew', 'question2', 'wrong answer1, wrong answer2, wrong answer3, right_answer', 'right_answer')
    assert exercise == sql_conn("""SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER FROM public.exercises
                    JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                    WHERE pupil_id =%s 
                    """, (111111,))


