from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Document

@login_required
def echo(request):
    return render(request, 'pad/echo.html')


@login_required
def document(request, doc_id):
    return render(request, 'pad/document.html', {'doc_id': doc_id})

class DocumentList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.filter(editors=self.request.user).prefetch_related("editors")