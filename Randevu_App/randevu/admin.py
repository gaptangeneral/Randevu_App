# randevu/admin.py

from django.contrib import admin
# Modellerimizi import ediyoruz
from .models import Service, Appointment, WorkingHours, BusinessSettings, ServiceCategory

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    """ServiceCategory modeli için Admin Panel görünümü."""
    list_display = ('name',)
    search_fields = ('name',)
    # İsteğe bağlı: Eğer order alanı eklediyseniz: list_display = ('name', 'order'), list_editable = ('order',)

@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    """BusinessSettings modeli için Admin Panel görünümü."""
    list_display = ('site_name', 'logo')

    def has_add_permission(self, request):
        # Sadece bir kayıt olmasına izin ver
        return not BusinessSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Silme yetkisini kaldır
        return False

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Service modeli için Admin Panel görünümünü özelleştirir."""
    list_display = ('name', 'category', 'duration', 'price', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'category__name')
    list_editable = ('category', 'duration', 'price', 'is_active')
    ordering = ('category__name', 'name')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Appointment modeli için Admin Panel görünümünü özelleştirir."""
    list_display = (
        'id',
        'customer_name',
        'start_time',
        'display_services', # Özel metod
        'get_total_duration_display', # Özel metod
        'status',
        'created_at'
    )
    list_filter = ('status', 'start_time', 'created_at', 'service__category') # Kategoriye göre filtre ekleyebiliriz
    search_fields = ('customer_name', 'customer_phone', 'service__name')
    readonly_fields = ('created_at', 'cancellation_code', 'end_time', 'get_total_duration') # Süreyi de readonly yapalım
    list_per_page = 25
    date_hierarchy = 'start_time'
    ordering = ('-start_time',)

    # Seçili hizmetleri göstermek için özel metod
    def display_services(self, obj):
        """ Randevuya bağlı hizmetlerin isimlerini virgülle ayırarak döndürür. """
        try:
            return ", ".join([service.name for service in obj.service.all()])
        except Exception:
            return "N/A"
    display_services.short_description = 'Seçilen Hizmetler'

    # Toplam süreyi göstermek için özel metod
    def get_total_duration_display(self, obj):
        """ Toplam süreyi dakika cinsinden döndürür. """
        return f"{obj.get_total_duration()} dk"
    get_total_duration_display.short_description = 'Toplam Süre'

    # Admin detay sayfasında M2M alanını daha kullanışlı yap
    filter_horizontal = ('service',)

@admin.register(WorkingHours)
class WorkingHoursAdmin(admin.ModelAdmin):
    """WorkingHours modeli için Admin Panel görünümünü özelleştirir."""
    list_display = ('get_day_of_week_display_custom', 'start_time', 'end_time', 'is_closed')
    list_editable = ('start_time', 'end_time', 'is_closed')
    ordering = ('day_of_week',)
    list_per_page = 10

    def get_day_of_week_display_custom(self, obj):
        """ list_display'de okunabilir gün ismini göstermek için helper metod """
        return obj.get_day_of_week_display()
    get_day_of_week_display_custom.short_description = 'Haftanın Günü'
