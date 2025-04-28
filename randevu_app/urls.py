
from django.contrib import admin
from django.urls import path,include
from django.conf import settings       # settings'i import et
from django.conf.urls.static import static # static'i import et
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('randevu/', include('randevu.urls', namespace='randevu')),
    path('', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),

    path(
        'hesap/giris/',
        auth_views.LoginView.as_view(template_name='registration/login.html'),
        name='login' # Bu ismi settings.py'da kullanacağız
    ),
    # Çıkış İşlemi (/hesap/cikis/ adresinde olacak)
    path(
        'hesap/cikis/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
