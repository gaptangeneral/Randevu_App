// static/js/admin_charts.js

// DOM'un tamamen yüklenmesini bekle
document.addEventListener('DOMContentLoaded', function() {
    console.log("admin_charts.js yüklendi. Grafikler oluşturuluyor...");

    // Grafik 1: Günlük Randevular
    const dailyChartElement = document.querySelector("#dailyAppointmentsChartApex");
    if (dailyChartElement) {
        try {
            // Veriyi data attribute'larından al ve JSON olarak parse et
            const dailyLabels = JSON.parse(dailyChartElement.dataset.labels || '[]');
            const dailyData = JSON.parse(dailyChartElement.dataset.data || '[]');

            console.log("Günlük Etiketler (JS - data attr):", dailyLabels);
            console.log("Günlük Veri (JS - data attr):", dailyData);

            if (typeof ApexCharts !== 'undefined') { // Kütüphane yüklü mü?
                const dailyChartOptions = {
                    chart: { type: 'line', height: 350, toolbar: { show: false }, zoom: { enabled: false } },
                    series: [{ name: 'Randevu Sayısı', data: dailyData }],
                    xaxis: { categories: dailyLabels },
                    yaxis: { title: { text: 'Randevu Sayısı' }, min: 0 },
                    stroke: { curve: 'smooth' },
                    tooltip: { y: { formatter: function (val) { return val + " adet" } } },
                    markers: { size: 5 },
                    grid: { borderColor: '#e7e7e7', row: { colors: ['#f3f3f3', 'transparent'], opacity: 0.5 } }
                };
                const dailyChart = new ApexCharts(dailyChartElement, dailyChartOptions);
                dailyChart.render();
                console.log("Günlük grafik render edildi.");
            } else {
                console.error("ApexCharts kütüphanesi bulunamadı! (Günlük Grafik)");
            }
        } catch (e) {
            console.error("Günlük grafik oluşturulurken hata:", e);
            dailyChartElement.innerHTML = "<p class='text-red-500'>Grafik yüklenirken bir hata oluştu.</p>";
        }
    } else {
        console.warn("Günlük grafik elementi (#dailyAppointmentsChartApex) bulunamadı.");
    }

    // Grafik 2: Hizmet Dağılımı
    const serviceChartElement = document.querySelector("#serviceDistributionChartApex");
    if (serviceChartElement) {
         try {
            // Veriyi data attribute'larından al ve JSON olarak parse et
            const serviceLabels = JSON.parse(serviceChartElement.dataset.labels || '[]');
            const serviceData = JSON.parse(serviceChartElement.dataset.data || '[]');

            console.log("Hizmet Etiketleri (JS - data attr):", serviceLabels);
            console.log("Hizmet Verisi (JS - data attr):", serviceData);

            if (typeof ApexCharts !== 'undefined') { // Kütüphane yüklü mü?
                 const serviceChartOptions = {
                    chart: { type: 'donut', height: 350 },
                    series: serviceData,
                    labels: serviceLabels,
                    responsive: [{ breakpoint: 480, options: { chart: { width: 200 }, legend: { position: 'bottom' } } }],
                    plotOptions: { pie: { donut: { labels: { show: true, total: { show: true, label: 'Toplam', formatter: function (w) { return w.globals.seriesTotals.reduce((a, b) => a + b, 0) } } } } } },
                    legend: { position: 'bottom' }
                 };
                 const serviceChart = new ApexCharts(serviceChartElement, serviceChartOptions);
                 serviceChart.render();
                 console.log("Hizmet dağılım grafiği render edildi.");
             } else {
                 console.error("ApexCharts kütüphanesi bulunamadı! (Hizmet Grafiği)");
             }
         } catch (e) {
             console.error("Hizmet dağılım grafiği oluşturulurken hata:", e);
             serviceChartElement.innerHTML = "<p class='text-red-500'>Grafik yüklenirken bir hata oluştu.</p>";
         }
    } else {
         console.warn("Hizmet dağılım grafiği elementi (#serviceDistributionChartApex) bulunamadı.");
    }

});