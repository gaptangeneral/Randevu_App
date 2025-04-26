# randevu/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid

# --- Site Ayarları Modeli ---
class BusinessSettings(models.Model):
    """ Site adı, logo gibi genel ayarları tutar. Sadece bir tane olmalı. """
    site_name = models.CharField(max_length=100, default="Randevu Sistemi", verbose_name="Site Adı")
    logo = models.ImageField(upload_to='site_logos/', blank=True, null=True, verbose_name="Site Logosu")
    # Gelecekte başka ayarlar eklenebilir (renkler, iletişim bilgileri vb.)

    def __str__(self):
        return self.site_name or "Site Ayarları"

    class Meta:
        verbose_name = "Site Ayarı"
        verbose_name_plural = "Site Ayarları"

# --- Hizmet Kategorisi Modeli ---
class ServiceCategory(models.Model):
    """ Hizmetleri gruplamak için kategori modeli. """
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategori Adı")
    # İsteğe bağlı: Özel sıralama için order alanı eklenebilir
    # order = models.PositiveIntegerField(default=0, verbose_name="Sıralama Önceliği")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Hizmet Kategorisi"
        verbose_name_plural = "Hizmet Kategorileri"
        ordering = ['name'] # Varsayılan olarak isme göre sırala

# --- Hizmet Modeli ---
class Service(models.Model):
    """ Sunulan hizmetleri tanımlar. """
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL, # Kategori silinirse hizmetleri silme, null yap
        null=True,
        blank=True, # Kategori atanmamış hizmetler olabilir
        related_name='services',
        verbose_name="Kategori"
    )
    name = models.CharField(max_length=100, verbose_name="Hizmet Adı")
    duration = models.PositiveIntegerField(verbose_name="Süre (dakika)")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat")
    is_active = models.BooleanField(default=True, verbose_name="Aktif mi?")
    # description = models.TextField(blank=True, null=True, verbose_name="Açıklama") # İsteğe bağlı

    def __str__(self):
        category_name = self.category.name if self.category else "Kategorisiz"
        return f"{category_name} - {self.name}"

    class Meta:
        verbose_name = "Hizmet"
        verbose_name_plural = "Hizmetler"
        ordering = ['category__name', 'name'] # Önce kategori, sonra hizmet adına göre sırala

# --- Randevu Modeli ---
class Appointment(models.Model):
    """ Müşteri randevularını tutar. """
    # ManyToManyField: Bir randevu birden fazla hizmet içerebilir
    service = models.ManyToManyField(
        Service,
        verbose_name="Seçilen Hizmetler",
        related_name="appointments"
    )

    start_time = models.DateTimeField(verbose_name="Başlangıç Zamanı")
    # end_time view'de hesaplanıp atanacak
    end_time = models.DateTimeField(verbose_name="Bitiş Zamanı", null=True, blank=True)
    customer_name = models.CharField(max_length=100, verbose_name="Müşteri Adı Soyadı")
    customer_phone = models.CharField(max_length=20, verbose_name="Müşteri Telefon")
    customer_email = models.EmailField(blank=True, null=True, verbose_name="Müşteri E-posta")

    STATUS_CHOICES = (
        ('pending', 'Beklemede'),
        ('confirmed', 'Onaylandı'),
        ('cancelled', 'İptal Edildi'),
        ('completed', 'Tamamlandı'),
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='confirmed', # Varsayılan durum
        verbose_name="Durum"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    cancellation_code = models.CharField(max_length=6, unique=True, blank=True, verbose_name="İptal Kodu")

    def calculate_end_time(self):
        """ Seçili hizmetlere göre bitiş zamanını hesaplar (kaydedilmeden önce çağrılabilir). """
        if not self.start_time:
            return None
        # Henüz kaydedilmediyse veya hizmet atanmadıysa süre 0 kabul edilir
        total_duration_minutes = 0
        if self.pk and self.service.exists(): # Sadece kaydedilmiş ve hizmeti olanlar için
             total_duration_minutes = sum(s.duration for s in self.service.all())
        elif hasattr(self, '_selected_services_for_save'): # View'den geçici olarak eklenen liste varsa
            total_duration_minutes = sum(s.duration for s in self._selected_services_for_save)

        return self.start_time + timedelta(minutes=total_duration_minutes)

    def save(self, *args, **kwargs):
        # İptal kodunu sadece ilk oluşturmada ve boşsa üret
        if not self.pk and not self.cancellation_code:
            self.cancellation_code = self._generate_unique_code()
        # end_time view tarafında ilk save'den ÖNCE atanacak.
        # Bu yüzden burada tekrar hesaplamaya gerek yok.
        super().save(*args, **kwargs)

    def _generate_unique_code(self):
        """Benzersiz 6 haneli iptal kodu üretir."""
        while True:
            code = str(uuid.uuid4().int)[:6].upper() # Büyük harf kullanalım
            if not Appointment.objects.filter(cancellation_code=code).exists():
                return code

    def get_total_duration(self):
        """ Kaydedilmiş randevunun toplam hizmet süresini döndürür. """
        if not self.pk or not self.service.exists():
            return 0
        return sum(s.duration for s in self.service.all())

    def __str__(self):
        service_names = "Hizmetler Yükleniyor..."
        if self.pk: # Kaydedilmişse hizmetlere erişmeyi dene
            try:
                service_names = ", ".join(s.name for s in self.service.all())
                if not service_names: service_names = "Hizmet Seçilmemiş"
            except Exception:
                 service_names = "İlişki Hatası"

        return f"{self.customer_name} - {self.start_time.strftime('%d.%m %H:%M')} ({service_names})"

    class Meta:
        verbose_name = "Randevu"
        verbose_name_plural = "Randevular"
        ordering = ['-start_time'] # En yeni randevular başta

# --- Çalışma Saatleri Modeli ---
class WorkingHours(models.Model):
    """ Haftanın günleri için çalışma saatlerini tanımlar. """
    DAY_CHOICES = (
        (0, 'Pazartesi'), (1, 'Salı'), (2, 'Çarşamba'),
        (3, 'Perşembe'), (4, 'Cuma'), (5, 'Cumartesi'), (6, 'Pazar')
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES, unique=True, verbose_name="Haftanın Günü")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Başlangıç Saati")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Bitiş Saati")
    is_closed = models.BooleanField(default=False, verbose_name="Kapalı mı?")

    def __str__(self):
        if self.is_closed:
            return f"{self.get_day_of_week_display()} - Kapalı"
        elif self.start_time and self.end_time:
            return f"{self.get_day_of_week_display()} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"
        else:
            return f"{self.get_day_of_week_display()} - Saatler Belirtilmemiş"

    def clean(self):
        """ Doğrulama: Kapalı değilse saatler girilmeli, bitiş başlangıçtan sonra olmalı. """
        if not self.is_closed and (not self.start_time or not self.end_time):
            raise ValidationError("Gün kapalı değilse başlangıç ve bitiş saatleri belirtilmelidir.")
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("Bitiş saati, başlangıç saatinden sonra olmalıdır.")

    class Meta:
        verbose_name = "Çalışma Saati"
        verbose_name_plural = "Çalışma Saatleri"
        ordering = ['day_of_week'] # Haftanın günlerine göre sırala
