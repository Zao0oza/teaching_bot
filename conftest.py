import asyncio
import logging
from pathlib import Path

import pytest

from pyrogram import Client

from tgintegration import BotController

examples_dir = Path(__file__).parent.parent

logger = logging.getLogger("tgintegration")
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
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


@pytest.fixture(scope="session")
async def client() -> Client:
    # noinspection PyCallingNonCallable
    client = Client(
        session_name="tgintegration_examples",
        workdir=examples_dir,
        api_id=api_id, api_hash=api_hash
    )
    await client.start()
    yield client
    await client.stop()


@pytest.fixture(scope="module")
async def controller(client):
    c = BotController(
        client=client,
        peer="@rusteach_bot",
        max_wait=10.0,
        wait_consecutive=0.8,
    )
    await c.initialize(start_client=False)
    yield c