from django.urls import path

from . import views

urlpatterns = [
    path('echo/', views.echo, name='echo'),
    path('documents/<slug:doc_id>/', views.document, name='document'),
]