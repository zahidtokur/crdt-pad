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
