import asyncio

from bot import *

from pathlib import Path

# This example uses the configuration of `config.ini` (see examples/README)
examples_dir = Path(__file__).parent.parent.absolute()
SESSION_NAME: str = "tgintegration_examples"

import pytest
from pyrogram import Client

from tgintegration import BotController
from tgintegration import Response

api_id = 19442712
api_hash = "fbf8febe2162a37c4bf2aeb2af309ee1"
# This example uses the configuration of `config.ini` (see examples/README)
examples_dir = Path(__file__).parent.parent.absolute()
SESSION_NAME: str = "tgintegration_examples"

@pytest.yield_fixture(scope="session", autouse=True)
def event_loop(request):
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# This example uses the configuration of `config.ini` (see examples/README)
def create_client(session_name: str = SESSION_NAME) -> Client:
    client = Client(
        session_name=session_name,
        workdir=examples_dir,
        api_id=api_id, api_hash=api_hash
    )
    client.load_config()
    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
class TestAsync:

    async def test_quick_if_pupil_exist(self):

        '''Быстро пробегаем по уроку'''
        controller = BotController(
            peer="@rusteach_bot",  # We are going to run tests on https://t.me/BotListBot
            client=create_client(),
            max_wait=6,  # Maximum timeout for responses (optional)
            wait_consecutive=4,  # Minimum time to wait for more/consecutive messages (optional)
            raise_no_response=True,  # Raise `InvalidResponseError` when no response received (defaults to True)
            global_action_delay=2.5,  # Choosing a rather high delay so we can follow along in realtime (optional)
        )
        sleep_time = 0.5
        async with controller.collect(count=1) as response:  # type: Response
            await controller.send_command("/start")
        sql_request = """ UPDATE pupils 
                                      SET CUR_EXERCISE = 1
                                      WHERE pupil_id = 370647884"""
        sql_conn(sql_request, ('',))
        await controller.send_command("да", add_bot_name=False)
        await sleep(sleep_time)
        for i in range(4):
            await sleep(sleep_time)
            await controller.send_command("right_answer", add_bot_name=False)
        await sleep(sleep_time)
        await controller.send_command("да", add_bot_name=False)
        await sleep(sleep_time)
        await controller.send_command("right_answer", add_bot_name=False)
        await sleep(sleep_time)
        await controller.send_command("да", add_bot_name=False)
        await sleep(sleep_time)
        async with controller.collect(count=2) as response:  # type: Response
            await controller.send_command("right_answer", add_bot_name=False)
        await controller.send_command("да", add_bot_name=False)
        assert response.num_messages == 2
        assert "молодец" in response.full_text.lower()


    async def test_complete_with_new_pupil(self):
        '''Прогоняем бота по всему курсу'''
        controller2 = BotController(
            peer="@rusteach_bot",  # We are going to run tests on https://t.me/BotListBot
            client=create_client(),
            # max_wait=2,  # Maximum timeout for responses (optional)
            wait_consecutive=1,  # Minimum time to wait for more/consecutive messages (optional)
            raise_no_response=True,  # Raise `InvalidResponseError` when no response received (defaults to True)
            # global_action_delay=2.5,  # Choosing a rather high delay so we can follow along in realtime (optional)
        )
        sql_request = """ DELETE FROM pupils WHERE pupil_id=370647884"""
        sql_conn(sql_request, ('',))
        async with controller2.collect(count=2) as response:  # type: Response
            await controller2.send_command("/start")
        assert response.num_messages == 1
        await controller2.send_command("test_pupil", add_bot_name=False)
        async with controller2.collect(count=1) as response:  # type: Response
            await controller2.send_command("да", add_bot_name=False)
        assert response.num_messages == 1

        async with controller2.collect(count=1) as response:  # type: Response
            await controller2.send_command("wrong_answer", add_bot_name=False)
        assert response.num_messages == 1
        while 'поздравляю' not in response.full_text.lower():
            async with controller2.collect(count=2) as response:  # type: Response
                await controller2.send_command("right_answer", add_bot_name=False)
            assert response.num_messages == 2
            if "молодец" in response.full_text.lower():
                await controller2.send_command("да", add_bot_name=False)
            else:
                assert "верно" in response.full_text.lower()


def test_get_pupil_from_db():
    exercise = ('test_pupil', 'question', 'wrong answer;wrong answer;wrong answer;wrong answer;', 'right_answer')
    assert exercise == sql_conn("""SELECT PUPIL_NAME, EXERCISE, CHOICES, RIGHT_ANSWER FROM public.exercises
                    JOIN pupils on pupils.cur_exercise=exercises.exercise_id
                    WHERE pupil_id =%s 
                    """, (1,))


def test_last_answer_for_lesson_from_db():
    assert (4,) == sql_conn("""SELECT MAX(EXERCISE_ID) FROM public.EXERCISEs
                                GROUP BY LESSON
                                HAVING LESSON  =%s 
                                """, (1,))
