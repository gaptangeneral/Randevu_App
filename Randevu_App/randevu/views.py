# randevu/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, time
from django import forms
import traceback
from django.db.models.functions import TruncDate
import json
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required, user_passes_test
from collections import OrderedDict

# Modelleri import et
from .models import Service, Appointment, WorkingHours, ServiceCategory, BusinessSettings

# --- Helper Fonksiyonlar ---
def is_superuser(user):
    """ Kullanıcının süper kullanıcı olup olmadığını kontrol eder. """
    return user.is_authenticated and user.is_superuser

def get_grouped_ordered_services():
    """ Aktif hizmetleri alır, kategoriye göre gruplar ve özel sıraya göre döndürür. """
    active_services = Service.objects.filter(is_active=True).select_related('category').order_by('category__name', 'name')
    grouped_services = {}
    for service in active_services:
        category_name = service.category.name if service.category else "Diğer Hizmetler"
        if category_name not in grouped_services:
            grouped_services[category_name] = []
        grouped_services[category_name].append(service)

    # Kategori sıralaması (Veritabanındaki gerçek isimleri kullanın!)
    desired_order = ["Otomobil", "Ticari", "Diğer"]
    ordered_grouped_services = []

    for category_name in desired_order:
        if category_name in grouped_services:
            ordered_grouped_services.append( (category_name, grouped_services[category_name]) )
            del grouped_services[category_name]

    for category_name, services_in_category in sorted(grouped_services.items()):
         ordered_grouped_services.append( (category_name, services_in_category) )

    return ordered_grouped_services


# --- Yönetici Paneli View'leri ---

@login_required
@user_passes_test(is_superuser)
def admin_dashboard_view(request):
    """ Admin dashboard sayfasını gösterir. """
    # === Randevu Listesi ===
    try:
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_appointments = Appointment.objects.filter(
            Q(created_at__gte=seven_days_ago) | Q(start_time__gte=timezone.now()),
            status__in=['pending', 'confirmed']
        ).order_by('-start_time').prefetch_related('service') # Hizmetleri de çekelim
    except Exception as e:
        print(f"HATA: Son randevular çekilirken: {e}")
        recent_appointments = Appointment.objects.none()
        messages.error(request, "Son randevular yüklenirken bir sorun oluştu.")

    # === Raporlama Verileri ===
    daily_labels, daily_data, service_labels, service_data = [], [], [], []
    try:
        # Günlük Randevu Sayısı
        daily_counts_queryset = Appointment.objects.filter(
            start_time__date__gte=seven_days_ago.date()
        ).annotate(date=TruncDate('start_time')).values('date').annotate(count=Count('id')).order_by('date')
        daily_labels = [item['date'].strftime('%d %b') for item in daily_counts_queryset]
        daily_data = [item['count'] for item in daily_counts_queryset]

        # Hizmet Dağılımı
        valid_appointments = Appointment.objects.filter(
            status__in=['pending', 'confirmed', 'completed']
        ).prefetch_related('service')
        service_counts = {}
        for appt in valid_appointments:
            for service in appt.service.all():
                service_counts[service.name] = service_counts.get(service.name, 0) + 1
        sorted_service_counts = dict(sorted(service_counts.items(), key=lambda item: item[1], reverse=True))
        service_labels = list(sorted_service_counts.keys())
        service_data = list(sorted_service_counts.values())

    except Exception as e:
        print(f"HATA: Rapor verileri oluşturulurken: {e}")
        traceback.print_exc()
        messages.error(request, "Rapor verileri oluşturulurken bir sorun oluştu.")

    # JSON'a çevirme
    try:
        daily_labels_json = json.dumps(daily_labels)
        daily_data_json = json.dumps(daily_data)
        service_labels_json = json.dumps(service_labels)
        service_data_json = json.dumps(service_data)
    except Exception as json_e:
        print(f"HATA: Veriler JSON'a çevrilirken: {json_e}")
        messages.error(request, "Grafik verileri hazırlanırken bir sorun oluştu.")
        daily_labels_json, daily_data_json, service_labels_json, service_data_json = '[]', '[]', '[]', '[]'

    context = {
        'recent_appointments': recent_appointments,
        'daily_labels': daily_labels_json,
        'daily_data': daily_data_json,
        'service_labels': service_labels_json,
        'service_data': service_data_json,
        'section': 'dashboard'
    }
    return render(request, 'randevu/admin_dashboard.html', context)

