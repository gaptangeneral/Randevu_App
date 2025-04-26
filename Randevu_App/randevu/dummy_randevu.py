# --- Dummy Randevu Oluşturma Betiği ---
import random
import datetime
from django.utils import timezone
# Modelleri doğru import ettiğinizden emin olun
from randevu.models import Service, Appointment, WorkingHours

def create_dummy_appointments(days_past=7, appointments_per_day_range=(5, 15)):
    """ Belirtilen gün sayısı kadar geçmişe dönük dummy randevular oluşturur. """

    print(f"Dummy randevu oluşturma başlatılıyor ({days_past} gün)...")

    active_services = list(Service.objects.filter(is_active=True))
    working_hours_map = {wh.day_of_week: wh for wh in WorkingHours.objects.all()}

    if not active_services:
        print("HATA: Hiç aktif servis bulunamadı. Lütfen önce servis ekleyin.")
        return
    if not working_hours_map:
        print("HATA: Hiç çalışma saati tanımlanmamış. Lütfen önce çalışma saatlerini ekleyin.")
        return

    today = timezone.localdate()
    current_tz = timezone.get_current_timezone()
    created_count = 0

    for i in range(days_past):
        current_date = today - datetime.timedelta(days=i)
        day_of_week = current_date.weekday()

        print(f"\n{current_date} ({day_of_week}) için randevular oluşturuluyor...")

        if day_of_week not in working_hours_map or working_hours_map[day_of_week].is_closed:
            print(f"-> Gün {day_of_week} için çalışma saati yok veya gün kapalı. Atlanıyor.")
            continue

        wh = working_hours_map[day_of_week]
        if not wh.start_time or not wh.end_time:
            print(f"-> Gün {day_of_week} için başlangıç/bitiş saati eksik. Atlanıyor.")
            continue

        num_appointments = random.randint(*appointments_per_day_range)
        print(f"-> {num_appointments} adet randevu oluşturulacak.")

        day_start_dt_naive = datetime.datetime.combine(current_date, wh.start_time)
        day_end_dt_naive = datetime.datetime.combine(current_date, wh.end_time)

        for _ in range(num_appointments):
            try:
                random_service = random.choice(active_services)
                service_duration = datetime.timedelta(minutes=random_service.duration)

                latest_possible_start_naive = day_end_dt_naive - service_duration
                if latest_possible_start_naive < day_start_dt_naive:
                    print(f"-> Servis süresi ({random_service.duration}dk) uygun değil, atlanıyor.")
                    continue

                start_timestamp = int(day_start_dt_naive.timestamp())
                end_timestamp = int(latest_possible_start_naive.timestamp())

                if start_timestamp >= end_timestamp:
                    print(f"-> Başlangıç/bitiş aralığı geçersiz, atlanıyor.")
                    continue

                random_timestamp = random.randint(start_timestamp, end_timestamp)
                start_dt_naive = datetime.datetime.fromtimestamp(random_timestamp)

                start_time_aware = timezone.make_aware(start_dt_naive, current_tz)

                customer_name = f"Müşteri {random.randint(100, 999)}"
                customer_phone = f"05{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(10, 99)} {random.randint(10, 99)}"

                appointment = Appointment(
                    service=random_service,
                    start_time=start_time_aware,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    status=random.choice(['confirmed', 'completed']),
                )
                appointment.save()
                created_count += 1
                print(f"  + Randevu #{appointment.id} ({appointment.start_time.strftime('%H:%M')}) oluşturuldu.")

            except Exception as e:
                print(f"  ! Randevu oluştururken hata: {e}")

    print(f"\nToplam {created_count} adet dummy randevu oluşturuldu.")

# Betiği çalıştırmak için: create_dummy_appointments()