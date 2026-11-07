from django.contrib.auth.views import LoginView, LogoutView
from accounts.views import SignUpView
from django.urls import path

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("sign-up/", SignUpView.as_view(), name="sign-up"),
]