@login_required
@user_passes_test(is_superuser)
def admin_cancel_appointment_view(request, appointment_id):
    """ Admin tarafından bir randevuyu iptal etmek için kullanılır. """
    try:
        appointment = get_object_or_404(Appointment, pk=appointment_id)
        if appointment.status != 'cancelled':
            original_status = appointment.get_status_display()
            appointment.status = 'cancelled'
            appointment.save(update_fields=['status']) # Sadece status'u güncelle
            messages.success(request, f"#{appointment.id} numaralı randevu başarıyla iptal edildi.")
        else:
            messages.warning(request, f"#{appointment.id} numaralı randevu zaten iptal edilmiş.")
    except Exception as e:
        messages.error(request, f"Randevu iptal edilirken bir hata oluştu: {e}")
    return redirect('randevu:admin_dashboard')


# --- Randevu Oluşturma View'leri ---

def appointment_create_view(request):
    """ Randevu oluşturma formunu gösterir ve işler. """
    if request.method == 'POST':
        # 1. Formdan verileri al
        service_ids = request.POST.getlist('service')
        date_str = request.POST.get('date')
        selected_time_str = request.POST.get('selected_time_slot')
        customer_name = request.POST.get('customer_name', '').strip()
        customer_phone = request.POST.get('customer_phone', '').strip()
        customer_email = request.POST.get('customer_email', '').strip()

        # 2. Temel Doğrulamalar
        form_valid = True
        if not service_ids:
            messages.error(request, 'Lütfen en az bir hizmet seçin.')
            form_valid = False
        if not all([date_str, selected_time_str, customer_name, customer_phone]):
            messages.error(request, 'Lütfen tüm zorunlu alanları doldurun.')
            form_valid = False

        # Eğer temel doğrulamada hata varsa, formu tekrar göster
        if not form_valid:
            context = {
                'ordered_grouped_services': get_grouped_ordered_services(),
                'submitted_data': request.POST,
                # Checkbox seçimlerini korumak için ID listesini string'e çevirip gönderelim
                'selected_service_ids_str': service_ids
             }
            return render(request, 'randevu/appointment_form.html', context)

        try:
            # 3. Verileri Gerekli Tiplere Dönüştür ve Hizmetleri Al
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            selected_time = datetime.strptime(selected_time_str, '%H:%M').time()
            selected_services = Service.objects.filter(pk__in=service_ids, is_active=True)

            if len(selected_services) != len(service_ids):
                raise ValueError("Seçilen hizmetlerden bazıları geçersiz veya aktif değil.")

            # 4. Toplam Süre ve Zaman Dilimi/Geçerlilik Kontrolleri
            total_duration = timedelta(minutes=sum(s.duration for s in selected_services))
            if total_duration.total_seconds() <= 0:
                 raise ValueError("Seçilen hizmetlerin toplam süresi 0 veya daha az olamaz.")

            if selected_date < timezone.localdate():
                raise ValueError("Geçmiş bir tarih seçilemez.")
            if selected_date == timezone.localdate() and selected_time < timezone.localtime().time():
                 # Sadece saati kontrol et, eşitliğe izin verilebilir belki?
                 # Şimdilik küçükse hata verelim.
                raise ValueError("Geçmiş bir saat seçilemez.")

            tz = timezone.get_current_timezone()
            start_time_aware = timezone.make_aware(datetime.combine(selected_date, selected_time), tz)
            end_time_aware = start_time_aware + total_duration

            # Çalışma saatleri kontrolü
            working_hours = WorkingHours.objects.get(day_of_week=selected_date.weekday())
            if working_hours.is_closed:
                 raise ValueError(f"{selected_date.strftime('%d.%m.%Y')} tarihi kapalıdır.")
            if not working_hours.start_time or not working_hours.end_time:
                 raise ValueError("Seçilen gün için çalışma saatleri tanımlanmamış.")

            day_start_dt_aware = timezone.make_aware(datetime.combine(selected_date, working_hours.start_time), tz)
            day_end_dt_aware = timezone.make_aware(datetime.combine(selected_date, working_hours.end_time), tz)

            if start_time_aware < day_start_dt_aware or end_time_aware > day_end_dt_aware:
                raise ValueError(f"Seçilen saat ({selected_time_str}) veya hizmet süresi ({total_duration}) çalışma saatleri ({working_hours.start_time.strftime('%H:%M')} - {working_hours.end_time.strftime('%H:%M')}) dışındadır.")

            # 5. Çakışma Kontrolü
            overlapping_appointments = Appointment.objects.filter(
                start_time__date=selected_date,
                status__in=['pending', 'confirmed'],
                end_time__isnull=False
            ).filter(
                start_time__lt=end_time_aware,
                end_time__gt=start_time_aware
            )

            if overlapping_appointments.exists():
                raise ValueError("Üzgünüz, seçtiğiniz saat ve süre boyunca başka bir randevu bulunmaktadır.")

            # 6. Randevuyu Oluştur ve Kaydet
            appointment = Appointment(
                start_time=start_time_aware,
                end_time=end_time_aware,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email or None, # Boşsa NULL yap
                status='confirmed'
            )
            # Geçici olarak hizmet listesini ekleyelim ki save metodu içinde erişilebilsin (eğer gerekirse)
            # appointment._selected_services_for_save = selected_services
            appointment.save() # cancellation_code üretilir

            # 7. ManyToMany İlişkisini Kur
            appointment.service.set(selected_services)

            # 8. Başarı Sayfasına Yönlendir
            context = {
                'appointment_id': appointment.id,
                'cancellation_code': appointment.cancellation_code,
                'appointment_time': appointment.start_time.strftime('%d.%m.%Y %H:%M'),
                'selected_services_list': [s.name for s in selected_services],
                'total_duration_minutes': total_duration.total_seconds() / 60
            }
            messages.success(request, f"{context['appointment_time']} için randevunuz başarıyla oluşturuldu!")
            return render(request, 'randevu/appointment_success.html', context)

        except WorkingHours.DoesNotExist:
            messages.error(request, f"{selected_date.strftime('%d.%m.%Y')} için çalışma saatleri bulunamadı.")
        except (Service.DoesNotExist, ValueError) as e:
            messages.error(request, f"Hata: {e}")
        except Exception as e:
            messages.error(request, "Randevu oluşturulurken beklenmedik bir hata oluştu.")
            print(f"Randevu kaydetme hatası: {e}")
            traceback.print_exc()

        # Hata durumunda formu tekrar göster
        context = {
            'ordered_grouped_services': get_grouped_ordered_services(),
            'submitted_data': request.POST,
            'selected_service_ids_str': service_ids
         }
        return render(request, 'randevu/appointment_form.html', context)

    else: # GET İsteği
        context = {
            'ordered_grouped_services': get_grouped_ordered_services()
        }
        return render(request, 'randevu/appointment_form.html', context)


