from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import config
import datetime
import os
import json
import string
import re
from modules.database import Database
from modules.browser import BrowserManager
from modules.decision_maker import DecisionMaker
from modules.scheduler import ActionScheduler
from modules.ai_manager import AIManager

class InstagramBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        
        # Scheduler (Zamanlama)
        self.scheduler = ActionScheduler()

        # Browser Manager Başlat
        self.browser_manager = BrowserManager()
        self.driver = self.browser_manager.build_driver()
        
        self.log_file = "history.log"
        self.wait = WebDriverWait(self.driver, 10)
        self.stats = {"LIKE": 0, "COMMENT": 0, "FOLLOW": 0, "FOLLOW_FROM_POST": 0, "FOLLOW_ALPHA": 0, "UNFOLLOW": 0}
        self.smart_file = "smart_state.json"
        self.smart_state = self.load_smart_state()
        
        # Telegram Ayarları (config.py'den al)
        self.tg_token = getattr(config, "TELEGRAM_TOKEN", None)
        self.tg_chat_id = getattr(config, "TELEGRAM_CHAT_ID", None)
        
        # Veritabanı Bağlantısı (Modüler)
        self.db = Database(username)
        
        # Karar Mekanizması (Modüler)
        self.decision_maker = DecisionMaker(self.db)
        
        # Yapay Zeka Yöneticisi
        self.ai_manager = AIManager(self)

    def send_telegram(self, message):
        """Telegram üzerinden bildirim gönderir."""
        if not self.tg_token or not self.tg_chat_id:
            return
            
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            data = {"chat_id": self.tg_chat_id, "text": message}
            requests.post(url, data=data, timeout=5)
        except:
            pass # İnternet yoksa veya hata varsa botu durdurma

    def log_action(self, action, target):
        # Veritabanına kaydet
        self.db.log_action(action, target)
        
        # Hafızadaki istatistikleri güncelle
        if action in self.stats:
            self.stats[action] += 1
        print(f"[{action}] {target}")
        
        # Smart State güncelle
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.smart_state["events"].append({"ts": timestamp, "action": action})
            self.save_smart_state()
        except:
            pass

    def check_history(self, target):
        # Veritabanından kontrol et
        if self.db.check_history(target):
            return True
            
        # Yedek olarak dosyadan kontrol et (Eski loglar için)
        if self._legacy_file_check(target):
            return True
            
        return False

    def _legacy_file_check(self, target):
        if not os.path.exists(self.log_file):
            return False
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                if target in f.read():
                    return True
        except:
            pass
        return False

    def rand_delay(self, long=False):
        self.scheduler.rand_delay(long)
    
    def human_click(self, element):
        self.browser_manager.human_click(element)

    def fast_delay(self):
        self.scheduler.fast_delay()
    
    def turbo_delay(self):
        self.scheduler.turbo_delay()

    def action_allowed(self, action):
        return self.decision_maker.action_allowed(action)

    def log_action(self, action, target):
        """Bu metod veritabanı loglama metoduyla değiştirildiği için artık kullanılmıyor,
        ancak eski referanslar için tutuluyor."""
        pass

    def check_history(self, target):
        """Bu metod veritabanı kontrol metoduyla değiştirildiği için artık kullanılmıyor,
        ancak eski referanslar için tutuluyor."""
        pass
    
    # Eski metotların kalıntılarını temizle
    def _legacy_check(self):
        pass

    def print_summary(self):
        total_follow = self.stats.get("FOLLOW", 0) + self.stats.get("FOLLOW_FROM_POST", 0) + self.stats.get("FOLLOW_ALPHA", 0)
        
        # Süre Hesabı
        elapsed = datetime.datetime.now() - self.session_start
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))

        print("\n" + "="*30)
        print(f"📊 OTURUM RAPORU (v2.2)")
        if hasattr(config, "SAFE_MODE") and config.SAFE_MODE:
            print(f"🛡️  Güvenli Mod : AKTİF")
        print(f"⏱️  Süre: {duration_str}")
        print("-" * 30)
        print(f"❤️  Beğeni        : {self.stats.get('LIKE', 0)}")
        print(f"💬  Yorum         : {self.stats.get('COMMENT', 0)}")
        print(f"👤  Takip         : {total_follow}")
        print(f"🚫  Takipten Çıkma: {self.stats.get('UNFOLLOW', 0)}")
        print("="*30 + "\n")

    def load_smart_state(self):
        try:
            if os.path.exists(self.smart_file):
                with open(self.smart_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return {"events": [], "blocks": 0}

    def save_smart_state(self):
        try:
            with open(self.smart_file, "w", encoding="utf-8") as f:
                json.dump(self.smart_state, f, ensure_ascii=False)
        except:
            pass

    def get_random_comment(self):
        """comments.txt dosyasından rastgele bir yorum döndürür."""
        try:
            with open("comments.txt", "r", encoding="utf-8") as f:
                comments = f.readlines()
            valid_comments = [c.strip() for c in comments if c.strip() and not c.startswith("#")]
            if valid_comments:
                return random.choice(valid_comments)
        except:
            pass
        return "Harika!" # Yedek yorum

    def close_browser(self):
        try:
            self.driver.quit()
        except:
            pass

    def is_action_blocked(self):
        try:
            src = self.driver.page_source.lower()
        except:
            return False
        patterns = [
            "action blocked",
            "we restrict certain activity",
            "try again later",
            "eylem engellendi",
            "şu anda bu işlemi gerçekleştiremiyoruz",
        ]
        return any(p in src for p in patterns)

    def parse_username_from_href(self, href):
        try:
            if not href:
                return None
            if "instagram.com" not in href:
                return None
            part = href.split("instagram.com/")[1]
            part = part.split("?")[0].split("#")[0]
            seg = part.split("/")[0].strip().lower()
            reserved = {
                "explore","accounts","reels","direct","archive","challenge","graphql","about","privacy",
                "api","p","stories","settings","saved","notifications","shop","channel","igtv","threads",
                "followers","following"
            }
            if not seg or seg in reserved:
                return None
            return seg
        except:
            return None
    def user_in_following_search(self, target_username, fast=True, turbo=False):
        driver = self.driver
        w = WebDriverWait(driver, 4 if (fast and turbo) else (7 if fast else 10))
        try:
            opened = False
            try:
                link_any = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following')]")))
                link_any.click()
                opened = True
            except:
                try:
                    link_header = w.until(EC.element_to_be_clickable((By.XPATH, "//header//ul/li[3]//a")))
                    link_header.click()
                    opened = True
                except:
                    pass
            if not opened:
                driver.get(f"https://www.instagram.com/{target_username}/following/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            inp = None
            try:
                inp = w.until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Ara' or @aria-label='Search']")))
            except:
                inp = None
            if inp:
                inp.clear()
                self.browser_manager.humanizer.type_like_human(inp, self.username)
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                my_href = f"https://www.instagram.com/{self.username}/"
                try:
                    w.until(EC.presence_of_element_located((By.XPATH, f"//a[@href='{my_href}']")))
                    return True
                except:
                    return False
        except:
            pass
        return None

    def user_follows_me_via_following(self, target_username, fast=True, turbo=False, max_scrolls=20):
        driver = self.driver
        w = WebDriverWait(driver, 4 if (fast and turbo) else (7 if fast else 10))
        try:
            driver.get(f"https://www.instagram.com/{target_username}/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            sr = self.user_in_following_search(target_username, fast=fast, turbo=turbo)
            if sr is True:
                return True
            opened = False
            try:
                link_any = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following')]")))
                link_any.click()
                opened = True
            except:
                try:
                    link_header = w.until(EC.element_to_be_clickable((By.XPATH, "//header//ul/li[3]//a")))
                    link_header.click()
                    opened = True
                except:
                    pass
            if not opened:
                driver.get(f"https://www.instagram.com/{target_username}/following/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay(True)
            my_href = f"https://www.instagram.com/{self.username}/"
            dialog = None
            use_page_list = False
            try:
                dialog = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']//div[contains(@class,'_aano')]")))
            except:
                use_page_list = True
            scrolls = 0
            if not use_page_list and dialog:
                last_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                while scrolls < max_scrolls:
                    scrolls += 1
                    links = dialog.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if href.startswith(my_href):
                            return True
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                    new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                    if new_h == last_h:
                        break
                    last_h = new_h
            else:
                last_h = driver.execute_script("return document.body.scrollHeight")
                while scrolls < max_scrolls:
                    scrolls += 1
                    links = driver.find_elements(By.XPATH, "//a[@href]")
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if href.startswith(my_href):
                            return True
                    driver.execute_script("window.scrollBy(0, 1800)")
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                    new_h = driver.execute_script("return document.body.scrollHeight")
                    if new_h == last_h:
                        break
                    last_h = new_h
        except:
            pass
        return False

    def login(self):
        # 1. Önce Cookie ile giriş denemesi
        print("Giriş kontrolü yapılıyor...")
        if self.browser_manager.load_cookies(self.username):
            if self.browser_manager.check_login_status():
                print(f"Çerezlerle giriş BAŞARILI: {self.username}")
                return
            else:
                print("Çerezler geçersiz veya süresi dolmuş, normal giriş yapılıyor...")
        
        # 2. Normal Giriş
        print("Normal giriş başlatılıyor...")
        self.driver.get("https://www.instagram.com/")
        self.rand_delay()
        
        try:
            # Kullanıcı adı
            username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            username_input.clear()
            self.browser_manager.humanizer.type_like_human(username_input, self.username)
            self.rand_delay()
            
            # Şifre
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.clear()
            self.browser_manager.humanizer.type_like_human(password_input, self.password)
            self.rand_delay()
            
            # Giriş Yap Butonu veya Enter
            password_input.send_keys(Keys.ENTER)
            self.rand_delay(True)
            print("Giriş bilgileri gönderildi, bekleniyor...")
            
            # Giriş başarılıysa çerezleri kaydet
            # time.sleep(5) # Tam yüklenmesini bekle - Optimize Edildi
            try:
                WebDriverWait(self.driver, 10).until(lambda d: self.browser_manager.check_login_status())
            except:
                pass
            
            if self.browser_manager.check_login_status():
                print("Giriş BAŞARILI.")
                self.browser_manager.save_cookies(self.username)
            else:
                print("Giriş başarısız olabilir, lütfen kontrol edin.")
            
        except Exception as e:
            print(f"Giriş yaparken hata oluştu: {e}")

    def autopilot(self, total=30, region="EU"):
        done = 0
        cycle = 0
        hashtags = ["travel","photo","music","art","city","summer","nature","istanbul"]
        while done < total:
            left = total - done
            cycle += 1
            if self.is_action_blocked():
                try:
                    self.smart_state["blocks"] += 1
                    self.save_smart_state()
                except:
                    pass
                break
            engage_amt = min(2, left)
            try:
                tag = random.choice(hashtags)
                self.like_photos_by_hashtag(tag, amount=engage_amt, follow=False, comment=(cycle % 3 == 0))
                done += engage_amt
            except:
                pass
            if done >= total:
                break
            follow_batch = min(5, total - done)
            got = 0
            if self.action_allowed("FOLLOW"):
                try:
                    got = self.follow_random_users_foreign(target_count=follow_batch, max_followers=getattr(config, "MAX_FOLLOWER_COUNT", 5000), min_followers=getattr(config, "MIN_FOLLOWER_COUNT", 50), only_private=True, fast=True, turbo=True, avoid_known=True, region=region, min_posts=3)
                except:
                    got = 0
                if got == 0:
                    try:
                        got = self.follow_users_by_alphabet(target_count=follow_batch, fast=True, turbo=True, avoid_known=True)
                    except:
                        got = 0
                if got == 0:
                    try:
                        got = self.follow_via_hashtag_pool(["london","berlin","paris","madrid","rome","amsterdam"], target_count=follow_batch, fast=True, turbo=True, avoid_known=True)
                    except:
                        got = 0
                done += got
            if done >= total:
                break
            if cycle % 4 == 0 and self.action_allowed("UNFOLLOW"):
                try:
                    uf = self.fast_modal_unfollow_nonfollowers(max_actions=15, fast=True, turbo=True)
                    done += min(uf, total - done)
                except:
                    pass
        print(f"Otomatik mod tamamlandı: {done}")
        return done

    def like_photos_by_hashtag(self, hashtag, amount=5, follow=False, comment=False):
        driver = self.driver
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        self.rand_delay(True)

        # İlk gönderiyi bul ve tıkla
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            first_post = None
            for link in links:
                href = link.get_attribute("href")
                if href and "/p/" in href:
                    first_post = link
                    break
            
            if first_post:
                first_post.click()
                self.rand_delay()
            else:
                print("Herhangi bir gönderi bulunamadı.")
                return

            for i in range(amount):
                # Gönderi URL'sini al (Loglama için)
                current_url = driver.current_url
                
                # Geçmiş kontrolü
                if self.check_history(current_url):
                    print(f"{i+1}. gönderi daha önce işlenmiş. Pas geçiliyor.")
                else:
                    # 1. BEĞENİ İŞLEMİ
                    try:
                        if self.action_allowed("LIKE"):
                            like_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//span/*[name()='svg' and (@aria-label='Beğen' or @aria-label='Like')]/..")))
                            like_button.click()
                            print(f"{i+1}. gönderi beğenildi.")
                            self.log_action("LIKE", current_url)
                            if self.is_action_blocked():
                                print("İşlem engellendi. Beklemeye alınıyor.")
                                return
                    except Exception:
                        print(f"{i+1}. gönderi zaten beğenilmiş olabilir.")

                    # 2. YORUM YAPMA İŞLEMİ
                    if comment:
                        try:
                            if self.decision_maker.action_allowed("COMMENT"):
                                comment_text = self.get_random_comment()
                                comment_area = self.wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Yorum ekle...' or @aria-label='Add a comment…']")))
                                comment_area.click()
                                self.rand_delay()
                                comment_area = self.wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Yorum ekle...' or @aria-label='Add a comment…']")))
                                self.browser_manager.humanizer.type_like_human(comment_area, comment_text)
                                self.rand_delay()
                                comment_area.send_keys(Keys.ENTER)
                                print(f"   -> Yorum yapıldı: {comment_text}")
                                self.log_action("COMMENT", current_url)
                                self.rand_delay()
                                if self.is_action_blocked():
                                    print("İşlem engellendi. Beklemeye alınıyor.")
                                    return
                        except Exception as e:
                            print(f"   -> Yorum yapılamadı.")

                    # 3. TAKİP ETME İŞLEMİ (Eğer isteniyorsa)
                    if follow:
                        try:
                            # "Takip Et" veya "Follow" metnini içeren butonu ara
                            if self.decision_maker.action_allowed("FOLLOW"):
                                follow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button/div/div[text()='Takip Et' or text()='Follow']")))
                                follow_btn.click()
                                print(f"   -> Kullanıcı takip edildi.")
                                self.log_action("FOLLOW_FROM_POST", current_url)
                                self.rand_delay()
                                if self.is_action_blocked():
                                    print("İşlem engellendi. Beklemeye alınıyor.")
                                    return
                        except Exception:
                            pass

                # Rastgele bekleme süresi
                self.rand_delay(long=(follow or comment))

                # Sonraki gönderiye geç
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.RIGHT)
                    self.rand_delay()
                except:
                    print("Sonraki gönderiye geçilemedi.")
                    break

        except Exception as e:
            print(f"Hashtag işlemi sırasında hata: {e}")

    def unfollow_non_followers(self, count=20, only_nonfollowers=True, use_whitelist=True, fast=True, turbo=False, min_days=0, keep_verified=False, keep_min_followers=0):
        # 1. Profil Sayfasına Git
        self.browser_manager.navigate_to_profile(self.username)
        if fast:
            self.fast_delay()
        else:
            self.rand_delay()
        
        # 2. Takip Edilenler Listesini Aç
        opened = self.browser_manager.open_following_modal(self.username)
        
        if fast:
            self.fast_delay()
        else:
            self.rand_delay(True)
            
        users_to_check = []
        dialog = self.browser_manager.get_modal_dialog()
        use_page_list = not opened or not dialog
        
        # 3. Kullanıcıları Topla
        last_height = 0
        if not use_page_list:
            last_height = self.driver.execute_script("return arguments[0].scrollHeight", dialog)
        else:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
        while len(users_to_check) < count:
            if not use_page_list:
                new_users = self.browser_manager.extract_users_from_element(dialog, count, users_to_check, self.username)
                self.browser_manager.scroll_element(dialog)
            else:
                new_users = self.browser_manager.extract_users_from_element(self.driver, count, users_to_check, self.username)
                self.browser_manager.scroll_window()
            
            if fast:
                self.fast_delay()
            else:
                self.rand_delay()
                
            if not use_page_list:
                new_height = self.driver.execute_script("return arguments[0].scrollHeight", dialog)
            else:
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
            if new_height == last_height:
                break
            last_height = new_height

        if len(users_to_check) > 0:
            count = min(count, len(users_to_check))
            print(f"Toplam kontrol edilecek hesap: {count}")

        # 4. Kullanıcıları İşle
        for user_url in users_to_check[:count]:
            try:
                # self.driver.get(user_url) -> Optimize edildi
                uname = self.parse_username_from_href(user_url)
                if uname:
                     self.browser_manager.navigate_to_profile(uname)
                else:
                     self.driver.get(user_url)

                if fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                
                # uname zaten yukarıda alındı
                # uname = None
                # try:
                #    uname = self.driver.current_url.strip("/").split("/")[-1].lower()
                # except:
                #    pass
                
                # Decision Maker ile Kontrol (Whitelist)
                if uname and self.decision_maker.is_whitelisted(uname):
                    continue
                
                # KORUMA KONTROLLERİ (Yeni)
                is_verified = False
                follower_count = 0
                
                if keep_verified or keep_min_followers > 0:
                    is_verified = self.browser_manager.is_verified_profile()
                    if keep_min_followers > 0:
                         try:
                             # Takipçi linkini bul
                             fl_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]")
                             fl_text = fl_link.text or fl_link.get_attribute("title")
                             follower_count = self.parse_follower_count(fl_text)
                         except:
                             pass

                # Bizi takip ediyor mu kontrolü
                is_following_me = self.user_follows_me_via_following(uname, fast=fast, turbo=False, max_scrolls=12 if fast else 20)
                
                # Decision Maker Unfollow Kararı
                if not self.decision_maker.should_unfollow(uname, is_following_me, min_days_followed=min_days,
                                                         keep_verified=keep_verified, is_verified=is_verified,
                                                         keep_min_followers=keep_min_followers, follower_count=follower_count,
                                                         ignore_relationship=not only_nonfollowers):
                     continue

                if self.decision_maker.action_allowed("UNFOLLOW"):
                    # Takiptesin butonunu bul
                    btn = self.browser_manager.find_following_button()
                    
                    if btn:
                        try:
                            btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click()", btn)
                    else:
                        print(f"Takiptesin düğmesi bulunamadı: {uname}")
                        continue
                        
                    if fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                        
                    # Onay butonunu bul
                    target = self.browser_manager.find_unfollow_confirm_button()
                    
                    if target:
                        try:
                            target.click()
                            print(f"BAŞARILI: {uname} takipten çıkıldı.")
                            self.log_action("UNFOLLOW", user_url)
                        except:
                            self.driver.execute_script("arguments[0].click()", target)
                    else:
                        print("Takibi Bırak kontrolü bulunamadı.")
                        continue
                        
                    if fast:
                        self.fast_delay()
                    else:
                        self.rand_delay(True)
                        
                    if self.is_action_blocked():
                        print("İşlem engellendi. Beklemeye alınıyor.")
                        return
            except Exception as e:
                print(f"Profil işlemi hatası: {e}")
    
    def index_list(self, list_type="followers", max_count=None, fast=True, turbo=False):
        driver = self.driver
        collected = []
        
        # 1. Profile Git
        self.browser_manager.navigate_to_profile(self.username)
        
        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()
            
        # 2. Modalı/Sayfayı Aç
        if list_type == "followers":
            self.browser_manager.open_followers_modal(self.username)
        else:
            self.browser_manager.open_following_modal(self.username)

        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()

        # 3. Dialog Kontrolü
        dialog = self.browser_manager.get_modal_dialog()
        use_page_list = (dialog is None)
        
        last_height = 0
        if not use_page_list and dialog:
            last_height = driver.execute_script("return arguments[0].scrollHeight", dialog)
        else:
            last_height = driver.execute_script("return document.body.scrollHeight")

        scroll_retries = 0
        
        while True:
            # Linkleri topla
            if not use_page_list and dialog:
                links = dialog.find_elements(By.TAG_NAME, "a")
            else:
                links = driver.find_elements(By.XPATH, "//main//a[@href]")
                
            for link in links:
                href = link.get_attribute("href") or ""
                uname = self.parse_username_from_href(href)
                if uname:
                    if uname != self.username.lower() and uname not in collected:
                        collected.append(uname)
                if max_count and len(collected) >= max_count:
                    break
            
            if max_count and len(collected) >= max_count:
                break
                
            # Scroll Yap
            new_height = 0
            if not use_page_list and dialog:
                new_height = self.browser_manager.scroll_element(dialog)
            else:
                new_height = self.browser_manager.scroll_window()
            
            # Bekleme
            if fast and turbo:
                time.sleep(1)
            elif fast:
                time.sleep(2)
            else:
                self.rand_delay()
                
            # Yükseklik Kontrolü (Scroll bitti mi?)
            if new_height == last_height:
                scroll_retries += 1
                if scroll_retries > 3:
                    break
                time.sleep(1)
            else:
                scroll_retries = 0
                last_height = new_height
                
        # Dosyaya yazma
        fname = "index_followers.txt" if list_type == "followers" else "index_following.txt"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                for u in collected:
                    f.write(u + "\n")
        except:
            pass
        print(f"{list_type} indeks tamamlandı: {len(collected)}")
        return collected
    
    def get_own_user_id(self):
        """Çerezlerden veya sayfadan kendi user_id'sini bulur."""
        try:
            # 1. Çerezden dene
            cookies = self.driver.get_cookies()
            for c in cookies:
                if c['name'] == 'ds_user_id':
                    return c['value']
            
            # 2. LocalStorage dene
            uid = self.driver.execute_script("return window.localStorage.getItem('ig_user_id')")
            if uid: return uid
            
            return None
        except:
            return None

    def fetch_users_via_api(self, list_type, limit=None, min_expected=0):
        """
        Gelişmiş Yöntem: Hem REST API hem de GraphQL yöntemlerini dener.
        Scroll sorununu tamamen ortadan kaldırır.
        list_type: 'followers' veya 'following'
        min_expected: Beklenen minimum kullanıcı sayısı (REST yedeğini tetiklemek için)
        """
        user_id = self.get_own_user_id()
        if not user_id:
            print("❌ User ID bulunamadı, API yöntemi iptal.")
            return set()

        print(f"🚀 API Modu Başlatılıyor ({list_type})... (Scrollsuz Hızlı Tarama)")
        
        endpoint_type = "followers" if list_type == "followers" else "following"
        
        # JS Script: Önce GraphQL, Olmazsa REST API dene
        js_script = """
            var callback = arguments[arguments.length - 1];
            var userId = arguments[0];
            var type = arguments[1]; // 'followers' or 'following'
            var limit = arguments[2] || 10000;
            var minExpected = arguments[3] || 0;
            
            // Cookie'den csrftoken al
            var match = document.cookie.match(/csrftoken=([^;]+)/);
            var csrftoken = match ? match[1] : null;
            
            if (!csrftoken) {
                callback({status: 'error', message: 'CSRF Token Missing'});
                return;
            }

            // Başlangıç beklemesi (Rate limit önlemi)
            await new Promise(r => setTimeout(r, 2000));

            var allUsers = [];
            var errors = [];

            // ---------------------------------------------------------
            // YÖNTEM 1: GraphQL API (Daha Güvenilir)
            // ---------------------------------------------------------
            async function tryGraphQL() {
                console.log("GraphQL Yöntemi Deneniyor...");
                
                // Hash Listesi (Güncel ve Alternatifli)
                var hashes = (type === 'followers') 
                    ? ['c76146de99bb02f6415203be841dd25a', '5aefa9893005572d237da36f5d61f13b'] 
                    : ['d04b0a864b4b54837c0d870b0e77e076'];
                
                var edgeName = (type === 'followers') ? 'edge_followed_by' : 'edge_follow';
                
                for (var queryHash of hashes) {
                    console.log("Denenen Hash: " + queryHash);
                    
                    try {
                        var nextCursor = null;
                        var hasNextPage = true;
                        var tempUsers = [];
                        
                        while (hasNextPage) {
                            var variables = {
                                "id": userId,
                                "include_reel": true,
                                "fetch_mutual": false,
                                "first": 50
                            };
                            if (nextCursor) variables.after = nextCursor;
                            
                            var url = `https://www.instagram.com/graphql/query/?query_hash=${queryHash}&variables=${encodeURIComponent(JSON.stringify(variables))}`;
                            
                            var response = await fetch(url);
                            if (!response.ok) {
                                 var txt = await response.text();
                                 throw new Error("HTTP " + response.status + " " + txt.substring(0, 100));
                            }
                            
                            var json = await response.json();
                            
                            if (!json.data || !json.data.user || !json.data.user[edgeName]) {
                                throw new Error("Invalid Data Structure");
                            }

                            var data = json.data.user[edgeName];
                            
                            for (var node of data.edges) {
                                tempUsers.push(node.node.username);
                            }
                            
                            console.log(`[GraphQL] Fetched ${data.edges.length} users.`);
                            
                            hasNextPage = data.page_info.has_next_page;
                            nextCursor = data.page_info.end_cursor;
                            
                            if (limit && (allUsers.length + tempUsers.length) >= limit) {
                                hasNextPage = false;
                            }
                            
                            // Rate limit önlemi
                            await new Promise(r => setTimeout(r, Math.random() * 1000 + 500));
                        }
                        
                        // Eğer buraya geldiyse başarılıdır
                        allUsers = allUsers.concat(tempUsers);
                        return true;
                        
                    } catch (e) {
                        console.error("Hash Failed:", e);
                        errors.push("GraphQL (" + queryHash + "): " + e.message);
                        // Diğer hash'e geç
                    }
                }
                
                return false; // Tüm hashler başarısız
            }

            // ---------------------------------------------------------
            // YÖNTEM 2: REST API (Yedek)
            // ---------------------------------------------------------
            async function tryRestAPI() {
                console.log("REST API Yöntemi Deneniyor...");
                
                var nextMaxId = null;
                var endpoint = `https://www.instagram.com/api/v1/friendships/${userId}/${type}/`;
                
                try {
                    while (true) {
                        var url = endpoint + '?count=200';
                        if (nextMaxId) url += '&max_id=' + nextMaxId;
                        
                        var headers = {
                            'x-ig-app-id': '936619500051864', 
                            'x-requested-with': 'XMLHttpRequest',
                            'x-csrftoken': csrftoken,
                            'x-asbd-id': '129477'
                        };

                        var response = await fetch(url, { headers: headers });
                        if (!response.ok) {
                            var txt = await response.text();
                            console.error("REST API Fail:", txt);
                            throw new Error("HTTP " + response.status + " " + txt.substring(0, 100));
                        }
                        
                        var json = await response.json();
                        var users = json.users || [];
                        
                        for (var u of users) {
                            allUsers.push(u.username);
                        }
                        
                        console.log(`[REST] Fetched ${users.length} users. Total: ${allUsers.length}`);

                        if (limit && allUsers.length >= limit) break;
                        if (!json.next_max_id) break;
                        
                        nextMaxId = json.next_max_id;
                        await new Promise(r => setTimeout(r, Math.random() * 500 + 300));
                    }
                    return true;
                } catch (e) {
                    console.error("REST API Hatası:", e);
                    errors.push("REST API: " + e.message);
                    return false;
                }
            }
            
            // Ana Akış
            async function main() {
                // Önce GraphQL dene
                var success = await tryGraphQL();
                
                // Kontrol: GraphQL başarılı ama sayı eksikse REST ile tamamlamayı dene
                if (success && minExpected > 0 && allUsers.length < minExpected) {
                    console.warn(`GraphQL eksik çekti (${allUsers.length}/${minExpected}). REST API ile tamamlanıyor...`);
                    // REST'i de çalıştır (allUsers'a ekleyecek)
                    await tryRestAPI();
                }
                // Eğer GraphQL tamamen başarısızsa zaten REST dene
                else if (!success || allUsers.length === 0) {
                     if (!success) allUsers = []; 
                     success = await tryRestAPI();
                }
                
                if (success || allUsers.length > 0) {
                    // Duplicate temizliği
                    var uniqueUsers = [...new Set(allUsers)];
                    callback({status: 'success', users: uniqueUsers});
                } else {
                    callback({status: 'error', message: 'Tüm yöntemler başarısız. Detaylar: ' + errors.join(' | ')});
                }
            }
            
            main();
        """
        
        try:
            self.driver.set_script_timeout(180) 
            result = self.driver.execute_async_script(js_script, user_id, endpoint_type, limit, min_expected)
            
            if result and result.get('status') == 'success':
                users = result.get('users', [])
                print(f"✅ API Tarama Başarılı: {len(users)} kişi çekildi.")
                return set(users)
            else:
                print(f"❌ API Hatası: {result.get('message')}")
                return set()
                
        except Exception as e:
            print(f"API Script Çalıştırma Hatası: {e}")
            return set()
    
    def scrape_modal_users(self, list_type="followers", limit=None, expected_min=None, target_username=None):
        """
        Belirtilen liste türünü (followers/following) modal üzerinden tamamen tarar ve kümeye atar.
        target_username: Eğer belirtilirse o kullanıcının listesini tarar (varsayılan: kendi profiliniz).
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        collected = set()
        
        target = target_username if target_username else self.username
        
        print(f"Liste taranıyor: {target} - {list_type}...")
        
        try:
            # Profile git (Optimize Edildi)
            self.browser_manager.navigate_to_profile(target)
            
            # Linki bul ve tıkla
            try:
                # Link genellikle href="/username/followers/" şeklindedir
                link = w.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/{list_type}/')]")))
                link.click()
            except:
                # Link bulunamazsa direkt URL'e git (bazen çalışmaz ama denemeye değer)
                driver.get(f"https://www.instagram.com/{target}/{list_type}/")
            
            time.sleep(3)

            # Dialog elementini bul (Role dialog) - Retry mekanizmalı ve Alternatifli
            dialog_container = None
            print("Dialog penceresi aranıyor...")

            # Strateji 1: Standart role='dialog'
            for i in range(5): # 5 deneme
                try:
                    dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    print("Dialog bulundu (role='dialog').")
                    break
                except:
                    time.sleep(1)

            # Strateji 2: Direkt scroll container (_aano)
            if not dialog_container:
                try:
                    print("Dialog role ile bulunamadı, _aano class aranıyor...")
                    dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, '_aano')]")))
                    print("Dialog yerine direkt scroll alanı bulundu.")
                except:
                    pass

            # Strateji 3: Başlık metninden bulma (Takipçiler/Followers)
            if not dialog_container:
                try:
                    print("Başlık metninden dialog aranıyor...")
                    xpath_text = "//*[contains(text(), 'Takipçiler') or contains(text(), 'Followers')]/ancestor::div[contains(@class, 'x1n2onr6') or contains(@class, '_aano') or position()=last()]"
                    dialog_container = driver.find_element(By.XPATH, xpath_text)
                    print("Başlık üzerinden container tahmin edildi.")
                except:
                    pass

            # Strateji 4: Main role (Tam sayfa görünümü için - Direct URL)
            if not dialog_container:
                try:
                    print("Main role aranıyor (Tam sayfa modu)...")
                    dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//main[@role='main']")))
                    print("Main container bulundu.")
                except:
                    pass

            # Strateji 5: Body (Son çare)
            if not dialog_container:
                try:
                    print("Son çare: Body elementi seçiliyor...")
                    dialog_container = driver.find_element(By.TAG_NAME, "body")
                except:
                    pass

            if not dialog_container:
                print("KRİTİK HATA: Dialog penceresi hiçbir yöntemle bulunamadı!")
                return set()
            
            # JavaScript ile scroll edilebilir alanı bul (Gelişmiş - ScrollHeight Öncelikli)
            dialog = driver.execute_script("""
                var container = arguments[0];
                var allDivs = container.getElementsByTagName('div');
                var bestDiv = null;
                var maxScrollHeight = 0;
                
                // Tüm divleri tara ve en büyük scrollHeight'a sahip olanı bul (Gerçek liste odur)
                for (var i = 0; i < allDivs.length; i++) {
                    var d = allDivs[i];
                    var style = window.getComputedStyle(d);
                    
                    // Görünür olmalı ve scroll edilebilir olmalı
                    if (d.scrollHeight > d.clientHeight && d.clientHeight > 0) {
                         // Overflow kontrolü (Opsiyonel ama güvenli)
                         if (style.overflowY === 'auto' || style.overflowY === 'scroll' || d.scrollHeight > 500) {
                             if (d.scrollHeight > maxScrollHeight) {
                                 maxScrollHeight = d.scrollHeight;
                                 bestDiv = d;
                             }
                         }
                    }
                }
                
                // Eğer bulamazsa, _aano class'ına bak
                if (!bestDiv) {
                    bestDiv = container.querySelector('div._aano');
                }
                
                // Hiçbiri olmazsa container'ın kendisini döndür
                return bestDiv || container;
            """, dialog_container)
            
            print("Scroll alanı tespit edildi.")
            
            # Odaklanma (Focus) Denemesi
            try:
                first_item = dialog.find_element(By.TAG_NAME, "a")
                ActionChains(driver).move_to_element(first_item).perform()
            except:
                pass

            last_len = 0
            same_len_count = 0
            
            while True:
                # Kullanıcıları topla
                js_links = driver.execute_script("""
                    var container = arguments[0];
                    // Hem 'a' tagleri hem de 'role=link' olanlar
                    var links = container.getElementsByTagName('a');
                    var hrefs = [];
                    for(var i=0; i<links.length; i++){
                        hrefs.push(links[i].href);
                    }
                    return hrefs;
                """, dialog)
                
                before_count = len(collected)
                if js_links:
                    for h in js_links:
                        u = self.parse_username_from_href(h)
                        if u and u != self.username.lower():
                            collected.add(u)
                
                # İlerleme kontrolü
                if len(collected) > before_count:
                    # Yeni veri geldiyse retry sıfırla
                    scroll_attempts = 0
                    same_len_count = 0
                else:
                    same_len_count += 1
                
                # Ekrana durum yaz
                if expected_min and expected_min > 0:
                     print(f"\r   -> Taranan: {len(collected)} / ~{expected_min}", end="")
                else:
                     print(f"\r   -> Taranan: {len(collected)}", end="")

                # Limit kontrolü
                if limit and len(collected) >= limit:
                    print(f"\nLimit ({limit}) aşıldı.")
                    break
                
                # Hedefe ulaşıldı mı?
                if expected_min and len(collected) >= expected_min:
                    print(f"\nHedef sayıya ({expected_min}) ulaşıldı.")
                    break

                # Scroll İşlemi (Geliştirilmiş Wiggle + scrollIntoView)
                # ----------------------------------------------------------------
                # YENİ YÖNTEM: En son elemanı bul ve görünür yap (Lazy Load Tetikleyici)
                # ----------------------------------------------------------------
                driver.execute_script("""
                    var container = arguments[0];
                    // Container içindeki tüm potansiyel öğeleri bul
                    var items = container.querySelectorAll('div[role="button"], div[role="listitem"], a'); 
                    if (items.length > 0) {
                        // Son öğeye odaklan ve scroll et
                        items[items.length - 1].scrollIntoView(true);
                    } else {
                        // Öğeler bulunamazsa klasik scroll
                        container.scrollTop = container.scrollHeight;
                    }
                """, dialog)
                time.sleep(1.0) # Yüklenmesi için bekle
                
                # Wiggle (Sallama) - Bazen scrollIntoView yetmez
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                time.sleep(0.5)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 300", dialog)
                time.sleep(0.3)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                time.sleep(0.8)
                
                new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                
                # Scroll takıldıysa veya liste uzamadıysa
                if new_h == last_h or same_len_count > 0:
                    if same_len_count > 0:
                        # Beklemeye devam et ama çok uzun sürerse çık
                        pass
                    
                    # Zorunlu bekleme (Yükleniyor olabilir)
                    time.sleep(1)

                    # 2. Yöntem: Mouse Wheel Event (JS) ve Element Odaklı Scroll
                    try:
                        # Gelişmiş Scroll Elementi Bulucu (Otomatik Tespit) - TEKRAR KONTROL
                        # Scroll yaparken element değişebilir, bu yüzden her seferinde kontrol ediyoruz.
                        new_dialog = driver.execute_script("""
                            var container = arguments[0];
                            var allDivs = container.getElementsByTagName('div');
                            var bestDiv = null;
                            var maxScrollHeight = 0;
                            
                            for (var i = 0; i < allDivs.length; i++) {
                                var d = allDivs[i];
                                if (d.scrollHeight > d.clientHeight && d.clientHeight > 0) {
                                    if (d.scrollHeight > maxScrollHeight) {
                                        maxScrollHeight = d.scrollHeight;
                                        bestDiv = d;
                                    }
                                }
                            }
                            return bestDiv || container;
                        """, dialog_container)
                        
                        if new_dialog and new_dialog != dialog:
                             dialog = new_dialog

                        # Son elemana scroll yap (Lazy Loading tetikleyici)
                        driver.execute_script("""
                            var d = arguments[0];
                            var items = d.querySelectorAll('div[role="button"], a'); 
                            if (items.length > 0) {
                                items[items.length - 1].scrollIntoView(true);
                            }
                        """, dialog)
                        time.sleep(0.5)

                        # KLAVYE DESTEĞİ (PAGE_DOWN) - YEDEK GÜÇ
                        try:
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                        except: pass

                    except: pass
                    
                    # Limit aşımı kontrolü (Zaman aşımı)
                    if same_len_count > 25: # 25 deneme boyunca veri gelmediyse
                        # Eğer hedefe çok yakınsak (%90) kabul et
                        if expected_min and len(collected) >= expected_min * 0.90:
                             print(f"\nVeri akışı durdu ama hedefe yakınız ({len(collected)}/{expected_min}). Devam ediliyor.")
                             break
                        
                        print("\nListe sonuna gelindi veya veri akışı durdu (Zaman aşımı).")
                        break

                    # Scroll yüksekliği değişmediyse sayacı artır
                    if new_h == last_h:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        last_h = new_h
                else:
                    last_h = new_h
            
            print(f"\n{list_type} tarama tamamlandı: {len(collected)} kişi bulundu.")

        except Exception as e:
            print(f"\nListe tarama hatası: {e}")
        
        # Modalı kapat (Gelişmiş)
        print("Modal kapatılıyor...")
        try:
            # 1. Kapat butonu (SVG)
            close_btn = driver.find_element(By.XPATH, "//*[name()='svg' and (@aria-label='Kapat' or @aria-label='Close')]/ancestor::div[@role='button']")
            close_btn.click()
            time.sleep(1)
        except:
            # 2. ESC tuşu
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
            
        return collected

    def smart_unfollow_cleanup(self, max_users=50, mode="non_followers"):
        """
        AI Modu için optimize edilmiş, profil gezmeden hızlı unfollow yapan metot.
        mode: "non_followers" (Sadece takip etmeyenler) veya "all" (Herkes)
        """
        print(f"\n⚡ AKILLI TEMİZLİK MODU ({mode}) BAŞLATILIYOR ⚡")
        
        # 0. CACHE TEMİZLİĞİ (Kullanıcı İsteği - Her Seferinde Taze Veri)
        # Kullanıcı "yanlış hesaplıyor" dediği için eski cache dosyalarını siliyoruz.
        cache_file = f"followers_cache_{self.username}.json"
        if os.path.exists(cache_file):
            try:
                print("🧹 Temizlik Modu: Eski cache dosyası siliniyor (Güncel veri çekilecek)...")
                os.remove(cache_file)
            except Exception as e:
                print(f"⚠️ Cache silinemedi: {e}")

        print("Adım 1: Profil verileri analiz ediliyor (Lütfen bekleyin)...")
        
        # 1. Listeleri Çek (Güvenli bir şekilde)
        try:
            self.browser_manager.navigate_to_profile(self.username)
            # Profil sayılarını al (Referans için)
            visible_following = 0
            visible_followers = 0
            
            try:
                fl_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following/')]")))
                visible_following = self.parse_follower_count(fl_link.text or fl_link.get_attribute("title"))
                
                f_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]")
                visible_followers = self.parse_follower_count(f_link.text or f_link.get_attribute("title"))
                
                print(f"📊 Profil Verisi: {visible_followers} Takipçi | {visible_following} Takip Edilen")
            except:
                print("⚠️ Profil sayıları tam okunamadı.")
                if visible_following == 0: visible_following = 1000
                if visible_followers == 0: visible_followers = 1000
                
            # ---------------------------------------------------------
            # YENİ YÖNTEM: Önce API (Fetch) ile dene, olmazsa Scroll yap
            # ---------------------------------------------------------
            
            following = self.fetch_users_via_api("following", limit=None, min_expected=visible_following)
            
            # API Eksik Çektiyse (Profil sayısının %90'ından az ise)
            # Eşik düşürüldü: %98 -> %90 (Scroll takılmasını önlemek için toleranslı)
            if following and visible_following > 0 and len(following) < visible_following * 0.90:
                 print(f"⚠️ API eksik liste çekti ({len(following)}/{visible_following}). Scroll ile tamamlanıyor...")
                 # Mevcut listeyi koruyarak scroll yap
                 scraped_following = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
                 following.update(scraped_following)
            elif following and visible_following > 0 and len(following) < visible_following:
                 print(f"ℹ️ API taraması tamamlandı: {len(following)}/{visible_following}. (Ufak farklar normaldir, devam ediliyor)")

            if not following:
                print("⚠️ API ile following çekilemedi, eski (scroll) yönteme geçiliyor...")
                following = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
            
            followers = set()
            if mode == "non_followers":
                print("🔄 Takipçi listesi güncelleniyor (Bu işlem biraz sürebilir)...")
                
                # API Rate Limit Önlemi: İki çağrı arasında bekle
                print("⏳ API güvenliği için 5 saniye bekleniyor...")
                time.sleep(5)
                
                # API ile Followers çek
                followers = self.fetch_users_via_api("followers", limit=None, min_expected=visible_followers)
                
                if not followers:
                    print("⚠️ API ile followers çekilemedi, eski (scroll) yönteme geçiliyor...")
                    # Sayfa yenileme (Modal temizliği)
                    self.driver.refresh()
                    time.sleep(3)
                    followers = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)
                
                # API Eksik Çektiyse (Profil sayısının %90'ından az ise)
                # Eşik düşürüldü: %98 -> %90 (Scroll takılmasını önlemek için toleranslı)
                if followers and visible_followers > 0 and len(followers) < visible_followers * 0.90:
                     print(f"⚠️ API eksik takipçi çekti ({len(followers)}/{visible_followers}). Scroll ile tamamlanıyor...")
                     scraped_followers = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)
                     followers.update(scraped_followers)
                elif followers and visible_followers > 0 and len(followers) < visible_followers:
                     print(f"ℹ️ API taraması tamamlandı: {len(followers)}/{visible_followers}. (Ufak farklar normaldir, devam ediliyor)")
            
        except Exception as e:
            print(f"Listeler çekilirken hata oluştu: {e}")
            return 0
            
        if not following:
            print("Takip edilenler listesi boş veya çekilemedi.")
            return 0
            
        # 2. Karşılaştır ve Hedef Belirle
        print("Adım 2: Hedef kitle belirleniyor...")
        
        target_pool = []
        if mode == "non_followers":
            target_pool = [u for u in following if u not in followers]
        else:
            target_pool = list(following) # Herkes
            
        # Whitelist ve Süre Kontrolü (Decision Maker)
        targets = []
        skipped_whitelist = 0
        skipped_recent = 0
        
        for u in target_pool:
            # 1. Whitelist Kontrolü
            if self.decision_maker.is_whitelisted(u):
                skipped_whitelist += 1
                continue
                
            # 2. Süre Kontrolü (Son 3 gün içinde takip edilenleri koru)
            should_unfollow = self.decision_maker.should_unfollow(u, is_following_me=False, min_days_followed=0, ignore_relationship=True)
            
            if should_unfollow:
                targets.append(u)
            else:
                skipped_recent += 1
                
        print(f"📊 Analiz Sonucu:")
        print(f"   - Toplam Takip Edilen: {len(following)}")
        if mode == "non_followers":
            print(f"   - Toplam Takipçi: {len(followers)}")
            print(f"   - Seni Takip Etmeyenler: {len(target_pool)}")
        else:
            print(f"   - Hedef Kitle: Herkes ({len(target_pool)} kişi)")
            
        print(f"   - Whitelist Koruması: {skipped_whitelist} kişi")
        print(f"   - Yeni Takip (3 Gün) Koruması: {skipped_recent} kişi")
        print(f"   - SİLİNECEK: {len(targets)} kişi")
        
        if not targets:
            print("✅ Temizlenecek kimse yok!")
            return 0
            
        if len(targets) > max_users:
            print(f"⚠️ Güvenlik limiti: Sadece ilk {max_users} kişi silinecek.")
            targets = targets[:max_users]
            
        # 3. Profil Ziyareti ile Silme (API Modu için Zorunlu)
        # API ile alınan veriler DOM'da (ekranda) olmadığı için liste üzerinden silinemez.
        # Bu yüzden en güvenli ve hatasız yöntem olan Profil Ziyareti moduna geçiyoruz.
        print("\n🚀 Adım 3: Güvenli silme işlemi başlıyor (Profil Ziyareti ile)...")
        print("   (API ile alınan listeler ekranda görünmediği için profil ziyareti zorunludur)")
        
        # Modalı kapat (Eğer açıksa)
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
        except: pass
        
        count = 0
        for user in targets:
            if self.is_action_blocked():
                print("⛔ Engel algılandı, işlem durduruluyor.")
                break
                
            print(f"🔥 Siliniyor: {user}...", end=" ")
            
            try:
                # Profiline git
                self.browser_manager.navigate_to_profile(user)
                
                # Rastgele bekleme (İnsan taklidi - Optimize Edildi)
                time.sleep(random.uniform(1.0, 2.5))
                
                # Butonu bul (Sayfadaki Takiptesin/Following butonu)
                unfollow_btn_found = self.browser_manager.find_following_button()
                
                if unfollow_btn_found:
                    # Tıkla
                    try:
                        unfollow_btn_found.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", unfollow_btn_found)
                    
                    # Onay Penceresi (Dialog) - Geliştirilmiş ve Optimize Edilmiş
                    try:
                        # Dialog gelmesini bekle (Maks 3 sn)
                        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    except:
                        pass

                    # Butonu bul ve tıkla
                    confirm_btn = self.browser_manager.find_unfollow_confirm_button()
                    
                    if confirm_btn:
                        try:
                            confirm_btn.click()
                            count += 1
                            self.log_action("UNFOLLOW", user)
                            print("SİLİNDİ ✅")
                        except:
                             self.driver.execute_script("arguments[0].click();", confirm_btn)
                             count += 1
                             self.log_action("UNFOLLOW", user)
                             print("SİLİNDİ ✅")
                    else:
                        print("Onay penceresi çıkmadı veya buton bulunamadı ❌")
                else:
                    print("Unfollow butonu bulunamadı (Zaten çıkılmış olabilir) ⚠️")
                
            except Exception as e:
                print(f"Hata: {e}")
                # Invalid Session ID hatası gelirse driver'ı yeniden başlatmak gerekebilir ama
                # şimdilik sadece pass geçiyoruz, döngü devam etsin.
                if "invalid session id" in str(e).lower():
                    print("KRİTİK HATA: Tarayıcı oturumu koptu. Çıkılıyor...")
                    break
            
            # İşlem arası bekleme
            time.sleep(random.uniform(1.0, 2.0))

        print(f"\n🎉 İşlem Tamamlandı! Toplam silinen: {count}")
        return count

    def algorithm_based_unfollow(self, fast=True, turbo=True, min_days=0, keep_verified=False, keep_min_followers=0):
        """
        Tam Algoritmik Mantık (Geliştirilmiş):
        1. Following listesini çek (Tümü)
        2. Followers listesini çek (Tümü)
        3. Karşılaştır (Difference)
        4. Whitelist uygula
        5. Hayalet Doğrulama (Ghost Check) - Ekstra Güvenlik
        6. Unfollow yap (Profil ziyareti ile - En güvenli yöntem)
        """
        
        # Önce profildeki sayıları al (Güvenlik Kontrolü İçin)
        self.driver.get(f"https://www.instagram.com/{self.username}/")
        time.sleep(3)
        
        visible_followers = 0
        visible_following = 0
        
        try:
            f_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]")))
            f_text = f_link.text or f_link.get_attribute("title")
            visible_followers = self.parse_follower_count(f_text)
            if visible_followers == 0:
                 try:
                     sp = f_link.find_element(By.XPATH, ".//span")
                     visible_followers = self.parse_follower_count(sp.get_attribute("title") or sp.text)
                 except: pass
            
            fl_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following/')]")))
            fl_text = fl_link.text or fl_link.get_attribute("title")
            visible_following = self.parse_follower_count(fl_text)
            if visible_following == 0:
                 try:
                     sp = fl_link.find_element(By.XPATH, ".//span")
                     visible_following = self.parse_follower_count(sp.get_attribute("title") or sp.text)
                 except: pass
                 
            print(f"📊 Profil Verisi -> Takipçi: {visible_followers} | Takip Edilen: {visible_following}")
        except:
            print("⚠️ Profil sayıları okunamadı, temkinli modda devam edilecek.")

        # 1. Following Çek
        following_set = self.fetch_users_via_api("following", limit=None)
        if not following_set:
             print("⚠️ API ile following çekilemedi, eski (scroll) yönteme geçiliyor...")
             following_set = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
        
        print(f"✅ Toplam Takip Edilen (Following): {len(following_set)}")
        
        if visible_following > 0 and len(following_set) < visible_following * 0.90:
             print(f"❌ UYARI: Takip edilen listesi eksik çekildi! (Beklenen: {visible_following}, Alınan: {len(following_set)})")
             print("İşlem güvenliği için durduruluyor.")
             return
        
        if not following_set:
            print("❌ Following listesi boş! İşlem iptal.")
            return

        # SAYFAYI YENİLE
        print("🔄 Sayfa yenileniyor...")
        self.browser_manager.navigate_to_profile(self.username)
        # self.driver.get(f"https://www.instagram.com/{self.username}/")
        # time.sleep(4)

        # 2. Followers Çek
        followers_set = self.fetch_users_via_api("followers", limit=None)
        if not followers_set:
             print("⚠️ API ile followers çekilemedi, eski (scroll) yönteme geçiliyor...")
             followers_set = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)

        print(f"✅ Toplam Takipçi (Followers): {len(followers_set)}")
        
        # GÜVENLİK KONTROLÜ
        if visible_followers > 0:
            if len(followers_set) < visible_followers * 0.95: 
                 print(f"❌ ACİL DURDURMA: Takipçi listesi eksik çekildi! (Beklenen: {visible_followers}, Alınan: {len(followers_set)})")
                 print("Bu durumda işlem yapılırsa SENİ TAKİP EDENLERİ DE SİLEBİLİRİM.")
                 return
        else:
            if not followers_set:
                 print("❌ ACİL DURDURMA: Profil bilgisi okunamadı ve takipçi listesi boş.")
                 return
            if len(followers_set) < 10 and len(following_set) > 20: 
                 print("❌ Çekilen takipçi sayısı çok düşük, işlem iptal ediliyor.")
                 return

        # 3. Karşılaştır
        to_unfollow = []
        for user in following_set:
            if user not in followers_set:
                if self.decision_maker.should_unfollow(user, is_following_me=False, min_days_followed=min_days):
                    to_unfollow.append(user)
        
        print(f"📋 Analiz Sonucu: {len(to_unfollow)} kişi takipten çıkılacak.")
        
        if len(to_unfollow) > len(following_set) * 0.9:
            print("⚠️ UYARI: Listenin %90'ından fazlasını silmek üzeresiniz.")
            confirm = input("Yine de devam edilsin mi? (evet/hayir): ")
            if confirm.lower() != "evet":
                return

        # ---------------------------------------------------------
        # 4. HAYALET DOĞRULAMA (GHOST CHECK)
        # ---------------------------------------------------------
        if to_unfollow:
            print("\n🕵️ GÜVENLİK MODU: Adaylar 'Followers' listesinde aranarak son kez doğrulanıyor...")
            verified_targets = []
            
            try:
                # Followers modalini aç
                self.driver.get(f"https://www.instagram.com/{self.username}/")
                time.sleep(3)
                
                f_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]")))
                f_link.click()
                time.sleep(3)
                
                dialog = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                search_box = dialog.find_element(By.TAG_NAME, "input")
                
                check_count = 0
                for user in to_unfollow:
                    check_count += 1
                    if check_count % 50 == 0:
                        print(f"   -> Kontrol edildi: {check_count}/{len(to_unfollow)}")

                    try:
                        search_box.send_keys(Keys.CONTROL + "a")
                        search_box.send_keys(Keys.DELETE)
                        search_box.send_keys(user)
                        time.sleep(0.6) 
                        
                        found = False
                        # Sonuç kontrolü
                        results = dialog.find_elements(By.XPATH, f".//a[contains(@href, '/{user}/')]")
                        if results:
                            found = True
                        else:
                            # Text kontrolü
                            spans = dialog.find_elements(By.XPATH, f".//span[contains(text(), '{user}')]")
                            if spans:
                                found = True
                                
                        if found:
                            print(f"❌ RİSK: {user} seni takip ediyor görünüyor (Listeden çıkarıldı).")
                        else:
                            verified_targets.append(user)
                            
                    except Exception as e:
                        print(f"   Doğrulama hatası ({user}): {e}")
                        verified_targets.append(user)
                
                to_unfollow = verified_targets
                print(f"✅ Doğrulama Bitti. Kesinleşen Hedef: {len(to_unfollow)} kişi")
                
            except Exception as e:
                print(f"Doğrulama modunda genel hata: {e}")
                print("⚠️ Doğrulama tamamlanamadı, mevcut listeyle devam ediliyor.")

        # 5. İşlem Başlıyor
        print("\n🚀 Unfollow işlemi başlatılıyor...")
        
        processed = 0
        for user in to_unfollow:
            try:
                self.driver.get(f"https://www.instagram.com/{user}/")
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                
                # KORUMA KONTROLLERİ
                is_verified = False
                follower_count = 0
                
                if keep_verified:
                    is_verified = self.browser_manager.is_verified_profile()
                    
                if keep_min_followers > 0:
                     try:
                         fl_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]")
                         fl_text = fl_link.text or fl_link.get_attribute("title")
                         follower_count = self.parse_follower_count(fl_text)
                     except: pass

                if not self.decision_maker.should_unfollow(user, is_following_me=False, min_days_followed=min_days,
                                                         keep_verified=keep_verified, is_verified=is_verified,
                                                         keep_min_followers=keep_min_followers, follower_count=follower_count):
                    print(f"🛡️ Atlandı (Koruma): {user}")
                    continue

                # Unfollow İşlemi
                if self.decision_maker.action_allowed("UNFOLLOW"):
                    # -----------------------------------------------------------
                    # Buton bulma mantığı (Geliştirilmiş - v2)
                    # -----------------------------------------------------------
                    unfollow_btn_found = None
                    
                    # 1. JS ile buton bulma (Daha kararlı)
                    unfollow_btn_found = self.driver.execute_script("""
                        var buttons = document.querySelectorAll('button, div[role="button"], a[role="button"]');
                        
                        // 1. Metin Kontrolü
                        for (var i = 0; i < buttons.length; i++) {
                            var t = (buttons[i].innerText || "").toLowerCase().trim();
                            // Tam eşleşme
                            if (['takiptesin', 'following', 'istek gönderildi', 'requested'].includes(t)) {
                                return buttons[i];
                            }
                            // İçerik kontrolü (Mesaj butonu hariç)
                            if ((t.includes('takiptesin') || t.includes('following')) && !t.includes('mesaj') && !t.includes('message')) {
                                 return buttons[i];
                            }
                        }
                        
                        // 2. Aria-Label Kontrolü (İkonlu butonlar için)
                        var svgs = document.querySelectorAll('svg[aria-label="Following"], svg[aria-label="Takiptesin"]');
                        if (svgs.length > 0) {
                            var p = svgs[0].closest('button, div[role="button"], a[role="button"]');
                            if (p) return p;
                        }
                        
                        return null;
                    """)
                    
                    # 2. Eğer JS bulamazsa, Python ile XPATH dene (Daha güçlü)
                    if not unfollow_btn_found:
                        try:
                            xpath_list = [
                                "//button[.//div[text()='Takiptesin']]",
                                "//button[.//div[text()='Following']]",
                                "//div[@role='button'][.//div[text()='Takiptesin']]",
                                "//div[@role='button'][.//div[text()='Following']]",
                                "//*[text()='Takiptesin']/ancestor::*[self::button or @role='button']",
                                "//*[text()='Following']/ancestor::*[self::button or @role='button']",
                                "//*[name()='svg' and (@aria-label='Takiptesin' or @aria-label='Following')]/ancestor::*[self::button or @role='button']"
                            ]
                            
                            for xp in xpath_list:
                                try:
                                    elems = self.driver.find_elements(By.XPATH, xp)
                                    for el in elems:
                                        if el.is_displayed():
                                            unfollow_btn_found = el
                                            break
                                    if unfollow_btn_found: break
                                except: pass
                        except: pass

                    if not unfollow_btn_found:
                        # Kontrol: "Takip Et" butonu var mı? (Zaten silinmiş mi?)
                        try:
                            follow_btn = self.driver.find_element(By.XPATH, "//button[text()='Takip Et' or text()='Follow' or text()='Follow Back']")
                            if follow_btn:
                                print(f"⚠️ Zaten takip edilmiyor: {user}")
                                continue
                        except: pass
                        
                        print(f"⚠️ 'Takiptesin' butonu bulunamadı: {user}")
                        continue
                    
                    # Tıkla
                    try:
                        unfollow_btn_found.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", unfollow_btn_found)
                    
                    time.sleep(1.5)

                    # -----------------------------------------------------------
                    # Onay Penceresi (Dialog) - Geliştirilmiş
                    # -----------------------------------------------------------
                    confirmed = False
                    
                    # Dialog Bekleme
                    try:
                        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    except:
                        time.sleep(1) 

                    # JS ile dialog butonu bulma
                    for _ in range(4): # 4 kere dene
                        confirmed = self.driver.execute_script("""
                            var dialog = document.querySelector('div[role="dialog"]');
                            var container = dialog || document.body;
                            var buttons = container.querySelectorAll('button, div[role="button"], div[tabindex="0"], span');
                            
                            // 1. Metin ile bul
                            for (var i = 0; i < buttons.length; i++) {
                                var t = (buttons[i].innerText || "").toLowerCase().trim();
                                if (['takibi bırak', 'unfollow', 'bırak'].includes(t)) {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                            
                            // 2. Renk ile bul (Kırmızı)
                            for (var i = 0; i < buttons.length; i++) {
                                var style = window.getComputedStyle(buttons[i]);
                                if (style.color.includes('237, 73, 86') || style.color.includes('255, 48, 64')) {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                        if confirmed: break
                        
                        # Python ile XPATH Fallback
                        try:
                            targets = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Takibi Bırak') or contains(text(), 'Unfollow')]")
                            for btn in targets:
                                if btn.is_displayed():
                                    try:
                                        btn.click()
                                        confirmed = True
                                        break
                                    except: pass
                        except: pass
                        
                        if confirmed: break
                        time.sleep(1.0)
                    
                    if confirmed:
                        self.log_action("UNFOLLOW", user)
                        print(f"✅ [{processed+1}/{len(to_unfollow)}] Takipten çıkıldı: {user}")
                        processed += 1
                        
                        if self.is_action_blocked():
                            print("⛔ Engel tespit edildi. Beklemeye alınıyor (120s)...")
                            time.sleep(120)
                        
                        if fast and turbo:
                            time.sleep(random.uniform(2, 5))
                        elif fast:
                            time.sleep(random.uniform(5, 12))
                        else:
                            self.rand_delay(True)
                    else:
                        print(f"⚠️ Onay penceresi bulunamadı: {user}")
                        
            except Exception as e:
                print(f"❌ Hata ({user}): {e}")
                continue
                
        print("\n🏁 Algoritmik unfollow tamamlandı.")
        self.send_telegram(f"🤖 Algoritmik Unfollow Tamamlandı!\n\nToplam Silinen: {processed}\nKalan Hedef: {len(to_unfollow) - processed}")

    def get_location_url(self, query):
        """Verilen sorgu için konum URL'sini bulur."""
        try:
            print(f"Konum aranıyor: {query}...")
            self.driver.get(f"https://www.instagram.com/web/search/topsearch/?context=place&query={query}")
            time.sleep(2)
            
            text = ""
            try:
                text = self.driver.find_element(By.TAG_NAME, "pre").text
            except:
                text = self.driver.page_source
                
            data = json.loads(text)
            places = data.get("places", [])
            
            if places:
                place = places[0].get("place", {})
                pk = place.get("pk")
                slug = place.get("slug")
                name = place.get("name")
                if pk and slug:
                    url = f"https://www.instagram.com/explore/locations/{pk}/{slug}/"
                    print(f"Konum bulundu: {name} ({url})")
                    return url
            print("Konum bulunamadı.")
            return None
        except Exception as e:
            print(f"Konum arama hatası: {e}")
            return None

    def collect_users_from_feed(self, url, limit=50):
        """Verilen feed URL'sinden (Hashtag/Konum) kullanıcı adlarını toplar."""
        driver = self.driver
        users = []
        
        print(f"Feed taranıyor... (Hedef: {limit} kullanıcı)")
        driver.get(url)
        time.sleep(5)
        
        # İlk gönderiyi bul ve tıkla
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            first_post = None
            for link in links:
                href = link.get_attribute("href")
                if href and "/p/" in href:
                    first_post = link
                    break
            
            if first_post:
                first_post.click()
                time.sleep(3)
            else:
                print("Gönderi bulunamadı.")
                return []
        except:
            return []
            
        # Gönderileri gez
        p_count = 0
        while len(users) < limit and p_count < limit * 3: # Sonsuz döngü önlemi
            p_count += 1
            try:
                # Kullanıcı adını al
                # Header kısmındaki link
                header_link = None
                try:
                    header_link = driver.find_element(By.XPATH, "//header//a[not(contains(@href, '/explore/'))]")
                except:
                    # Alternatif XPATH
                    header_link = driver.find_element(By.XPATH, "//div[contains(@class, '_aaqt')]//a")

                if header_link:
                    username = header_link.text
                    if not username: # Bazen text boş olabilir, href'den al
                        href = header_link.get_attribute("href")
                        if href:
                            username = self.parse_username_from_href(href)

                    if username and username not in users:
                        users.append(username)
                        print(f"Bulundu: {username} ({len(users)}/{limit})")
                
                # Sonraki gönderi
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                time.sleep(random.uniform(1.5, 3))
            except:
                # Sonraki gönderiye geçmeyi dene (hata olsa bile)
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ARROW_RIGHT)
                    time.sleep(2)
                except:
                    break
        
        return users

    def get_active_users_from_seed(self, seed_username, limit=30):
        """
        Seed (Kaynak) kullanıcının son gönderilerinden yorum yapanları ve beğenenleri toplar.
        Bu yöntem 'Aktif' kullanıcıları bulur.
        """
        driver = self.driver
        users = set()
        
        print(f"Kaynak taranıyor: {seed_username} (Hedef: {limit} aktif kullanıcı)")
        
        try:
            self.browser_manager.navigate_to_profile(seed_username)
            time.sleep(3)
            
            # Son 3 gönderiyi gez
            # Profildeki ilk 3 gönderi linkini al (Pinned olabilir, sorun değil)
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                post_links = [l.get_attribute("href") for l in links if "/p/" in l.get_attribute("href")]
                # Tekrar edenleri temizle ve ilk 3'ü al
                post_links = list(dict.fromkeys(post_links))[:3]
            except:
                post_links = []
                
            if not post_links:
                print("   -> Gönderi bulunamadı.")
                return []
                
            for post_url in post_links:
                if len(users) >= limit:
                    break
                    
                driver.get(post_url)
                time.sleep(3)
                
                # Yorumları açmaya çalış (Load more comments)
                try:
                    load_more = driver.find_element(By.XPATH, "//*[contains(text(), 'View more comments') or contains(text(), 'daha fazla yorum')]")
                    load_more.click()
                    time.sleep(2)
                except: pass
                
                # Yorumlardaki kullanıcı adlarını topla
                # Genellikle _a9zc, _a9ze classları veya basitçe 'a' tagleri
                try:
                    # Yorum alanını bulmaya çalış
                    comment_area = driver.find_elements(By.XPATH, "//ul//div//a")
                    for elem in comment_area:
                        href = elem.get_attribute("href")
                        if href:
                            u = self.parse_username_from_href(href)
                            if u and u != seed_username and u != self.username:
                                users.add(u)
                except: pass
                
                print(f"   -> {len(users)} kişi toplandı...")
                
        except Exception as e:
            print(f"Seed hata: {e}")
            
        return list(users)

    def follow_smart_seeds(self, limit=20, criteria=None):
        """
        Akıllı Seed Takip Modülü (Filtresiz, Hızlı, Rastgele)
        """
        driver = self.driver
        followed = 0
        processed = 0
        
        # GERÇEK ARTIŞ: Dalgalı Limit
        variance = int(limit * 0.10)
        actual_limit = limit + random.randint(-variance, variance)
        if actual_limit < 1: actual_limit = 1
        
        # Popüler Türk Kadın Influencer/Ünlü Listesi (Seed Pool)
        seeds = [
            "danlabilic", "duyguozaslan", "seymasubasi", "gamzeercel", "handemiyy", 
            "bensusoral", "serenaysarikaya", "ezgimola", "demetozdemir", "neslihanatagul", 
            "hazalkaya", "fahriyevcen", "elcinsangu", "busevarol", "eceerken", "caglasikel",
            "burcuozberk", "aslienver", "pelinakil", "benguofficial", "demetakalin",
            "sedasayan", "ebrugundes", "hadise", "muratboz", "acunilicali", 
            "cznburak", "nusret" 
        ]
        
        random.shuffle(seeds)
        
        print(f"Akıllı Seed Takip Başlıyor. Hedef: ~{limit} (Planlanan: {actual_limit})")
        
        seed_index = 0
        while followed < actual_limit:
            if seed_index >= len(seeds):
                seed_index = 0
                random.shuffle(seeds) 
                
            current_seed = seeds[seed_index]
            seed_index += 1
            
            # Strateji Seçimi: %70 Yorumlar (Aktif), %30 Takipçiler (Pasif)
            strategy = "comments" if random.random() > 0.3 else "followers"
            
            candidates = []
            if strategy == "comments":
                candidates = self.get_active_users_from_seed(current_seed, limit=40)
            else:
                try:
                    s_set = self.scrape_modal_users("followers", limit=40, target_username=current_seed)
                    candidates = list(s_set)
                except:
                    candidates = []
            
            if not candidates:
                continue
            
            # RASTGELELİK: Aday listesini karıştır
            random.shuffle(candidates)
                
            print(f"Analiz edilecek aday sayısı: {len(candidates)}")
            
            for username in candidates:
                if followed >= actual_limit:
                    break
                    
                # Geçmiş kontrolü
                if self.check_history(username):
                    continue
                    
                processed += 1
                print(f"[{processed}] İşleniyor: {username}")
                
                try:
                    # Profile git
                    self.browser_manager.navigate_to_profile(username)
                    time.sleep(random.uniform(1.5, 2.5)) 
                    
                    # Gizli Profil Kontrolü
                    is_private = self.browser_manager.is_private_profile()
                    if is_private:
                        print(f"   -> Gizli Profil. Sadece takip isteği gönderilecek.")
                    
                    # ETKİLEŞİM ODAKLI BÜYÜME (Story + Like + Follow)
                    
                    if not is_private:
                        # 1. Hikaye İzleme (Varsa)
                        # %40 ihtimalle hikayeyi izle
                        if random.random() < 0.40:
                             self.browser_manager.watch_story()
                             time.sleep(1)

                        # 2. Son Gönderiyi Beğenme
                        # %50 ihtimalle son gönderiyi beğen
                        if random.random() < 0.50:
                             self.browser_manager.like_latest_post(limit=1)
                             time.sleep(1)

                    # 3. Doğrudan Takip (Filtresiz, Hızlı)
                    try:
                        # 3 saniye bekle
                        short_wait = WebDriverWait(driver, 3)
                        btn = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                        
                        btn.click()
                        followed += 1
                        self.log_action("FOLLOW", username)
                        print(f"   -> BAŞARILI. Toplam: {followed}/{actual_limit}")
                        
                        # Hızlandırıldı (5-10 sn)
                        time.sleep(random.uniform(5, 10))
                        
                    except:
                        # Takip butonu yoksa, belki zaten takip ediliyor?
                        try:
                            following_btn = driver.find_elements(By.XPATH, "//button[.//div[contains(text(), 'Takiptesin') or contains(text(), 'Following')]]")
                            if following_btn:
                                print("   -> Zaten takip ediliyor.")
                                self.log_action("FOLLOW", username)
                            else:
                                print("   -> Takip butonu bulunamadı.")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Profil hatası: {e}")
                    continue
            
            # Seed değişimi öncesi bekleme
            time.sleep(3)

    def follow_target_followers(self, target_username, limit=50):
        """
        Belirtilen kullanıcının takipçilerini sırayla takip eder.
        Filtre yok, analiz yok, sadece takip.
        """
        driver = self.driver
        
        # GERÇEK ARTIŞ: Günlük aksiyonlar dalgalı olmalı (Limit +/- %10)
        variance = int(limit * 0.10)
        actual_limit = limit + random.randint(-variance, variance)
        if actual_limit < 1: actual_limit = 1
        
        print(f"Hedef Profil: {target_username}")
        print(f"Hedef Takip (Dalgalı): ~{limit} (Planlanan: {actual_limit})")
        
        try:
            # 1. Profile Git
            self.browser_manager.navigate_to_profile(target_username)
            # time.sleep(2) -> Gereksiz, navigate_to_profile zaten bekliyor
            
            # 2. Takipçiler butonuna tıkla
            try:
                # "/followers/" içeren linki bul
                f_link = self.wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/followers/')]")))
                f_link.click()
            except:
                print("Takipçi listesi açılamadı (Gizli profil veya buton yok).")
                return

            # time.sleep(3) -> Optimize Edildi
            
            # 3. Liste Yapısını Tespit Et (Modal vs Tam Sayfa)
            dialog = None
            scrollable_element = None
            is_full_page = False

            try:
                # A) Modal Diyalog Kontrolü
                # Dialog penceresinin açılmasını bekle (Maks 5 sn)
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                
                dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
                print("   -> Modal görünümü tespit edildi.")
                
                # Scroll edilebilir alanı bul (JS ile)
                scrollable_element = driver.execute_script("""
                    var container = arguments[0];
                    var divs = container.getElementsByTagName('div');
                    var maxH = 0;
                    var maxDiv = null;
                    for(var i=0; i<divs.length; i++){
                        var style = window.getComputedStyle(divs[i]);
                        if(style.overflowY === 'auto' || style.overflowY === 'scroll'){
                            if(divs[i].scrollHeight > maxH){
                                maxH = divs[i].scrollHeight;
                                maxDiv = divs[i];
                            }
                        }
                    }
                    if (maxDiv) return maxDiv;
                    return container;
                """, dialog)
                
            except:
                # B) Tam Sayfa Kontrolü
                if "/followers" in driver.current_url or "/following" in driver.current_url:
                    print("   -> Tam sayfa görünümü tespit edildi.")
                    is_full_page = True
                    dialog = driver.find_element(By.TAG_NAME, "body") # Butonları tüm sayfada ara
                else:
                    print("Modal dialog veya liste sayfası bulunamadı.")
                    return

            followed_count = 0
            consecutive_no_buttons = 0
            last_scroll_pos = -1
            same_scroll_count = 0
            
            while followed_count < actual_limit:
                # Scroll pozisyonu kontrolü (Listenin sonuna gelip gelmediğimizi anlamak için)
                try:
                    if is_full_page:
                        current_pos = driver.execute_script("return window.pageYOffset;")
                    else:
                        current_pos = driver.execute_script("return arguments[0].scrollTop;", scrollable_element)
                    
                    if current_pos == last_scroll_pos:
                        same_scroll_count += 1
                        if same_scroll_count > 15: # 15 tur boyunca aynı yerdeysek (yüklenme gecikmeleri için toleranslı)
                            print("Liste sonuna gelindi (Scroll ilerlemiyor), çıkılıyor.")
                            break
                    else:
                        same_scroll_count = 0
                        last_scroll_pos = current_pos
                except:
                    pass

                try:
                    # Butonları bul (Takip Et / Follow / Takiptesin / Following)
                    # Genişletilmiş XPath: 'Takip' kelimesi 'Takiptesin'i de kapsar, böylece zaten takip edilenleri görüp geçebiliriz.
                    buttons = dialog.find_elements(By.XPATH, ".//button[.//div[contains(text(), 'Takip') or contains(text(), 'Follow')]]")
                except:
                    buttons = []
                
                # Buton yoksa scroll yap
                if not buttons:
                    consecutive_no_buttons += 1
                    if consecutive_no_buttons > 20:
                        print("Liste sonuna gelindi veya buton bulunamadı, çıkılıyor.")
                        break
                        
                    if is_full_page:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    else:
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                    time.sleep(1.5)
                    continue
                else:
                    consecutive_no_buttons = 0

                # Bazen hiç işlem yapmadan aşağı kaydır (Rastgelelik için)
                if random.random() < 0.10:
                     print("   -> Rastgele: Liste kaydırılıyor (Atlama yapılıyor)...")
                     if is_full_page:
                         driver.execute_script("window.scrollBy(0, 600);")
                     else:
                         driver.execute_script("arguments[0].scrollTop += 600;", scrollable_element)
                     time.sleep(random.uniform(0.5, 1.0))
                     continue

                processed_in_batch = 0
                for btn in buttons:
                    if followed_count >= actual_limit:
                        break
                    
                    try:
                        # Zaten takip ediliyor mu kontrolü
                        txt = (btn.text or "").lower()
                        
                        # 1. Negatif Kontrol: Zaten takip ediliyorsa atla
                        if "takiptesin" in txt or "following" in txt or "istek" in txt or "requested" in txt:
                            continue
                            
                        # 2. Pozitif Kontrol: Sadece 'Takip' veya 'Follow' içerenler
                        if "takip" not in txt and "follow" not in txt:
                            continue
                            
                        # RASTGELELİK: %50 ihtimalle bu kişiyi pas geç
                        # Böylece sırayla gitmemiş oluruz
                        if random.random() < 0.50:
                            continue

                        # Görünürlük
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.3) 
                        
                        btn.click()
                        followed_count += 1
                        print(f"[{followed_count}/{actual_limit}] Takip edildi.")
                        processed_in_batch += 1
                        
                        # Hızlandırıldı (Eski: 3-7 sn -> Yeni: 1-2 sn)
                        time.sleep(random.uniform(1, 2))
                        
                    except:
                        pass
                
                # Batch bitince veya işlem yapılmadıysa scroll yap
                if is_full_page:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                else:
                    # En son butonu görünür yapmayı dene (Lazy load tetiklemek için en iyisi)
                    if buttons:
                        try:
                            last_btn = buttons[-1]
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_btn)
                        except:
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                    else:
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                
                self.safe_sleep(1.5, 2.0)
                
        except Exception as e:
            print(f"Hata: {e}")

    def follow_users_with_criteria(self, target_list, criteria=None, limit=50):
        """
        Belirtilen listedeki kullanıcıları kriterlere göre filtreleyip takip eder.
        criteria: {"gender": "female", "nationality": "turkish"}
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        print(f"Kriterli takip başlıyor. Hedef: {limit} kişi. Kriterler: {criteria}")
        
        processed = 0
        followed = 0
        
        for user in target_list:
            if followed >= limit:
                break
                
            # Engel kontrolü
            if self.is_action_blocked():
                print("İşlem engellendi, durduruluyor.")
                break
                
            # Daha önce kontrol edildi mi?
            if self.check_history(user):
                continue
                
            processed += 1
            print(f"[{processed}/{len(target_list)}] Analiz ediliyor: {user}")
            
            try:
                # Profile git
                self.browser_manager.navigate_to_profile(user)
                self.safe_sleep(2, 4)
                
                # Profil bilgilerini topla
                user_data = {
                    "username": user,
                    "fullname": "",
                    "bio": "",
                    "follower_count": 0,
                    "following_count": 0,
                    "is_private": False,
                    "is_verified": False
                }
                
                # Fullname
                try:
                    # H1 genellikle kullanıcı adı, fullname altında span veya div içinde olabilir
                    # Instagram yapısı değişebilir, meta tag'den çekmek daha güvenli olabilir
                    meta_title = driver.title # "Name (@username) • Instagram photos..."
                    if "(" in meta_title:
                        user_data["fullname"] = meta_title.split("(")[0].strip()
                except: pass
                
                # Bio
                try:
                    # Basit bir tespit: h1'in altındaki div'ler
                    # veya meta description
                    meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                    if meta_desc:
                        user_data["bio"] = meta_desc # Genellikle "X Followers, Y Following, Z Posts - ..."
                except: pass
                
                # Bio (Alternatif - Sayfa içi)
                try:
                    bio_elem = driver.find_element(By.XPATH, "//h1/..//div[contains(@class, '_aa_c')]") # Örnek class, değişebilir
                    if bio_elem:
                        user_data["bio"] += " " + bio_elem.text
                except: pass

                # Takipçi Sayısı (Karar mekanizması için - Geliştirilmiş)
                try:
                    # 1. Link üzerinden (/followers/)
                    f_link = driver.find_elements(By.XPATH, f"//a[contains(@href, '/followers/')]")
                    if f_link:
                        txt = f_link[0].text or f_link[0].get_attribute("title")
                        if txt:
                            user_data["follower_count"] = self.parse_follower_count(txt)
                    
                    # 2. UI Span taraması
                    if user_data["follower_count"] == 0:
                        spans = driver.find_elements(By.XPATH, "//ul//li//span")
                        for s in spans:
                            t_title = s.get_attribute("title")
                            t_text = s.text
                            if t_title:
                                val = self.parse_follower_count(t_title)
                                if val > 0:
                                    user_data["follower_count"] = val
                                    break
                            if "follower" in t_text or "takipçi" in t_text:
                                user_data["follower_count"] = self.parse_follower_count(t_text)
                                break
                                
                    # 3. Meta Tag Fallback
                    if user_data["follower_count"] == 0:
                        user_data["follower_count"] = self.get_follower_count_from_meta()
                except: pass

                # Karar ver
                if self.decision_maker.should_follow(user_data, criteria):
                    print(f"   -> Kriterlere uygun! Takip ediliyor: {user}")
                    
                    # Takip Et Butonu
                    btn = self.browser_manager.find_following_button() # Bu 'Following' yani zaten takip ediliyor demek
                    if btn:
                        print("   -> Zaten takip ediliyor.")
                        self.log_action("FOLLOW", user) # Veritabanına işle
                    else:
                        # Takip Et butonunu bul (Mavi buton)
                        try:
                            f_btn = w.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                            f_btn.click()
                            followed += 1
                            self.log_action("FOLLOW", user)
                            print(f"   -> Başarılı. Toplam: {followed}")
                            
                            # Bekleme
                            self.rand_delay()
                        except:
                            print("   -> Takip et butonu bulunamadı.")
                else:
                    print("   -> Kriterlere uymuyor, geçildi.")
                    
            except Exception as e:
                print(f"Hata ({user}): {e}")
                
        print(f"İşlem tamamlandı. Toplam Takip: {followed}")
        self.send_telegram(f"✅ Kriterli Takip Tamamlandı!\n\nTakip Edilen: {followed}\nİncelenen: {processed}")

    def fast_modal_unfollow_nonfollowers(self, max_actions=300, fast=True, turbo=True, min_days=0, keep_verified=False):
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        followers_set = set() # Başlangıçta boş küme olarak tanımlanmalı
        
        # 1. ADIM: Takipçileri (Followers) hafızaya al
        # Önce yerel dosyadan yüklemeyi dene
        followers_file = "known_followers.txt"
        loaded_from_file = False
        
        if os.path.exists(followers_file):
            try:
                with open(followers_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip().lower()
                        if line:
                            followers_set.add(line)
                if len(followers_set) > 0:
                    print(f"\nBilgi: Önbellekte {len(followers_set)} takipçi kayıtlı.")
                    use_cache = input("Takipçi listesini yeniden taramak yerine önbelleği kullanmak ister misiniz? (E/h) (Hızlı): ").strip().lower()
                    if use_cache in ["e", "evet", "yes", "y", ""]:
                        loaded_from_file = True
                        print("Önbellek kullanılıyor. Tarama atlandı.")
                    else:
                        followers_set.clear()
                        print("Önbellek temizlendi, yeniden taranacak.")
                else:
                    print("Bilgi: Önbellek dosyası bulundu ancak içi boş.")
            except Exception as e:
                print(f"Önbellek okuma hatası: {e}")

        if not loaded_from_file:
            print("Güncel takipçi listesi taranıyor... (Bu işlem listenin uzunluğuna göre zaman alabilir)")
            driver.get(f"https://www.instagram.com/{self.username}/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            
            total_followers = 0
            try:
                # Takipçi sayısını al (Modalı açmak için)
                # Aynı zamanda sayıyı da çekelim
                link = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]")))
            
                try:
                    # Sayıyı çek
                    c_txt = ""
                    # 1. Title attribute (Genellikle tam sayı: "1,234")
                    try:
                        sp = link.find_element(By.XPATH, ".//span[@title]")
                        c_txt = sp.get_attribute("title")
                    except:
                        pass
                
                    if not c_txt:
                        # 2. Span text (Genellikle "1.2k" formatında olabilir veya direkt sayı)
                        try:
                            spans = link.find_elements(By.TAG_NAME, "span")
                            for s in spans:
                                t = s.text.strip()
                                if any(char.isdigit() for char in t):
                                    c_txt = t
                                    break
                        except:
                            pass
                            
                    total_followers = self.parse_follower_count(c_txt)
                    print(f"Profilde görünen takipçi sayısı: {total_followers}")
                except:
                    pass
                
                # Eğer UI'dan çekilemediyse veya 0 geldiyse Meta Tag dene
                if total_followers == 0:
                    try:
                        total_followers = self.get_follower_count_from_meta()
                        print(f"Meta etiketinden çekilen takipçi sayısı: {total_followers}")
                    except:
                        pass

                link.click()
            except:
                # Link bulunamazsa bile meta tag dene (sayfa yüklendiyse)
                if total_followers == 0:
                    try:
                        # Header'dan çekmeyi dene (Daha güvenilir selector)
                        # href="/username/followers/" olan linki bul
                        f_link = driver.find_element(By.XPATH, f"//a[contains(@href, '/followers/')]//span")
                        total_followers = self.parse_follower_count(f_link.text)
                        print(f"Header linkinden çekilen takipçi sayısı: {total_followers}")
                    except:
                        try:
                            total_followers = self.get_follower_count_from_meta()
                            print(f"Meta etiketinden çekilen takipçi sayısı (Fallback): {total_followers}")
                        except:
                            pass
                        
                driver.get(f"https://www.instagram.com/{self.username}/followers/")
        
            try:
                # Dialog elementini bul (Role dialog) - Retry mekanizmalı ve Alternatifli
                dialog_container = None
                print("Dialog penceresi aranıyor...")
                
                # Strateji 1: Standart role='dialog'
                for i in range(5): # 5 deneme
                    try:
                        # Önce varlığını kontrol et
                        dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                        print("Dialog bulundu (role='dialog').")
                        break
                    except:
                        time.sleep(1)
                
                # Strateji 2: Direkt scroll container (_aano)
                if not dialog_container:
                    try:
                        print("Dialog role ile bulunamadı, _aano class aranıyor...")
                        dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, '_aano')]")))
                        # _aano bulunduysa, bu zaten scrollable alandır, ama biz container olarak bunu kullanabiliriz
                        # veya bunun parent'ını dialog kabul edebiliriz.
                        # Hiyerarşiyi bozmamak için bunu container kabul edelim.
                        print("Dialog yerine direkt scroll alanı bulundu.")
                    except:
                        pass

                # Strateji 3: Başlık metninden bulma (Takipçiler/Followers)
                if not dialog_container:
                    try:
                        print("Başlık metninden dialog aranıyor...")
                        xpath_text = "//*[contains(text(), 'Takipçiler') or contains(text(), 'Followers')]/ancestor::div[contains(@class, 'x1n2onr6') or contains(@class, '_aano') or position()=last()]"
                        dialog_container = driver.find_element(By.XPATH, xpath_text)
                        print("Başlık üzerinden container tahmin edildi.")
                    except:
                        pass

                # Strateji 4: Main role (Tam sayfa görünümü için - Direct URL)
                if not dialog_container:
                    try:
                        print("Main role aranıyor (Tam sayfa modu)...")
                        dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//main[@role='main']")))
                        print("Main container bulundu.")
                    except:
                        pass
                
                # Strateji 5: Body (Son çare)
                if not dialog_container:
                    try:
                        print("Son çare: Body elementi seçiliyor...")
                        dialog_container = driver.find_element(By.TAG_NAME, "body")
                    except:
                        pass

                if not dialog_container:
                    print("KRİTİK HATA: Dialog penceresi hiçbir yöntemle bulunamadı!")
                    # Son çare: Sayfa kaynağını analiz için dump edebiliriz ama şimdilik exception.
                    raise Exception("Dialog penceresi bulunamadı.")
                
                # JavaScript ile scroll edilebilir alanı bul (Daha robust)
                def get_scrollable_dialog(d_container):
                    return driver.execute_script("""
                        var container = arguments[0];
                        // Öncelik 1: _aano class'ı (Instagram standart modal scroll class'ı)
                        var aano = container.querySelector('div._aano');
                        if (aano) return aano;
                        
                        // Öncelik 2: Computed Style kontrolü
                        var divs = container.getElementsByTagName('div');
                        for (var i = 0; i < divs.length; i++) {
                            var style = window.getComputedStyle(divs[i]);
                            if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                                return divs[i];
                            }
                        }
                        
                        return container; 
                    """, d_container)

                dialog = get_scrollable_dialog(dialog_container)
                # Debug: Hangi elementi bulduğumuzu görelim
                try:
                    d_class = dialog.get_attribute("class")
                    print(f"Scroll edilecek element class: {d_class}")
                except: pass

                last_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                scroll_attempts = 0
                
                while True:
                    try:
                        # Eğer dialog stale olduysa döngü başında yenilemeyi dene
                        try:
                            dialog.is_enabled()
                        except:
                             # Stale ise yenile
                             dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                             dialog = get_scrollable_dialog(dialog_container)

                        # Görünen linklerden kullanıcı adlarını topla
                        # 1. Yöntem: JavaScript (En Güvenli - Stale Element Yaratmaz)
                        try:
                            js_links = driver.execute_script("""
                                var container = arguments[0];
                                if (!container) return [];
                                var links = container.getElementsByTagName('a');
                                var hrefs = [];
                                for(var i=0; i<links.length; i++){
                                    hrefs.push(links[i].href);
                                }
                                return hrefs;
                            """, dialog)
                            
                            if js_links:
                                for h in js_links:
                                    try:
                                        u = self.parse_username_from_href(h)
                                        if u and u != self.username.lower():
                                            followers_set.add(u)
                                    except: pass
                        except:
                            pass

                        # 2. Yöntem: Selenium (Yedek) - Stale hatası verirse pass geç
                        try:
                            links = dialog.find_elements(By.TAG_NAME, "a")
                            for a in links:
                                try:
                                    h = a.get_attribute("href")
                                    if h:
                                        u = self.parse_username_from_href(h)
                                        if u and u != self.username.lower():
                                            followers_set.add(u)
                                except: pass
                        except:
                            pass
                        
                        # Scroll yap (Daha doğal olması için hafif yukarı aşağı oynat)
                        # Yöntem 1: Son elemana odaklan ve görünür yap (En etkilisi)
                        try:
                            # Dialog içindeki son linki bul
                            last_link = dialog.find_elements(By.TAG_NAME, "a")[-1]
                            driver.execute_script("arguments[0].scrollIntoView(true);", last_link)
                        except:
                            # Eğer link yoksa, JS ile scrollTop dene
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                        
                        time.sleep(0.5 if turbo else 1)
                        
                        # Yöntem 2: Klavye Tuşu (PAGE_DOWN) - JS yetmezse tetikleyici olsun
                        try:
                            # Önce odaklan
                            dialog.click()
                            dialog.send_keys(Keys.PAGE_DOWN)
                        except:
                            pass
                            
                        new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                        if new_h == last_h:
                            # Scroll takıldıysa hafif yukarı yapıp tekrar aşağı dene
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 300", dialog)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                            time.sleep(1)
                            new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                            
                        if new_h == last_h:
                            scroll_attempts += 1
                            # print(f"Scroll denemesi: {scroll_attempts}/15")
                            
                            # Eğer hedeflenen sayıya yaklaştıysak ve scroll çalışmıyorsa zorlama
                            if total_followers > 0 and len(followers_set) >= total_followers * 0.95:
                                print(f"Hedeflenen sayıya ulaşıldı ({len(followers_set)}/{total_followers}), tarama tamamlanıyor.")
                                break

                            if scroll_attempts > 15: # Deneme sayısını 5'ten 15'e çıkardık (Daha sabırlı olsun)
                                print("Scroll sonuna gelindi veya takıldı.")
                                break
                            time.sleep(1)
                        else:
                            scroll_attempts = 0
                            last_h = new_h
                        
                        # Aşırı büyük hesaplar için güvenlik limiti (50k takipçi varsa donmasın)
                        if len(followers_set) > 50000: 
                            print("Takipçi limiti (50000) aşıldı, tarama durduruluyor.")
                            break
                        
                        if len(followers_set) % 500 == 0 and len(followers_set) > 0:
                            print(f"   -> Toplanan takipçi: {len(followers_set)}")

                    except Exception as loop_e:
                        if "stale" in str(loop_e).lower():
                            print("Stale Element (Scroll), dialog yenileniyor...")
                            try:
                                dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                                dialog = get_scrollable_dialog(dialog_container)
                                continue
                            except:
                                break
                        else:
                            print(f"Scroll döngü hatası: {loop_e}")
                            # Kritik olmayan hatalarda devam et
                            pass

            except Exception as e:
                print(f"Takipçi listesi alınırken genel hata: {e}")
                if len(followers_set) > 0:
                    print(f"Hata alındı ancak {len(followers_set)} takipçi toplandı. İşleme devam ediliyor...")
                else:
                    return 0
            
            print(f"Toplam {len(followers_set)} takipçi hafızaya alındı.")
            # Cache'e kaydet
            try:
                with open(followers_file, "w", encoding="utf-8") as f:
                    for u in followers_set:
                        f.write(f"{u}\n")
                print(f"Takipçi listesi önbelleğe kaydedildi: {followers_file}")
            except Exception as e:
                print(f"Önbellek kayıt hatası: {e}")
        
        if loaded_from_file:
            # Dosyadan yüklendiyse, toplam sayıyı dosyadaki kadar varsay
            total_followers = len(followers_set)

        if len(followers_set) == 0:
            print("Takipçi listesi boş veya alınamadı. İşlem güvenliği için durduruluyor.")
            return 0
            
        if total_followers == 0:
            print("GÜVENLİK UYARISI: Toplam takipçi sayısı doğrulanamadı!")
            print(f"Sistem {len(followers_set)} kişi buldu ancak toplam sayıyı bilmediği için listenin tam olup olmadığını garanti edemiyor.")
            print("Hatalı unfollow (sizi takip edenleri çıkarma) riskini önlemek için işlem durduruluyor.")
            print("Lütfen internet bağlantınızı kontrol edip tekrar deneyin veya 'Yavaş Mod'u kullanın.")
            return 0
        
        if len(followers_set) < total_followers * 0.95: # %90'dan %95'e çıkardık (Daha güvenli)
            print(f"GÜVENLİK UYARISI: Eksik liste! (Beklenen: ~{total_followers}, Alınan: {len(followers_set)})")
            print("Hatalı unfollow yapmamak için işlem iptal ediliyor.")
            return 0

        # Modalı kapat (Sadece tarama yapıldıysa)
        if not loaded_from_file:
            try:
                close_btn = driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@class, '_abl-')]")
                close_btn.click()
            except:
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except: pass
        
        time.sleep(1)
        
        # 2. ADIM: Takip Edilenler listesine git ve unfollow yap
        print("Takip edilenler kontrol ediliyor ve işlem başlıyor...")
        processed = 0
        checked_users = set()
        
        try:
            link = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following/')]")))
            link.click()
        except:
            driver.get(f"https://www.instagram.com/{self.username}/following/")
            
        try:
            # Dialog elementini bul (Role dialog)
            dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            
            # JavaScript ile scroll edilebilir alanı bul
            dialog = driver.execute_script("""
                var container = arguments[0];
                var divs = container.getElementsByTagName('div');
                for (var i = 0; i < divs.length; i++) {
                    var style = window.getComputedStyle(divs[i]);
                    if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                        return divs[i];
                    }
                }
                var aano = container.querySelector('div._aano');
                if (aano) return aano;
                return container; 
            """, dialog_container)
            
            last_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
            scroll_attempts = 0
            scanned_count = 0
            
            while processed < max_actions:
                # 1. Yöntem: Standart listitem
                items = dialog.find_elements(By.XPATH, ".//div[@role='listitem']")
                
                # 2. Yöntem: Fallback - Buton içeren ve link içeren herhangi bir div
                if not items:
                     items = dialog.find_elements(By.XPATH, ".//div[.//button and .//a[not(contains(@href, '/explore/'))]]")
                
                if not items:
                    print("Listelenen öğe bulunamadı (scroll bekleniyor)...")
                
                # Yeni tarananları say
                current_batch_new = 0
                
                for item in items:
                    if processed >= max_actions:
                        break
                    
                    try:
                        # Kullanıcı adını çek
                        try:
                            a_tag = item.find_element(By.TAG_NAME, "a")
                            href = a_tag.get_attribute("href")
                            uname = self.parse_username_from_href(href)
                        except:
                            continue
                            
                        if not uname or uname in checked_users:
                            continue
                        
                        checked_users.add(uname)
                        scanned_count += 1
                        current_batch_new += 1
                        
                        if scanned_count % 50 == 0:
                            print(f"   -> Kontrol edilen: {scanned_count} | İşlem yapılan: {processed}")

                        # Verified Check (DOM üzerinden)
                        is_verified = False
                        if keep_verified:
                            try:
                                # Mavi tik genellikle svg aria-label="Verified" veya "Doğrulanmış"
                                svgs = item.find_elements(By.TAG_NAME, "svg")
                                for svg in svgs:
                                    aria = svg.get_attribute("aria-label") or ""
                                    if "Verified" in aria or "Doğrulanmış" in aria:
                                        is_verified = True
                                        break
                            except:
                                pass

                        # Decision Maker Kontrolü
                        if not self.decision_maker.should_unfollow(uname, is_following_me=(uname in followers_set), min_days_followed=min_days, keep_verified=keep_verified, is_verified=is_verified):
                            continue
                        
                        print(f"Tespit edildi (Takip etmiyor): {uname}")
                        
                        # Butonu bul
                        btn = None
                        
                        # JavaScript ile butonu bulma (Daha güvenilir)
                        try:
                            # Bu script, elementin içindeki butonları tarar ve 'Takip Et' olmayan ama 'Takiptesin'/'Following' olanı döndürür
                            btn = driver.execute_script("""
                                var item = arguments[0];
                                var buttons = item.getElementsByTagName('button');
                                for (var i = 0; i < buttons.length; i++) {
                                    var t = buttons[i].innerText || "";
                                    var tl = t.toLowerCase();
                                    
                                    // Negatif kontrol yerine Pozitif kontrol (Daha güvenli)
                                    // 'Mesaj Gönder' butonuna tıklamaması için
                                    // Takiptesin, Following, İstek, Requested
                                    if (tl.includes('takiptesin') || tl.includes('following') || tl.includes('istek') || tl.includes('requested')) {
                                        return buttons[i];
                                    }
                                }
                                return null;
                            """, item)
                        except:
                            pass

                        if not btn:
                            try:
                                # 1. Deneme: Yaygın metinler
                                btn = item.find_element(By.XPATH, ".//button[contains(., 'Takiptesin') or contains(., 'Following') or contains(., 'İstek') or contains(., 'Requested')]")
                            except:
                                pass
                        
                        if btn:
                            try:
                                # Tıklama işlemi
                                try:
                                    btn.click()
                                except:
                                    driver.execute_script("arguments[0].click();", btn)
                                
                                time.sleep(1) # Modalın açılması için biraz bekle
                                
                                # Onay butonu - JavaScript ile bulma
                                confirm = None
                                try:
                                    confirm = driver.execute_script("""
                                        var dialogs = document.querySelectorAll("div[role='dialog']");
                                        if (dialogs.length == 0) return null;
                                        var dialog = dialogs[dialogs.length - 1]; // En son açılan dialog
                                        var buttons = dialog.getElementsByTagName('button');
                                        for (var i = 0; i < buttons.length; i++) {
                                            var t = buttons[i].innerText || "";
                                            var tl = t.toLowerCase();
                                            // Türkçe karakter sorunu için geniş kapsamlı kontrol
                                            // 'bırak', 'birak', 'unfollow'
                                            if (tl.includes('bırak') || tl.includes('birak') || tl.includes('unfollow')) {
                                                return buttons[i];
                                            }
                                        }
                                        return null;
                                    """)
                                except:
                                    pass
                                
                                if not confirm:
                                     # XPath fallback
                                    try:
                                        confirm = w.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='dialog']//button[contains(., 'Takibi Bırak') or contains(., 'Unfollow')]")))
                                    except:
                                        pass

                                if confirm:
                                    try:
                                        confirm.click()
                                    except:
                                        driver.execute_script("arguments[0].click();", confirm)
                                    
                                    processed += 1
                                    self.log_action("UNFOLLOW", uname)
                                    print(f"BAŞARILI: {uname} takipten çıkıldı.")
                                else:
                                    print(f"HATA: {uname} için onay butonu bulunamadı.")
                                    # Dialog açıksa kapatmaya çalış (Cancel/İptal)
                                    try:
                                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                    except:
                                        pass

                                if fast and turbo:
                                    self.turbo_delay()
                                elif fast:
                                    self.fast_delay()
                                else:
                                    self.rand_delay()
                                    
                                if self.is_action_blocked():
                                    print("İşlem engellendi. Beklemeye alınıyor.")
                                    return processed
                            except Exception as e:
                                print(f"Unfollow tıklama hatası ({uname}): {e}")
                        else:
                            print(f"UYARI: {uname} için 'Takiptesin' butonu bulunamadı.")
                            pass
                            
                    except Exception as e:
                        continue
                
                # Scroll Logic (Döngü içinde)
                try:
                    # Dialog içindeki son linki bul
                    last_link = dialog.find_elements(By.TAG_NAME, "a")[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", last_link)
                except:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                
                time.sleep(1 if turbo else 2)
                
                new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                if new_h == last_h:
                    # Scroll takıldıysa hafif yukarı yapıp tekrar aşağı dene
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 200", dialog)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                    time.sleep(1)
                    new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)

                if new_h == last_h:
                    scroll_attempts += 1
                    # Takıldıysa PageDown dene
                    try:
                        dialog.click()
                        dialog.send_keys(Keys.PAGE_DOWN)
                    except: pass
                    
                    if scroll_attempts > 10: # Deneme sayısını 4'ten 10'a çıkardık
                        print("Scroll limitine ulaşıldı.")
                        break
                    time.sleep(1)
                else:
                    scroll_attempts = 0
                    last_h = new_h
                    
        except Exception as e:
            print(f"Following listesi işlenirken hata: {e}")
            
        print(f"Hızlı unfollow tamamlandı: {processed}")
        return processed
    def bulk_unfollow_nonfollowers(self, max_actions=None, fast=True, turbo=True, verify_all=False, min_days=0):
        try:
            with open("index_following.txt", "r", encoding="utf-8") as f:
                following = {l.strip().lower() for l in f if l.strip()}
        except:
            following = set(self.index_list("following", fast=fast, turbo=turbo))
        try:
            with open("index_followers.txt", "r", encoding="utf-8") as f:
                followers = {l.strip().lower() for l in f if l.strip()}
        except:
            followers = set(self.index_list("followers", fast=fast, turbo=turbo))
            
        # Whitelist yükle
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

        targets = [u for u in following if u not in followers and u not in whitelist]
        if verify_all:
            for u in list(following):
                try:
                    chk = self.user_in_following_search(u, fast=fast, turbo=turbo)
                    if chk is False and u not in targets and u not in whitelist:
                        targets.append(u)
                except:
                    continue
        driver = self.driver
        w = WebDriverWait(driver, 4 if (fast and turbo) else (7 if fast else 10))
        done = 0
        print(f"Hedef toplu unfollow sayısı: {len(targets)}")
        for uname in targets:
            if max_actions is not None and done >= max_actions:
                break
            
            # Decision Maker Kontrolü (Süre Bazlı Unfollow için)
            if not self.decision_maker.should_unfollow(uname, is_following_me=False, min_days_followed=min_days):
                continue

            driver.get(f"https://www.instagram.com/{uname}/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            try:
                chk = self.user_in_following_search(uname, fast=fast, turbo=turbo)
                if chk is True:
                    print(f"Atlandı (geri takip var): {uname}")
                    continue
                btn = None
                for xp_btn in [
                    "//button[.//div[contains(text(), 'Takiptesin') or contains(text(), 'Following')]]",
                    "//button[contains(., 'Takiptesin') or contains(., 'Following')]",
                    "//button[.//div[contains(text(), 'İstek Gönderildi') or contains(text(), 'Requested')]]",
                    "//button[contains(., 'İstek Gönderildi') or contains(., 'Requested')]",
                    "//button[@aria-label='Following']",
                    "//div[text()='Takiptesin' or text()='Following']/ancestor::button"
                ]:
                    try:
                        btn = w.until(EC.element_to_be_clickable((By.XPATH, xp_btn)))
                        break
                    except:
                        continue
                if not btn:
                    try:
                        alt_follow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                        print(f"Atlandı (takipte değil): {uname}")
                        continue
                    except:
                        print(f"Takip durumu algılanamadı: {uname}")
                        continue
                try:
                    btn.click()
                except:
                    driver.execute_script("arguments[0].click()", btn)
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                target = None
                for xp in [
                    "//button[.//div[text()='Takibi Bırak' or text()='Unfollow']]",
                    "//button[contains(., 'Takibi Bırak') or contains(., 'Unfollow')]",
                    "//span[text()='Takibi Bırak' or text()='Unfollow']",
                    "//div[text()='Takibi Bırak' or text()='Unfollow']"
                ]:
                    try:
                        target = w.until(EC.element_to_be_clickable((By.XPATH, xp)))
                        break
                    except:
                        continue
                if not target:
                    # Belki "İstek Gönderildi" idi ve iptal oldu?
                    if btn and ("İstek" in (btn.text or "") or "Requested" in (btn.text or "")):
                        print(f"İstek geri çekildi: {uname}")
                    else:
                        print(f"Unfollow kontrolü bulunamadı: {uname}")
                        continue
                else:
                    try:
                        target.click()
                    except:
                        driver.execute_script("arguments[0].click()", target)
                
                self.log_action("UNFOLLOW", uname)
                done += 1
                if self.is_action_blocked():
                    print("İşlem engellendi. Beklemeye alınıyor.")
                    break
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay(True)
            except:
                continue
        print(f"Toplu unfollow tamamlandı: {done}")
        return done

    def parse_follower_count(self, text):
        """
        '1,234', '1.234', '10.5k', '10,5b', '1.2m', '10,5 B' gibi metinleri sayıya çevirir.
        Hem Türkçe (B/M/K) hem İngilizce (K/M) desteği.
        """
        if not text:
            return 0
        
        text = text.lower().strip()
        
        # Kelimeleri ayır
        parts = text.split()
        if not parts:
            return 0
            
        clean_text = parts[0]
        
        # Eğer 2. parça bir birim ise (K, M, B, Bin, Milyon vb.)
        if len(parts) > 1:
            suffix = parts[1]
            if suffix in ['k', 'm', 'b', 'mn', 'bn', 'bin', 'milyon']:
                clean_text += suffix
        
        text = clean_text
        
        # Ön temizlik: Sadece rakam, virgül, nokta ve harfler kalsın
        text = re.sub(r'[^0-9.,kmb]', '', text)
        
        if not text:
            return 0
            
        multiplier = 1
        
        # Suffix kontrolü
        if 'k' in text:
            multiplier = 1000
            text = text.replace('k', '')
        elif 'm' in text:
            multiplier = 1000000
            text = text.replace('m', '')
        elif 'b' in text: # b: bin (TR) veya billion (EN) -> Instagram'da B genellikle Bin'dir (TR arayüzde)
             # Ancak TR arayüzde "B" = Bin, EN arayüzde "B" = Billion olabilir.
             # Bot genellikle TR odaklı ama EN desteği de lazım.
             # Basit çözüm: Eğer sayı küçükse (10.5 B) -> Muhtemelen Bin.
             # Eğer EN arayüz ise ve 1B ise -> Milyar.
             # Şimdilik TR "Bin" olarak varsayalım.
            multiplier = 1000
            text = text.replace('b', '')
            
        try:
            # Eğer multiplier > 1 ise, ondalık ayracı olabilir.
            if multiplier > 1:
                text = text.replace(',', '.')
                val = float(text)
                return int(val * multiplier)
            else:
                # Multiplier yoksa, tam sayıdır.
                text = text.replace('.', '').replace(',', '')
                return int(text)
        except:
            return 0

    def get_follower_count_from_meta(self):
        """Yedek yöntem: Meta etiketlerinden takipçi sayısını çek."""
        try:
            meta = self.driver.find_element(By.XPATH, "//meta[@property='og:description']")
            content = meta.get_attribute("content")
            if not content:
                return 0
            
            # Regex ile sayı ve "Followers/Takipçi" kelimesini yakala
            match = re.search(r'([\d.,]+\s*[kmbKMB]?)\s+(?:Followers|Takipçi)', content, re.IGNORECASE)
            
            if match:
                return self.parse_follower_count(match.group(1))
            
            return 0
        except:
            return 0

    def get_user_stats_from_profile_page(self):
        """
        Profil sayfasındaki HTML'den takipçi ve takip edilen sayılarını çeker.
        Dönüş: (follower_count, following_count)
        """
        try:
            # 1. Meta Tag Yöntemi (En Hızlı)
            try:
                meta = self.driver.find_element(By.XPATH, "//meta[@property='og:description']")
                content = meta.get_attribute("content")
                if content:
                    # Örn: "100 Followers, 200 Following, ..."
                    follower_match = re.search(r'([\d.,]+\s*[kmbKMB]?)\s+(?:Followers|Takipçi)', content, re.IGNORECASE)
                    following_match = re.search(r'([\d.,]+\s*[kmbKMB]?)\s+(?:Following|Takip)', content, re.IGNORECASE)
                    
                    follower_count = self.parse_follower_count(follower_match.group(1)) if follower_match else 0
                    following_count = self.parse_follower_count(following_match.group(1)) if following_match else 0
                    
                    if follower_count > 0:
                        return follower_count, following_count
            except:
                pass

            # 2. Sayfa İçi Elementler (Yedek)
            # Genellikle header içindeki ul > li > a veya span
            # XPATH: //header//ul/li[2]//span/@title (Followers için)
            # Bu kısım karmaşık olabilir çünkü yapı değişebiliyor.
            
            return 0, 0
        except:
            return 0, 0

    def follow_users_by_criteria(self, hashtag, count=10, max_followers=3000):
        driver = self.driver
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        self.rand_delay(True)
        
        # İlk gönderiyi bul ve tıkla
        try:
            links = driver.find_elements(By.TAG_NAME, "a")
            first_post = None
            for link in links:
                href = link.get_attribute("href")
                if href and "/p/" in href:
                    first_post = link
                    break
            
            if first_post:
                first_post.click()
                time.sleep(3)
            else:
                print("Herhangi bir gönderi bulunamadı.")
                return

            processed_count = 0
            while processed_count < count:
                try:
                    # Mevcut gönderinin sahibinin kullanıcı adını bul
                    # Genellikle gönderinin üst kısmında 'a' etiketi içinde
                    # Header kısmını bulmaya çalışalım
                    header_link = driver.find_element(By.XPATH, "//header//a[not(contains(@href, '/explore/'))]")
                    profile_url = header_link.get_attribute("href")
                    
                    if profile_url:
                        # Yeni sekmede profili aç
                        driver.execute_script("window.open('');")
                        driver.switch_to.window(driver.window_handles[1])
                        driver.get(profile_url)
                        self.rand_delay()
                        
                        try:
                            # Takipçi sayısını bul
                            # Genellikle: <a href="/kullanici/followers/"><span>123</span> followers</a>
                            # veya <ul><li>...</li></ul> yapısında 2. li
                            followers_element = None
                            try:
                                followers_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]/span")))
                            except:
                                try:
                                    # Alternatif yapı
                                    followers_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ul/li[2]/a/span")))
                                except:
                                    pass
                            
                            if followers_element:
                                count_text = followers_element.get_attribute("title")
                                if not count_text:
                                    count_text = followers_element.text
                                
                                follower_num = self.parse_follower_count(count_text)
                                print(f"Kullanıcı İnceleniyor: {profile_url} | Takipçi: {follower_num}")
                                
                                if follower_num > 0 and follower_num <= max_followers:
                                    # Takip Et
                                    try:
                                        if self.action_allowed("FOLLOW"):
                                            follow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")))
                                            follow_btn.click()
                                            print("   -> KRİTERE UYGUN: Takip edildi.")
                                            processed_count += 1
                                            self.log_action("FOLLOW", profile_url)
                                            self.rand_delay(True)
                                    except:
                                        print("   -> Takip butonu bulunamadı (Zaten takip ediliyor olabilir).")
                                else:
                                    print("   -> Kriter dışı (Takipçi sayısı yüksek veya okunamadı).")
                            else:
                                print("   -> Takipçi sayısı elementine ulaşılamadı.")

                        except Exception as e:
                            print(f"Profil inceleme hatası: {e}")
                        
                        # Sekmeyi kapat ve ana sekmeye dön
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        
                    else:
                        print("Kullanıcı linki bulunamadı.")

                except Exception as e:
                    print(f"Gönderi işlenirken hata: {e}")
                    # Hata olsa bile sekmeyi kontrol et
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                # Sonraki gönderiye geç
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.RIGHT)
                    self.rand_delay()
                except:
                    print("Sonraki gönderiye geçilemedi.")
                    break

        except Exception as e:
            print(f"Hashtag işlemi sırasında hata: {e}")

    def follow_users_by_alphabet(self, letters="abcçdefgğhıijklmnoöprsştuüvyz", target_count=20, max_followers=None, min_followers=None, only_private=True, fast=True, randomize=True, turbo=False, avoid_known=True):
        driver = self.driver
        processed = 0
        seen = set()
        driver.get("https://www.instagram.com/")
        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()
        while processed < target_count:
            letter_list = list(letters)
            if randomize:
                random.shuffle(letter_list)
            for ch in letter_list:
                if processed >= target_count:
                    break
                driver.get(f"https://www.instagram.com/web/search/topsearch/?query={ch}")
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                text = ""
                try:
                    text = driver.find_element(By.TAG_NAME, "pre").text
                except:
                    text = driver.page_source
                try:
                    data = json.loads(text)
                except:
                    continue
                users = data.get("users", [])
                try:
                    if randomize:
                        random.shuffle(users)
                    else:
                        users.sort(key=lambda e: (e.get("user", {}).get("is_private") is not True, e.get("user", {}).get("follower_count") or 999999))
                except:
                    pass
                for entry in users:
                    if processed >= target_count:
                        break
                    user = entry.get("user", {})
                    username = user.get("username")
                    fc = user.get("follower_count")
                    ip = user.get("is_private")
                    friendship = user.get("friendship_status") or {}
                    following_me = friendship.get("following") if friendship else user.get("following")
                    followed_by = friendship.get("followed_by") if friendship else user.get("followed_by")
                    anon_pic = user.get("has_anonymous_profile_picture")
                    if not username:
                        continue
                    if username in seen:
                        continue
                    if avoid_known and (following_me is True or followed_by is True or friendship.get("outgoing_request") is True or friendship.get("incoming_request") is True):
                        seen.add(username)
                        continue
                    if only_private and ip is not True:
                        seen.add(username)
                        continue
                    if min_followers is None and hasattr(config, "MIN_FOLLOWER_COUNT"):
                        min_followers = getattr(config, "MIN_FOLLOWER_COUNT")
                    if fc is not None:
                        if max_followers is not None and fc > max_followers:
                            seen.add(username)
                            continue
                        if min_followers is not None and fc < min_followers:
                            seen.add(username)
                            continue
                    if anon_pic is True:
                        seen.add(username)
                        continue
                    seen.add(username)
                    driver.get(f"https://www.instagram.com/{username}/")
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                    try:
                        if self.action_allowed("FOLLOW"):
                            follow_btn = driver.find_element(By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")
                            follow_btn.click()
                            print(f"   -> Hedef: {username} | Takipçi: {fc} | Gizli: {ip}")
                            self.log_action("FOLLOW_ALPHA", username)
                            processed += 1
                            if fast and turbo:
                                self.turbo_delay()
                            elif fast:
                                self.fast_delay()
                            else:
                                self.rand_delay(True)
                            if self.is_action_blocked():
                                print("İşlem engellendi. Beklemeye alınıyor.")
                                return processed
                    except:
                        if fast and turbo:
                            self.turbo_delay()
                        elif fast:
                            self.fast_delay()
                        else:
                            self.rand_delay()
        print(f"Toplam takip edilen: {processed}")
        return processed

    def follow_random_users(self, target_count=20, max_followers=None, min_followers=None, only_private=False, fast=True, turbo=False, avoid_known=True, prefer_foreign=False):
        driver = self.driver
        processed = 0
        seen = set()
        alphabet = string.ascii_lowercase + "çğıöşü" + string.digits
        driver.get("https://www.instagram.com/")
        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()
        attempts = 0
        while processed < target_count:
            if prefer_foreign:
                seeds_pool = ["ny","la","uk","usa","de","fr","es","it","jp","br","mx","ca","au","in","ae","sa","ru","nl","se","no","fi","pt","us","gb"]
                bigrams = ["th","en","an","er","re","in","on","at","ti","es","ar","or"]
                seeds_pool.extend(bigrams)
                seed = random.choice(seeds_pool)
            else:
                seed = "".join(random.choice(alphabet) for _ in range(random.choice([2, 3])))
            driver.get(f"https://www.instagram.com/web/search/topsearch/?query={seed}")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            text = ""
            try:
                text = driver.find_element(By.TAG_NAME, "pre").text
            except:
                text = driver.page_source
            try:
                data = json.loads(text)
            except:
                continue
            users = data.get("users", [])
            random.shuffle(users)
            for entry in users:
                if processed >= target_count:
                    break
                user = entry.get("user", {})
                username = user.get("username")
                fc = user.get("follower_count")
                ip = user.get("is_private")
                friendship = user.get("friendship_status") or {}
                following_me = friendship.get("following") if friendship else user.get("following")
                followed_by = friendship.get("followed_by") if friendship else user.get("followed_by")
                anon_pic = user.get("has_anonymous_profile_picture")
                full_name = user.get("full_name") or ""
                if not username:
                    continue
                if username in seen:
                    continue
                if avoid_known and (following_me is True or followed_by is True or friendship.get("outgoing_request") is True or friendship.get("incoming_request") is True):
                    seen.add(username)
                    continue
                if only_private and ip is not True:
                    seen.add(username)
                    continue
                if min_followers is None and hasattr(config, "MIN_FOLLOWER_COUNT"):
                    min_followers = getattr(config, "MIN_FOLLOWER_COUNT")
                if fc is not None:
                    if max_followers is not None and fc > max_followers:
                        seen.add(username)
                        continue
                    if min_followers is not None and fc < min_followers:
                        seen.add(username)
                        continue
                if anon_pic is True:
                    seen.add(username)
                    continue
                if prefer_foreign:
                    tr_chars = "çğıöşü"
                    if any(ch in username.lower() for ch in tr_chars) or any(ch in full_name.lower() for ch in tr_chars):
                        seen.add(username)
                        continue
                    tr_words = ["turkiye","türkiye","turkish","turk","istanbul","ankara","izmir","tr ", " tr", ".tr", "_tr"]
                    low = (username or "").lower() + " " + full_name.lower()
                    if any(w in low for w in tr_words):
                        seen.add(username)
                        continue
                seen.add(username)
                driver.get(f"https://www.instagram.com/{username}/")
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                try:
                    if prefer_foreign:
                        try:
                            lang = (driver.execute_script("return document.documentElement.lang") or "").lower()
                        except:
                            lang = ""
                        pg = driver.page_source.lower()
                        if ("og:locale" in pg and "tr" in pg) or lang.startswith("tr"):
                            continue
                    if self.action_allowed("FOLLOW"):
                        follow_btn = driver.find_element(By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")
                        follow_btn.click()
                        print(f"   -> Rastgele: {username} | Takipçi: {fc} | Gizli: {ip}")
                        self.log_action("FOLLOW_ALPHA", username)
                        processed += 1
                        if fast and turbo:
                            self.turbo_delay()
                        elif fast:
                            self.fast_delay()
                        else:
                            self.rand_delay(True)
                        if self.is_action_blocked():
                            print("İşlem engellendi. Beklemeye alınıyor.")
                            return processed
                except:
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
            attempts += 1
            if prefer_foreign and processed < target_count and attempts % 3 == 0:
                need = min(5, target_count - processed)
                tags = ["newyork","london","paris","losangeles","tokyo","berlin","amsterdam","barcelona","madrid","rome","dubai","sydney","toronto","vancouver","melbourne"]
                gained = self.follow_via_hashtag_pool(tags, target_count=need, max_followers=max_followers, min_followers=min_followers, only_private=only_private, fast=fast, turbo=turbo, avoid_known=avoid_known)
                processed += gained
        print(f"Toplam takip edilen: {processed}")
        return processed

    def follow_random_users_foreign(self, target_count=20, max_followers=None, min_followers=None, only_private=False, fast=True, turbo=False, avoid_known=True, region=None, min_posts=None):
        driver = self.driver
        processed = 0
        seen = set()
        alphabet = string.ascii_lowercase + "çğıöşü" + string.digits
        driver.get("https://www.instagram.com/")
        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()
        attempts = 0
        while processed < target_count:
            seeds_map = {
                "NA": ["ny","la","usa","sf","sd","miami","sea","bos","chi","toronto","vancouver","ca","us","austin","dallas"],
                "EU": ["uk","london","de","berlin","fr","paris","es","madrid","it","rome","nl","amsterdam","se","stockholm","no","oslo","fi","helsinki","pt","lisbon"],
                "APAC": ["jp","tokyo","kr","seoul","sg","singapore","au","sydney","melbourne","in","mumbai","delhi","hk","hongkong"],
                "LATAM": ["br","rio","saopaulo","mx","mexico","cdmx","ar","buenosaires","co","bogota","chile","santiago"],
                "MENA": ["ae","dubai","sa","riyadh","qa","doha","eg","cairo","jo","amman","kw","kuwait"]
            }
            seeds_pool = []
            if region and region in seeds_map:
                seeds_pool = seeds_map[region]
            else:
                for v in seeds_map.values():
                    seeds_pool.extend(v)
            seeds_pool.extend(["us","gb","nyc","la","en","th"])
            seed = random.choice(seeds_pool)
            driver.get(f"https://www.instagram.com/web/search/topsearch/?query={seed}")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            text = ""
            try:
                text = driver.find_element(By.TAG_NAME, "pre").text
            except:
                text = driver.page_source
            try:
                data = json.loads(text)
            except:
                continue
            users = data.get("users", [])
            random.shuffle(users)
            for entry in users:
                if processed >= target_count:
                    break
                user = entry.get("user", {})
                username = user.get("username")
                fc = user.get("follower_count")
                ip = user.get("is_private")
                friendship = user.get("friendship_status") or {}
                following_me = friendship.get("following") if friendship else user.get("following")
                followed_by = friendship.get("followed_by") if friendship else user.get("followed_by")
                anon_pic = user.get("has_anonymous_profile_picture")
                full_name = user.get("full_name") or ""
                if not username:
                    continue
                if username in seen:
                    continue
                if avoid_known and (following_me is True or followed_by is True or friendship.get("outgoing_request") is True or friendship.get("incoming_request") is True):
                    seen.add(username)
                    continue
                if only_private and ip is not True:
                    seen.add(username)
                    continue
                if min_followers is None and hasattr(config, "MIN_FOLLOWER_COUNT"):
                    min_followers = getattr(config, "MIN_FOLLOWER_COUNT")
                if fc is not None:
                    if max_followers is not None and fc > max_followers:
                        seen.add(username)
                        continue
                    if min_followers is not None and fc < min_followers:
                        seen.add(username)
                        continue
                if anon_pic is True:
                    seen.add(username)
                    continue
                tr_chars = "çğıöşü"
                if any(ch in username.lower() for ch in tr_chars) or any(ch in full_name.lower() for ch in tr_chars):
                    seen.add(username)
                    continue
                tr_words = ["turkiye","türkiye","turkish","turk","istanbul","ankara","izmir","tr ", " tr", ".tr", "_tr"]
                low = (username or "").lower() + " " + full_name.lower()
                if any(w in low for w in tr_words):
                    seen.add(username)
                    continue
                seen.add(username)
                driver.get(f"https://www.instagram.com/{username}/")
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                try:
                    try:
                        lang = (driver.execute_script("return document.documentElement.lang") or "").lower()
                    except:
                        lang = ""
                    pg = driver.page_source.lower()
                    if ("og:locale" in pg and "tr" in pg) or lang.startswith("tr"):
                        continue
                    if min_posts is not None:
                        pc = self.get_posts_count()
                        if pc is not None and pc < min_posts:
                            continue
                    if self.action_allowed("FOLLOW"):
                        follow_btn = driver.find_element(By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")
                        follow_btn.click()
                        print(f"   -> Rastgele: {username} | Takipçi: {fc} | Gizli: {ip}")
                        self.log_action("FOLLOW_ALPHA", username)
                        processed += 1
                        if fast and turbo:
                            self.turbo_delay()
                        elif fast:
                            self.fast_delay()
                        else:
                            self.rand_delay(True)
                        if self.is_action_blocked():
                            print("İşlem engellendi. Beklemeye alınıyor.")
                            return processed
                except:
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
            attempts += 1
            if processed < target_count and attempts % 3 == 0:
                need = min(5, target_count - processed)
                tags_map = {
                    "NA": ["newyork","losangeles","toronto","vancouver","sanfrancisco","chicago","boston","miami","seattle","austin"],
                    "EU": ["london","paris","berlin","amsterdam","madrid","barcelona","rome","lisbon","stockholm","oslo","helsinki"],
                    "APAC": ["tokyo","seoul","singapore","sydney","melbourne","mumbai","delhi","hongkong"],
                    "LATAM": ["saopaulo","rio","mexico","cdmx","buenosaires","bogota","santiago"],
                    "MENA": ["dubai","riyadh","doha","cairo","amman","kuwait"]
                }
                tags = []
                if region and region in tags_map:
                    tags = tags_map[region]
                else:
                    for v in tags_map.values():
                        tags.extend(v)
                gained = self.follow_via_hashtag_pool(tags, target_count=need, max_followers=max_followers, min_followers=min_followers, only_private=only_private, fast=fast, turbo=turbo, avoid_known=avoid_known)
                processed += gained
        print(f"Toplam takip edilen: {processed}")
        return processed

    def follow_via_hashtag_pool(self, hashtags, target_count=10, max_followers=None, min_followers=None, only_private=False, fast=True, turbo=False, avoid_known=True):
        driver = self.driver
        processed = 0
        pool = list(hashtags)
        random.shuffle(pool)
        for tag in pool:
            if processed >= target_count:
                break
            driver.get(f"https://www.instagram.com/explore/tags/{tag}/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
            except:
                continue
            first_post = None
            for link in links:
                href = link.get_attribute("href")
                if href and "/p/" in href:
                    first_post = link
                    break
            if not first_post:
                continue
            first_post.click()
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            tries = 0
            while processed < target_count and tries < 20:
                tries += 1
                try:
                    header_link = driver.find_element(By.XPATH, "//header//a[not(contains(@href, '/explore/'))]")
                    profile_url = header_link.get_attribute("href")
                except:
                    profile_url = None
                if profile_url:
                    driver.get(profile_url)
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                    fc_num = None
                    ip = None
                    friendship = {}
                    try:
                        followers_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]/span")))
                        count_text = followers_element.get_attribute("title") or followers_element.text
                        fc_num = self.parse_follower_count(count_text)
                    except:
                        pass
                    if min_followers is None and hasattr(config, "MIN_FOLLOWER_COUNT"):
                        min_followers = getattr(config, "MIN_FOLLOWER_COUNT")
                    if fc_num is not None:
                        if max_followers is not None and fc_num > max_followers:
                            pass
                        elif min_followers is not None and fc_num < min_followers:
                            pass
                        else:
                            try:
                                if self.action_allowed("FOLLOW"):
                                    follow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")))
                                    follow_btn.click()
                                    self.log_action("FOLLOW", profile_url)
                                    processed += 1
                                    if fast and turbo:
                                        self.turbo_delay()
                                    elif fast:
                                        self.fast_delay()
                                    else:
                                        self.rand_delay(True)
                            except:
                                pass
                    driver.get(f"https://www.instagram.com/explore/tags/{tag}/")
                    if fast and turbo:
                        self.turbo_delay()
                    elif fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                    try:
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.RIGHT)
                    except:
                        break
        return processed

    def follow_combined(self, letters, target_count=20, max_followers=None, min_followers=None, only_private=True, fast=True, turbo=True):
        processed = 0
        chunk = 3
        while processed < target_count:
            remain = target_count - processed
            a_count = min(chunk, remain)
            r_count = min(chunk, remain - a_count)
            gained_a = self.follow_users_by_alphabet(letters=letters, target_count=a_count, max_followers=max_followers, min_followers=min_followers, only_private=only_private, fast=fast, randomize=True, turbo=turbo, avoid_known=True)
            processed += gained_a
            if processed >= target_count:
                break
            gained_r = self.follow_random_users(target_count=r_count, max_followers=max_followers, min_followers=min_followers, only_private=only_private, fast=fast, turbo=turbo, avoid_known=True)
            processed += gained_r
            if gained_a == 0 and gained_r == 0:
                fallback = min(5, target_count - processed)
                tags = ["nature", "travel", "photo", "istanbul", "music", "art", "sport", "love", "summer", "city"]
                processed += self.follow_via_hashtag_pool(tags, target_count=fallback, max_followers=max_followers, min_followers=min_followers, only_private=only_private, fast=fast, turbo=turbo, avoid_known=True)
        print("Kombine takip tamamlandı.")

    def follow_smart_seeds(self, limit=20, criteria=None):
        """
        Popüler profillerden (Seed) gerçek kullanıcıları bulup kriterlere göre takip eder.
        """
        driver = self.driver
        followed = 0
        processed = 0
        
        # Seed Listesi (Popüler Türk Kadın Profilleri - Aktif kitle için)
        seeds = ["danlabilic", "duyguozaslan", "seymasubasi", "handemiyy", "gamze_ercel", "neslihanatagul", "demetozdemir", "acunilicali", "cznburak", "hadise"]
        random.shuffle(seeds)
        
        print(f"Akıllı Takip Başlıyor. Hedef: {limit}. Kriterler: {criteria}")
        
        for seed_user in seeds:
            if followed >= limit:
                break
                
            print(f"\nKaynak Profil Taranıyor: {seed_user}")
            try:
                # 1. Profile Git
                self.browser_manager.navigate_to_profile(seed_user)
                time.sleep(random.uniform(2, 4))
                
                # 2. Takipçileri veya Yorumcuları Topla
                # %70 ihtimalle son gönderi yorumcuları (daha aktif), %30 takipçiler
                users_to_check = []
                
                if random.random() < 0.7:
                    # Son gönderiye git
                    try:
                        # İlk gönderiyi bul (Grid'deki ilk link)
                        # Genellikle _aagw class'ı post thumbnail'i
                        try:
                            first_post = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, '_aagw')]")))
                            first_post.click()
                        except:
                            # Alternatif selektör
                            first_post = driver.find_element(By.TAG_NAME, "article").find_element(By.TAG_NAME, "a")
                            first_post.click()
                            
                        time.sleep(random.uniform(3, 5))
                        
                        # Yorumları aç/yükle (Basitçe sayfada görünenleri al)
                        # Modal içindeki yorum yapanları bul
                        # Genellikle h3 veya span içinde kullanıcı adları olur
                        comment_elems = driver.find_elements(By.XPATH, "//ul//h3//div//span//a")
                        if not comment_elems:
                             comment_elems = driver.find_elements(By.XPATH, "//ul//h3//a")
                             
                        for el in comment_elems:
                            u = el.text
                            if u and u not in users_to_check and u != seed_user:
                                users_to_check.append(u)
                                
                        # Modalı kapat (ESC veya X butonu veya dışarı tıkla)
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        print(f"   -> {len(users_to_check)} aktif kullanıcı (yorumcu) bulundu.")
                    except Exception as e:
                        print(f"   -> Post analizi hatası: {e}")
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        except: pass
                
                # Eğer yorumcu bulunamadıysa veya şans eseri takipçilere bakılacaksa
                if not users_to_check:
                    try:
                        # Takipçi modalını aç
                        users_set = self.scrape_modal_users("followers", limit=50, target_username=seed_user)
                        users_to_check = list(users_set)
                        print(f"   -> {len(users_to_check)} kullanıcı (takipçi) toplandı.")
                    except Exception as e:
                        print(f"   -> Takipçi toplama hatası: {e}")
                
                # 3. Bulunan Kullanıcıları Analiz Et ve Takip Et
                random.shuffle(users_to_check)
                
                for username in users_to_check:
                    if followed >= limit:
                        break
                        
                    # Geçmiş kontrolü
                    if self.check_history(username):
                        continue
                        
                    processed += 1
                    print(f"[{processed}] Analiz: {username}")
                    
                    try:
                        # Profile git
                        self.browser_manager.navigate_to_profile(username)
                        time.sleep(random.uniform(2, 4))
                        
                        # Veri Topla
                        user_data = {
                            "username": username,
                            "fullname": "",
                            "bio": "",
                            "follower_count": 0,
                            "following_count": 0,
                            "is_private": False,
                            "is_verified": False
                        }
                        
                        # Takipçi Sayısı Kontrolü (KRİTİK)
                        try:
                            # Header kısmındaki 2. li elemanı (takipçi)
                            # Bazen değişebilir, o yüzden aria-label veya title'a bakmak lazım ama basitçe xpath
                            f_elem = driver.find_element(By.XPATH, "//ul/li[2]//span")
                            f_title = f_elem.get_attribute("title")
                            if not f_title:
                                f_title = f_elem.text
                            
                            # "1.5M", "10K" gibi formatları parse et
                            f_count = self.parse_follower_count(f_title)
                            user_data["follower_count"] = f_count
                            print(f"   -> Takipçi: {f_count}")
                        except:
                            print("   -> Takipçi sayısı okunamadı.")
                        
                        # Fullname ve Bio
                        try:
                            if "(" in driver.title:
                                user_data["fullname"] = driver.title.split("(")[0].strip()
                            else:
                                user_data["fullname"] = driver.title.split("•")[0].strip()
                                
                            meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                            if meta_desc:
                                user_data["bio"] = meta_desc
                        except: pass
                        
                        # Karar Ver
                        if self.decision_maker.should_follow(user_data, criteria):
                            print(f"   -> KRİTERLERE UYGUN! Takip ediliyor...")
                            
                            # Takip Et Butonu
                            btn = self.browser_manager.find_following_button()
                            if btn:
                                print("   -> Zaten takip ediliyor.")
                                self.log_action("FOLLOW", username)
                            else:
                                try:
                                    f_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                                    f_btn.click()
                                    followed += 1
                                    self.log_action("FOLLOW", username)
                                    print(f"   -> BAŞARILI. Toplam: {followed}/{limit}")
                                    time.sleep(random.uniform(25, 45))
                                except Exception as e:
                                    print(f"   -> Buton tıklama hatası: {e}")
                        else:
                            print("   -> Kriterlere uymuyor (Takipçi sayısı yüksek veya cinsiyet/uyruk uymuyor).")
                            
                    except Exception as e:
                        print(f"Profil hatası: {e}")
                        continue
                        
            except Exception as e:
                print(f"Seed hatası ({seed_user}): {e}")
                continue

    def post_comment(self, post_url, comment_text):
        """
        Belirtilen gönderiye yorum yapar.
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        try:
            if post_url and post_url != driver.current_url:
                driver.get(post_url)
                self.rand_delay()
                
            # Yorum alanını bul
            print(f"Yorum yapılıyor: '{comment_text}'")
            
            # 1. Textarea'yı bul
            try:
                comment_box = w.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
                comment_box.click()
                time.sleep(1)
                
                # Tekrar bul (bazen click sonrası değişir)
                comment_box = driver.find_element(By.TAG_NAME, "textarea")
                
                # Yorumu yaz (Humanizer ile)
                self.browser_manager.humanizer.type_like_human(comment_box, comment_text)
                time.sleep(1)
                
                # Paylaş butonunu bul
                # Genellikle textarea'nın formunda veya yanında "Paylaş" veya "Post" yazan buton
                post_btn = None
                try:
                    post_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Paylaş') or contains(text(), 'Post')]")
                except:
                    # Alternatif: Form submit
                    pass
                    
                if post_btn:
                    post_btn.click()
                else:
                    comment_box.send_keys(Keys.ENTER)
                    
                print("✅ Yorum gönderildi.")
                self.log_action("COMMENT", post_url)
                self.rand_delay()
                return True
                
            except Exception as e:
                print(f"❌ Yorum alanı bulunamadı veya yazılamadı: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Yorum işlemi hatası: {e}")
            return False

    def mass_follow_target(self, target_username, accounts_file="accounts.txt"):
        """
        accounts.txt dosyasındaki hesaplarla sırayla giriş yapıp target_username'i takip eder.
        """
        try:
            with open(accounts_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            accounts = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#") and ":" in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        accounts.append((parts[0].strip(), parts[1].strip()))
            
            print(f"Toplam {len(accounts)} adet hesap bulundu.")
            
            # Mevcut tarayıcıyı kapat (temiz başlangıç için)
            self.driver.quit()

            for i, (acc_user, acc_pass) in enumerate(accounts):
                print(f"\n[{i+1}/{len(accounts)}] Giriş yapılıyor: {acc_user}")
                
                # Her hesap için yeni driver başlat (Cookie temizliği için en garanti yol)
                driver = self.browser_manager.build_driver()
                
                try:
                    driver.get("https://www.instagram.com/")
                    self.rand_delay()
                    
                    # Giriş Yap
                    try:
                        u_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
                        self.browser_manager.humanizer.type_like_human(u_input, acc_user)
                        p_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password")))
                        self.browser_manager.humanizer.type_like_human(p_input, acc_pass)
                        p_input.send_keys(Keys.ENTER)
                        self.rand_delay(True)
                        
                        # Giriş başarılı mı kontrol et (basitçe URL değişti mi veya profil ikonu var mı)
                        if "accounts/login" in driver.current_url:
                            print(f"   -> Giriş başarısız (Şifre yanlış veya checkpoint).")
                            driver.quit()
                            continue
                            
                        # Hedef profile git
                        driver.get(f"https://www.instagram.com/{target_username}/")
                        self.rand_delay()
                        
                        # Takip Et butonunu bul ve tıkla
                        try:
                            # Takip Et, Follow, Geri Takip Et butonlarını kapsar
                            follow_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")))
                            follow_btn.click()
                            print(f"   -> BAŞARILI: {target_username} takip edildi.")
                            self.log_action("FOLLOW", target_username)
                            self.rand_delay()
                        except:
                            print(f"   -> Takip butonu bulunamadı (Zaten takip ediliyor olabilir).")
                            
                    except Exception as e:
                        print(f"   -> İşlem hatası: {e}")
                        
                except Exception as e:
                    print(f"   -> Tarayıcı hatası: {e}")
                
                finally:
                    driver.quit()
                    # Hesaplar arası bekleme
                    self.rand_delay(True)

            # İşlem bitince ana botu tekrar başlatmak için constructor'ı çağırmıyoruz, program bitiyor.
            print("\nToplu takip işlemi tamamlandı.")
            
        except FileNotFoundError:
            print(f"{accounts_file} dosyası bulunamadı.")
        except Exception as e:
            print(f"Genel hata: {e}")

if __name__ == "__main__":
    try:
        print("Bot başlatılıyor...")
        
        print("\n" + "="*50)
        print("INSTAGRAM AKILLI ASİSTAN v2.0")
        print("="*50)
        print("1. 🚀 AKILLI ASİSTAN'I BAŞLAT (Önerilen)")
        print("   (Sizin yerinize takip, beğeni, unfollow ve analiz yapar)")
        print("2. 🛠️ Manuel Araçlar (Gelişmiş)")
        print("   (Eski menüyü açar)")
        
        main_choice = input("Seçiminiz (1-2): ")
        
        mode = "13" # Varsayılan olarak AI modu (eski 13)
        
        if main_choice == "2":
            print("\n" + "="*50)
            print("MANUEL ARAÇLAR MENÜSÜ")
            print("="*50)
            print("1 - Hashtag ile Beğeni Yap")
            print("2 - Hashtag ile Beğeni + Takip Yap (Standart)")
            print("3 - Beni Takip Etmeyenleri Çıkar (Unfollow)")
            print("4 - Filtreli Takip (Sadece Az/Orta Takipçili Kullanıcılar)")
            print("5 - Yan Hesaplarla Beni Takip Et (accounts.txt gerekir)")
            print("6 - Hashtag ile Beğeni + Yorum + Takip (Full Paket)")
            print("7 - Alfabe ile Kullanıcı Takip Et")
            print("8 - Rastgele Kullanıcı Takip Et")
            print("9 - Kombine (Alfabe + Rastgele) Süper Hız")
            print("10 - Otomatik (Akıllı - Eski)")
            print("11 - Hızlı Toplu Unfollow (İndeks Bazlı)")
            print("12 - Hedef Profil Takipçileri (Hızlı & Filtresiz)")
            
            mode = input("Seçiminiz (1-12): ")
        
        if mode == "5":
            target_user = input("Takip edilecek kullanıcı adı (Örn: sizin adınız): ")
            # Bu modda giriş yapmaya gerek yok, fonksiyon içinde her hesap için ayrı giriş yapılacak.
            # Ancak sınıf yapısı gereği bir instance oluşturmalıyız, dummy veri ile.
            bot = InstagramBot("dummy", "dummy")
            bot.driver.quit() # Başlangıçta açılan boş tarayıcıyı kapat
            bot.mass_follow_target(target_user)
            bot.print_summary()
            
        elif mode in ["1", "2", "3", "4", "6", "7", "8", "9", "10", "11", "12", "13"]:
            # Diğer modlar için giriş yapılması şart
            bot = InstagramBot(config.USERNAME, config.PASSWORD)
            bot.login()
            
            # Oturum açma bildirimlerini geçmek için manuel bekleme veya ek kod gerekebilir.
            # Kullanıcıdan devam etmek için enter beklemesi
            input("Giriş yaptıktan ve pop-up'ları geçtikten sonra Enter'a basın...")
            
            if mode == "1" or mode == "2" or mode == "6":
                hashtag = input("Etkileşim yapılacak hashtag'i girin (başında # olmadan): ")
                count_input = input("Kaç gönderi ile etkileşime girilsin?: ")
                
                do_follow = False
                do_comment = False
                
                if mode == "2":
                    do_follow = True
                    print("DİKKAT: Takip etme modu seçildi. Engel yememek için işlem süreleri uzatılacak.")
                elif mode == "6":
                    do_follow = True
                    do_comment = True
                    print("DİKKAT: Full Paket seçildi (Beğeni+Yorum+Takip). İşlem süreleri daha uzun olacak.")
                
                if count_input.isdigit():
                    count = int(count_input)
                    bot.like_photos_by_hashtag(hashtag, count, follow=do_follow, comment=do_comment)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir sayı girin.")
                    
            elif mode == "3":
                print("\nUYARI: Bu işlem profilinizdeki 'Takip Edilenler' listesini tarar.")
                print("Sizi takip etmeyen kullanıcıları bulup takipten çıkarır.")
                print("Çok fazla işlem yapmak hesabınızın kısıtlanmasına neden olabilir.")

                # Whitelist Ekleme
                add_wl = input("Whitelist'e (Silinmeyecekler listesi) kullanıcı eklemek ister misiniz? (Y/n): ").strip().lower()
                if add_wl in ["y", "yes"]:
                    to_add = input("Kullanıcı adlarını virgülle ayırarak girin: ")
                    count_wl = 0
                    for u in to_add.split(","):
                         if u.strip():
                            bot.decision_maker.add_to_whitelist(u)
                            count_wl += 1
                    print(f"{count_wl} kullanıcı whitelist'e eklendi.")
                
                method_input = input("Hangi yöntem kullanılsın?\n1 - Klasik (Tek tek profil gezme - Yavaş/Güvenli)\n2 - Hızlı/Seri (Listeden tarama - Çok daha hızlı)\n3 - Algoritmik (Tam Liste Analizi - En Güvenli)\nSeçim (1/2/3): ").strip()
                
                min_days_input = input("Minimum kaç gündür takipte olanlar silinsin? (Örn: 3, Hepsi: 0): ").strip()
                min_days = int(min_days_input) if min_days_input.isdigit() else 0

                keep_verified_input = input("Mavi tikli (Onaylı) hesaplar silinmesin mi? (Y/n): ").strip().lower()
                keep_verified = True if keep_verified_input in ["", "y", "yes"] else False
                
                keep_min_followers = 0
                if method_input != "2":
                     kmf_input = input("En az kaç takipçisi olanlar silinmesin? (Popüler hesap koruması - Örn: 10000, Yok: 0): ").strip()
                     keep_min_followers = int(kmf_input) if kmf_input.isdigit() else 0
                else:
                     print("Bilgi: Hızlı Mod'da takipçi sayısı kontrolü yapılamaz (Sadece Mavi Tik korunabilir).")

                if method_input == "2":
                    # Hızlı Mod (fast_modal_unfollow_nonfollowers)
                    check_all_input = input("Tüm takip ettiklerin kontrol edilsin mi? (Y/n): ").strip().lower()
                    if check_all_input in ["", "y", "yes"]:
                        count = 999999
                        print("Tüm liste taranacak (Limit: Limitsiz).")
                    else:
                        c_in = input("Kaç kişi kontrol edilsin?: ")
                        count = int(c_in) if c_in.isdigit() else 300
                    
                    fast_mode_input = input("Hızlı bekleme modu (Fast) açılsın mı? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Süper Hız (Turbo) açılsın mı? (Y/n): ").strip().lower()
                    
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    
                    print("Hızlı tarama ve unfollow başlatılıyor...")
                    # whitelist zaten fonksiyon içinde yükleniyor
                    bot.fast_modal_unfollow_nonfollowers(max_actions=count, fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                    
                elif method_input == "3":
                    # Algoritmik Mod
                    fast_mode_input = input("Hızlı mod açılsın mı? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Süper Hız açılsın mı? (Y/n): ").strip().lower()
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    
                    bot.algorithm_based_unfollow(fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified, keep_min_followers=keep_min_followers)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                    
                else:
                    # Klasik Mod
                    count_input = input("Kaç kişi kontrol edilsin? (Önerilen: 20-50): ")
                    only_nonfollowers_input = input("Sadece seni takip etmeyenler çıkarılsın mı? (Y/n): ").strip().lower()
                    whitelist_use_input = input("whitelist.txt istisnalar kullanılacak mı? (Y/n): ").strip().lower()
                    fast_mode_input = input("Hızlı mod açılsın mı? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Süper Hız (çok kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                    
                    if count_input.isdigit():
                        count = int(count_input)
                        only_nf = True if only_nonfollowers_input in ["", "y", "yes"] else False
                        use_wl = True if whitelist_use_input in ["", "y", "yes"] else False
                        fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                        turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                        bot.unfollow_non_followers(count, only_nonfollowers=only_nf, use_whitelist=use_wl, fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified, keep_min_followers=keep_min_followers)
                        print("İşlem tamamlandı.")
                        bot.print_summary()
                    else:
                        print("Lütfen geçerli bir sayı girin.")

            elif mode == "4":
                print("\nBu mod, hashtag'deki kullanıcıların profiline gider, takipçi sayısını kontrol eder.")
                print("Eğer takipçi sayısı belirlediğiniz sınırın altındaysa takip eder.")
                
                hashtag = input("Hedef hashtag'i girin (başında # olmadan): ")
                count_input = input("Kaç kullanıcı TAKİP EDİLSİN? (Denenen değil, başarılı takip sayısı): ")
                max_followers_input = input("Maksimum takipçi sayısı kaç olsun? (Örn: 3000): ")
                
                if count_input.isdigit() and max_followers_input.isdigit():
                    count = int(count_input)
                    max_f = int(max_followers_input)
                    bot.follow_users_by_criteria(hashtag, count, max_followers=max_f)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli sayılar girin.")
            elif mode == "7":
                letters_input = input("Alfabe (varsayılan: abcçdefgğhıijklmnoöprsştuüvyz): ").strip()
                if not letters_input:
                    letters_input = "abcçdefgğhıijklmnoöprsştuüvyz"
                target_input = input("Kaç kullanıcı takip edilsin?: ")
                max_followers_input = input("Maksimum takipçi sayısı sınırı (boş bırakılabilir): ")
                min_followers_input = input("Minimum takipçi sayısı sınırı (boş bırakılabilir): ")
                only_private_input = input("Sadece gizli profiller takip edilsin mi? (Y/n): ").strip().lower()
                fast_mode_input = input("Hızlı mod (daha kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                if target_input.isdigit():
                    target = int(target_input)
                    max_f = None
                    min_f = None
                    if max_followers_input.strip() and max_followers_input.isdigit():
                        max_f = int(max_followers_input)
                    if min_followers_input.strip() and min_followers_input.isdigit():
                        min_f = int(min_followers_input)
                    only_private = True if only_private_input in ["", "y", "yes"] else False
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    bot.follow_users_by_alphabet(letters_input, target, max_followers=max_f, min_followers=min_f, only_private=only_private, fast=fast_mode)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir sayı girin.")
            elif mode == "8":
                target_input = input("Kaç kullanıcı takip edilsin?: ")
                max_followers_input = input("Maksimum takipçi sayısı sınırı (boş bırakılabilir): ")
                min_followers_input = input("Minimum takipçi sayısı sınırı (boş bırakılabilir): ")
                only_private_input = input("Sadece gizli profiller takip edilsin mi? (Y/n): ").strip().lower()
                fast_mode_input = input("Hızlı mod (daha kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                turbo_mode_input = input("Süper Hız (çok kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                foreign_input = input("Yabancı odaklı seçim yapılsın mı? (Y/n): ").strip().lower()
                region_input = input("Bölge (NA/EU/APAC/LATAM/MENA, boş: global): ").strip().upper()
                min_posts_input = input("Minimum gönderi sayısı (boş geçilebilir, öneri: 5): ").strip()
                if target_input.isdigit():
                    target = int(target_input)
                    max_f = None
                    min_f = None
                    if max_followers_input.strip() and max_followers_input.isdigit():
                        max_f = int(max_followers_input)
                    if min_followers_input.strip() and min_followers_input.isdigit():
                        min_f = int(min_followers_input)
                    only_private = True if only_private_input in ["", "y", "yes"] else False
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    prefer_foreign = True if foreign_input in ["", "y", "yes"] else False
                    region = region_input if region_input in ["NA","EU","APAC","LATAM","MENA"] else None
                    min_posts = int(min_posts_input) if min_posts_input.isdigit() else None
                    if prefer_foreign:
                        bot.follow_random_users_foreign(target_count=target, max_followers=max_f, min_followers=min_f, only_private=only_private, fast=fast_mode, turbo=turbo_mode, avoid_known=True, region=region, min_posts=min_posts)
                    else:
                        bot.follow_random_users(target_count=target, max_followers=max_f, min_followers=min_f, only_private=only_private, fast=fast_mode, turbo=turbo_mode, avoid_known=True)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir sayı girin.")
            elif mode == "9":
                letters_input = input("Alfabe (varsayılan: abcçdefgğhıijklmnoöprsştuüvyz): ").strip()
                if not letters_input:
                    letters_input = "abcçdefgğhıijklmnoöprsştuüvyz"
                target_input = input("Toplam kaç kullanıcı takip edilsin?: ")
                max_followers_input = input("Maksimum takipçi sayısı sınırı (boş bırakılabilir): ")
                min_followers_input = input("Minimum takipçi sayısı sınırı (boş bırakılabilir): ")
                only_private_input = input("Sadece gizli profiller takip edilsin mi? (Y/n): ").strip().lower()
                fast_mode_input = input("Hızlı mod (daha kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                turbo_mode_input = input("Süper Hız (çok kısa beklemeler) açılsın mı? (Y/n): ").strip().lower()
                if target_input.isdigit():
                    target = int(target_input)
                    max_f = None
                    min_f = None
                    if max_followers_input.strip() and max_followers_input.isdigit():
                        max_f = int(max_followers_input)
                    if min_followers_input.strip() and min_followers_input.isdigit():
                        min_f = int(min_followers_input)
                    only_private = True if only_private_input in ["", "y", "yes"] else False
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    bot.follow_combined(letters_input, target_count=target, max_followers=max_f, min_followers=min_f, only_private=only_private, fast=fast_mode, turbo=turbo_mode)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir sayı girin.")
            elif mode == "10":
                target_input = input("Toplam kaç işlem yapılsın? (Öneri: 30): ").strip()
                region_input = input("Bölge odağı (NA/EU/APAC/LATAM/MENA): ").strip().upper()
                if target_input.isdigit():
                    total = int(target_input)
                    region = region_input if region_input in ["NA","EU","APAC","LATAM","MENA"] else "EU"
                    bot.autopilot(total=total, region=region)
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir sayı girin.")
            elif mode == "11":
                build_input = input("Önce indeksleri oluşturulsun mu? (Y/n): ").strip().lower()
                fast_mode_input = input("Hızlı mod açılsın mı? (Y/n): ").strip().lower()
                turbo_mode_input = input("Süper Hız açılsın mı? (Y/n): ").strip().lower()
                
                min_days_input = input("Minimum kaç gündür takipte olanlar silinsin? (Örn: 3, Hepsi: 0): ").strip()
                min_days = int(min_days_input) if min_days_input.isdigit() else 0

                confirm_input = input("Seni takip etmeyenlerin hepsi takipten çıkarılsın mı? (Y/n): ").strip().lower()
                fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                if build_input in ["", "y", "yes"]:
                    bot.index_list("following", fast=fast_mode, turbo=turbo_mode)
                    bot.index_list("followers", fast=fast_mode, turbo=turbo_mode)
                if confirm_input in ["", "y", "yes"]:
                    done_modal = bot.fast_modal_unfollow_nonfollowers(max_actions=300, fast=True, turbo=turbo_mode, min_days=min_days)
                    if done_modal == 0:
                        bot.bulk_unfollow_nonfollowers(max_actions=None, fast=fast_mode, turbo=turbo_mode, verify_all=False, min_days=min_days)
                else:
                    print("İşlem iptal edildi.")
                print("İşlem tamamlandı.")
                bot.print_summary()
            elif mode == "12":
                print("\nBU MOD: Hedef Profil Takipçileri (Hızlı & Filtresiz)")
                print("Belirtilen bir profilin takipçiler listesine girer ve sırayla takip eder.")
                
                target_username = input("Hedef Profil (Kullanıcı Adı): ").strip()
                limit_input = input("Kaç kişi TAKİP EDİLSİN?: ")
                
                if target_username and limit_input.isdigit():
                    bot.follow_target_followers(target_username, int(limit_input))
                    
                    print("İşlem tamamlandı.")
                    bot.print_summary()
                else:
                    print("Lütfen geçerli bir kullanıcı adı ve sayı girin.")

            elif mode == "13":
                print("\nBU MOD: AI Akıllı Yönetim Modu")
                print("Bot, yapay zeka ile kendi kararlarını vererek çalışır.")
                print("Sürekli moddur, durdurmak için CTRL+C yapın.")
                
                try:
                    bot.ai_manager.start_smart_mode()
                except KeyboardInterrupt:
                    print("\nAI Modu kullanıcı tarafından durduruldu.")
                except Exception as e:
                    print(f"AI Modu Hatası: {e}")

        else:
            print("Geçersiz seçim.")
            
    except Exception as e:
        print(f"\nBİR HATA OLUŞTU:\n{e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nProgramı kapatmak için Enter'a basın...")
        # bot.close_browser()
