from django.shortcuts import render
from django.views.generic import View, TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.urls import reverse
import calendar
from datetime import date, timedelta
from django.utils.dateparse import parse_date
from checker.models import Exam, Student
from core.models import Franchise



def home(request):
    """Home page - dashboard"""
    upcoming_exams = Exam.objects.filter(exam_date__gte=date.today()).order_by('exam_date')
    total_exams = Exam.objects.count()
    total_students = Student.objects.count()
    total_franchises = Franchise.objects.count()

    context = {
        'upcoming_exams': upcoming_exams,
        'total_exams': total_exams,
        'total_students': total_students,
        'total_franchises': total_franchises,
    }
    return render(request, 'index.html', context)



class CustomLoginView(LoginView):
    template_name = 'auth/login.html'
    redirect_authenticated_user = True 

    def form_valid(self, form):
        remember_me = self.request.POST.get('remember_me')
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)
        return super().form_valid(form)

    def get_success_url(self):

        return self.get_redirect_url() or reverse('home')
    
class CustomLogoutView(LogoutView):
    next_page = 'login'