def appointment_success_view(request):
    """ Başarı sayfasını gösterir. """
    return render(request, 'randevu/appointment_success.html')


# --- API View ---

def get_available_slots_api(request):
    """ Müsait saatleri hesaplar ve JSON döndürür (toplam süreye göre). """
    available_slots = []
    slot_interval = 30 # Slot aralığı (dakika)

    date_str = request.GET.get('date')
    service_ids_str = request.GET.getlist('service_ids[]')

    # Parametre kontrolleri
    if not date_str:
        return JsonResponse({'error': 'Lütfen tarih seçin.'}, status=400)
    if not service_ids_str:
        return JsonResponse({'available_slots': [], 'message': 'Lütfen en az bir hizmet seçin.'}) # Hata yerine boş liste

    try:
        # Hizmetleri ve toplam süreyi hesapla
        service_ids = [int(sid) for sid in service_ids_str]
        selected_services = Service.objects.filter(pk__in=service_ids, is_active=True)

        if len(selected_services) != len(service_ids):
            # Geçersiz ID varsa hata vermek yerine belki sadece geçerlileri kullanabiliriz?
            # Şimdilik hata verelim.
             return JsonResponse({'error': 'Seçilen hizmetlerden bazıları geçersiz veya aktif değil.'}, status=400)

        total_duration_minutes = sum(s.duration for s in selected_services)
        if total_duration_minutes <= 0:
             # Süre 0 ise boş liste döndür
             return JsonResponse({'available_slots': [], 'message': 'Seçilen hizmetlerin toplam süresi 0.'})
        service_duration = timedelta(minutes=total_duration_minutes)

        # Tarih ve çalışma saatleri kontrolleri
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if selected_date < timezone.localdate():
             return JsonResponse({'available_slots': [], 'message': 'Geçmiş tarihler için saat gösterilemez.'})

        working_hours = WorkingHours.objects.get(day_of_week=selected_date.weekday())
        if working_hours.is_closed or not working_hours.start_time or not working_hours.end_time:
            return JsonResponse({'available_slots': [], 'message': 'Seçilen gün kapalı veya çalışma saatleri tanımsız.'})

        # Mevcut randevuları al
        existing_appointments = Appointment.objects.filter(
            start_time__date=selected_date,
            end_time__isnull=False
        ).exclude(status='cancelled').order_by('start_time')

        # Zaman dilimi ve slot hesaplama
        tz = timezone.get_current_timezone()
        day_start_dt_aware = timezone.make_aware(datetime.combine(selected_date, working_hours.start_time), tz)
        day_end_dt_aware = timezone.make_aware(datetime.combine(selected_date, working_hours.end_time), tz)
        current_slot_start_aware = day_start_dt_aware
        now_aware = timezone.localtime() # Mevcut zamanı döngü dışında alalım

        while True:
            slot_end_aware = current_slot_start_aware + service_duration
            if slot_end_aware > day_end_dt_aware: break # İş bitişini aştıysa döngüden çık

            is_past_time = (selected_date == now_aware.date() and current_slot_start_aware < now_aware)

            is_overlap = False
            if not is_past_time:
                for appt in existing_appointments:
                    if current_slot_start_aware < appt.end_time and slot_end_aware > appt.start_time:
                        is_overlap = True
                        break

            if not is_overlap and not is_past_time:
                available_slots.append(current_slot_start_aware.strftime('%H:%M'))

            current_slot_start_aware += timedelta(minutes=slot_interval)

    except WorkingHours.DoesNotExist:
        return JsonResponse({'available_slots': [], 'message': 'Çalışma saatleri bulunamadı.'})
    except ValueError: # Tarih formatı vs. hataları
        return JsonResponse({'error': 'Geçersiz tarih veya hizmet IDsi.'}, status=400)
    except Exception as e:
        print(f"API Hatası (get_available_slots_api): {e}")
        traceback.print_exc()
        return JsonResponse({'error': 'Müsait saatler getirilirken bir sorun oluştu.'}, status=500)

    return JsonResponse({'available_slots': available_slots})


