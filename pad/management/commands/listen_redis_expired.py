import os
import logging
import time
import redis

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Listens to Redis expired key events and runs cleanup"

    def handle(self, *args, **options):
        while True:
            try:
                self.listen()
            except redis.ConnectionError:
                logger.exception("Redis connection dropped, will retry in 5 secs")
                time.sleep(5)

    def listen(self):
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.Redis.from_url(redis_url, decode_responses=True)

        r.config_set("notify-keyspace-events", "Ex")

        db = r.connection_pool.connection_kwargs.get("db", 0)
        pubsub = r.pubsub()
        pubsub.subscribe(f"__keyevent@{db}__:expired")

        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            self.dispatch(message["data"])

    def dispatch(self, raw_key: str):
        key = self.strip_prefix(raw_key)
        if key.startswith("document:") and not key.endswith(":active_users"):
            _, doc_pk, user_id = key.split(":", 2)
            
            # Remove from active_users
            active_users = cache.get(f"document:{doc_pk}:active_users")
            disconnected_username = active_users.get(int(user_id))
            active_users.pop(int(user_id))
            cache.set(f"document:{doc_pk}:active_users", active_users, 30)
            
            # Send user_leave message to channel
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"document_{doc_pk}",
                {
                    "type": "user_leave",
                    "user_id": user_id,
                    "username": disconnected_username,
                    "sender": "clean-up"
                }
            )
            
    def strip_prefix(self, raw_key: str) -> str:
        cache_conf = settings.CACHES["default"]
        prefix = cache_conf.get("KEY_PREFIX", "")
        version = cache_conf.get("VERSION", 1)
        full_prefix = f"{prefix}:{version}:"
        if raw_key.startswith(full_prefix):
            return raw_key[len(full_prefix):]
        return raw_key
