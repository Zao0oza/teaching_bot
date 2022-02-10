import pytest
from main import *


def test_question_for_pupil_right(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda: 'right_answer')
    assert exercise_for_pupil(['question1', ['wrong answer1', 'wrong answer2', 'wrong answer3', 'right_answer'],
                              'right_answer']) is True


def test_question_for_pupil_wrong(monkeypatch):
    monkeypatch.setattr('builtins.input', lambda: 'wrong_answer')
    assert exercise_for_pupil(['question1', ['wrong answer1', 'wrong answer2', 'wrong answer3', 'right_answer'],
                              'right_answer']) is False


#@pytest.mark.parametrize('user_id', 'question_id', [(1, 1), (2, 2)])
#def test_get_pupil_from_db(user_id, question_id):
#    assert question_id == get_pupil_from_db(user_id)


def test_get_pupil_from_db():
    exercise =('Andrew','question2', 'wrong answer1, wrong answer2, wrong answer3, right_answer', 'right_answer')
    assert exercise == get_pupil_from_db(111111)
