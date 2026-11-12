from django.urls import path
from .consumer import DocumentConsumer

websocket_urlpatterns = [
    path('ws/documents/<int:pk>/', DocumentConsumer.as_asgi()),
]