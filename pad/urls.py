from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "pad"

urlpatterns = [
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('documents/<slug:slug>/', views.DocumentDetail.as_view(), name='document-detail'),
    path('documents/', views.DocumentList.as_view(), name='document-list'),
]