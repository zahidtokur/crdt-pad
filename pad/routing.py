from django.urls import path
from .consumer import DocumentConsumer

websocket_urlpatterns = [
    path('ws/documents/<slug:slug>/', DocumentConsumer.as_asgi()),
]