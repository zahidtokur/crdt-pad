from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def echo(request):
    return render(request, 'pad/echo.html')


@login_required
def document(request, doc_id):
    return render(request, 'pad/document.html', {'doc_id': doc_id})

