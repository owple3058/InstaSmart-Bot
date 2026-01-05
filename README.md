# 🤖 Smart Instagram Bot (Open Source)

Bu proje, Python ve Selenium kullanılarak geliştirilmiş, insan davranışlarını taklit eden akıllı bir Instagram botudur. 

## 🚀 Özellikler

- **Akıllı Navigasyon:** Instagram'ın tespit algoritmalarına yakalanmamak için butonları ve linkleri insan gibi kullanır.
- **Güvenli Mod (Safe Mode):** Günlük limitleri aşmamak için otomatik hız ayarı yapar.
- **Hedef Kitle Analizi:** Belirli hesapların takipçilerini analiz eder ve kriterlere uyanları takip eder.
- **Otomatik Takipten Çıkma (Unfollow):** Sizi takip etmeyenleri veya belirli kriterleri sağlayanları takipten çıkarır.
- **Veritabanı Desteği:** Yapılan işlemleri SQLite veritabanında tutar, aynı kişiye tekrar işlem yapmaz.
- **İnsan Taklidi:** Mouse hareketleri, bekleme süreleri ve kaydırma işlemleri randomize edilmiştir.

## 🛠️ Kurulum

1. **Projeyi İndirin:**
   ```bash
   git clone https://github.com/kullaniciadi/instagram-bot.git
   cd instagram-bot
   ```

2. **Gerekli Kütüphaneleri Yükleyin:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Yapılandırma Dosyalarını Hazırlayın:**
   - `config.example.py` -> `config.py` (Kullanıcı bilgileri)
   - `comments.example.txt` -> `comments.txt` (Yorum listesi)
   - `whitelist.example.txt` -> `whitelist.txt` (Takipten çıkılmayacaklar)

   ```bash
   # Windows için örnek kopyalama
   copy config.example.py config.py
   copy comments.example.txt comments.txt
   copy whitelist.example.txt whitelist.txt
   ```

   `config.py` dosyasını açıp kendi kullanıcı adı ve şifrenizi girin:

   ```python
   # config.py
   USERNAME = "kullanici_adiniz"
   PASSWORD = "sifreniz"
   ```

## ▶️ Kullanım

Botu başlatmak için terminalde şu komutu çalıştırın:

```bash
python main.py
```

Açılan menüden yapmak istediğiniz işlemi seçin:
1. **Zaman Tüneli Etkileşimi:** Ana sayfanızdaki gönderileri beğenir.
2. **Keşfet Etkileşimi:** Keşfet sayfasındaki gönderilerle etkileşime girer.
3. **Hashtag/Konum Analizi:** Belirli etiketlerdeki kullanıcıları bulur.
4. **Hedef Profil Analizi:** Rakip sayfaların takipçilerini analiz eder ve takip eder.
5. **Smart Unfollow:** Sizi takip etmeyenleri temizler.

## ⚠️ Yasal Uyarı

Bu proje sadece eğitim amaçlıdır. Instagram'ın kullanım koşullarına aykırı işlemlerden doğabilecek hesap kapanması veya kısıtlanması gibi durumlardan kullanıcı sorumludur. Lütfen limitleri abartmadan ve **Safe Mode** açık şekilde kullanın.

## 🤝 Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce tartışma başlatınız.

## 📄 Lisans

[MIT](LICENSE)
