import time
import random
import datetime
import sys
import os

# Ana dizinden config modülünü import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from modules.profile_analyzer import ProfileAnalyzer

class AIManager:
    """
    Yapay Zeka Yöneticisi:
    Botun tüm hareketlerini akıllıca yöneten, limitleri hesaplayan ve
    insan benzeri davranışlar sergileyen ana kontrol mekanizması.
    """
    def __init__(self, bot):
        self.bot = bot
        self.analyzer = ProfileAnalyzer()
        self.session_start_time = datetime.datetime.now()
        self.actions_taken = {
            "LIKE": 0,
            "FOLLOW": 0,
            "UNFOLLOW": 0,
            "COMMENT": 0
        }
        self.energy = 100 # %100 Enerji ile başlar
        self.strategy = None # Kullanıcı seçimi
        self.target_profile = None # Hedef profil (opsiyonel)
        self.unfollow_mode = "non_followers" # Varsayılan unfollow modu
        self.niche_tags = [] # Kullanıcı ilgi alanları
        
    def start_smart_mode(self):
        """
        Yapay Zeka Modunu Başlatır.
        Sürekli döngü halinde en mantıklı işlemi seçer ve uygular.
        """
        print("\n" + "="*50)
        print("🤖 YAPAY ZEKA YÖNETİM PANELİ (GELİŞMİŞ v2.2)")
        print("="*50)
        
        # Kullanıcı Niche (İlgi Alanı) Girişi
        print("Lütfen ilgi alanlarınızı veya hedef kitlenizi virgülle ayırarak girin.")
        print("Örn: fitness, yazılım, gezi, moda, yemek")
        niche_input = input("İlgi Alanları (Boş bırakırsanız genel mod çalışır): ").strip()
        if niche_input:
            self.niche_tags = [t.strip() for t in niche_input.split(",") if t.strip()]
            print(f"✅ İlgi alanları kaydedildi: {', '.join(self.niche_tags)}")
        else:
            print("ℹ️ Genel modda devam edilecek.")

        print("\nLütfen AI için bir öncelik belirleyin:")
        print("1 - Takip Odaklı (Hashtag/Keşfet Analizi)")
        print("2 - Beğeni Odaklı (Etkileşim Artırma)")
        print("3 - Unfollow / Temizlik (Takip Etmeyenleri Çıkar)")
        print("4 - Hedef Profil Analizi ve Takip (Rakip Analizi)")
        print("5 - Yorum Odaklı (Etkileşim ve Görünürlük)")
        print("6 - Tam Otonom (AI Karar Versin - Karma Mod)")
        print("7 - Süper Fan Modu (Hikaye + Beğeni + Takip) [YENİ]")
        
        choice = input("\nSeçiminiz (1-7): ").strip()
        
        if choice == "1":
            self.strategy = "FOLLOW_FOCUS"
            print("✅ Mod Seçildi: Takip Odaklı")
        elif choice == "2":
            self.strategy = "LIKE_FOCUS"
            print("✅ Mod Seçildi: Beğeni Odaklı")
        elif choice == "3":
            self.strategy = "UNFOLLOW_FOCUS"
            print("✅ Mod Seçildi: Temizlik Odaklı")
            
            # Alt Seçenekler
            print("\nTemizlik Tipi:")
            print("1 - Sadece Beni Takip Etmeyenler (Hainler) [Önerilen]")
            print("2 - Herkesi Sil (Whitelist Hariç)")
            
            sub_choice = input("Seçiminiz (1-2): ").strip()
            if sub_choice == "2":
                self.unfollow_mode = "all"
                print("⚠️ DİKKAT: Whitelist dışındaki herkes silinecek!")
            else:
                self.unfollow_mode = "non_followers"
                print("👍 Sadece geri takip yapmayanlar silinecek.")

        elif choice == "4":
            self.strategy = "TARGET_FOCUS"
            self.target_profile = input("Hedef Profil (Kullanıcı Adı): ").strip()
            print(f"✅ Mod Seçildi: {self.target_profile} analizi yapılacak.")
        elif choice == "5":
            self.strategy = "COMMENT_FOCUS"
            print("✅ Mod Seçildi: Yorum Odaklı")
        elif choice == "7":
            self.strategy = "SUPER_FAN"
            print("✅ Mod Seçildi: Süper Fan Modu (Yüksek Etkileşim)")
        else:
            self.strategy = "AUTO"
            print("✅ Mod Seçildi: Tam Otonom")

        print("\nSistem analizi yapılıyor ve işlemler başlıyor...")
        print("="*50 + "\n")
        
        consecutive_low_activity = 0
        total_actions_session = 0
        
        while True:
            # 0. Sistem Sağlık Kontrolü (YENİ)
            health = self.bot.browser_manager.check_system_health()
            if health != "OK":
                if health == "BLOCKED":
                    print("🛑 KRİTİK: Instagram işlem engeli tespit edildi. Bot durduruluyor.")
                    break
                elif health == "NO_NET":
                    print("⚠️ İnternet bağlantısı koptu. 60 saniye bekleniyor...")
                    time.sleep(60)
                    continue

            # 1. Durum Analizi
            action = self.decide_next_action()
            
            if action == "SLEEP":
                self.take_smart_break()
                continue
                
            if action == "STOP":
                print("🛑 Günlük limitler veya enerji tükendi. İşlem sonlandırılıyor.")
                break
            
            # 2. İşlemi Uygula
            print(f"\n🔄 Döngü Başlıyor (Aksiyon: {action})")
            result = self.execute_action(action)
            total_actions_session += result
            
            # Verimsizlik Kontrolü
            if result == 0:
                consecutive_low_activity += 1
            else:
                consecutive_low_activity = 0
                
            if consecutive_low_activity >= 3:
                print("\n⚠️ Üst üste 3 kez işlem yapılamadı. Bot dinlenmeye alınıyor veya durduruluyor.")
                if self.strategy == "UNFOLLOW_FOCUS":
                    print("🛑 Temizlik tamamlanmış veya yapılamıyor olabilir. Çıkış yapılıyor.")
                    break
                else:
                    self.take_smart_break()
                    consecutive_low_activity = 0 # Sıfırla ve devam et
            
            # 3. Enerji ve Durum Güncelleme
            self.update_state()
            
            # 4. Döngü Kontrolü (Temizlik bittiyse dur)
            if self.strategy == "UNFOLLOW_FOCUS" and action == "UNFOLLOW_CLEANUP":
                if result == 0:
                    print("\n✅ TEMİZLİK TAMAMLANDI: Silinecek kimse kalmadı.")
                    print("🛑 AI Modu sonlandırılıyor...")
                    break
                else:
                    print(f"✅ Bu turda {result} kişi silindi. Devam ediliyor...")
                    time.sleep(5) # İki tur arası kısa mola
            
            # Bilgilendirme
            print(f"📊 Oturum Özeti: Toplam {total_actions_session} işlem yapıldı. Enerji: %{self.energy}")
            
    def decide_next_action(self):
        """
        Hangi işlemin yapılacağına karar verir.
        Karar Kriterleri:
        - Kullanıcı Stratejisi (self.strategy)
        - Günlük Limitler
        - Enerji Durumu
        """
        # Limit Kontrolleri
        can_follow = self.bot.decision_maker.action_allowed("FOLLOW")
        can_like = self.bot.decision_maker.action_allowed("LIKE")
        can_unfollow = self.bot.decision_maker.action_allowed("UNFOLLOW")
        
        if not can_follow and "FOLLOW" in str(self.strategy):
            print("⚠️ Takip limiti dolu.")
        if not can_like and "LIKE" in str(self.strategy):
            print("⚠️ Beğeni limiti dolu.")
        if not self.bot.decision_maker.action_allowed("COMMENT") and "COMMENT" in str(self.strategy):
            print("⚠️ Yorum limiti dolu.")
            
        # --- STRATEJİYE GÖRE KARAR ---
        
        if self.strategy == "FOLLOW_FOCUS":
            if can_follow and self.energy > 30:
                return "FOLLOW_HUNT"
            elif can_like: # Takip yapamıyorsan beğeni yap
                return "LIKE_HUNT"
                
        elif self.strategy == "LIKE_FOCUS":
            if can_like and self.energy > 20:
                return "LIKE_HUNT"
                
        elif self.strategy == "UNFOLLOW_FOCUS":
            if can_unfollow and self.energy > 20:
                return "UNFOLLOW_CLEANUP"
                
        elif self.strategy == "TARGET_FOCUS":
            if can_follow and self.energy > 30:
                return "TARGET_FOLLOW" # Özel aksiyon
            elif can_like:
                return "LIKE_HUNT" # Yedek
        
        elif self.strategy == "COMMENT_FOCUS":
            if self.bot.decision_maker.action_allowed("COMMENT") and self.energy > 40:
                return "COMMENT_HUNT"
            elif can_like:
                return "LIKE_HUNT"
        
        elif self.strategy == "SUPER_FAN":
            if can_follow and can_like and self.energy > 40:
                return "DEEP_INTERACTION"
            elif can_like:
                return "LIKE_HUNT"
        
        # --- AUTO MOD veya FALLBACK (Strateji yapılamıyorsa) ---
        
        # Eğer takip limiti varsa ve enerji yüksekse -> TAKİP ODAKLI
        if can_follow and self.energy > 50:
            return "FOLLOW_HUNT"
            
        # Eğer beğeni limiti varsa -> BEĞENİ ODAKLI
        if can_like:
            return "LIKE_HUNT"
            
        # Eğer unfollow limiti varsa ve diğerleri bittiyse -> UNFOLLOW
        if can_unfollow:
            # Sadece takip edilenler indekslendiyse veya rastgele bir şansla
            if random.random() < 0.3: # %30 ihtimalle temizlik yap
                return "UNFOLLOW_CLEANUP"
            
        # Hiçbir şey yapılamıyorsa -> UYKU
        return "STOP"

    def execute_action(self, action_type):
        """Seçilen aksiyonu gerçekleştirir."""
        print(f"\n🧠 AI Kararı: {action_type} uygulanıyor...")
        result = 0
        
        if action_type == "FOLLOW_HUNT":
            # Hedef kitle bul ve takip et
            target = self.find_smart_target()
            if target:
                print(f"🎯 Hedef Belirlendi: {target}")
                self.bot.like_photos_by_hashtag(target, amount=random.randint(5, 15), follow=True)
                result = 1
                
        elif action_type == "LIKE_HUNT":
            target = self.find_smart_target()
            if target:
                print(f"❤️ Hedef Belirlendi: {target}")
                self.bot.like_photos_by_hashtag(target, amount=random.randint(10, 20), follow=False)
                result = 1

        elif action_type == "COMMENT_HUNT":
            target = self.find_smart_target()
            if target:
                print(f"💬 Hedef Belirlendi: {target}")
                self.execute_comment_strategy(target)
                result = 1

        elif action_type == "UNFOLLOW_CLEANUP":
            print(f"🧹 Temizlik Zamanı: Akıllı Temizlik Modu ({self.unfollow_mode})...")
            # Kullanıcının isteği üzerine: Karşılaştırmalı ve hızlı silme
            # 50-70 kişilik bir temizlik yapalım
            count = random.randint(50, 70)
            result = self.bot.smart_unfollow_cleanup(max_users=count, mode=self.unfollow_mode)
            
        elif action_type == "TARGET_FOLLOW":
            if self.target_profile:
                print(f"🎯 Hedef Profil Analizi: {self.target_profile}")
                # Mevcut follow_target_followers fonksiyonunu kullan
                # Ancak miktar olarak az ve öz gidelim
                self.bot.follow_target_followers(self.target_profile, limit=random.randint(10, 20))
                result = 1
            else:
                print("⚠️ Hedef profil belirtilmemiş, genel moda geçiliyor.")
                self.strategy = "FOLLOW_FOCUS" # Stratejiyi değiştir

        elif action_type == "DEEP_INTERACTION":
            target = self.find_smart_target()
            if target:
                print(f"🌟 Süper Fan Modu: {target} etiketi üzerinde derin etkileşim...")
                self.execute_deep_interaction(target)
                result = 1
        
        return result

    def execute_deep_interaction(self, hashtag):
        """
        Süper Fan Etkileşimi:
        1. Profile Git
        2. Hikaye İzle (Varsa)
        3. 2-3 Fotoğraf Beğen
        4. Takip Et
        """
        print(f"🚀 '{hashtag}' etiketi taranıyor...")
        
        # Hashtag sayfasına git
        self.bot.driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(5)
        
        # İlk 9 gönderiden rastgele birini seç (Popülerler usually top 9)
        try:
            posts = self.bot.driver.find_elements(self.bot.By.XPATH, "//a[contains(@href, '/p/')]")
            if not posts:
                print("❌ Gönderi bulunamadı.")
                return

            # Rastgele 3 kişi seç
            selected_posts = random.sample(posts[:15], min(3, len(posts)))
            
            for post in selected_posts:
                try:
                    post_url = post.get_attribute("href")
                    print(f"🔎 İncelenen gönderi: {post_url}")
                    
                    # Gönderiye git
                    self.bot.driver.get(post_url)
                    time.sleep(3)
                    
                    # Kullanıcı adını al
                    try:
                        username_element = self.bot.driver.find_element(self.bot.By.XPATH, "//header//div[contains(@class, '_aaqt')]//a")
                        username = username_element.text
                    except:
                        # Alternatif seçici
                        try:
                            username_element = self.bot.driver.find_element(self.bot.By.XPATH, "//h2/div/a")
                            username = username_element.text
                        except:
                            print("❌ Kullanıcı adı alınamadı.")
                            continue
                            
                    print(f"👤 Hedef Kullanıcı: {username}")
                    
                    if self.bot.check_history(username):
                        print("   -> Daha önce işlem yapılmış, geçiliyor.")
                        continue
                        
                    # Profile git
                    self.bot.browser_manager.navigate_to_profile(username)
                    time.sleep(3)
                    
                    # 1. Hikaye İzle
                    watched = self.bot.browser_manager.watch_story()
                    if watched:
                        print("   -> 👁️ Hikaye izlendi.")
                    else:
                        print("   -> Hikaye yok veya izlenemedi.")
                        
                    # 2. Beğeni (Son 2-3 gönderi)
                    self.bot.browser_manager.like_latest_post(limit=random.randint(2, 3))
                    print("   -> ❤️ Son gönderiler beğenildi.")
                    
                    # 3. Takip Et
                    # Takip butonunu bul (Browser manager'dan veya main'den alınabilir ama basitçe burada bulalım)
                    try:
                        follow_btn = self.bot.driver.find_element(self.bot.By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")
                        follow_btn.click()
                        print("   -> ✅ Takip edildi.")
                        self.bot.log_action("FOLLOW", username)
                    except:
                        print("   -> Takip butonu bulunamadı (Zaten takipte veya istek gönderildi).")
                        
                    # İşlem sonrası bekleme
                    time.sleep(random.randint(10, 20))
                    
                except Exception as e:
                    print(f"Profil işlem hatası: {e}")
                    continue
                    
        except Exception as e:
            print(f"Hashtag tarama hatası: {e}")

    def execute_comment_strategy(self, hashtag):
        """Hashtag üzerinden gönderi bulur ve yorum yapar."""
        print("💬 Yorum stratejisi başlatılıyor...")
        
        # Kategoriye göre yorumlar
        general_comments = ["Harika! 🔥", "Süper paylaşım 👏", "Çok iyi ✨", "Beğendim 👍", "Başarılı 🌟"]
        
        niche_comments = {
            "fitness": ["Basmaya devam! 💪", "Harika form 🔥", "Motivasyon tavan! 🚀", "Güçlü duruş 🦍"],
            "yazılım": ["Temiz kod! 💻", "Başarılı proje 🚀", "Kolay gelsin ☕", "Hangi dil? 🤔"],
            "gezi": ["Harika manzara 🌍", "İyi tatiller! ✈️", "Neresi burası? 😍", "Çok güzel kare 📸"],
            "yemek": ["Afiyet olsun 😋", "Nefis görünüyor 🍔", "Ellerine sağlık 👨‍🍳", "Tarif var mı? 📝"],
            "moda": ["Tarzın harika ✨", "Çok şık 👌", "Kombin süper 🔥", "Nereden aldın? 😍"],
            "sanat": ["Harika yetenek 🎨", "Çok yaratıcı ✨", "Eline sağlık 🖌️", "İlham verici 🌟"]
        }
        
        # Etikete uygun yorum listesini seç
        selected_comments = general_comments
        for key, comments in niche_comments.items():
            if key in hashtag.lower():
                selected_comments = comments + general_comments # Karıştır
                print(f"💡 '{key}' kategorisine uygun yorumlar seçildi.")
                break
        
        # Hashtag sayfasına git
        self.bot.driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(5)
        
        # İlk postu aç
        try:
            first_post = self.bot.driver.find_element(self.bot.By.XPATH, "//a[contains(@href, '/p/')]")
            first_post.click()
            time.sleep(3)
            
            # 3-5 gönderiye yorum yap
            count = 0
            limit = random.randint(3, 5)
            
            while count < limit:
                try:
                    text = random.choice(selected_comments)
                    success = self.bot.post_comment(None, text) # URL None çünkü zaten posttayız
                    
                    if success:
                        count += 1
                        print(f"[{count}/{limit}] Yorum yapıldı: {text}")
                    
                    # Sonraki gönderiye geç
                    next_btn = self.bot.driver.find_element(self.bot.By.XPATH, "//button[contains(@aria-label, 'İleri') or contains(@aria-label, 'Next')]")
                    next_btn.click()
                    time.sleep(random.randint(5, 10))
                    
                except Exception as e:
                    print(f"Yorum döngüsü hatası: {e}")
                    break
                    
        except Exception as e:
            print(f"Hashtag açma hatası: {e}")

    def find_smart_target(self):
        """İlgi alanlarına göre dinamik hedef belirler."""
        
        # Kullanıcı tanımlı ilgi alanları varsa onlardan seç
        if self.niche_tags and random.random() < 0.7: # %70 ihtimalle kullanıcının istediklerini kullan
            selected = random.choice(self.niche_tags)
            print(f"🎯 Kullanıcı İlgi Alanı: '{selected}' seçildi.")
            return selected

        # Yoksa veya %30 ihtimalle zamana göre genel takıl
        # Genişletilmiş İlgi Alanları
        morning_tags = ["coffee", "breakfast", "goodmorning", "nature", "sunrise", "motivation"]
        work_tags = ["technology", "coding", "business", "work", "design", "developer"]
        evening_tags = ["food", "dinner", "relax", "movie", "music", "art"]
        night_tags = ["night", "stars", "sleep", "dream", "reading", "peace"]
        
        hour = datetime.datetime.now().hour
        
        selected_tag = "general"
        if 6 <= hour < 11:
            selected_tag = random.choice(morning_tags)
            print(f"🌅 Sabah Modu: '{selected_tag}' etiketi analiz ediliyor...")
        elif 11 <= hour < 18:
            selected_tag = random.choice(work_tags)
            print(f"💼 Gün Ortası Modu: '{selected_tag}' etiketi analiz ediliyor...")
        elif 18 <= hour < 23:
            selected_tag = random.choice(evening_tags)
            print(f"🌆 Akşam Modu: '{selected_tag}' etiketi analiz ediliyor...")
        else:
            selected_tag = random.choice(night_tags)
            print(f"🌙 Gece Modu: '{selected_tag}' etiketi analiz ediliyor...")
            
        return selected_tag

    def take_smart_break(self):
        """İnsan benzeri dinlenme molası verir."""
        duration = random.randint(120, 600) # 2-10 dakika
        print(f"☕ AI Molası: {duration//60} dakika dinleniliyor...")
        time.sleep(duration)
        self.energy = min(100, self.energy + 10) # Enerji yenile

    def update_state(self):
        """Her işlemden sonra durumu günceller."""
        self.energy -= random.randint(5, 15)
        if self.energy < 20:
            print("🔋 Enerji düşük, dinlenme modu aktifleşecek.")
            self.take_smart_break()

    def score_user(self, user_data):
        """
        Bir kullanıcıyı analiz eder ve 0-100 arası puan verir.
        Yüksek puan = Kaliteli Kullanıcı (Takip etmeye değer)
        """
        score = 50 # Başlangıç puanı
        
        # 1. Profil Resmi Kontrolü (Varsayım)
        # (Selenium ile profil resmi olup olmadığına bakılabilir ama şu an text based gidiyoruz)
        
        # 2. Takipçi/Takip Oranı
        followers = user_data.get('follower_count', 0)
        following = user_data.get('following_count', 0)
        
        if following > 0:
            ratio = followers / following
            if 0.5 < ratio < 3.0: # Normal kullanıcı
                score += 20
            elif ratio > 10: # Influencer olabilir (Zor geri döner)
                score -= 10
            elif ratio < 0.2: # Spam/Bot olabilir
                score -= 20
                
        # 3. Bio Analizi (NLP Simülasyonu)
        bio = user_data.get('bio', '').lower()
        positive_keywords = ["student", "mühendis", "doktor", "sanat", "art", "travel", "blog", "vlog"]
        negative_keywords = ["bet", "bahis", "kazan", "takip", "gt", "unf", "crypto", "forex"]
        
        for word in positive_keywords:
            if word in bio:
                score += 10
                
        for word in negative_keywords:
            if word in bio:
                score -= 30
                
        return max(0, min(100, score))
