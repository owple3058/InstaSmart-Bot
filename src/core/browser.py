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
from src.utils.humanizer import Humanizer

# To import config module from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import config
except ImportError:
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
        
        # Get headless setting from config or use parameter
        is_headless = self.headless or (hasattr(config, "HEADLESS") and config.HEADLESS)
        if is_headless:
            opts.add_argument("--headless=new")
            
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--window-size=1280,900")
        
        # Performance Optimizations
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        
        # Disable images (Optional - Controlled via Config)
        if hasattr(config, "DISABLE_IMAGES") and config.DISABLE_IMAGES:
            prefs = {"profile.managed_default_content_settings.images": 2}
            opts.add_experimental_option("prefs", prefs)
        
        # Page load strategy (Don't wait for all resources)
        opts.page_load_strategy = 'eager'
        
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=opts)
        self.wait = WebDriverWait(self.driver, 10)
        self.humanizer = Humanizer(self.driver)
        return self.driver

    def save_cookies(self, username):
        """Saves cookies to a file."""
        try:
            cookies = self.driver.get_cookies()
            with open(f"cookies_{username}.pkl", "wb") as f:
                pickle.dump(cookies, f)
            print("Cookies saved.")
        except Exception as e:
            print(f"Error saving cookies: {e}")

    def load_cookies(self, username):
        """Loads saved cookies."""
        try:
            filename = f"cookies_{username}.pkl"
            if os.path.exists(filename):
                self.driver.get("https://www.instagram.com/")
                time.sleep(2)
                with open(filename, "rb") as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        # 'sameSite' attribute can sometimes cause issues, filter if needed
                        if 'expiry' in cookie:
                            # Selenium sometimes errors on int/float conversion, but usually ok.
                            pass
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            pass
                print("Cookies loaded, refreshing page...")
                self.driver.refresh()
                time.sleep(3)
                return True
        except Exception as e:
            print(f"Error loading cookies: {e}")
        return False
        
    def check_login_status(self):
        """Checks if logged in."""
        try:
            self.driver.get("https://www.instagram.com/")
            
            # Wait for login input or profile photo (Max 5 sec)
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: "accounts/login" in d.current_url or d.find_elements(By.XPATH, "//img[contains(@alt, 'profile') or contains(@alt, 'Profil')]")
                )
            except:
                pass # Continue even if timeout, might be loaded

            # If on login page
            if "accounts/login" in self.driver.current_url:
                return False
            
            # Is there a profile icon?
            try:
                self.driver.find_element(By.XPATH, "//img[contains(@alt, 'profile') or contains(@alt, 'Profil')]")
                return True
            except:
                pass
            return True # If URL is not login, probably logged in
        except:
            return False

    def human_click(self, element):
        """Performs human-like mouse click."""
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
        """Smart Navigation: Prefer if already there or clickable."""
        target_url = f"https://www.instagram.com/{username}/"
        current_url = self.driver.current_url
        
        # 1. If already on profile
        if current_url.rstrip("/") == target_url.rstrip("/"):
            print(f"📍 Already on profile: {username}")
            return

        # 2. If there is a link to user on page (e.g. Post header)
        try:
            # User link in header or post owner link
            links = self.driver.find_elements(By.XPATH, f"//a[@href='/{username}/']")
            for link in links:
                if link.is_displayed():
                    print(f"🔗 Link found for {username}, clicking...")
                    link.click()
                    # Wait until URL changes (Max 5 sec)
                    try:
                        self.wait.until(lambda d: d.current_url.rstrip("/") == target_url.rstrip("/"))
                    except:
                        time.sleep(2) # Fallback
                    
                    if self.driver.current_url.rstrip("/") == target_url.rstrip("/"):
                        return
        except:
            pass

        # 3. Fallback: Direct Go
        self.driver.get(target_url)

    def check_system_health(self):
        """System health check: Blocked? No internet?"""
        try:
            # 1. Block Check (Action Blocked)
            page_source = self.driver.page_source
            if "Try Again Later" in page_source or "Daha Sonra Tekrar Dene" in page_source:
                print("🚨 CRITICAL: Instagram Action Blocked detected!")
                return "BLOCKED"
            
            # 2. Internet/Load Error
            if "No internet" in self.driver.title or "ERR_INTERNET_DISCONNECTED" in page_source:
                print("🚨 CRITICAL: No internet connection!")
                return "NO_NET"
                
            return "OK"
        except:
            return "OK"

    def open_following_modal(self, username):
        """Opens the following list modal."""
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
                # If modal cannot be opened, go directly to page
                self.driver.get(f"https://www.instagram.com/{username}/following/")
                return False

    def open_followers_modal(self, username):
        """Opens the followers list modal."""
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
                # If modal cannot be opened, go directly to page
                self.driver.get(f"https://www.instagram.com/{username}/followers/")
                return False

    def get_modal_dialog(self):
        try:
            dialog_container = self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            # Find scrollable area with JavaScript (Advanced)
            scrollable_div = self.driver.execute_script("""
                var container = arguments[0];
                var divs = container.getElementsByTagName('div');
                // Priority 1: _aano class (Instagram standard)
                var aano = container.querySelector('div._aano');
                if (aano) return aano;
                
                // Priority 2: Overflow style check
                for (var i = 0; i < divs.length; i++) {
                    var style = window.getComputedStyle(divs[i]);
                    if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
                        return divs[i];
                    }
                }
                
                // Priority 3: Div with highest scrollHeight (Containing content)
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
        """Collects user links from the given element."""
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
        Scrolls the element smoothly.
        Important for avoiding bot detection.
        """
        try:
            # Method 1: Smooth Scroll API
            self.driver.execute_script("arguments[0].scrollBy({top: 500, behavior: 'smooth'});", element)
            time.sleep(0.5)
            
            # Method 2: Random Scroll (Human mimic)
            # Occasionally scroll up and down
            if random.random() < 0.1:
                self.driver.execute_script("arguments[0].scrollBy({top: -100, behavior: 'smooth'});", element)
                time.sleep(0.3)
                self.driver.execute_script("arguments[0].scrollBy({top: 150, behavior: 'smooth'});", element)
            
            # Method 3: Go to bottom (For ScrollHeight update)
            # But do it smoothly instead of jumping
            # self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
            
            # Alternative: Step by step
            current_scroll = self.driver.execute_script("return arguments[0].scrollTop", element)
            total_height = self.driver.execute_script("return arguments[0].scrollHeight", element)
            
            if total_height - current_scroll > 500:
                 self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
            
            return self.driver.execute_script("return arguments[0].scrollHeight", element)
        except Exception as e:
            # Fallback: Old method
            try:
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", element)
                return self.driver.execute_script("return arguments[0].scrollHeight", element)
            except:
                return 0

    def scroll_window(self):
        """
        Scrolls the window smoothly.
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
        """Finds 'Following' or 'Requested' button (Enhanced)."""
        # Try JS first (Most stable)
        try:
            btn = self.driver.execute_script("""
                var buttons = document.querySelectorAll('button, div[role="button"], a[role="button"]');
                
                // 1. Text Check
                for (var i = 0; i < buttons.length; i++) {
                    var t = (buttons[i].innerText || "").toLowerCase().trim();
                    // Exact match
                    if (['takiptesin', 'following', 'istek gönderildi', 'requested'].includes(t)) {
                        return buttons[i];
                    }
                    // Content check (Excluding message button)
                    if ((t.includes('takiptesin') || t.includes('following')) && !t.includes('mesaj') && !t.includes('message')) {
                         return buttons[i];
                    }
                }
                
                // 2. Aria-Label Check
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
        """Finds 'Unfollow' confirm button (Enhanced)."""
        # Try JS
        try:
            btn = self.driver.execute_script("""
                var dialog = document.querySelector('div[role="dialog"]');
                var container = dialog || document.body;
                var buttons = container.querySelectorAll('button, div[role="button"], div[tabindex="0"], span');
                
                // 1. Find by Text
                for (var i = 0; i < buttons.length; i++) {
                    var t = (buttons[i].innerText || "").toLowerCase().trim();
                    if (['takibi bırak', 'unfollow', 'bırak'].includes(t)) {
                        return buttons[i];
                    }
                }
                
                // 2. Find by Color (Red)
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
        """Likes user's latest posts."""
        try:
            # Find first posts in profile (Usually 'a' tag containing '/p/')
            # Top 3 posts might be 'Pinned', so checking row by row is better.
            # But let's simply take first X posts.
            
            posts = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            if not posts:
                print("   -> No posts found to like.")
                return 0
                
            liked_count = 0
            for i in range(min(limit, len(posts))):
                try:
                    post = posts[i]
                    post_url = post.get_attribute("href")
                    
                    # Open post in new tab (to not disturb current page)
                    self.driver.execute_script("window.open(arguments[0], '_blank');", post_url)
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    time.sleep(3)
                    
                    # Find like button (SVG path or aria-label)
                    # On Instagram like button usually has 'Like' or 'Beğen' aria-label
                    # and svg class might change.
                    
                    # Check status: Already liked? (Usually red heart, aria-label 'Unlike'/'Vazgeç')
                    try:
                        unlike_btn = self.driver.find_element(By.XPATH, "//svg[@aria-label='Beğenmekten Vazgeç' or @aria-label='Unlike']")
                        if unlike_btn:
                            print(f"   -> Post already liked.")
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                            continue
                    except:
                        pass
                        
                    # Like button
                    like_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//svg[@aria-label='Beğen' or @aria-label='Like']")))
                    
                    # Click (Might need to click parent element)
                    parent_btn = like_btn.find_element(By.XPATH, "./ancestor::div[@role='button']")
                    parent_btn.click()
                    
                    print(f"   -> Post liked.")
                    liked_count += 1
                    time.sleep(2)
                    
                except Exception as e:
                    # print(f"Like error: {e}")
                    pass
                finally:
                    # Close tab and return to main tab
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
            return liked_count
        except Exception as e:
            print(f"Like process error: {e}")
            return 0
