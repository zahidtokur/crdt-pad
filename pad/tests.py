import json

from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.conf import settings

from config.asgi import application
from .models import Document

HEADERS = [(b'origin', b'http://testserver')]


def communicator(path, session_id=None):
    headers = list(HEADERS)
    if session_id:
        headers.append((b'cookie', f'sessionid={session_id}'.encode()))
    return WebsocketCommunicator(application, path, headers=headers)


class DocumentGroupTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.editor_1 = get_user_model().objects.create_user('user1', password='pw')
        self.editor_2 = get_user_model().objects.create_user('user2', password='pw')
        self.document = Document.objects.create(owner=self.editor_1, title='Test Document')
        self.document.editors.add(self.editor_1, self.editor_2)
        self.outsider = get_user_model().objects.create_user('user3', password='pw')
    
    def session_id_for(self, user):
        self.client.force_login(user)
        return self.client.cookies['sessionid'].value
    
    async def test_anonymous_connection_is_rejected(self):
        ws = communicator(f'/ws/documents/{self.document.pk}/')
        connected, _ = await ws.connect()
        self.assertFalse(connected)
        
    async def test_unauthorized_connection_is_rejected(self):
        session_id = await sync_to_async(self.session_id_for)(self.outsider)
        ws = communicator(f'/ws/documents/{self.document.pk}/', session_id)
        connected, _ = await ws.connect()
        self.assertFalse(connected)
        
    async def test_authorized_connection_is_accepted(self):
        session_id = await sync_to_async(self.session_id_for)(self.editor_1)
        ws = communicator(f'/ws/documents/{self.document.pk}/', session_id)
        connected, _ = await ws.connect()
        self.assertTrue(connected)
        
        await ws.disconnect()
        
    async def test_user_connection_messages(self):
        editor_1_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_1))
        self.assertTrue((await editor_1_ws.connect())[0])
        initial_msg = await editor_1_ws.receive_from()
        self.assertEqual(json.loads(initial_msg).get("type"), "active_users")
        
        editor_2_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_2))
        self.assertTrue((await editor_2_ws.connect())[0])
        initial_msg = await editor_2_ws.receive_from()
        self.assertEqual(json.loads(initial_msg).get("type"), "active_users")
        
        user_join_msg = await editor_1_ws.receive_from()
        self.assertEqual(json.loads(user_join_msg), 
                         {"type": "user_join", "username": self.editor_2.username})
        
        await editor_1_ws.disconnect()
        user_leave_msg = await editor_2_ws.receive_from()
        self.assertEqual(json.loads(user_leave_msg), 
                         {"type": "user_leave", "username": self.editor_1.username})
        
        await editor_2_ws.disconnect()
        
    async def test_document_update_received(self):
        editor_1_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_1))
        await editor_1_ws.connect()
        await editor_1_ws.receive_from() # pop initial message
        
        editor_2_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_2))
        await editor_2_ws.connect()
        await editor_2_ws.receive_from() # pop initial message
        await editor_1_ws.receive_from() # pop 'user_join' message
        
        document_update_msg = json.dumps({'type': 'document_update',
                                          'text': 'hi'})
        await editor_1_ws.send_to(text_data=document_update_msg)
        
        self.assertEqual(await editor_2_ws.receive_from(), document_update_msg)
        self.assertTrue(await editor_1_ws.receive_nothing())
        
        await editor_1_ws.disconnect()
        await editor_2_ws.disconnect()
        
    async def test_cursor_update_received(self):
        editor_1_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_1))
        await editor_1_ws.connect()
        await editor_1_ws.receive_from() # pop initial message
        
        editor_2_ws = communicator(f'/ws/documents/{self.document.pk}/', 
                                    await sync_to_async(self.session_id_for)(self.editor_2))
        await editor_2_ws.connect()
        await editor_2_ws.receive_from() # pop initial message
        await editor_1_ws.receive_from() # pop 'user_join' message
        
        cursor_update_msg = json.dumps({'type': 'cursor_update',
                                        'cursor_position': 10,
                                        'username': self.editor_1.username})
        await editor_1_ws.send_to(text_data=cursor_update_msg)
        
        self.assertEqual(await editor_2_ws.receive_from(), cursor_update_msg)
        self.assertTrue(await editor_1_ws.receive_nothing())
        
        await editor_1_ws.disconnect()
        await editor_2_ws.disconnect()

    async def test_multiple_connection_for_same_user(self):
        observer = communicator(f'/ws/documents/{self.document.pk}/', 
                              await sync_to_async(self.session_id_for)(self.editor_1))
        self.assertTrue((await observer.connect())[0])
        await observer.receive_from() # pop initial message
        
        conn_1 = communicator(f'/ws/documents/{self.document.pk}/', 
                              await sync_to_async(self.session_id_for)(self.editor_2))
        self.assertTrue((await conn_1.connect())[0])
        
        user_join_msg = await observer.receive_from()
        self.assertEqual(json.loads(user_join_msg), 
                         {"type": "user_join", "username": self.editor_2.username})
        
        conn_2 = communicator(f'/ws/documents/{self.document.pk}/', 
                             await sync_to_async(self.session_id_for)(self.editor_2))
        self.assertTrue((await conn_2.connect())[0])
        self.assertTrue(await observer.receive_nothing()) # doesn't receive 'user_join' msg
        
        await conn_2.disconnect()
        self.assertTrue(await observer.receive_nothing()) # doesn't receive 'user_leave' msg
        
        await conn_1.disconnect()
        user_leave_msg = await observer.receive_from()
        self.assertEqual(json.loads(user_leave_msg), 
                         {"type": "user_leave", "username": self.editor_2.username})
        
        await observer.disconnect()

    def test_document_page_requires_login(self):
        response = self.client.get(f'/documents/{self.document.pk}/')
        self.assertEqual(response.status_code, 302)
