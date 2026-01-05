from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import random
import os
import sys
import re
import pickle
from modules.humanizer import Humanizer

# Ana dizinden config modülünü import edebilmek için
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class BrowserManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.humanizer = None

    def build_driver(self):
        ua = random.choice(config.USER_AGENTS) if hasattr(config, "USER_AGENTS") else None
        opts = Options()
        if ua:
            opts.add_argument(f"user-agent={ua}")
        
        # Config'den headless ayarını al veya parametreyi kullan
        is_headless = self.headless or (hasattr(config, "HEADLESS") and config.HEADLESS)
        if is_headless:
            opts.add_argument("--headless=new")
            
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1280,900")
        
        # Performans Optimizasyonları
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        
        # Görselleri devre dışı bırakma (Opsiyonel - Config'den kontrol edilebilir)
        if hasattr(config, "DISABLE_IMAGES") and config.DISABLE_IMAGES:
            prefs = {"profile.managed_default_content_settings.images": 2}
            opts.add_experimental_option("prefs", prefs)
        
        # Sayfa yükleme stratejisi (Tüm kaynakları bekleme)
        opts.page_load_strategy = 'eager'
        
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
        self.wait = WebDriverWait(self.driver, 10)
        self.humanizer = Humanizer(self.driver)
        return self.driver

    def save_cookies(self, username):
        """Çerezleri dosyaya kaydeder."""
        try:
            cookies = self.driver.get_cookies()
            with open(f"cookies_{username}.pkl", "wb") as f:
                pickle.dump(cookies, f)
            print("Çerezler kaydedildi.")
        except Exception as e:
            print(f"Çerez kaydetme hatası: {e}")

    def load_cookies(self, username):
        """Kayıtlı çerezleri yükler."""
        try:
            filename = f"cookies_{username}.pkl"
            if os.path.exists(filename):
                self.driver.get("https://www.instagram.com/")
                time.sleep(2)
                with open(filename, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        # 'sameSite' özelliği bazen sorun çıkarabilir, gerekirse filtrele
                        if 'expiry' in cookie:
                            # Selenium bazen int/float dönüşümünde hata verebilir, ama genellikle ok.
                            pass
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            pass
                print("Çerezler yüklendi, sayfa yenileniyor...")
                self.driver.refresh()
                time.sleep(3)
                return True
        except Exception as e:
            print(f"Çerez yükleme hatası: {e}")
        return False
        
    def check_login_status(self):
        """Giriş yapılmış mı kontrol eder."""
        try:
            self.driver.get("https://www.instagram.com/")
            
            # Login input veya profil fotosu gelene kadar bekle (Maks 5 sn)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: "accounts/login" in d.current_url or d.find_elements(By.XPATH, "//img[contains(@alt, 'profile') or contains(@alt, 'Profil')]")
                )
            except:
                pass # Timeout yese de devam et, belki yüklenmiştir

            # Eğer login sayfasındaysak (url contains accounts/login)
            if "accounts/login" in self.driver.current_url:
                return False
            
            # Profil ikonu vs var mı?
            try:
                self.driver.find_element(By.XPATH, "//img[contains(@alt, 'profile') or contains(@alt, 'Profil')]")
                return True
            except:
                pass
            return True # URL login değilse muhtemelen giriştir
        except:
            return False

    def human_click(self, element):
        """İnsan benzeri fare hareketiyle tıklama yapar."""
        if self.humanizer:
            self.humanizer.smart_click(element)
        else:
            try:
                action = ActionChains(self.driver)
                action.move_to_element_with_offset(element, random.randint(-5, 5), random.randint(-5, 5))
                action.pause(random.uniform(0.1, 0.3)) 
                action.click()
                action.perform()
            except:
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                except:
                    pass

    def navigate_to_profile(self, username):
        """Akıllı Navigasyon: Zaten oradaysak veya tıklayarak gidebiliyorsak onu tercih et."""
        target_url = f"https://www.instagram.com/{username}/"
        current_url = self.driver.current_url
        
        # 1. Zaten profildeysek
        if current_url.rstrip("/") == target_url.rstrip("/"):
            print(f"📍 Zaten {username} profilindeyiz.")
            return

        # 2. Sayfada kullanıcıya giden bir link varsa (Örn: Post başlığı)
        try:
            # Header'daki kullanıcı adı linki veya post sahibi linki
            links = self.driver.find_elements(By.XPATH, f"//a[@href='/{username}/']")
            for link in links:
                if link.is_displayed():
                    print(f"🔗 {username} linki bulundu, tıklanıyor...")
                    link.click()
                    # URL değişene kadar bekle (Maks 5 sn)
                    try:
                        self.wait.until(lambda d: d.current_url.rstrip("/") == target_url.rstrip("/"))
                    except:
                        time.sleep(2) # Fallback
                    
                    if self.driver.current_url.rstrip("/") == target_url.rstrip("/"):
                        return
        except:
            pass

        # 3. Fallback: Direkt Git
        self.driver.get(target_url)

    def check_system_health(self):
        """Sistem sağlık kontrolü: Engel var mı, internet var mı?"""
        try:
            # 1. Engel Kontrolü (Action Blocked)
            page_source = self.driver.page_source
            if "Try Again Later" in page_source or "Daha Sonra Tekrar Dene" in page_source:
                print("🚨 KRİTİK: Instagram işlem engeli (Action Blocked) tespit edildi!")
                return "BLOCKED"
            
            # 2. İnternet/Yükleme Hatası
            if "No internet" in self.driver.title or "ERR_INTERNET_DISCONNECTED" in page_source:
                print("🚨 KRİTİK: İnternet bağlantısı yok!")
                return "NO_NET"
                
            return "OK"
        except:
            return "OK"

    def open_following_modal(self, username):
        """Takip edilenler listesini açar."""
        try:
            link_any = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following')]")))
            link_any.click()
            return True
        except:
            try:
                link_header = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//header//ul/li[3]//a")))
                link_header.click()
                return True
            except:
                # Modal açılamazsa direkt sayfaya git
                self.driver.get(f"https://www.instagram.com/{username}/following/")
                return False

    def open_followers_modal(self, username):
        """Takipçi listesini açar."""
        try:
            link_any = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers')]")))
            link_any.click()
            return True
        except:
            try:
                link_header = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//header//ul/li[2]//a")))
                link_header.click()
                return True
            except:
                # Modal açılamazsa direkt sayfaya git
                self.driver.get(f"https://www.instagram.com/{username}/followers/")
                return False

    def get_modal_dialog(self):
        try:
            dialog_container = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            # JavaScript ile scroll edilebilir alanı bul (Gelişmiş)
            scrollable_div = self.driver.execute_script("""
                var container = arguments[0];
                var divs = container.getElementsByTagName('div');
                // Öncelik 1: _aano class (Instagram standartı)
                var aano = container.querySelector('div._aano');
                if (aano) return aano;
                
                // Öncelik 2: Overflow style kontrolü
                for (var i = 0; i < divs.length; i++) {
                    var style = window.getComputedStyle(divs[i]);
                    if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                        return divs[i];
                    }
                }
                
                // Öncelik 3: En yüksek scrollHeight'e sahip div (İçerik barındıran)
                var maxH = 0;
                var maxDiv = null;
                for (var i = 0; i < divs.length; i++) {
                    if (divs[i].scrollHeight > maxH) {
                        maxH = divs[i].scrollHeight;
                        maxDiv = divs[i];
                    }
                }
                if (maxDiv && maxH > 100) return maxDiv;

                return container; 
            """, dialog_container)
            return scrollable_div
        except:
            return None

    def extract_users_from_element(self, element, count, existing_list, my_username):
        """Verilen element içindeki kullanıcı linklerini toplar."""
        new_users = []
        links = element.find_elements(By.TAG_NAME, "a")
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith("https://www.instagram.com/") and "/explore" not in href and "/following" not in href and "/followers" not in href:
                if href not in existing_list and my_username not in href:
                    existing_list.append(href)
                    new_users.append(href)
                if len(existing_list) >= count:
                    break
        return new_users

    def scroll_element(self, element):
        """
        Elementi smooth (yumuşak) bir şekilde aşağı kaydırır.
        Instagram bot tespiti için bu önemlidir.
        """
        try:
            # 1. Yöntem: Smooth Scroll API
            self.driver.execute_script("arguments[0].scrollBy({top: 500, behavior: 'smooth'});", element)
            time.sleep(0.5)
            
            # 2. Yöntem: Random Scroll (İnsan taklidi)
            # Arada bir yukarı çıkıp tekrar in
            if random.random() < 0.1:
                self.driver.execute_script("arguments[0].scrollBy({top: -100, behavior: 'smooth'});", element)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].scrollBy({top: 150, behavior: 'smooth'});", element)
            
            # 3. Yöntem: En alta git (ScrollHeight güncellemesi için)
            # Ancak direkt zıplamak yerine yine smooth yapalım
            # self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
            
            # Alternatif: Adım adım in
            current_scroll = self.driver.execute_script("return arguments[0].scrollTop", element)
            total_height = self.driver.execute_script("return arguments[0].scrollHeight", element)
            
            if total_height - current_scroll > 500:
                 self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
            
            return self.driver.execute_script("return arguments[0].scrollHeight", element)
        except Exception as e:
            # Fallback: Eski yöntem
            try:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
                return self.driver.execute_script("return arguments[0].scrollHeight", element)
            except:
                return 0

    def scroll_window(self):
        """
        Pencereyi smooth kaydırır.
        """
        try:
            self.driver.execute_script("window.scrollBy({top: 800, behavior: 'smooth'});")
            time.sleep(0.5)
            if random.random() < 0.2:
                 self.driver.execute_script("window.scrollBy({top: -200, behavior: 'smooth'});")
                 time.sleep(0.3)
                 self.driver.execute_script("window.scrollBy({top: 300, behavior: 'smooth'});")
            
            return self.driver.execute_script("return document.body.scrollHeight")
        except:
             self.driver.execute_script("window.scrollBy(0, 1000)")
             return self.driver.execute_script("return document.body.scrollHeight")

    def find_following_button(self):
        """'Takiptesin' veya 'Following' butonunu bulur (Geliştirilmiş)."""
        # Önce JS ile dene (En kararlı)
        try:
            btn = self.driver.execute_script("""
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
                
                // 2. Aria-Label Kontrolü
                var svgs = document.querySelectorAll('svg[aria-label="Following"], svg[aria-label="Takiptesin"]');
                if (svgs.length > 0) {
                    var p = svgs[0].closest('button, div[role="button"], a[role="button"]');
                    if (p) return p;
                }
                return null;
            """)
            if btn: return btn
        except: pass

        # Fallback: Python XPATH
        xpath_list = [
            "//button[.//div[contains(text(), 'Takiptesin') or contains(text(), 'Following')]]",
            "//div[@role='button'][.//div[contains(text(), 'Takiptesin') or contains(text(), 'Following')]]",
            "//*[text()='Takiptesin']/ancestor::*[self::button or @role='button']",
            "//*[text()='Following']/ancestor::*[self::button or @role='button']",
            "//*[name()='svg' and (@aria-label='Takiptesin' or @aria-label='Following')]/ancestor::*[self::button or @role='button']"
        ]
        
        for xp in xpath_list:
            try:
                elems = self.driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed():
                        return el
            except: pass
            
        return None

    def find_unfollow_confirm_button(self):
        """'Takibi Bırak' onay butonunu bulur (Geliştirilmiş)."""
        # JS ile dene
        try:
            btn = self.driver.execute_script("""
                var dialog = document.querySelector('div[role="dialog"]');
                var container = dialog || document.body;
                var buttons = container.querySelectorAll('button, div[role="button"], div[tabindex="0"], span');
                
                // 1. Metin ile bul
                for (var i = 0; i < buttons.length; i++) {
                    var t = (buttons[i].innerText || "").toLowerCase().trim();
                    if (['takibi bırak', 'unfollow', 'bırak'].includes(t)) {
                        return buttons[i];
                    }
                }
                
                // 2. Renk ile bul (Kırmızı)
                for (var i = 0; i < buttons.length; i++) {
                    var style = window.getComputedStyle(buttons[i]);
                    if (style.color.includes('237, 73, 86') || style.color.includes('255, 48, 64')) {
                        return buttons[i];
                    }
                }
                return null;
            """)
            if btn: return btn
        except: pass

        # Fallback XPATH
        xpath_list = [
            "//button[contains(., 'Takibi Bırak') or contains(., 'Unfollow')]",
            "//div[@role='button'][contains(., 'Takibi Bırak') or contains(., 'Unfollow')]",
            "//span[contains(text(), 'Takibi Bırak') or contains(text(), 'Unfollow')]"
        ]
        
        for xp in xpath_list:
            try:
                elems = self.driver.find_elements(By.XPATH, xp)
                for el in elems:
                    if el.is_displayed():
                        return el
            except: pass
            
        return None

    def like_latest_post(self, limit=1):
        """Kullanıcının son gönderilerini beğenir."""
        try:
            # Profildeki ilk postları bul (Genellikle 'a' tag'i ve href'i '/p/' içerenler)
            # En üstteki 3 post genellikle 'Pinned' olabilir, o yüzden satır satır bakmak lazım.
            # Ancak basitçe ilk X postu alalım.
            
            posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            if not posts:
                print("   -> Beğenilecek gönderi bulunamadı.")
                return 0
                
            liked_count = 0
            for i in range(min(limit, len(posts))):
                try:
                    post = posts[i]
                    post_url = post.get_attribute("href")
                    
                    # Postu yeni sekmede aç (mevcut sayfayı bozmamak için)
                    self.driver.execute_script("window.open(arguments[0], '_blank');", post_url)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(3)
                    
                    # Beğen butonunu bul (SVG path veya aria-label)
                    # Instagram'da beğen butonu genellikle 'Beğen' veya 'Like' aria-label'ına sahiptir
                    # ve svg class'ı değişebilir.
                    
                    # Durum kontrolü: Zaten beğenilmiş mi? (Genellikle kırmızı kalp olur, aria-label 'Vazgeç'/'Unlike' olur)
                    try:
                        unlike_btn = self.driver.find_element(By.XPATH, "//svg[@aria-label='Beğenmekten Vazgeç' or @aria-label='Unlike']")
                        if unlike_btn:
                            print(f"   -> Gönderi zaten beğenilmiş.")
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                            continue
                    except:
                        pass
                        
                    # Beğen butonu
                    like_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//svg[@aria-label='Beğen' or @aria-label='Like']")))
                    
                    # Tıkla (Parent elemente tıklamak gerekebilir)
                    parent_btn = like_btn.find_element(By.XPATH, "./ancestor::div[@role='button']")
                    parent_btn.click()
                    
                    print(f"   -> Gönderi beğenildi.")
                    liked_count += 1
                    time.sleep(2)
                    
                except Exception as e:
                    # print(f"Beğeni hatası: {e}")
                    pass
                finally:
                    # Sekmeyi kapat ve ana sekmeye dön
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            
            return liked_count
        except Exception as e:
            print(f"Like işlemi hatası: {e}")
            return 0

    def is_private_profile(self):
        """Profilin gizli olup olmadığını kontrol eder."""
        try:
            # "Bu hesap gizli" metnini ara
            # H2 veya span içinde olabilir
            private_indicators = [
                "//h2[contains(text(), 'Bu Hesap Gizli') or contains(text(), 'This Account is Private')]",
                "//div[contains(text(), 'Bu Hesap Gizli') or contains(text(), 'This Account is Private')]",
                "//span[contains(text(), 'Bu Hesap Gizli') or contains(text(), 'This Account is Private')]"
            ]
            
            for xpath in private_indicators:
                try:
                    self.driver.find_element(By.XPATH, xpath)
                    return True
                except:
                    continue
            
            return False
        except:
            return False

    def is_verified_profile(self):
        """Profilin onaylı (mavi tikli) olup olmadığını kontrol eder."""
        try:
            # Header kısmında svg aranır
            # aria-label="Verified" veya "Doğrulanmış"
            verified_indicators = [
                "//svg[@aria-label='Verified']",
                "//svg[@aria-label='Doğrulanmış']",
                "//svg[contains(@aria-label, 'Verified')]",
                "//svg[contains(@aria-label, 'Doğrulanmış')]"
            ]
            
            for xpath in verified_indicators:
                try:
                    self.driver.find_element(By.XPATH, f"//header{xpath}")
                    return True
                except:
                    continue
            return False
        except:
            return False

    def watch_story(self):
        """Profilin hikayesini izler (Varsa)."""
        try:
            # Profil resmi etrafındaki halka (Canvas veya role='button')
            # Genellikle profil resmi bir butondur ve aria-disabled="false" ise hikaye vardır.
            
            profile_btn = self.driver.find_element(By.XPATH, "//header//div[@role='button']")
            
            # Hikaye olup olmadığını anlamak zor olabilir, tıklayıp deneyelim.
            # Eğer hikaye yoksa sadece profil resmi büyür (bu durumda geri çıkmak gerekir mi? Hayır, modal açılmazsa sorun yok)
            
            # Canvas kontrolü (Genellikle hikaye varsa canvas vardır)
            has_canvas = False
            try:
                profile_btn.find_element(By.TAG_NAME, "canvas")
                has_canvas = True
            except:
                pass
                
            if has_canvas:
                print("   -> Hikaye tespit edildi, izleniyor...")
                profile_btn.click()
                time.sleep(5) # Hikayenin yüklenmesi ve izlenmesi için bekle
                
                # Hikayeden çık (ESC veya Close butonu)
                try:
                    self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                    time.sleep(1)
                    # Veya close butonu
                    # close_btn = self.driver.find_element(By.XPATH, "//div[@aria-label='Kapat' or @aria-label='Close']")
                    # close_btn.click()
                except:
                    self.driver.get(self.driver.current_url) # Sayfayı yenile/geri yükle
                    
                return True
        except:
            pass
        return False

    def close_browser(self):
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
