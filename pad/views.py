from django.shortcuts import render


def echo(request):
    return render(request, 'pad/echo.html')
