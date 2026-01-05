import datetime
import os
import sys

# Ana dizinden config modülünü import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from modules.profile_analyzer import ProfileAnalyzer

class DecisionMaker:
    def __init__(self, database):
        self.db = database
        self.whitelist = self.load_whitelist()
        self.analyzer = ProfileAnalyzer()

    def load_whitelist(self):
        """whitelist.txt dosyasını yükler."""
        whitelist = set()
        if os.path.exists("whitelist.txt"):
            try:
                with open("whitelist.txt", "r", encoding="utf-8") as f:
                    for line in f:
                        l = line.strip().lower()
                        if l and not l.startswith("#"):
                            whitelist.add(l)
            except:
                pass
        return whitelist

    def is_whitelisted(self, username):
        """Kullanıcının whitelist'te olup olmadığını kontrol eder."""
        return username.lower() in self.whitelist

    def action_allowed(self, action):
        """Günlük limitlere göre işlemin yapılıp yapılamayacağını kontrol eder."""
        max_map = {
            "LIKE": getattr(config, "MAX_LIKES_PER_DAY", 150),
            "FOLLOW": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "COMMENT": getattr(config, "MAX_COMMENTS_PER_DAY", 60),
            "FOLLOW_ALPHA": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "FOLLOW_FROM_POST": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "UNFOLLOW": getattr(config, "MAX_UNFOLLOWS_PER_DAY", 120),
        }
        max_allowed = max_map.get(action, 1000)
        
        # Bugün yapılan işlem sayısını veritabanından çek
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        stats = self.db.get_stats(today)
        
        if not stats:
            return True # Henüz kayıt yoksa izin ver
            
        # stats tablosu yapısı: date, likes, follows, unfollows, comments
        # indexler: 0: date, 1: likes, 2: follows, 3: unfollows, 4: comments
        
        current_count = 0
        if action == "LIKE":
            current_count = stats[1]
        elif "FOLLOW" in action: # FOLLOW, FOLLOW_ALPHA, FOLLOW_FROM_POST
            current_count = stats[2]
        elif action == "UNFOLLOW":
            current_count = stats[3]
        elif action == "COMMENT":
            current_count = stats[4]
            
        return current_count < max_allowed

    def add_to_whitelist(self, username):
        """Whitelist'e kullanıcı ekler ve dosyayı günceller."""
        username = username.strip().lower()
        if not username:
            return
        
        self.whitelist.add(username)
        
        try:
            with open("whitelist.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{username}")
        except Exception as e:
            print(f"Whitelist dosyasına yazılamadı: {e}")

    def should_unfollow(self, username, is_following_me, min_days_followed=None, keep_verified=False, is_verified=False, keep_min_followers=0, follower_count=0, ignore_relationship=False):
        """Bir kullanıcının takipten çıkılıp çıkılmayacağına karar verir."""
        # 1. Whitelist kontrolü
        if self.is_whitelisted(username):
            return False
            
        # 2. Beni takip ediyorsa ve politika "takip edeni silme" ise (varsayılan bu)
        if is_following_me and not ignore_relationship:
            return False

        # 3. Süre Kontrolü (Akıllı Unfollow)
        if min_days_followed and min_days_followed > 0:
            follow_time = self.db.get_follow_timestamp(username)
            if follow_time:
                days_diff = (datetime.datetime.now() - follow_time).days
                if days_diff < min_days_followed:
                    return False
            else:
                pass
        
        # 4. Verified (Mavi Tik) Kontrolü
        if keep_verified and is_verified:
            return False
            
        # 5. Takipçi Sayısı Kontrolü (Popüler hesapları koruma)
        if keep_min_followers > 0 and follower_count > keep_min_followers:
            return False
            
        return True

    def should_follow(self, user_data, criteria=None):
        """
        Bir kullanıcının takip edilip edilmeyeceğine karar verir.
        user_data: dict -> {
            "follower_count": int, 
            "following_count": int, 
            "is_private": bool, 
            "is_verified": bool,
            "username": str,
            "fullname": str,
            "bio": str
        }
        criteria: dict -> {"gender": "female", "nationality": "turkish"}
        """
        # 1. Sayısal Kriterler (Config)
        min_followers = getattr(config, "MIN_FOLLOWER_COUNT", 50)
        max_followers = getattr(config, "MAX_FOLLOWER_COUNT", 5000)
        
        if criteria:
            if "max_followers" in criteria:
                max_followers = criteria["max_followers"]
            if "min_followers" in criteria:
                min_followers = criteria["min_followers"]
        
        if user_data.get("follower_count", 0) < min_followers:
            print(f"   -> RED: Takipçi sayısı az ({user_data.get('follower_count', 0)} < {min_followers})")
            return False
            
        if user_data.get("follower_count", 0) > max_followers:
            print(f"   -> RED: Takipçi sayısı fazla ({user_data.get('follower_count', 0)} > {max_followers})")
            return False
            
        # 3. Oran Kontrolü (Spam/Bot Analizi)
        # Takip Edilen / Takipçi oranı çok yüksekse (örn: 200 takipçi, 5000 takip edilen) muhtemelen spamdır.
        followers = user_data.get("follower_count", 1)
        following = user_data.get("following_count", 0)
        
        if followers > 0:
            ratio = following / followers
            if ratio > 5.0: # Takip ettiği, takipçisinin 5 katından fazlaysa
                print(f"   -> RED: Spam şüphesi (Oran: {ratio:.1f})")
                return False
                
        # 4. Gelişmiş Profil Analizi (Cinsiyet ve Uyruk)
        if criteria:
            analysis = self.analyzer.analyze(user_data)
            print(f"   -> Profil Analizi: Cinsiyet={analysis['gender']}, Uyruk={analysis['nationality']}")
            
            # Cinsiyet Filtresi
            target_gender = criteria.get("gender")
            if target_gender:
                if analysis["gender"] != target_gender and analysis["gender"] != "unknown":
                    print(f"   -> RED: Cinsiyet uymuyor (İstenen: {target_gender}, Bulunan: {analysis['gender']})")
                    return False
                if analysis["gender"] == "unknown":
                    # İsteğe bağlı: Bilinmiyorsa geç mi, yoksa şans ver mi?
                    print(f"   -> RED: Cinsiyet belirlenemedi (Unknown)")
                    return False

            # Uyruk Filtresi
            target_nationality = criteria.get("nationality")
            if target_nationality:
                if analysis["nationality"] != target_nationality and analysis["nationality"] != "unknown":
                    return False
                if analysis["nationality"] == "unknown" and target_nationality == "turkish":
                    # Türkçe karakter yoksa ve türkçe isteniyorsa, riskli.
                    return False
                    
        return True
