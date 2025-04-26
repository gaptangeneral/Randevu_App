# Genellikle uygulamanızın içinde context_processors.py adında bir dosyaya konur.
# Örneğin: settings_app/context_processors.py

# 1. Gerekli Modeli İçe Aktarın
#    'settings_app' yerine BusinessSettings modelinizin bulunduğu
#    uygulamanın adını yazın. Model adı zaten BusinessSettings.
# <<< DEĞİŞTİR >>> (Uygulama adını kendi projenize göre düzeltin)
from randevu.models import BusinessSettings

def site_ayarlari_context(request): # Fonksiyon adını değiştirdim, daha açıklayıcı
    """
    BusinessSettings modelinden site adı ve logo gibi genel ayarları alıp
    template context'ine doğrudan ekler.
    """
    settings_obj = None
    # Ayarlar bulunamazsa veya alanlar boşsa kullanılacak varsayılan değerler:
    site_adi_degeri = "Site Adı Belirtilmemiş"
    site_logo_url_degeri = None # Varsayılan olarak logo yok

    try:
        # BusinessSettings modelinden sadece bir tane olması gerektiği için ilkini alırız.
        settings_obj = BusinessSettings.objects.first()
    except Exception as e:
        # Veritabanı hatası veya model bulunamaması gibi durumlarda hata basılabilir.
        print(f"HATA: Context processor 'site_ayarlari_context' BusinessSettings nesnesini alırken sorun oluştu: {e}")
        # Hata durumunda varsayılan değerler kullanılacak.
        pass # Hata olsa bile devam et, varsayılanları döndür

    if settings_obj:
        # 2. Ayarlar nesnesinden değerleri okuyun
        #    Modelinizdeki GERÇEK alan adlarını kullanıyoruz ('site_name', 'logo')
        site_name_field = 'site_name' # admin.py'den gelen bilgi
        logo_field = 'logo'          # admin.py'den gelen bilgi

        # getattr kullanarak alanları güvenli okuma ve varsayılan atama:
        site_adi_degeri = getattr(settings_obj, site_name_field, site_adi_degeri)

        # Logo alanı için özel kontrol (alan var mı? değeri var mı? .url çalışıyor mu?)
        if hasattr(settings_obj, logo_field):
            logo_instance = getattr(settings_obj, logo_field)
            if logo_instance: # Logo alanı boş değilse
                try:
                    site_logo_url_degeri = logo_instance.url
                except ValueError:
                    # Bazen dosya atanmamışsa .url ValueError verebilir
                    site_logo_url_degeri = None

    # 3. Template'e gönderilecek sözlüğü oluşturun
    #    Buradaki anahtarlar ('site_adi', 'site_logo_url') template içinde
    #    {{ site_adi }} ve {{ site_logo_url }} olarak kullanacağınız isimlerdir.
    #    İsterseniz anahtarları model alanlarıyla aynı yapabilirsiniz ('site_name' gibi)
    #    ama önceki kullanıma uyumlu olması için 'site_adi' bırakıyorum.
    context = {
        'site_adi': site_adi_degeri,
        'site_logo_url': site_logo_url_degeri,
    }

    return context