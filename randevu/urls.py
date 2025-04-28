# randevu/urls.py

from django.urls import path
from django.contrib.auth import views as auth_views
from . import views # randevu uygulamasının views.py dosyasını import et
from django.contrib.auth.decorators import login_required, user_passes_test
from .views import is_superuser # <<< --- BU SATIRI EKLEYİN ---

app_name = 'randevu' # URL isimleri için namespace tanımlıyoruz

urlpatterns = [
    # Ana randevu oluşturma sayfası için URL
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('api/available-slots/', views.get_available_slots_api, name='api_available_slots'),
    path('basarili/', views.appointment_success_view, name='appointment_success'),
    path('iptal-kontrol/', views.appointment_lookup_cancel_view, name='appointment_lookup_cancel'),

    # Admin URL'leri
    path(
        'yonetim/dashboard/',
        # is_superuser artık burada tanımlı/import edilmiş olmalı
        login_required(user_passes_test(is_superuser)(views.admin_dashboard_view)),
        name='admin_dashboard'
    ),
    path(
        'yonetim/iptal/<int:appointment_id>/',
        login_required(user_passes_test(is_superuser)(views.admin_cancel_appointment_view)),
        name='admin_cancel_appointment'
    ),
]
