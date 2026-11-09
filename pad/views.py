from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Document


class DocumentDetail(LoginRequiredMixin, DetailView):
    model = Document


class DocumentList(LoginRequiredMixin, ListView):
    model = Document
    paginate_by = 10

    def get_queryset(self):
        return Document.objects.filter(editors=self.request.user).prefetch_related("editors")
