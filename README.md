# OSB Firma Veri Toplama Sistemi

Türkiye'deki Organize Sanayi Bölgelerinin (OSB) web sitelerinden firma bilgilerini otomatik olarak toplamak, temizlemek, standartlaştırmak ve dışa aktarmak için geliştirilmiş Python tabanlı bir veri otomasyon projesidir.

Bu proje, staj süresince farklı OSB web sitelerindeki firma bilgilerinin manuel olarak toplanması yerine otomatikleştirilmesi amacıyla geliştirilmiştir.

## Özellikler

- Firma adı toplama
- Sektör bilgisi toplama
- Telefon numarası toplama
- E-posta adresi toplama
- Web sitesi bilgisi toplama
- Adres bilgisi toplama
- Türkçe karakter normalizasyonu
- Eksik iletişim bilgileri için alternatif arama mekanizması
- CSV çıktısı oluşturma
- Google Sheets entegrasyonu
- Hata yönetimi
- Tekrar deneme mekanizması
- Tekrarlanan kayıtların önlenmesi

## Sistem Nasıl Çalışır?

Proje genel olarak aşağıdaki veri akışını kullanır:

OSB Web Sitesi  
↓  
Firma Listesinin Alınması  
↓  
Firma Detay Sayfalarının Taranması  
↓  
Verilerin Temizlenmesi ve Standartlaştırılması  
↓  
İletişim Bilgilerinin Kontrol Edilmesi  
↓  
CSV / Google Sheets Aktarımı  

## Kullanılan Teknolojiler

- Python
- Requests
- BeautifulSoup
- Google Sheets API
- Google OAuth / Service Account

## Proje Yapısı

```text
osb-company-scraper/
│
├── scraper.py
├── processing/
│   └── cleaner.py
├── requirements.txt
├── README.md
└── .gitignore
