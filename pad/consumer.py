import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache

from .models import Document


class DocumentConsumer(AsyncWebsocketConsumer):
    group_name = None
    doc_cache_key = None
    user_status_cache_key = None

    async def connect(self):
        self.user = self.scope["user"]
        self.slug = self.scope["url_route"]["kwargs"]["slug"]
        
        if not await self.is_authorized():
            await self.close()
            return
        
        self.group_name = f'document_{self.slug}'
        self.doc_cache_key = f'document_{self.slug}_active_users'
        self.user_status_cache_key = f'document_{self.slug}_user_{self.user.id}'
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.on_authorized_connect()

    async def disconnect(self, code):
        if self.group_name:
            active_users = cache.get(self.doc_cache_key)
            active_users.pop(self.user.id, None)
            cache.set(self.doc_cache_key, active_users, 30)
            cache.delete(self.user_status_cache_key)
            await self.channel_layer.group_send(self.group_name, {
                "type": "user.leave",
                "user_id": self.user.id,
                "username": self.user.username,
                "sender": self.channel_name,
            })
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        msg_type = data.get("type")
        handler = getattr(self, f"handle_{msg_type.replace('.', '_')}", None) if isinstance(msg_type, str) else None

        if handler is None:
            await self.send_error("unknown_type", f"Unknown message type: {msg_type!r}")
            return

        await handler(data.get("data", {}))

    async def document_message(self, event):
        await self.send(text_data=event['message'])

    @database_sync_to_async
    def _check_perms(self):
        return self.user.is_authenticated and Document.objects.filter(
            editors=self.user, slug=self.slug).exists()

    async def is_authorized(self) -> bool:
        return await self._check_perms()
    
    async def on_authorized_connect(self):
        active_users = cache.get(self.doc_cache_key) or {}
        await self.send(json.dumps({"type": "active_users",
                                    "users": active_users}))
        
        if self.user.id not in active_users.keys():
            await self.channel_layer.group_send(self.group_name, {
                    "type": "user.join",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "sender": self.channel_name,
                })
            
            active_users.update({self.user.id: self.user.username})
            cache.set(self.doc_cache_key, active_users, 30)
            cache.set(self.user_status_cache_key, self.user.id, 30)

    async def user_join(self, event):
        if event["sender"] == self.channel_name:
            return
        await self.send(json.dumps({"type": "user_join", "username": event["username"]}))
        
    async def user_leave(self, event):
        if event["sender"] == self.channel_name:
            return
        await self.send(json.dumps({"type": "user_leave", "username": event["username"]}))
        
    async def send_error(self, code, detail):
        await self.send(json.dumps({"type": "error", "code": code, "detail": detail}))

    async def handle_heartbeat(self, data):
        cache.touch(self.doc_cache_key)
        cache.touch(self.user_status_cache_key)