# --- Randevu İptal View ---

def appointment_lookup_cancel_view(request):
    """ POST isteği ile gelen 6 haneli kodu kullanarak randevuyu bulur ve iptal eder. """
    cancellation_code = None
    if request.method == 'POST':
        cancellation_code = request.POST.get('cancellation_code', '').strip().upper()
        if not cancellation_code or len(cancellation_code) != 6:
            messages.error(request, "Lütfen geçerli 6 haneli bir iptal kodu girin.")
        else:
            try:
                appointment = Appointment.objects.get(cancellation_code=cancellation_code)
                if appointment.status in ['pending', 'confirmed']:
                    appointment.status = 'cancelled'
                    appointment.save(update_fields=['status'])
                    messages.success(request, f"Randevunuz başarıyla iptal edildi.")
                elif appointment.status == 'cancelled':
                    messages.warning(request, "Bu randevu zaten iptal edilmiş.")
                else:
                    messages.error(request, f"Bu randevu durumu ({appointment.get_status_display()}) nedeniyle iptal edilemez.")
            except Appointment.DoesNotExist:
                messages.error(request, f"'{cancellation_code}' kodu ile eşleşen bir randevu bulunamadı.")
            except Exception as e:
                messages.error(request, "İptal işlemi sırasında bir hata oluştu.")
                print(f"İptal (kod:{cancellation_code}) hatası: {e}")

    return redirect('randevu:appointment_create')

