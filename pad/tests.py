from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from config.asgi import application

HEADERS = [(b'origin', b'http://testserver')]


def communicator(path, session_id=None):
    headers = list(HEADERS)
    if session_id:
        headers.append((b'cookie', f'sessionid={session_id}'.encode()))
    return WebsocketCommunicator(application, path, headers=headers)


class EchoAuthTests(TestCase):
    def session_id_for(self, username):
        user = get_user_model().objects.create_user(username, password='pw')
        client = Client()
        client.force_login(user)
        return client.cookies['sessionid'].value

    async def test_anonymous_connection_is_rejected(self):
        ws = communicator('/ws/echo/')
        connected, _ = await ws.connect()
        self.assertFalse(connected)

    async def test_invalid_session_is_rejected(self):
        ws = communicator('/ws/echo/', session_id='invalid')
        connected, _ = await ws.connect()
        self.assertFalse(connected)

    async def test_each_connection_is_tied_to_its_user(self):
        alice_session = await sync_to_async(self.session_id_for)('alice')
        bob_session = await sync_to_async(self.session_id_for)('bob')
        alice = communicator('/ws/echo/', alice_session)
        bob = communicator('/ws/echo/', bob_session)
        self.assertTrue((await alice.connect())[0])
        self.assertTrue((await bob.connect())[0])

        await alice.send_to(text_data='hi')
        await bob.send_to(text_data='hello')
        self.assertEqual(await alice.receive_from(), 'alice: hi')
        self.assertEqual(await bob.receive_from(), 'bob: hello')

        await alice.disconnect()
        await bob.disconnect()

    def test_echo_page_requires_login(self):
        response = self.client.get('/echo/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))
