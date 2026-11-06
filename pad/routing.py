from django.urls import path
from .consumer import DocumentConsumer, EchoConsumer

websocket_urlpatterns = [
    path('ws/echo/', EchoConsumer.as_asgi()),
    path('ws/documents/<slug:doc_id>/', DocumentConsumer.as_asgi()),
]