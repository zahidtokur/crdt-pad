from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        username = self.scope['user'].username
        await self.send(text_data=f'{username}: {text_data}')


class DocumentConsumer(AsyncWebsocketConsumer):
    group_name = None

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        doc_id = self.scope['url_route']['kwargs']['doc_id']
        self.group_name = f'document_{doc_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        username = self.scope['user'].username
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'document.message', 'message': f'{username}: {text_data}'},
        )

    async def document_message(self, event):
        await self.send(text_data=event['message'])
