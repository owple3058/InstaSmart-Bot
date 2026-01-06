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
from src.core.database import Database
from src.core.browser import BrowserManager
from src.core.plugin_manager import PluginManager
from src.guard.guard import Guard
from src.scheduler.scheduler import ActionScheduler
from src.utils.ai_manager import AIManager
from src.logger.logger import logger
from src.strategies.standard_strategies import LikeHashtagStrategy
from src.strategies.behavior_strategies import PassiveGrowthStrategy, ObservationOnlyStrategy, ManualAssistStrategy

class InstagramBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        
        # Scheduler
        self.scheduler = ActionScheduler()

        # Initialize Browser Manager
        self.browser_manager = BrowserManager()
        self.driver = self.browser_manager.build_driver()
        
        self.log_file = "history.log"
        self.wait = WebDriverWait(self.driver, 10)
        self.stats = {"LIKE": 0, "COMMENT": 0, "FOLLOW": 0, "FOLLOW_FROM_POST": 0, "FOLLOW_ALPHA": 0, "UNFOLLOW": 0}
        self.smart_file = "smart_state.json"
        self.smart_state = self.load_smart_state()
        
        # Telegram Settings (from config.py)
        self.tg_token = getattr(config, "TELEGRAM_TOKEN", None)
        self.tg_chat_id = getattr(config, "TELEGRAM_CHAT_ID", None)
        
        # Database Connection (Modular)
        self.db = Database(username)
        
        # Guard (Limit / Risk)
        self.guard = Guard(self.db)
        
        # Plugin Manager
        self.plugin_manager = PluginManager(self)
        self.plugin_manager.load_plugins()
        
        # Dry Run Mode
        self.dry_run = getattr(config, "DRY_RUN", False)
        if self.dry_run:
            logger.warning("DRY RUN MODE ENABLED", hint="No actual actions will be performed.")

        # Strategies
        self.strategies = {
            "LIKE_HASHTAG": LikeHashtagStrategy(self)
        }
        
        self.session_start = datetime.datetime.now()
        
        # AI Manager
        self.ai_manager = AIManager(self)

        # Behaviors
        self.behaviors = {
            "PASSIVE": PassiveGrowthStrategy(self),
            "OBSERVATION": ObservationOnlyStrategy(self),
            "MANUAL_ASSIST": ManualAssistStrategy(self)
        }
        self.current_behavior = None

    def send_telegram(self, message):
        """Sends notification via Telegram."""
        if not self.tg_token or not self.tg_chat_id:
            return
            
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
            data = {"chat_id": self.tg_chat_id, "text": message}
            requests.post(url, data=data, timeout=5)
        except:
            pass # Do not stop bot if no internet or error

    def log_action(self, action, target):
        if self.dry_run:
            # In Dry Run, we don't save to DB or update stats to keep simulation pure.
            # perform_action already logs to console/file via logger.
            return

        # Save to database
        self.db.log_action(action, target)
        
        # Update in-memory stats
        if action in self.stats:
            self.stats[action] += 1
            
        logger.success(f"Action executed", action=action, target=target)
        
        # Update Smart State
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.smart_state["events"].append({"ts": timestamp, "action": action})
            self.save_smart_state()
        except:
            pass

    def check_history(self, target):
        # Check from database
        if self.db.check_history(target):
            return True
            
        # Check from file as backup (For legacy logs)
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

    def perform_action(self, action_type, element, info=None):
        """
        Central method to execute actions.
        Respects DRY_RUN mode.
        """
        # Hook: Before Action
        if not self.plugin_manager.trigger_before_action(action_type, element, info):
            return False

        if self.dry_run:
            logger.info(f"DRY RUN: Would perform {action_type}", info=info)
            # Simulate success delay
            self.rand_delay()
            # Hook: After Action (Dry Run considered success for flow)
            self.plugin_manager.trigger_hook("after_action", action_type, element, True, info=info)
            return True
            
        try:
            if element:
                element.click()
            logger.success(f"Action performed: {action_type}", info=info)
            
            # Hook: After Action (Success)
            self.plugin_manager.trigger_hook("after_action", action_type, element, True, info=info)
            return True
        except Exception as e:
            logger.error(f"Action failed: {action_type}", error=str(e))
            
            # Hook: After Action (Fail)
            self.plugin_manager.trigger_hook("after_action", action_type, element, False, info=info)
            # Hook: On Error
            self.plugin_manager.trigger_hook("on_error", e, context=f"Action {action_type}")
            return False

    def fast_delay(self):
        self.scheduler.fast_delay()
    
    def turbo_delay(self):
        self.scheduler.turbo_delay()

    def action_allowed(self, action):
        return self.guard.action_allowed(action)
    
    # Legacy cleanup helper
    def _legacy_check(self):
        pass

    def print_summary(self):
        total_follow = self.stats.get("FOLLOW", 0) + self.stats.get("FOLLOW_FROM_POST", 0) + self.stats.get("FOLLOW_ALPHA", 0)
        
        # Duration Calculation
        elapsed = datetime.datetime.now() - self.session_start
        hours, remainder = divmod(elapsed.total_seconds(), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))

        summary = (
            f"\n{'='*30}\n"
            f"📊 SESSION REPORT (v3.0 - Framework)\n"
            f"🛡️  Safe Mode : {'ACTIVE' if getattr(config, 'SAFE_MODE', False) else 'OFF'}\n"
            f"⏱️  Duration: {duration_str}\n"
            f"{'-' * 30}\n"
            f"❤️  Likes         : {self.stats.get('LIKE', 0)}\n"
            f"💬  Comments      : {self.stats.get('COMMENT', 0)}\n"
            f"👤  Follows       : {total_follow}\n"
            f"🚫  Unfollows     : {self.stats.get('UNFOLLOW', 0)}\n"
            f"{'='*30}\n"
        )
        logger.info(summary)

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
        """Returns a random comment from comments.txt."""
        try:
            with open("comments.txt", "r", encoding="utf-8") as f:
                comments = f.readlines()
            valid_comments = [c.strip() for c in comments if c.strip() and not c.startswith("#")]
            if valid_comments:
                return random.choice(valid_comments)
        except:
            pass
        return "Great!" # Fallback comment

    def close_browser(self):
        self.plugin_manager.trigger_hook("on_bot_stop")
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
        # 1. Try login with Cookies first
        logger.info("Checking login status with cookies...")
        if self.browser_manager.load_cookies(self.username):
            if self.browser_manager.check_login_status():
                logger.success(f"Login with cookies SUCCESS", username=self.username)
                self.plugin_manager.trigger_hook("on_bot_start")
                return
            else:
                logger.warning("Cookies invalid or expired, starting normal login...")
        
        # 2. Normal Login
        logger.info("Starting normal login process...")
        self.driver.get("https://www.instagram.com/")
        self.rand_delay()
        
        try:
            # Username
            username_input = self.wait.until(EC.presence_of_element_located((By.NAME, "username")))
            username_input.clear()
            self.browser_manager.humanizer.type_like_human(username_input, self.username)
            self.rand_delay()
            
            # Password
            password_input = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.clear()
            self.browser_manager.humanizer.type_like_human(password_input, self.password)
            self.rand_delay()
            
            # Login Button or Enter
            password_input.send_keys(Keys.ENTER)
            self.rand_delay(True)
            logger.info("Credentials sent, waiting for redirect...")
            
            # Save cookies if login successful
            # time.sleep(5) # Wait for full load - Optimized
            try:
                WebDriverWait(self.driver, 10).until(lambda d: self.browser_manager.check_login_status())
            except:
                pass
            
            if self.browser_manager.check_login_status():
                logger.success("Login SUCCESS")
                self.browser_manager.save_cookies(self.username)
                self.plugin_manager.trigger_hook("on_bot_start")
            else:
                logger.error("Login might have failed", hint="Check screenshot or browser")
            
        except Exception as e:
            logger.error("Error during login", error=str(e))

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
        print(f"Autopilot mode completed: {done}")
        return done

    def set_behavior(self, behavior_name):
        """
        Sets the current behavior strategy.
        Options: PASSIVE, OBSERVATION, MANUAL_ASSIST
        """
        behavior_name = behavior_name.upper()
        if behavior_name in self.behaviors:
            self.current_behavior = self.behaviors[behavior_name]
            logger.info(f"Behavior changed", behavior=behavior_name, status="ACTIVE")
        else:
            logger.error(f"Behavior not found", behavior=behavior_name, available=list(self.behaviors.keys()))

    def run_behavior_cycle(self):
        """
        Executes one cycle of the current behavior.
        """
        # 1. Global Safety Check
        if not self.guard.is_safe_to_proceed():
            return
            
        # 2. UI Change / Risk Check
        if self.guard.check_ui_change(self.driver):
            return

        # 3. Check Silence Period (Sleep Mode)
        self.scheduler.enforce_silence_period()

        if self.current_behavior:
            try:
                self.current_behavior.perform_cycle()
                self.guard.report_success() # Reset errors on success
            except Exception as e:
                logger.error(f"Error in behavior cycle", error=str(e), behavior=type(self.current_behavior).__name__)
                self.guard.report_error(str(e)) # Report error to Guard
        else:
            logger.warning("No behavior set", hint="Use set_behavior() first")

    def like_photos_by_hashtag(self, hashtag, amount=5, follow=False, comment=False):
        """
        Delegates to LikeHashtagStrategy.
        """
        if "LIKE_HASHTAG" in self.strategies:
            self.strategies["LIKE_HASHTAG"].execute(hashtag, amount=amount, follow=follow, comment=comment)
        else:
            logger.error("Strategy not found: LIKE_HASHTAG")

    def unfollow_non_followers(self, count=20, only_nonfollowers=True, use_whitelist=True, fast=True, turbo=False, min_days=0, keep_verified=False, keep_min_followers=0):
        # 1. Go to Profile Page
        self.browser_manager.navigate_to_profile(self.username)
        if fast:
            self.fast_delay()
        else:
            self.rand_delay()
        
        # 2. Open Following List
        opened = self.browser_manager.open_following_modal(self.username)
        
        if fast:
            self.fast_delay()
        else:
            self.rand_delay(True)
            
        users_to_check = []
        dialog = self.browser_manager.get_modal_dialog()
        use_page_list = not opened or not dialog
        
        # 3. Collect Users
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
            print(f"Total accounts to check: {count}")

        # 4. Process Users
        for user_url in users_to_check[:count]:
            try:
                # self.driver.get(user_url) -> Optimized
                uname = self.parse_username_from_href(user_url)
                if uname:
                     self.browser_manager.navigate_to_profile(uname)
                else:
                     self.driver.get(user_url)

                if fast:
                    self.fast_delay()
                else:
                    self.rand_delay()
                
                # Check with Decision Maker (Whitelist)
                if uname and self.guard.is_whitelisted(uname):
                    continue
                
                # PROTECTION CHECKS (New)
                is_verified = False
                follower_count = 0
                
                if keep_verified or keep_min_followers > 0:
                    is_verified = self.browser_manager.is_verified_profile()
                    if keep_min_followers > 0:
                         try:
                             # Find followers link
                             fl_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers')]")
                             fl_text = fl_link.text or fl_link.get_attribute("title")
                             follower_count = self.parse_follower_count(fl_text)
                         except:
                             pass

                # Check if they follow us
                is_following_me = self.user_follows_me_via_following(uname, fast=fast, turbo=False, max_scrolls=12 if fast else 20)
                
                # Decision Maker Unfollow Decision
                if not self.guard.should_unfollow(uname, is_following_me, min_days_followed=min_days,
                                                         keep_verified=keep_verified, is_verified=is_verified,
                                                         keep_min_followers=keep_min_followers, follower_count=follower_count,
                                                         ignore_relationship=not only_nonfollowers):
                     continue

                if self.guard.action_allowed("UNFOLLOW"):
                    # Find 'Following' button
                    btn = self.browser_manager.find_following_button()
                    
                    if btn:
                        try:
                            # Use perform_action (Dry Run supported)
                            # Note: This is just the first click to open dialog, but we can treat it as part of the action.
                            # However, in dry run, we might not want to open the dialog if we can't click confirm.
                            # But user said "Sayfa gez, Element bul". So opening dialog is fine.
                            # BUT, if we don't open dialog, we can't find confirm button.
                            # If dry_run is True, perform_action returns True but DOES NOT CLICK.
                            # So dialog won't open. So we can't find confirm button.
                            
                            # Solution: For the setup clicks (opening dialog), we should probably allow them IF they are safe.
                            # But clicking "Following" button IS safe (it just opens a menu), it's the "Unfollow" in menu that is the action.
                            # WAIT: Clicking "Following" button opens the "Unfollow" confirmation popup.
                            # So we SHOULD click this even in Dry Run to find the confirm button?
                            # No, if we click this, the popup appears.
                            # If we want to simulate the whole flow, we should click this.
                            # The critical action is the CONFIRMATION.
                            
                            if self.dry_run:
                                # In dry run, we can simulate finding the button and stopping there?
                                # Or we can click the first button (safe) and NOT click the second.
                                # Let's click the first button even in dry run, because it's just opening a menu.
                                btn.click()
                            else:
                                btn.click()
                                
                        except:
                            if not self.dry_run:
                                self.driver.execute_script("arguments[0].click()", btn)
                    else:
                        logger.warning(f"Following button not found", user=uname)
                        continue
                        
                    if fast:
                        self.fast_delay()
                    else:
                        self.rand_delay()
                        
                    # Find confirm button
                    target = self.browser_manager.find_unfollow_confirm_button()
                    
                    if target:
                        # THIS is the critical action
                        if self.perform_action("UNFOLLOW", target, info={"user": uname, "url": user_url}):
                             # Log action (DB/Stats) - Safely ignored in Dry Run
                             self.log_action("UNFOLLOW", user_url)
                    else:
                        # If dry run, we might not have opened the dialog (if we decided not to click above).
                        # But since we decided to click above, target should be found.
                        if not self.dry_run:
                             logger.warning("Unfollow confirmation not found")
                        else:
                             logger.info("DRY RUN: Unfollow confirmation would be here.")
                        continue
                        
                    if fast:
                        self.fast_delay()
                    else:
                        self.rand_delay(True)
                        
                    if self.is_action_blocked():
                        logger.warning("Action blocked. Waiting.")
                        return
            except Exception as e:
                print(f"Profile operation error: {e}")
    
    def index_list(self, list_type="followers", max_count=None, fast=True, turbo=False):
        driver = self.driver
        collected = []
        
        # 1. Go to Profile
        self.browser_manager.navigate_to_profile(self.username)
        
        if fast and turbo:
            self.turbo_delay()
        elif fast:
            self.fast_delay()
        else:
            self.rand_delay()
            
        # 2. Open Modal/Page
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

        # 3. Dialog Check
        dialog = self.browser_manager.get_modal_dialog()
        use_page_list = (dialog is None)
        
        last_height = 0
        if not use_page_list and dialog:
            last_height = driver.execute_script("return arguments[0].scrollHeight", dialog)
        else:
            last_height = driver.execute_script("return document.body.scrollHeight")

        scroll_retries = 0
        
        while True:
            # Collect links
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
                
            # Scroll
            new_height = 0
            if not use_page_list and dialog:
                new_height = self.browser_manager.scroll_element(dialog)
            else:
                new_height = self.browser_manager.scroll_window()
            
            # Wait
            if fast and turbo:
                time.sleep(1)
            elif fast:
                time.sleep(2)
            else:
                self.rand_delay()
                
            # Height Check (Scroll finished?)
            if new_height == last_height:
                scroll_retries += 1
                if scroll_retries > 3:
                    break
                time.sleep(1)
            else:
                scroll_retries = 0
                last_height = new_height
                
        # Write to file
        fname = "index_followers.txt" if list_type == "followers" else "index_following.txt"
        try:
            with open(fname, "w", encoding="utf-8") as f:
                for u in collected:
                    f.write(u + "\n")
        except:
            pass
        print(f"{list_type} index completed: {len(collected)}")
        return collected
    
    def get_own_user_id(self):
        """Finds own user_id from cookies or page."""
        try:
            # 1. Try from cookies
            cookies = self.driver.get_cookies()
            for c in cookies:
                if c['name'] == 'ds_user_id':
                    return c['value']
            
            # 2. Try LocalStorage
            uid = self.driver.execute_script("return window.localStorage.getItem('ig_user_id')")
            if uid: return uid
            
            return None
        except:
            return None

    def fetch_users_via_api(self, list_type, limit=None, min_expected=0):
        """
        Advanced Method: Tries both REST API and GraphQL methods.
        Eliminates scroll issues.
        list_type: 'followers' or 'following'
        min_expected: Minimum expected users (to trigger REST backup)
        """
        user_id = self.get_own_user_id()
        if not user_id:
            print("❌ User ID not found, API method cancelled.")
            return set()

        print(f"🚀 Starting API Mode ({list_type})... (Fast Scan without Scroll)")
        
        endpoint_type = "followers" if list_type == "followers" else "following"
        
        # JS Script: Try GraphQL first, then REST API
        js_script = """
            var callback = arguments[arguments.length - 1];
            var userId = arguments[0];
            var type = arguments[1]; // 'followers' or 'following'
            var limit = arguments[2] || 10000;
            var minExpected = arguments[3] || 0;
            
            // Get csrftoken from cookie
            var match = document.cookie.match(/csrftoken=([^;]+)/);
            var csrftoken = match ? match[1] : null;
            
            if (!csrftoken) {
                callback({status: 'error', message: 'CSRF Token Missing'});
                return;
            }

            // Initial wait (Rate limit precaution)
            await new Promise(r => setTimeout(r, 2000));

            var allUsers = [];
            var errors = [];

            // ---------------------------------------------------------
            // METHOD 1: GraphQL API (More Reliable)
            // ---------------------------------------------------------
            async function tryGraphQL() {
                console.log("Trying GraphQL Method...");
                
                // Hash List (Current and Alternative)
                var hashes = (type === 'followers') 
                    ? ['c76146de99bb02f6415203be841dd25a', '5aefa9893005572d237da36f5d61f13b'] 
                    : ['d04b0a864b4b54837c0d870b0e77e076'];
                
                var edgeName = (type === 'followers') ? 'edge_followed_by' : 'edge_follow';
                
                for (var queryHash of hashes) {
                    console.log("Trying Hash: " + queryHash);
                    
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
                            
                            // Rate limit precaution
                            await new Promise(r => setTimeout(r, Math.random() * 1000 + 500));
                        }
                        
                        // If here, success
                        allUsers = allUsers.concat(tempUsers);
                        return true;
                        
                    } catch (e) {
                        console.error("Hash Failed:", e);
                        errors.push("GraphQL (" + queryHash + "): " + e.message);
                        // Move to next hash
                    }
                }
                
                return false; // All hashes failed
            }

            // ---------------------------------------------------------
            // METHOD 2: REST API (Backup)
            // ---------------------------------------------------------
            async function tryRestAPI() {
                console.log("Attempting REST API Method...");
                
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
                    console.error("REST API Error:", e);
                    errors.push("REST API: " + e.message);
                    return false;
                }
            }
            
            // Main Flow
            async function main() {
                // Try GraphQL first
                var success = await tryGraphQL();
                
                // Check: If GraphQL successful but count is missing, try to complete with REST
                if (success && minExpected > 0 && allUsers.length < minExpected) {
                    console.warn(`GraphQL fetched incomplete (${allUsers.length}/${minExpected}). Completing with REST API...`);
                    // Run REST as well (will append to allUsers)
                    await tryRestAPI();
                }
                // If GraphQL failed completely, try REST anyway
                else if (!success || allUsers.length === 0) {
                     if (!success) allUsers = []; 
                     success = await tryRestAPI();
                }
                
                if (success || allUsers.length > 0) {
                    // Duplicate cleanup
                    var uniqueUsers = [...new Set(allUsers)];
                    callback({status: 'success', users: uniqueUsers});
                } else {
                    callback({status: 'error', message: 'All methods failed. Details: ' + errors.join(' | ')});
                }
            }
            
            main();
        """
        
        try:
            self.driver.set_script_timeout(180) 
            result = self.driver.execute_async_script(js_script, user_id, endpoint_type, limit, min_expected)
            
            if result and result.get('status') == 'success':
                users = result.get('users', [])
                print(f"✅ API Scan Successful: {len(users)} users fetched.")
                return set(users)
            else:
                print(f"❌ API Error: {result.get('message')}")
                return set()
                
        except Exception as e:
            print(f"API Script Execution Error: {e}")
            return set()
    
    def scrape_modal_users(self, list_type="followers", limit=None, expected_min=None, target_username=None):
        """
        Fully scrapes the specified list type (followers/following) via modal and adds to set.
        target_username: If specified, scrapes that user's list (default: your own profile).
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        collected = set()
        
        target = target_username if target_username else self.username
        
        print(f"Scanning list: {target} - {list_type}...")
        
        try:
            # Go to profile (Optimized)
            self.browser_manager.navigate_to_profile(target)
            
            # Find link and click
            try:
                # Link is usually href="/username/followers/"
                link = w.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/{list_type}/')]")))
                link.click()
            except:
                # If link not found, go directly to URL (sometimes doesn't work but worth a try)
                driver.get(f"https://www.instagram.com/{target}/{list_type}/")
            
            time.sleep(3)

            # Find dialog element (Role dialog) - With Retry mechanism and Alternatives
            dialog_container = None
            print("Searching for dialog window...")

            # Strategy 1: Standard role='dialog'
            for i in range(5): # 5 attempts
                try:
                    dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    print("Dialog found (role='dialog').")
                    break
                except:
                    time.sleep(1)

            # Strategy 2: Direct scroll container (_aano)
            if not dialog_container:
                try:
                    print("Dialog not found by role, searching for _aano class...")
                    dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, '_aano')]")))
                    print("Direct scroll area found instead of dialog.")
                except:
                    pass

            # Strategy 3: Find by title text (Followers/Following)
            if not dialog_container:
                try:
                    print("Searching dialog by title text...")
                    xpath_text = "//*[contains(text(), 'Takipçiler') or contains(text(), 'Followers')]/ancestor::div[contains(@class, 'x1n2onr6') or contains(@class, '_aano') or position()=last()]"
                    dialog_container = driver.find_element(By.XPATH, xpath_text)
                    print("Container inferred from title.")
                except:
                    pass

            # Strategy 4: Main role (For full page view - Direct URL)
            if not dialog_container:
                try:
                    print("Searching main role (Full page mode)...")
                    dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//main[@role='main']")))
                    print("Main container found.")
                except:
                    pass

            # Strategy 5: Body (Last resort)
            if not dialog_container:
                try:
                    print("Last resort: Selecting Body element...")
                    dialog_container = driver.find_element(By.TAG_NAME, "body")
                except:
                    pass

            if not dialog_container:
                logger.error("CRITICAL ERROR: Dialog window could not be found by any method!")
                return set()
            
            # Find scrollable area with JavaScript (Advanced - Priority on ScrollHeight)
            dialog = driver.execute_script("""
                var container = arguments[0];
                var allDivs = container.getElementsByTagName('div');
                var bestDiv = null;
                var maxScrollHeight = 0;
                
                // Scan all divs and find the one with the largest scrollHeight (That is the real list)
                for (var i = 0; i < allDivs.length; i++) {
                    var d = allDivs[i];
                    var style = window.getComputedStyle(d);
                    
                    // Must be visible and scrollable
                    if (d.scrollHeight > d.clientHeight && d.clientHeight > 0) {
                         // Overflow check (Optional but safe)
                         if (style.overflowY === 'auto' || style.overflowY === 'scroll' || d.scrollHeight > 500) {
                             if (d.scrollHeight > maxScrollHeight) {
                                 maxScrollHeight = d.scrollHeight;
                                 bestDiv = d;
                             }
                         }
                    }
                }
                
                // If not found, look for _aano class
                if (!bestDiv) {
                    bestDiv = container.querySelector('div._aano');
                }
                
                // If none work, return the container itself
                return bestDiv || container;
            """, dialog_container)
            
            print("Scroll area detected.")
            
            # Focus attempt
            try:
                first_item = dialog.find_element(By.TAG_NAME, "a")
                ActionChains(driver).move_to_element(first_item).perform()
            except:
                pass

            last_len = 0
            same_len_count = 0
            
            while True:
                # Collect users
                js_links = driver.execute_script("""
                    var container = arguments[0];
                    // Both 'a' tags and those with 'role=link'
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
                
                # Progress check
                if len(collected) > before_count:
                    # If new data came, reset retry
                    scroll_attempts = 0
                    same_len_count = 0
                else:
                    same_len_count += 1
                
                # Print status to screen
                if expected_min and expected_min > 0:
                     print(f"\r   -> Scanned: {len(collected)} / ~{expected_min}", end="")
                else:
                     print(f"\r   -> Scanned: {len(collected)}", end="")

                # Limit check
                if limit and len(collected) >= limit:
                    print(f"\nLimit ({limit}) exceeded.")
                    break
                
                # Target reached?
                if expected_min and len(collected) >= expected_min:
                    print(f"\nTarget count ({expected_min}) reached.")
                    break

                # Scroll Operation (Enhanced Wiggle + scrollIntoView)
                # ----------------------------------------------------------------
                # NEW METHOD: Find last element and make visible (Lazy Load Trigger)
                # ----------------------------------------------------------------
                driver.execute_script("""
                    var container = arguments[0];
                    // Find all potential items inside container
                    var items = container.querySelectorAll('div[role="button"], div[role="listitem"], a'); 
                    if (items.length > 0) {
                        // Focus on last item and scroll
                        items[items.length - 1].scrollIntoView(true);
                    } else {
                        // If items not found, classic scroll
                        container.scrollTop = container.scrollHeight;
                    }
                """, dialog)
                time.sleep(1.0) # Wait for load
                
                # Wiggle - Sometimes scrollIntoView is not enough
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                time.sleep(0.5)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 300", dialog)
                time.sleep(0.3)
                driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                time.sleep(0.8)
                
                new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                
                # If scroll stuck or list didn't grow
                if new_h == last_h or same_len_count > 0:
                    if same_len_count > 0:
                        # Continue waiting but exit if too long
                        pass
                    
                    # Mandatory wait (Might be loading)
                    time.sleep(1)

                    # Method 2: Mouse Wheel Event (JS) and Element Focused Scroll
                    try:
                        # Advanced Scroll Element Finder (Auto Detect) - RECHECK
                        # Element might change while scrolling, so check every time.
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

                        # Scroll to last element (Lazy Loading trigger)
                        driver.execute_script("""
                            var d = arguments[0];
                            var items = d.querySelectorAll('div[role="button"], a'); 
                            if (items.length > 0) {
                                items[items.length - 1].scrollIntoView(true);
                            }
                        """, dialog)
                        time.sleep(0.5)

                        # KEYBOARD SUPPORT (PAGE_DOWN) - BACKUP POWER
                        try:
                            from selenium.webdriver.common.keys import Keys
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
                        except: pass

                    except: pass
                    
                    # Limit check (Timeout)
                    if same_len_count > 25: # If no data for 25 attempts
                        # If very close to target (90%) accept
                        if expected_min and len(collected) >= expected_min * 0.90:
                             print(f"\nData flow stopped but close to target ({len(collected)}/{expected_min}). Continuing.")
                             break
                        
                        print("\nEnd of list reached or data flow stopped (Timeout).")
                        break

                    # If scroll height didn't change, increase counter
                    if new_h == last_h:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        last_h = new_h
                else:
                    last_h = new_h
            
            print(f"\n{list_type} scan completed: {len(collected)} people found.")

        except Exception as e:
            print(f"\nList scan error: {e}")
        
        # Close modal (Advanced)
        print("Closing modal...")
        try:
            # 1. Close button (SVG)
            close_btn = driver.find_element(By.XPATH, "//*[name()='svg' and (@aria-label='Kapat' or @aria-label='Close')]/ancestor::div[@role='button']")
            close_btn.click()
            time.sleep(1)
        except:
            # 2. ESC key
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass
            
        return collected

    def smart_unfollow_cleanup(self, max_users=50, mode="non_followers"):
        """
        Optimized method for AI Mode, performs fast unfollow without visiting profiles (initially).
        mode: "non_followers" (Only those not following back) or "all" (Everyone)
        """
        print(f"\n⚡ STARTING SMART CLEANUP MODE ({mode}) ⚡")
        
        # 0. CACHE CLEANUP (User Request - Fresh Data Every Time)
        # Deleting old cache files as user reported "incorrect calculation".
        cache_file = f"followers_cache_{self.username}.json"
        if os.path.exists(cache_file):
            try:
                print("🧹 Cleanup Mode: Deleting old cache file (Fetching fresh data)...")
                os.remove(cache_file)
            except Exception as e:
                print(f"⚠️ Cache could not be deleted: {e}")

        print("Step 1: Analyzing profile data (Please wait)...")
        
        # 1. Fetch Lists (Safely)
        try:
            self.browser_manager.navigate_to_profile(self.username)
            # Get profile counts (For reference)
            visible_following = 0
            visible_followers = 0
            
            try:
                fl_link = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/following/')]")))
                visible_following = self.parse_follower_count(fl_link.text or fl_link.get_attribute("title"))
                
                f_link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/followers/')]")
                visible_followers = self.parse_follower_count(f_link.text or f_link.get_attribute("title"))
                
                print(f"📊 Profile Data: {visible_followers} Followers | {visible_following} Following")
            except:
                print("⚠️ Profile counts could not be read completely.")
                if visible_following == 0: visible_following = 1000
                if visible_followers == 0: visible_followers = 1000
                
            # ---------------------------------------------------------
            # NEW METHOD: Try API (Fetch) first, if fails, Scroll
            # ---------------------------------------------------------
            
            following = self.fetch_users_via_api("following", limit=None, min_expected=visible_following)
            
            # If API fetched incomplete (Less than 90% of profile count)
            # Threshold lowered: 98% -> 90% (Tolerant to avoid scroll stuck)
            if following and visible_following > 0 and len(following) < visible_following * 0.90:
                 print(f"⚠️ API fetched incomplete list ({len(following)}/{visible_following}). Completing with Scroll...")
                 # Scroll while preserving current list
                 scraped_following = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
                 following.update(scraped_following)
            elif following and visible_following > 0 and len(following) < visible_following:
                 print(f"ℹ️ API scan completed: {len(following)}/{visible_following}. (Small differences are normal, continuing)")

            if not following:
                print("⚠️ API failed to fetch following, switching to old (scroll) method...")
                following = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
            
            followers = set()
            if mode == "non_followers":
                print("🔄 Updating follower list (This may take a while)...")
                
                # API Rate Limit Precaution: Wait between two calls
                print("⏳ Waiting 5 seconds for API safety...")
                time.sleep(5)
                
                # Fetch Followers with API
                followers = self.fetch_users_via_api("followers", limit=None, min_expected=visible_followers)
                
                if not followers:
                    print("⚠️ API failed to fetch followers, switching to old (scroll) method...")
                    # Refresh page (Modal cleanup)
                    self.driver.refresh()
                    time.sleep(3)
                    followers = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)
                
                # If API fetched incomplete (Less than 90% of profile count)
                # Threshold lowered: 98% -> 90% (Tolerant to avoid scroll stuck)
                if followers and visible_followers > 0 and len(followers) < visible_followers * 0.90:
                     print(f"⚠️ API fetched incomplete followers ({len(followers)}/{visible_followers}). Completing with Scroll...")
                     scraped_followers = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)
                     followers.update(scraped_followers)
                elif followers and visible_followers > 0 and len(followers) < visible_followers:
                     print(f"ℹ️ API scan completed: {len(followers)}/{visible_followers}. (Small differences are normal, continuing)")
            
        except Exception as e:
            print(f"Error occurred while fetching lists: {e}")
            return 0
            
        if not following:
            print("Following list is empty or could not be fetched.")
            return 0
            
        # 2. Compare and Determine Target
        print("Step 2: Determining target audience...")
        
        target_pool = []
        if mode == "non_followers":
            target_pool = [u for u in following if u not in followers]
        else:
            target_pool = list(following) # Everyone
            
        # Whitelist and Time Check (Decision Maker)
        targets = []
        skipped_whitelist = 0
        skipped_recent = 0
        
        for u in target_pool:
            # 1. Whitelist Check
            if self.guard.is_whitelisted(u):
                skipped_whitelist += 1
                continue
                
            # 2. Time Check (Protect those followed within last 3 days)
            should_unfollow = self.guard.should_unfollow(u, is_following_me=False, min_days_followed=0, ignore_relationship=True)
            
            if should_unfollow:
                targets.append(u)
            else:
                skipped_recent += 1
                
        print(f"📊 Analysis Result:")
        print(f"   - Total Following: {len(following)}")
        if mode == "non_followers":
            print(f"   - Total Followers: {len(followers)}")
            print(f"   - Not Following You: {len(target_pool)}")
        else:
            print(f"   - Target Audience: Everyone ({len(target_pool)} users)")
            
        print(f"   - Whitelist Protection: {skipped_whitelist} users")
        print(f"   - New Follow (3 Days) Protection: {skipped_recent} users")
        print(f"   - TO UNFOLLOW: {len(targets)} users")
        
        if not targets:
            print("✅ No one to clean!")
            return 0
            
        if len(targets) > max_users:
            print(f"⚠️ Safety limit: Only first {max_users} users will be unfollowed.")
            targets = targets[:max_users]
            
        # 3. Delete via Profile Visit (Mandatory for API Mode)
        # Since data fetched via API is not in DOM, we cannot delete via list.
        # So we switch to Profile Visit mode which is the safest.
        print("\n🚀 Step 3: Starting safe unfollow operation (via Profile Visit)...")
        print("   (Profile visit is mandatory since API lists are not on screen)")
        
        # Close modal (If open)
        try:
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(1)
        except: pass
        
        count = 0
        for user in targets:
            if self.is_action_blocked():
                print("⛔ Action Block Detected, stopping operation.")
                break
                
            print(f"🔥 Unfollowing: {user}...", end=" ")
            
            try:
                # Go to profile
                self.browser_manager.navigate_to_profile(user)
                
                # Random wait (Human mimic - Optimized)
                time.sleep(random.uniform(1.0, 2.5))
                
                # Find button (Following button on page)
                unfollow_btn_found = self.browser_manager.find_following_button()
                
                if unfollow_btn_found:
                    # Click
                    try:
                        unfollow_btn_found.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", unfollow_btn_found)
                    
                    # Confirmation Dialog - Improved and Optimized
                    try:
                        # Wait for dialog (Max 3 sec)
                        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    except:
                        pass

                    # Find and click button
                    confirm_btn = self.browser_manager.find_unfollow_confirm_button()
                    
                    if confirm_btn:
                        try:
                            confirm_btn.click()
                            count += 1
                            self.log_action("UNFOLLOW", user)
                            print("UNFOLLOWED ✅")
                        except:
                             self.driver.execute_script("arguments[0].click();", confirm_btn)
                             count += 1
                             self.log_action("UNFOLLOW", user)
                             print("UNFOLLOWED ✅")
                    else:
                        print("Confirmation dialog didn't appear or button not found ❌")
                else:
                    print("Unfollow button not found (Maybe already unfollowed) ⚠️")
                
            except Exception as e:
                print(f"Error: {e}")
                # If Invalid Session ID error occurs, driver might need restart but
                # for now just pass, continue loop.
                if "invalid session id" in str(e).lower():
                    print("CRITICAL ERROR: Browser session lost. Exiting...")
                    break
            
            # Wait between actions
            time.sleep(random.uniform(1.0, 2.0))

        print(f"\n🎉 Operation Completed! Total unfollowed: {count}")
        return count

    def algorithm_based_unfollow(self, fast=True, turbo=True, min_days=0, keep_verified=False, keep_min_followers=0):
        """
        Full Algorithmic Logic (Improved):
        1. Fetch Following list (All)
        2. Fetch Followers list (All)
        3. Compare (Difference)
        4. Apply Whitelist
        5. Ghost Check - Extra Security
        6. Unfollow (via Profile visit - Safest method)
        """
        
        # First get profile counts (For Safety Check)
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
                 
            print(f"📊 Profile Data -> Followers: {visible_followers} | Following: {visible_following}")
        except:
            print("⚠️ Profile counts could not be read, continuing in cautious mode.")

        # 1. Fetch Following
        following_set = self.fetch_users_via_api("following", limit=None)
        if not following_set:
             print("⚠️ Failed to fetch following via API, switching to old (scroll) method...")
             following_set = self.scrape_modal_users("following", expected_min=int(visible_following * 0.95) if visible_following else None)
        
        print(f"✅ Total Following: {len(following_set)}")
        
        if visible_following > 0 and len(following_set) < visible_following * 0.90:
             print(f"❌ WARNING: Following list fetched incompletely! (Expected: {visible_following}, Got: {len(following_set)})")
             print("Stopping for safety.")
             return
        
        if not following_set:
            print("❌ Following list is empty! Operation cancelled.")
            return

        # REFRESH PAGE
        print("🔄 Refreshing page...")
        self.browser_manager.navigate_to_profile(self.username)
        # self.driver.get(f"https://www.instagram.com/{self.username}/")
        # time.sleep(4)

        # 2. Fetch Followers
        followers_set = self.fetch_users_via_api("followers", limit=None)
        if not followers_set:
             print("⚠️ Failed to fetch followers via API, switching to old (scroll) method...")
             followers_set = self.scrape_modal_users("followers", expected_min=int(visible_followers * 0.95) if visible_followers else None)

        print(f"✅ Total Followers: {len(followers_set)}")
        
        # SAFETY CHECK
        if visible_followers > 0:
            if len(followers_set) < visible_followers * 0.95: 
                 print(f"❌ EMERGENCY STOP: Followers list fetched incompletely! (Expected: {visible_followers}, Got: {len(followers_set)})")
                 print("Proceeding now might delete users WHO ARE FOLLOWING YOU.")
                 return
        else:
            if not followers_set:
                 print("❌ EMERGENCY STOP: Profile info readable and followers list is empty.")
                 return
            if len(followers_set) < 10 and len(following_set) > 20: 
                 print("❌ Fetched follower count is too low, operation cancelled.")
                 return

        # 3. Compare
        to_unfollow = []
        for user in following_set:
            if user not in followers_set:
                if self.guard.should_unfollow(user, is_following_me=False, min_days_followed=min_days):
                    to_unfollow.append(user)
        
        print(f"📋 Analysis Result: {len(to_unfollow)} users will be unfollowed.")
        
        if len(to_unfollow) > len(following_set) * 0.9:
            print("⚠️ WARNING: You are about to unfollow more than 90% of the list.")
            confirm = input("Continue anyway? (yes/no): ")
            if confirm.lower() != "yes":
                return

        # ---------------------------------------------------------
        # 4. GHOST CHECK
        # ---------------------------------------------------------
        if to_unfollow:
            print("\n🕵️ SAFETY MODE: Verifying candidates one last time in 'Followers' list...")
            verified_targets = []
            
            try:
                # Open Followers modal
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
                        print(f"   -> Checked: {check_count}/{len(to_unfollow)}")

                    try:
                        search_box.send_keys(Keys.CONTROL + "a")
                        search_box.send_keys(Keys.DELETE)
                        search_box.send_keys(user)
                        time.sleep(0.6) 
                        
                        found = False
                        # Check result
                        results = dialog.find_elements(By.XPATH, f".//a[contains(@href, '/{user}/')]")
                        if results:
                            found = True
                        else:
                            # Text check
                            spans = dialog.find_elements(By.XPATH, f".//span[contains(text(), '{user}')]")
                            if spans:
                                found = True
                                
                        if found:
                            print(f"❌ RISK: {user} seems to be following you (Removed from list).")
                        else:
                            verified_targets.append(user)
                            
                    except Exception as e:
                        print(f"   Verification error ({user}): {e}")
                        verified_targets.append(user)
                
                to_unfollow = verified_targets
                print(f"✅ Verification Finished. Final Target: {len(to_unfollow)} users")
                
            except Exception as e:
                print(f"General error in verification mode: {e}")
                print("⚠️ Verification could not be completed, continuing with current list.")

        # 5. Start Operation
        print("\n🚀 Starting Unfollow operation...")
        
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
                
                # PROTECTION CHECKS
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

                if not self.guard.should_unfollow(user, is_following_me=False, min_days_followed=min_days,
                                                         keep_verified=keep_verified, is_verified=is_verified,
                                                         keep_min_followers=keep_min_followers, follower_count=follower_count):
                    print(f"🛡️ Skipped (Protection): {user}")
                    continue

                # Unfollow Operation
                if self.guard.action_allowed("UNFOLLOW"):
                    # -----------------------------------------------------------
                    # Button finding logic (Improved - v2)
                    # -----------------------------------------------------------
                    unfollow_btn_found = None
                    
                    # 1. JS button finding (More stable)
                    unfollow_btn_found = self.driver.execute_script("""
                        var buttons = document.querySelectorAll('button, div[role="button"], a[role="button"]');
                        
                        // 1. Text Control
                        for (var i = 0; i < buttons.length; i++) {
                            var t = (buttons[i].innerText || "").toLowerCase().trim();
                            // Exact match
                            if (['takiptesin', 'following', 'istek gönderildi', 'requested'].includes(t)) {
                                return buttons[i];
                            }
                            // Content control (Except message button)
                            if ((t.includes('takiptesin') || t.includes('following')) && !t.includes('mesaj') && !t.includes('message')) {
                                 return buttons[i];
                            }
                        }
                        
                        // 2. Aria-Label Control (For icon buttons)
                        var svgs = document.querySelectorAll('svg[aria-label="Following"], svg[aria-label="Takiptesin"]');
                        if (svgs.length > 0) {
                            var p = svgs[0].closest('button, div[role="button"], a[role="button"]');
                            if (p) return p;
                        }
                        
                        return null;
                    """)
                    
                    # 2. If JS fails, try Python XPATH (Stronger)
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
                        # Check: Is there a "Follow" button? (Already unfollowed?)
                        try:
                            follow_btn = self.driver.find_element(By.XPATH, "//button[text()='Takip Et' or text()='Follow' or text()='Follow Back']")
                            if follow_btn:
                                print(f"⚠️ Already not following: {user}")
                                continue
                        except: pass
                        
                        print(f"⚠️ 'Following' button not found: {user}")
                        continue
                    
                    # Click
                    try:
                        unfollow_btn_found.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", unfollow_btn_found)
                    
                    time.sleep(1.5)

                    # -----------------------------------------------------------
                    # Confirmation Dialog - Improved
                    # -----------------------------------------------------------
                    confirmed = False
                    
                    # Wait for Dialog
                    try:
                        self.wait.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                    except:
                        time.sleep(1) 

                    # Find dialog button via JS
                    for _ in range(4): # Try 4 times
                        confirmed = self.driver.execute_script("""
                            var dialog = document.querySelector('div[role="dialog"]');
                            var container = dialog || document.body;
                            var buttons = container.querySelectorAll('button, div[role="button"], div[tabindex="0"], span');
                            
                            // 1. Find by Text
                            for (var i = 0; i < buttons.length; i++) {
                                var t = (buttons[i].innerText || "").toLowerCase().trim();
                                if (['takibi bırak', 'unfollow', 'bırak'].includes(t)) {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                            
                            // 2. Find by Color (Red)
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
                        
                        # Python XPATH Fallback
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
                        print(f"✅ [{processed+1}/{len(to_unfollow)}] Unfollowed: {user}")
                        processed += 1
                        
                        if self.is_action_blocked():
                            print("⛔ Block detected. Waiting (120s)...")
                            time.sleep(120)
                        
                        if fast and turbo:
                            time.sleep(random.uniform(2, 5))
                        elif fast:
                            time.sleep(random.uniform(5, 12))
                        else:
                            self.rand_delay(True)
                    else:
                        print(f"⚠️ Confirmation dialog not found: {user}")
                        
            except Exception as e:
                print(f"❌ Error ({user}): {e}")
                continue
                
        print("\n🏁 Algorithmic unfollow completed.")
        self.send_telegram(f"🤖 Algorithmic Unfollow Completed!\n\nTotal Unfollowed: {processed}\nRemaining Target: {len(to_unfollow) - processed}")

    def get_location_url(self, query):
        """Finds location URL for the given query."""
        try:
            print(f"Searching for location: {query}...")
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
                    print(f"Location found: {name} ({url})")
                    return url
            print("Location not found.")
            return None
        except Exception as e:
            print(f"Location search error: {e}")
            return None

    def collect_users_from_feed(self, url, limit=50):
        """Collects usernames from the given feed URL (Hashtag/Location)."""
        driver = self.driver
        users = []
        
        print(f"Scanning feed... (Target: {limit} users)")
        driver.get(url)
        time.sleep(5)
        
        # Find and click the first post
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
                print("Post not found.")
                return []
        except:
            return []
            
        # Iterate posts
        p_count = 0
        while len(users) < limit and p_count < limit * 3: # Infinite loop precaution
            p_count += 1
            try:
                # Get username
                # Link in header
                header_link = None
                try:
                    header_link = driver.find_element(By.XPATH, "//header//a[not(contains(@href, '/explore/'))]")
                except:
                    # Alternative XPATH
                    header_link = driver.find_element(By.XPATH, "//div[contains(@class, '_aaqt')]//a")

                if header_link:
                    username = header_link.text
                    if not username: # Sometimes text might be empty, get from href
                        href = header_link.get_attribute("href")
                        if href:
                            username = self.parse_username_from_href(href)

                    if username and username not in users:
                        users.append(username)
                        print(f"Found: {username} ({len(users)}/{limit})")
                
                # Next post
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ARROW_RIGHT)
                time.sleep(random.uniform(1.5, 3))
            except:
                # Try to go to next post (even if error)
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    body.send_keys(Keys.ARROW_RIGHT)
                    time.sleep(2)
                except:
                    break
        
        return users

    def get_active_users_from_seed(self, seed_username, limit=30):
        """
        Collects commenters and likers from the Seed (Source) user's recent posts.
        This method finds 'Active' users.
        """
        driver = self.driver
        users = set()
        
        print(f"Scanning source: {seed_username} (Target: {limit} active users)")
        
        try:
            self.browser_manager.navigate_to_profile(seed_username)
            time.sleep(3)
            
            # Iterate last 3 posts
            # Get first 3 post links from profile (Pinned is fine)
            try:
                links = driver.find_elements(By.TAG_NAME, "a")
                post_links = [l.get_attribute("href") for l in links if "/p/" in l.get_attribute("href")]
                # Remove duplicates and take first 3
                post_links = list(dict.fromkeys(post_links))[:3]
            except:
                post_links = []
                
            if not post_links:
                print("   -> Post not found.")
                return []
                
            for post_url in post_links:
                if len(users) >= limit:
                    break
                    
                driver.get(post_url)
                time.sleep(3)
                
                # Try to open comments (Load more comments)
                try:
                    load_more = driver.find_element(By.XPATH, "//*[contains(text(), 'View more comments') or contains(text(), 'daha fazla yorum')]")
                    load_more.click()
                    time.sleep(2)
                except: pass
                
                # Collect usernames from comments
                # Generally _a9zc, _a9ze classes or simply 'a' tags
                try:
                    # Try to find comment area
                    comment_area = driver.find_elements(By.XPATH, "//ul//div//a")
                    for elem in comment_area:
                        href = elem.get_attribute("href")
                        if href:
                            u = self.parse_username_from_href(href)
                            if u and u != seed_username and u != self.username:
                                users.add(u)
                except: pass
                
                print(f"   -> {len(users)} users collected...")
                
        except Exception as e:
            print(f"Seed error: {e}")
            
        return list(users)

    def follow_smart_seeds(self, limit=20, criteria=None):
        """
        Smart Seed Follow Module (Unfiltered, Fast, Random)
        """
        driver = self.driver
        followed = 0
        processed = 0
        
        # REAL INCREASE: Fluctuating Limit
        variance = int(limit * 0.10)
        actual_limit = limit + random.randint(-variance, variance)
        if actual_limit < 1: actual_limit = 1
        
        # Popular Influencer/Celebrity List (Seed Pool)
        seeds = [
            "danlabilic", "duyguozaslan", "seymasubasi", "gamzeercel", "handemiyy", 
            "bensusoral", "serenaysarikaya", "ezgimola", "demetozdemir", "neslihanatagul", 
            "hazalkaya", "fahriyevcen", "elcinsangu", "busevarol", "eceerken", "caglasikel",
            "burcuozberk", "aslienver", "pelinakil", "benguofficial", "demetakalin",
            "sedasayan", "ebrugundes", "hadise", "muratboz", "acunilicali", 
            "cznburak", "nusret" 
        ]
        
        random.shuffle(seeds)
        
        print(f"Smart Seed Follow Starting. Target: ~{limit} (Planned: {actual_limit})")
        
        seed_index = 0
        while followed < actual_limit:
            if seed_index >= len(seeds):
                seed_index = 0
                random.shuffle(seeds) 
                
            current_seed = seeds[seed_index]
            seed_index += 1
            
            # Strategy Selection: 70% Comments (Active), 30% Followers (Passive)
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
            
            # RANDOMNESS: Shuffle candidate list
            random.shuffle(candidates)
                
            print(f"Number of candidates to analyze: {len(candidates)}")
            
            for username in candidates:
                if followed >= actual_limit:
                    break
                    
                # History check
                if self.check_history(username):
                    continue
                    
                processed += 1
                print(f"[{processed}] Processing: {username}")
                
                try:
                    # Go to profile
                    self.browser_manager.navigate_to_profile(username)
                    time.sleep(random.uniform(1.5, 2.5)) 
                    
                    # Private Profile Check
                    is_private = self.browser_manager.is_private_profile()
                    if is_private:
                        print(f"   -> Private Profile. Only follow request will be sent.")
                    
                    # INTERACTION FOCUSED GROWTH (Story + Like + Follow)
                    
                    if not is_private:
                        # 1. Watch Story (If exists)
                        # Watch story with 40% probability
                        if random.random() < 0.40:
                             self.browser_manager.watch_story()
                             time.sleep(1)

                        # 2. Like Latest Post
                        # Like latest post with 50% probability
                        if random.random() < 0.50:
                             self.browser_manager.like_latest_post(limit=1)
                             time.sleep(1)

                    # 3. Direct Follow (Unfiltered, Fast)
                    try:
                        # Wait 3 seconds
                        short_wait = WebDriverWait(driver, 3)
                        btn = short_wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                        
                        btn.click()
                        followed += 1
                        self.log_action("FOLLOW", username)
                        print(f"   -> SUCCESS. Total: {followed}/{actual_limit}")
                        
                        # Speeded up (5-10 sec)
                        time.sleep(random.uniform(5, 10))
                        
                    except:
                        # If no follow button, maybe already following?
                        try:
                            following_btn = driver.find_elements(By.XPATH, "//button[.//div[contains(text(), 'Takiptesin') or contains(text(), 'Following')]]")
                            if following_btn:
                                print("   -> Already following.")
                                self.log_action("FOLLOW", username)
                            else:
                                print("   -> Follow button not found.")
                        except:
                            pass
                            
                except Exception as e:
                    print(f"Profile error: {e}")
                    continue
            
            # Wait before seed change
            time.sleep(3)

    def follow_target_followers(self, target_username, limit=50):
        """
        Delegates to FollowStrategy.
        """
        if "FOLLOW" in self.strategies:
            self.strategies["FOLLOW"].execute(target_username, amount=limit)
        else:
            print("Error: FOLLOW strategy not found.")

    def follow_users_with_criteria(self, target_list, criteria=None, limit=50):
        """
        Follows users in the list filtering by criteria.
        criteria: {"gender": "female", "nationality": "turkish"}
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        print(f"Criteria follow starting. Target: {limit} users. Criteria: {criteria}")
        
        processed = 0
        followed = 0
        
        for user in target_list:
            if followed >= limit:
                break
                
            # Block check
            if self.is_action_blocked():
                print("Action blocked, stopping.")
                break
                
            # Checked before?
            if self.check_history(user):
                continue
                
            processed += 1
            print(f"[{processed}/{len(target_list)}] Analyzing: {user}")
            
            try:
                # Go to profile
                self.browser_manager.navigate_to_profile(user)
                self.safe_sleep(2, 4)
                
                # Collect profile info
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
                    # H1 is usually username, fullname might be in span or div under it
                    # Instagram structure changes, pulling from meta tag might be safer
                    meta_title = driver.title # "Name (@username) • Instagram photos..."
                    if "(" in meta_title:
                        user_data["fullname"] = meta_title.split("(")[0].strip()
                except: pass
                
                # Bio
                try:
                    # Simple detection: divs under h1
                    # or meta description
                    meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                    if meta_desc:
                        user_data["bio"] = meta_desc # Usually "X Followers, Y Following, Z Posts - ..."
                except: pass
                
                # Bio (Alternative - In-page)
                try:
                    bio_elem = driver.find_element(By.XPATH, "//h1/..//div[contains(@class, '_aa_c')]") # Example class, might change
                    if bio_elem:
                        user_data["bio"] += " " + bio_elem.text
                except: pass

                # Follower Count (Decision mechanism - Improved)
                try:
                    # 1. Via Link (/followers/)
                    f_link = driver.find_elements(By.XPATH, f"//a[contains(@href, '/followers/')]")
                    if f_link:
                        txt = f_link[0].text or f_link[0].get_attribute("title")
                        if txt:
                            user_data["follower_count"] = self.parse_follower_count(txt)
                    
                    # 2. UI Span scan
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

                # Decide
                if self.guard.should_follow(user_data, criteria):
                    print(f"   -> Criteria matched! Following: {user}")
                    
                    # Follow Button
                    btn = self.browser_manager.find_following_button() # This means 'Following' so already followed
                    if btn:
                        print("   -> Already followed.")
                        self.log_action("FOLLOW", user) # Log to database
                    else:
                        # Find Follow button (Blue button)
                        try:
                            f_btn = w.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                            f_btn.click()
                            followed += 1
                            self.log_action("FOLLOW", user)
                            print(f"   -> Success. Total: {followed}")
                            
                            # Wait
                            self.rand_delay()
                        except:
                            print("   -> Follow button not found.")
                else:
                    print("   -> Does not match criteria, skipped.")
                    
            except Exception as e:
                print(f"Error ({user}): {e}")
                
        print(f"Process completed. Total Followed: {followed}")
        self.send_telegram(f"✅ Criteria Follow Completed!\n\nFollowed: {followed}\nAnalyzed: {processed}")

    def fast_modal_unfollow_nonfollowers(self, max_actions=300, fast=True, turbo=True, min_days=0, keep_verified=False):
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        followers_set = set() # Must be defined as empty set initially
        
        # STEP 1: Load Followers into memory
        # Try loading from local file first
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
                    print(f"\nInfo: {len(followers_set)} followers cached.")
                    use_cache = input("Use cache instead of rescanning followers? (Y/n) (Fast): ").strip().lower()
                    if use_cache in ["y", "yes", ""]:
                        loaded_from_file = True
                        print("Using cache. Scan skipped.")
                    else:
                        followers_set.clear()
                        print("Cache cleared, rescanning.")
                else:
                    print("Info: Cache file found but empty.")
            except Exception as e:
                print(f"Cache read error: {e}")

        if not loaded_from_file:
            print("Scanning current followers list... (This may take time depending on list size)")
            driver.get(f"https://www.instagram.com/{self.username}/")
            if fast and turbo:
                self.turbo_delay()
            elif fast:
                self.fast_delay()
            else:
                self.rand_delay()
            
            total_followers = 0
            try:
                # Get follower count (To open modal)
                # Also get the count number
                link = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/followers/')]")))
            
                try:
                    # Get count
                    c_txt = ""
                    # 1. Title attribute (Usually full number: "1,234")
                    try:
                        sp = link.find_element(By.XPATH, ".//span[@title]")
                        c_txt = sp.get_attribute("title")
                    except:
                        pass
                
                    if not c_txt:
                        # 2. Span text (Usually "1.2k" format or direct number)
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
                    print(f"Visible follower count on profile: {total_followers}")
                except:
                    pass
                
                # If failed from UI or 0, try Meta Tag
                if total_followers == 0:
                    try:
                        total_followers = self.get_follower_count_from_meta()
                        print(f"Follower count from meta tag: {total_followers}")
                    except:
                        pass

                link.click()
            except:
                # Even if link not found, try meta tag (if page loaded)
                if total_followers == 0:
                    try:
                        # Try fetching from Header (More reliable selector)
                        # Find link with href="/username/followers/"
                        f_link = driver.find_element(By.XPATH, f"//a[contains(@href, '/followers/')]//span")
                        total_followers = self.parse_follower_count(f_link.text)
                        print(f"Follower count from header link: {total_followers}")
                    except:
                        try:
                            total_followers = self.get_follower_count_from_meta()
                            print(f"Follower count from meta tag (Fallback): {total_followers}")
                        except:
                            pass
                        
                driver.get(f"https://www.instagram.com/{self.username}/followers/")
        
            try:
                # Find Dialog element (Role dialog) - Retry mechanism and Alternatives
                dialog_container = None
                print("Searching for dialog window...")
                
                # Strategy 1: Standard role='dialog'
                for i in range(5): # 5 attempts
                    try:
                        # Check existence first
                        dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[@role='dialog']")))
                        print("Dialog found (role='dialog').")
                        break
                    except:
                        time.sleep(1)
                
                # Strategy 2: Direct scroll container (_aano)
                if not dialog_container:
                    try:
                        print("Dialog not found by role, searching for _aano class...")
                        dialog_container = w.until(EC.visibility_of_element_located((By.XPATH, "//div[contains(@class, '_aano')]")))
                        # If _aano found, this is already the scrollable area, but we can use it as container
                        # or accept its parent as dialog.
                        # Let's accept it as container to not break hierarchy.
                        print("Direct scroll area found instead of dialog.")
                    except:
                        pass

                # Strategy 3: Find by Title text (Takipçiler/Followers)
                if not dialog_container:
                    try:
                        print("Searching dialog by title text...")
                        xpath_text = "//*[contains(text(), 'Takipçiler') or contains(text(), 'Followers')]/ancestor::div[contains(@class, 'x1n2onr6') or contains(@class, '_aano') or position()=last()]"
                        dialog_container = driver.find_element(By.XPATH, xpath_text)
                        print("Container guessed from title.")
                    except:
                        pass

                # Strategy 4: Main role (For full page view - Direct URL)
                if not dialog_container:
                    try:
                        print("Searching Main role (Full page mode)...")
                        dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//main[@role='main']")))
                        print("Main container found.")
                    except:
                        pass
                
                # Strategy 5: Body (Last resort)
                if not dialog_container:
                    try:
                        print("Last resort: Selecting Body element...")
                        dialog_container = driver.find_element(By.TAG_NAME, "body")
                    except:
                        pass

                if not dialog_container:
                    print("CRITICAL ERROR: Dialog window not found by any method!")
                    # Last resort: We could dump page source for analysis but exception for now.
                    raise Exception("Dialog window not found.")
                
                # Find scrollable area via JavaScript (More robust)
                def get_scrollable_dialog(d_container):
                    return driver.execute_script("""
                        var container = arguments[0];
                        // Priority 1: _aano class (Instagram standard modal scroll class)
                        var aano = container.querySelector('div._aano');
                        if (aano) return aano;
                        
                        // Priority 2: Computed Style check
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
                # Debug: See which element we found
                try:
                    d_class = dialog.get_attribute("class")
                    print(f"Scroll element class: {d_class}")
                except: pass

                last_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                scroll_attempts = 0
                
                while True:
                    try:
                        # If dialog is stale try refreshing at start of loop
                        try:
                            dialog.is_enabled()
                        except:
                             # Refresh if stale
                             dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                             dialog = get_scrollable_dialog(dialog_container)

                        # Collect usernames from visible links
                        # Method 1: JavaScript (Safest - Doesn't create Stale Element)
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

                        # Method 2: Selenium (Backup) - Pass if Stale error
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
                        
                        # Scroll (Move up and down slightly for more natural behavior)
                        # Method 1: Focus on last element and make visible (Most effective)
                        try:
                            # Find last link in dialog
                            last_link = dialog.find_elements(By.TAG_NAME, "a")[-1]
                            driver.execute_script("arguments[0].scrollIntoView(true);", last_link)
                        except:
                            # If no link, try scrollTop with JS
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                        
                        time.sleep(0.5 if turbo else 1)
                        
                        # Method 2: Keyboard Key (PAGE_DOWN) - Trigger if JS is not enough
                        try:
                            # Focus first
                            dialog.click()
                            dialog.send_keys(Keys.PAGE_DOWN)
                        except:
                            pass
                            
                        new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                        if new_h == last_h:
                            # If scroll stuck, try slightly up then down again
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 300", dialog)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                            time.sleep(1)
                            new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                            
                        if new_h == last_h:
                            scroll_attempts += 1
                            # print(f"Scroll attempt: {scroll_attempts}/15")
                            
                            # If close to target count and scroll not working, don't force
                            if total_followers > 0 and len(followers_set) >= total_followers * 0.95:
                                print(f"Target count reached ({len(followers_set)}/{total_followers}), finishing scan.")
                                break

                            if scroll_attempts > 15: # Increased attempts from 5 to 15 (Be more patient)
                                print("Scroll end reached or stuck.")
                                break
                            time.sleep(1)
                        else:
                            scroll_attempts = 0
                            last_h = new_h
                        
                        # Safety limit for huge accounts (Don't freeze if 50k followers)
                        if len(followers_set) > 50000: 
                            print("Follower limit (50000) exceeded, stopping scan.")
                            break
                        
                        if len(followers_set) % 500 == 0 and len(followers_set) > 0:
                            print(f"   -> Collected followers: {len(followers_set)}")

                    except Exception as loop_e:
                        if "stale" in str(loop_e).lower():
                            print("Stale Element (Scroll), refreshing dialog...")
                            try:
                                dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                                dialog = get_scrollable_dialog(dialog_container)
                                continue
                            except:
                                break
                        else:
                            print(f"Scroll loop error: {loop_e}")
                            # Continue on non-critical errors
                            pass

            except Exception as e:
                print(f"General error while fetching follower list: {e}")
                if len(followers_set) > 0:
                    print(f"Error received but {len(followers_set)} followers collected. Continuing...")
                else:
                    return 0
            
            print(f"Total {len(followers_set)} followers cached.")
            # Save to Cache
            try:
                with open(followers_file, "w", encoding="utf-8") as f:
                    for u in followers_set:
                        f.write(f"{u}\n")
                print(f"Follower list cached: {followers_file}")
            except Exception as e:
                print(f"Cache save error: {e}")
        
        if loaded_from_file:
            # If loaded from file, assume total count is same as file count
            total_followers = len(followers_set)

        if len(followers_set) == 0:
            print("Follower list is empty or could not be retrieved. Stopping for safety.")
            return 0
            
        if total_followers == 0:
            print("SECURITY WARNING: Total follower count could not be verified!")
            print(f"System found {len(followers_set)} people but cannot guarantee list completeness without total count.")
            print("Operation stopping to prevent accidental unfollow (removing people who follow you).")
            print("Please check internet connection and try again or use 'Slow Mode'.")
            return 0
        
        if len(followers_set) < total_followers * 0.95: # Increased from 90% to 95% (Safer)
            print(f"SECURITY WARNING: Incomplete list! (Expected: ~{total_followers}, Retrieved: {len(followers_set)})")
            print("Operation cancelled to avoid incorrect unfollows.")
            return 0

        # Close modal (If only scanning was done)
        if not loaded_from_file:
            try:
                close_btn = driver.find_element(By.XPATH, "//div[@role='dialog']//button[contains(@class, '_abl-')]")
                close_btn.click()
            except:
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                except: pass
        
        time.sleep(1)
        
        # 2. STEP: Go to Following list and unfollow
        print("Checking following list and starting operation...")
        processed = 0
        checked_users = set()
        
        try:
            link = w.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/following/')]")))
            link.click()
        except:
            driver.get(f"https://www.instagram.com/{self.username}/following/")
            
        try:
            # Find dialog element (Role dialog)
            dialog_container = w.until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
            
            # Find scrollable area via JavaScript
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
                # Method 1: Standard listitem
                items = dialog.find_elements(By.XPATH, ".//div[@role='listitem']")
                
                # Method 2: Fallback - Any div containing button and link
                if not items:
                     items = dialog.find_elements(By.XPATH, ".//div[.//button and .//a[not(contains(@href, '/explore/'))]]")
                
                if not items:
                    print("No listed items found (waiting for scroll)...")
                
                # Count newly scanned
                current_batch_new = 0
                
                for item in items:
                    if processed >= max_actions:
                        break
                    
                    try:
                        # Extract username
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
                            print(f"   -> Checked: {scanned_count} | Processed: {processed}")

                        # Verified Check (via DOM)
                        is_verified = False
                        if keep_verified:
                            try:
                                # Blue tick usually svg aria-label="Verified" or "Doğrulanmış"
                                svgs = item.find_elements(By.TAG_NAME, "svg")
                                for svg in svgs:
                                    aria = svg.get_attribute("aria-label") or ""
                                    if "Verified" in aria or "Doğrulanmış" in aria:
                                        is_verified = True
                                        break
                            except:
                                pass

                        # Decision Maker Check
                        if not self.guard.should_unfollow(uname, is_following_me=(uname in followers_set), min_days_followed=min_days, keep_verified=keep_verified, is_verified=is_verified):
                            continue
                        
                        print(f"Detected (Not following back): {uname}")
                        
                        # Find button
                        btn = None
                        
                        # Find button via JavaScript (More reliable)
                        try:
                            # This script scans buttons inside element and returns 'Following'/'Takiptesin' ones (not 'Follow')
                            btn = driver.execute_script("""
                                var item = arguments[0];
                                var buttons = item.getElementsByTagName('button');
                                for (var i = 0; i < buttons.length; i++) {
                                    var t = buttons[i].innerText || "";
                                    var tl = t.toLowerCase();
                                    
                                    // Positive check instead of negative (Safer)
                                    // To avoid clicking 'Message' button
                                    //# Takiptesin, Following, İstek, Requested
                                    # Also checks for Turkish 'takiptesin' etc. for compatibility
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
                                # 1. Attempt: Common texts
                                btn = item.find_element(By.XPATH, ".//button[contains(., 'Takiptesin') or contains(., 'Following') or contains(., 'İstek') or contains(., 'Requested')]")
                            except:
                                pass
                        
                        if btn:
                            try:
                                # Click operation
                                try:
                                    btn.click()
                                except:
                                    driver.execute_script("arguments[0].click();", btn)
                                
                                time.sleep(1) # Wait for modal to open
                                
                                # Confirm button - Find via JavaScript
                                confirm = None
                                try:
                                    confirm = driver.execute_script("""
                                        var dialogs = document.querySelectorAll("div[role='dialog']");
                                        if (dialogs.length == 0) return null;
                                        var dialog = dialogs[dialogs.length - 1]; // Last opened dialog
                                        var buttons = dialog.getElementsByTagName('button');
                                        for (var i = 0; i < buttons.length; i++) {
                                            var t = buttons[i].innerText || "";
                                            var tl = t.toLowerCase();
                                            // Wide check for Turkish characters
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
                                    print(f"SUCCESS: {uname} unfollowed.")
                                else:
                                    print(f"ERROR: Confirmation button not found for {uname}.")
                                    # If dialog is open, try to close it (Cancel)
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
                                    print("Operation blocked. Entering wait state.")
                                    return processed
                            except Exception as e:
                                print(f"Unfollow click error ({uname}): {e}")
                        else:
                            print(f"WARNING: 'Following' button not found for {uname}.")
                            pass
                            
                    except Exception as e:
                        continue
                
                # Scroll Logic (Inside loop)
                try:
                    # Find the last link in the dialog
                    last_link = dialog.find_elements(By.TAG_NAME, "a")[-1]
                    driver.execute_script("arguments[0].scrollIntoView(true);", last_link)
                except:
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                
                time.sleep(1 if turbo else 2)
                
                new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)
                if new_h == last_h:
                    # If scroll is stuck, try slightly up and then down again
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight - 200", dialog)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", dialog)
                    time.sleep(1)
                    new_h = driver.execute_script("return arguments[0].scrollHeight", dialog)

                if new_h == last_h:
                    scroll_attempts += 1
                    # If stuck, try PageDown
                    try:
                        dialog.click()
                        dialog.send_keys(Keys.PAGE_DOWN)
                    except: pass
                    
                    if scroll_attempts > 10: # Increased attempts from 4 to 10
                        print("Scroll limit reached.")
                        break
                    time.sleep(1)
                else:
                    scroll_attempts = 0
                    last_h = new_h
                    
        except Exception as e:
            print(f"Error processing Following list: {e}")
            
        print(f"Fast unfollow completed: {processed}")
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
            
        # Load Whitelist
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
        print(f"Target bulk unfollow count: {len(targets)}")
        for uname in targets:
            if max_actions is not None and done >= max_actions:
                break
            
            # Decision Maker Check (For time-based Unfollow)
            if not self.guard.should_unfollow(uname, is_following_me=False, min_days_followed=min_days):
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
                    print(f"Skipped (follows back): {uname}")
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
                        print(f"Skipped (not following): {uname}")
                        continue
                    except:
                        print(f"Follow status not detected: {uname}")
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
                    # Maybe it was "Requested" and got cancelled?
                    if btn and ("İstek" in (btn.text or "") or "Requested" in (btn.text or "")):
                        print(f"Request withdrawn: {uname}")
                    else:
                        print(f"Unfollow control not found: {uname}")
                        continue
                else:
                    try:
                        target.click()
                    except:
                        driver.execute_script("arguments[0].click()", target)
                
                self.log_action("UNFOLLOW", uname)
                done += 1
                if self.is_action_blocked():
                    print("Operation blocked. Entering wait state.")
                    break
                if fast and turbo:
                    self.turbo_delay()
                elif fast:
                    self.fast_delay()
                else:
                    self.rand_delay(True)
            except:
                continue
        print(f"Bulk unfollow completed: {done}")
        return done

    def parse_follower_count(self, text):
        """
        Converts texts like '1,234', '1.234', '10.5k', '10,5b', '1.2m', '10,5 B' to number.
        Supports both Turkish (B/M/K) and English (K/M).
        """
        if not text:
            return 0
        
        text = text.lower().strip()
        
        # Split words
        parts = text.split()
        if not parts:
            return 0
            
        clean_text = parts[0]
        
        # If 2nd part is a unit (K, M, B, Bin, Million etc.)
        if len(parts) > 1:
            suffix = parts[1]
            if suffix in ['k', 'm', 'b', 'mn', 'bn', 'bin', 'milyon']:
                clean_text += suffix
        
        text = clean_text
        
        # Pre-cleaning: Keep only digits, comma, dot and letters
        text = re.sub(r'[^0-9.,kmb]', '', text)
        
        if not text:
            return 0
            
        multiplier = 1
        
        # Suffix check
        if 'k' in text:
            multiplier = 1000
            text = text.replace('k', '')
        elif 'm' in text:
            multiplier = 1000000
            text = text.replace('m', '')
        elif 'b' in text: # b: bin (TR) or billion (EN) -> In Instagram B is usually Bin (in TR interface)
             # However, in TR interface "B" = Bin, in EN interface "B" = Billion.
             # Bot is usually TR focused but EN support is needed.
             # Simple solution: If number is small (10.5 B) -> Probably Bin.
             # If EN interface and 1B -> Billion.
             # For now assume TR "Bin".
            multiplier = 1000
            text = text.replace('b', '')
            
        try:
            # If multiplier > 1, it might have decimal separator.
            if multiplier > 1:
                text = text.replace(',', '.')
                val = float(text)
                return int(val * multiplier)
            else:
                # If no multiplier, it is an integer.
                text = text.replace('.', '').replace(',', '')
                return int(text)
        except:
            return 0

    def get_follower_count_from_meta(self):
        """Backup method: Get follower count from meta tags."""
        try:
            meta = self.driver.find_element(By.XPATH, "//meta[@property='og:description']")
            content = meta.get_attribute("content")
            if not content:
                return 0
            
            # Catch number and "Followers/Takipçi" word with regex
            match = re.search(r'([\d.,]+\s*[kmbKMB]?)\s+(?:Followers|Takipçi)', content, re.IGNORECASE)
            
            if match:
                return self.parse_follower_count(match.group(1))
            
            return 0
        except:
            return 0

    def get_user_stats_from_profile_page(self):
        """
        Parses the follower count from the profile page HTML.
        Returns: (follower_count, following_count)
        """
        try:
            # 1. Meta Tag Method (Fastest)
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

            # 2. In-Page Elements (Backup)
            # Usually ul > li > a or span inside header
            # XPATH: //header//ul/li[2]//span/@title (For Followers)
            # This part can be complex because the structure changes.
            
            return 0, 0
        except:
            return 0, 0

    def follow_users_by_criteria(self, hashtag, count=10, max_followers=3000):
        driver = self.driver
        driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        self.rand_delay(True)
        
        # Find and click the first post
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
                print("No posts found.")
                return

            processed_count = 0
            while processed_count < count:
                try:
                    # Find post owner's username
                    # Usually in an 'a' tag at the top of the post
                    # Let's try to find the Header part
                    header_link = driver.find_element(By.XPATH, "//header//a[not(contains(@href, '/explore/'))]")
                    profile_url = header_link.get_attribute("href")
                    
                    if profile_url:
                        # Open profile in new tab
                        driver.execute_script("window.open('');")
                        driver.switch_to.window(driver.window_handles[1])
                        driver.get(profile_url)
                        self.rand_delay()
                        
                        try:
                            # Find follower count
                            # Usually: <a href="/kullanici/followers/"><span>123</span> followers</a>
                            # or 2nd li in <ul><li>...</li></ul> structure
                            followers_element = None
                            try:
                                followers_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/followers/')]/span")))
                            except:
                                try:
                                    # Alternative structure
                                    followers_element = self.wait.until(EC.presence_of_element_located((By.XPATH, "//ul/li[2]/a/span")))
                                except:
                                    pass
                            
                            if followers_element:
                                count_text = followers_element.get_attribute("title")
                                if not count_text:
                                    count_text = followers_element.text
                                
                                follower_num = self.parse_follower_count(count_text)
                                print(f"Analyzing User: {profile_url} | Followers: {follower_num}")
                                
                                if follower_num > 0 and follower_num <= max_followers:
                                    # Follow
                                    try:
                                        if self.action_allowed("FOLLOW"):
                                            follow_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et') or contains(text(), 'Follow Back')]]")))
                                            follow_btn.click()
                                            print("   -> CRITERIA MATCH: Followed.")
                                            processed_count += 1
                                            self.log_action("FOLLOW", profile_url)
                                            self.rand_delay(True)
                                    except:
                                        print("   -> Follow button not found (Might be already followed).")
                                else:
                                    print("   -> Out of criteria (Follower count high or unreadable).")
                            else:
                                print("   -> Follower count element not reachable.")

                        except Exception as e:
                            print(f"Profile analysis error: {e}")
                        
                        # Close tab and return to main tab
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        
                    else:
                        print("User link not found.")

                except Exception as e:
                    print(f"Error processing post: {e}")
                    # Check tab even if error
                    if len(driver.window_handles) > 1:
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])

                # Move to next post
                try:
                    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.RIGHT)
                    self.rand_delay()
                except:
                    print("Could not move to next post.")
                    break

        except Exception as e:
            print(f"Error during hashtag operation: {e}")

    def follow_users_by_alphabet(self, letters="abcdefghijklmnopqrstuvwxyz", target_count=20, max_followers=None, min_followers=None, only_private=True, fast=True, randomize=True, turbo=False, avoid_known=True):
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
                            follow_btn = driver.find_element(By.XPATH, "//button[.//div[contains(text(), 'Follow') or contains(text(), 'Follow Back')]]")
                            follow_btn.click()
                            print(f"   -> Target: {username} | Followers: {fc} | Private: {ip}")
                            self.log_action("FOLLOW_ALPHA", username)
                            processed += 1
                            if fast and turbo:
                                self.turbo_delay()
                            elif fast:
                                self.fast_delay()
                            else:
                                self.rand_delay(True)
                            if self.is_action_blocked():
                                print("Operation blocked. Waiting.")
                                return processed
                    except:
                        if fast and turbo:
                            self.turbo_delay()
                        elif fast:
                            self.fast_delay()
                        else:
                            self.rand_delay()
        print(f"Total followed: {processed}")
        return processed

    def follow_random_users(self, target_count=20, max_followers=None, min_followers=None, only_private=False, fast=True, turbo=False, avoid_known=True, prefer_foreign=False):
        driver = self.driver
        processed = 0
        seen = set()
        alphabet = string.ascii_lowercase + string.digits
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
                        print(f"   -> Random: {username} | Followers: {fc} | Private: {ip}")
                        self.log_action("FOLLOW_ALPHA", username)
                        processed += 1
                        if fast and turbo:
                            self.turbo_delay()
                        elif fast:
                            self.fast_delay()
                        else:
                            self.rand_delay(True)
                        if self.is_action_blocked():
                            print("Action blocked. Entering wait state.")
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
                            print("Operation blocked. Waiting...")
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
        print(f"Total followed: {processed}")
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
        print("Combined follow completed.")

    def follow_smart_seeds(self, limit=20, criteria=None):
        """
        Finds real users from popular profiles (Seed) and follows them based on criteria.
        """
        driver = self.driver
        followed = 0
        processed = 0
        
        # Seed List (Popular Profiles - For active audience)
        seeds = ["danlabilic", "duyguozaslan", "seymasubasi", "handemiyy", "gamze_ercel", "neslihanatagul", "demetozdemir", "acunilicali", "cznburak", "hadise"]
        random.shuffle(seeds)
        
        print(f"Smart Follow Starting. Target: {limit}. Criteria: {criteria}")
        
        for seed_user in seeds:
            if followed >= limit:
                break
                
            print(f"\nScanning Source Profile: {seed_user}")
            try:
                # 1. Go to Profile
                self.browser_manager.navigate_to_profile(seed_user)
                time.sleep(random.uniform(2, 4))
                
                # 2. Collect Followers or Commenters
                # 70% chance commenters (more active), 30% followers
                users_to_check = []
                
                if random.random() < 0.7:
                    # Go to last post
                    try:
                        # Find first post (First link in Grid)
                        # Usually _aagw class is post thumbnail
                        try:
                            first_post = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, '_aagw')]")))
                            first_post.click()
                        except:
                            # Alternative selector
                            first_post = driver.find_element(By.TAG_NAME, "article").find_element(By.TAG_NAME, "a")
                            first_post.click()
                            
                        time.sleep(random.uniform(3, 5))
                        
                        # Open/load comments (Simply take what is visible)
                        # Find commenters in modal
                        # Usually username is in h3 or span
                        comment_elems = driver.find_elements(By.XPATH, "//ul//h3//div//span//a")
                        if not comment_elems:
                             comment_elems = driver.find_elements(By.XPATH, "//ul//h3//a")
                             
                        for el in comment_elems:
                            u = el.text
                            if u and u not in users_to_check and u != seed_user:
                                users_to_check.append(u)
                                
                        # Close modal (ESC or X button or click outside)
                        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        time.sleep(1)
                        print(f"   -> {len(users_to_check)} active users (commenters) found.")
                    except Exception as e:
                        print(f"   -> Post analysis error: {e}")
                        try:
                            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                        except: pass
                
                # If no commenters found or by chance checking followers
                if not users_to_check:
                    try:
                        # Open followers modal
                        users_set = self.scrape_modal_users("followers", limit=50, target_username=seed_user)
                        users_to_check = list(users_set)
                        print(f"   -> {len(users_to_check)} users (followers) collected.")
                    except Exception as e:
                        print(f"   -> Follower collection error: {e}")
                
                # 3. Analyze and Follow Found Users
                random.shuffle(users_to_check)
                
                for username in users_to_check:
                    if followed >= limit:
                        break
                        
                    # History check
                    if self.check_history(username):
                        continue
                        
                    processed += 1
                    print(f"[{processed}] Analysis: {username}")
                    
                    try:
                        # Go to profile
                        self.browser_manager.navigate_to_profile(username)
                        time.sleep(random.uniform(2, 4))
                        
                        # Collect Data
                        user_data = {
                            "username": username,
                            "fullname": "",
                            "bio": "",
                            "follower_count": 0,
                            "following_count": 0,
                            "is_private": False,
                            "is_verified": False
                        }
                        
                        # Follower Count Check (CRITICAL)
                        try:
                            # 2nd li element in header (followers)
                            # Can change, so checking aria-label or title is better but xpath is simple
                            f_elem = driver.find_element(By.XPATH, "//ul/li[2]//span")
                            f_title = f_elem.get_attribute("title")
                            if not f_title:
                                f_title = f_elem.text
                            
                            # Parse formats like "1.5M", "10K"
                            f_count = self.parse_follower_count(f_title)
                            user_data["follower_count"] = f_count
                            print(f"   -> Followers: {f_count}")
                        except:
                            print("   -> Follower count could not be read.")
                        
                        # Fullname and Bio
                        try:
                            if "(" in driver.title:
                                user_data["fullname"] = driver.title.split("(")[0].strip()
                            else:
                                user_data["fullname"] = driver.title.split("•")[0].strip()
                                
                            meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
                            if meta_desc:
                                user_data["bio"] = meta_desc
                        except: pass
                        
                        # Make Decision
                        if self.guard.should_follow(user_data, criteria):
                            print(f"   -> CRITERIA MATCH! Following...")
                            
                            # Follow Button
                            btn = self.browser_manager.find_following_button()
                            if btn:
                                print("   -> Already followed.")
                                self.log_action("FOLLOW", username)
                            else:
                                try:
                                    f_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")))
                                    f_btn.click()
                                    followed += 1
                                    self.log_action("FOLLOW", username)
                                    print(f"   -> SUCCESS. Total: {followed}/{limit}")
                                    time.sleep(random.uniform(25, 45))
                                except Exception as e:
                                    print(f"   -> Button click error: {e}")
                        else:
                            print("   -> Criteria mismatch (Follower count high or gender/nationality mismatch).")
                            
                    except Exception as e:
                        print(f"Profile error: {e}")
                        continue
                        
            except Exception as e:
                print(f"Seed error ({seed_user}): {e}")
                continue

    def post_comment(self, post_url, comment_text):
        """
        Comments on the specified post.
        """
        driver = self.driver
        w = WebDriverWait(driver, 10)
        
        try:
            if post_url and post_url != driver.current_url:
                driver.get(post_url)
                self.rand_delay()
                
            # Find comment area
            print(f"Commenting: '{comment_text}'")
            
            # 1. Find Textarea
            try:
                comment_box = w.until(EC.presence_of_element_located((By.TAG_NAME, "textarea")))
                comment_box.click()
                time.sleep(1)
                
                # Find again (sometimes changes after click)
                comment_box = driver.find_element(By.TAG_NAME, "textarea")
                
                # Write comment (with Humanizer)
                self.browser_manager.humanizer.type_like_human(comment_box, comment_text)
                time.sleep(1)
                
                # Find Share button
                # Usually "Post" or "Share" button near textarea
                post_btn = None
                try:
                    post_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Paylaş') or contains(text(), 'Post')]")
                except:
                    # Alternative: Form submit
                    pass
                    
                if post_btn:
                    post_btn.click()
                else:
                    comment_box.send_keys(Keys.ENTER)
                    
                print("✅ Comment sent.")
                self.log_action("COMMENT", post_url)
                self.rand_delay()
                return True
                
            except Exception as e:
                print(f"❌ Comment area not found or unwritable: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Comment operation error: {e}")
            return False

    def mass_follow_target(self, target_username, accounts_file="accounts.txt"):
        """
        Logs in with accounts from accounts.txt and follows target_username.
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
            
            print(f"Total {len(accounts)} accounts found.")
            
            # Close current browser (for clean start)
            self.driver.quit()

            for i, (acc_user, acc_pass) in enumerate(accounts):
                print(f"\n[{i+1}/{len(accounts)}] Logging in: {acc_user}")
                
                # Start new driver for each account (Best way for cookie cleanup)
                driver = self.browser_manager.build_driver()
                
                try:
                    driver.get("https://www.instagram.com/")
                    self.rand_delay()
                    
                    # Log In
                    try:
                        u_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "username")))
                        self.browser_manager.humanizer.type_like_human(u_input, acc_user)
                        p_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "password")))
                        self.browser_manager.humanizer.type_like_human(p_input, acc_pass)
                        p_input.send_keys(Keys.ENTER)
                        self.rand_delay(True)
                        
                        # Check if login successful (URL changed or profile icon present)
                        if "accounts/login" in driver.current_url:
                            print(f"   -> Login failed (Wrong password or checkpoint).")
                            driver.quit()
                            continue
                            
                        # Go to target profile
                        driver.get(f"https://www.instagram.com/{target_username}/")
                        self.rand_delay()
                        
                        # Find and click Follow button
                        try:
                            # Covers Follow, Follow Back buttons
                            follow_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow') or contains(text(), 'Geri Takip Et')]]")))
                            follow_btn.click()
                            print(f"   -> SUCCESS: {target_username} followed.")
                            self.log_action("FOLLOW", target_username)
                            self.rand_delay()
                        except:
                            print(f"   -> Follow button not found (Might be already followed).")
                            
                    except Exception as e:
                        print(f"   -> Operation error: {e}")
                        
                except Exception as e:
                    print(f"   -> Browser error: {e}")
                
                finally:
                    driver.quit()
                    # Wait between accounts
                    self.rand_delay(True)

            # Program ends after operation.
            print("\nMass follow operation completed.")
            
        except FileNotFoundError:
            print(f"{accounts_file} file not found.")
        except Exception as e:
            print(f"General error: {e}")

if __name__ == "__main__":
    try:
        print("Bot starting...")
        
        print("\n" + "="*50)
        print("INSTAGRAM SMART ASSISTANT v2.0")
        print("="*50)
        print("1. 🚀 START SMART ASSISTANT (Recommended)")
        print("   (Performs follow, like, unfollow and analysis for you)")
        print("2. 🛠️ Manual Tools (Advanced)")
        print("   (Opens legacy menu)")
        
        main_choice = input("Choice (1-2): ")
        
        mode = "13" # Default AI mode
        
        if main_choice == "2":
            print("\n" + "="*50)
            print("MANUAL TOOLS MENU")
            print("="*50)
            print("1 - Like by Hashtag")
            print("2 - Like + Follow by Hashtag (Standard)")
            print("3 - Unfollow Non-Followers")
            print("4 - Filtered Follow (Low/Mid Follower Count Only)")
            print("5 - Follow Me with Side Accounts (needs accounts.txt)")
            print("6 - Like + Comment + Follow by Hashtag (Full Pack)")
            print("7 - Follow Users by Alphabet")
            print("8 - Follow Random Users")
            print("9 - Combined (Alphabet + Random) Super Speed")
            print("10 - Automatic (Smart - Legacy)")
            print("11 - Fast Bulk Unfollow (Index Based)")
            print("12 - Target Profile Followers (Fast & Unfiltered)")
            
            mode = input("Choice (1-12): ")
        
        if mode == "5":
            target_user = input("Username to follow (e.g. your username): ")
            # No login needed for this mode here
            bot = InstagramBot("dummy", "dummy")
            bot.driver.quit() 
            bot.mass_follow_target(target_user)
            bot.print_summary()
            
        elif mode in ["1", "2", "3", "4", "6", "7", "8", "9", "10", "11", "12", "13"]:
            # Login required
            bot = InstagramBot(config.USERNAME, config.PASSWORD)
            bot.login()
            
            input("Press Enter after logging in and clearing pop-ups...")
            
            if mode == "1" or mode == "2" or mode == "6":
                hashtag = input("Enter hashtag to interact with (without #): ")
                count_input = input("How many posts to interact with?: ")
                
                do_follow = False
                do_comment = False
                
                if mode == "2":
                    do_follow = True
                    print("WARNING: Follow mode selected. Operation times will be extended to avoid bans.")
                elif mode == "6":
                    do_follow = True
                    do_comment = True
                    print("WARNING: Full Pack selected (Like+Comment+Follow). Operation times will be longer.")
                
                if count_input.isdigit():
                    count = int(count_input)
                    bot.like_photos_by_hashtag(hashtag, count, follow=do_follow, comment=do_comment)
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid number.")
                    
            elif mode == "3":
                print("\nWARNING: This operation scans your 'Following' list.")
                print("Finds and unfollows users who don't follow you back.")
                print("Too many actions may cause your account to be restricted.")

                # Whitelist
                add_wl = input("Add users to Whitelist (Do not unfollow)? (Y/n): ").strip().lower()
                if add_wl in ["y", "yes"]:
                    to_add = input("Enter usernames separated by commas: ")
                    count_wl = 0
                    for u in to_add.split(","):
                         if u.strip():
                            bot.guard.add_to_whitelist(u)
                            count_wl += 1
                    print(f"{count_wl} users added to whitelist.")
                
                method_input = input("Which method?\n1 - Classic (Visit profiles - Slow/Safe)\n2 - Fast/Batch (Scan list - Much Faster)\n3 - Algorithmic (Full Analysis - Most Safe)\nChoice (1/2/3): ").strip()
                
                min_days_input = input("Unfollow only if followed for min X days? (e.g. 3, All: 0): ").strip()
                min_days = int(min_days_input) if min_days_input.isdigit() else 0

                keep_verified_input = input("Keep Verified (Blue Tick) accounts? (Y/n): ").strip().lower()
                keep_verified = True if keep_verified_input in ["", "y", "yes"] else False
                
                keep_min_followers = 0
                if method_input != "2":
                     kmf_input = input("Keep accounts with min followers? (Popular protection - e.g. 10000, None: 0): ").strip()
                     keep_min_followers = int(kmf_input) if kmf_input.isdigit() else 0
                else:
                     print("Info: Follower count check not available in Fast Mode (Only Blue Tick can be protected).")

                if method_input == "2":
                    # Fast Mode
                    check_all_input = input("Check all following? (Y/n): ").strip().lower()
                    if check_all_input in ["", "y", "yes"]:
                        count = 999999
                        print("Full list will be scanned (Limit: Unlimited).")
                    else:
                        c_in = input("How many people to check?: ")
                        count = int(c_in) if c_in.isdigit() else 300
                    
                    fast_mode_input = input("Enable Fast Wait Mode? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Enable Super Speed (Turbo)? (Y/n): ").strip().lower()
                    
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    
                    print("Starting fast scan and unfollow...")
                    bot.fast_modal_unfollow_nonfollowers(max_actions=count, fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified)
                    print("Operation completed.")
                    bot.print_summary()
                    
                elif method_input == "3":
                    # Algorithmic Mode
                    fast_mode_input = input("Enable fast mode? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Enable Super Speed? (Y/n): ").strip().lower()
                    fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                    turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                    
                    bot.algorithm_based_unfollow(fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified, keep_min_followers=keep_min_followers)
                    print("Operation completed.")
                    bot.print_summary()
                    
                else:
                    # Classic Mode
                    count_input = input("How many to check? (Recommended: 20-50): ")
                    only_nonfollowers_input = input("Unfollow only those who don't follow back? (Y/n): ").strip().lower()
                    whitelist_use_input = input("Use whitelist.txt exceptions? (Y/n): ").strip().lower()
                    fast_mode_input = input("Enable fast mode? (Y/n): ").strip().lower()
                    turbo_mode_input = input("Enable Super Speed (very short waits)? (Y/n): ").strip().lower()
                    
                    if count_input.isdigit():
                        count = int(count_input)
                        only_nf = True if only_nonfollowers_input in ["", "y", "yes"] else False
                        use_wl = True if whitelist_use_input in ["", "y", "yes"] else False
                        fast_mode = True if fast_mode_input in ["", "y", "yes"] else False
                        turbo_mode = True if turbo_mode_input in ["", "y", "yes"] else False
                        bot.unfollow_non_followers(count, only_nonfollowers=only_nf, use_whitelist=use_wl, fast=fast_mode, turbo=turbo_mode, min_days=min_days, keep_verified=keep_verified, keep_min_followers=keep_min_followers)
                        print("Operation completed.")
                        bot.print_summary()
                    else:
                        print("Please enter a valid number.")

            elif mode == "4":
                print("\nThis mode visits profiles from hashtag and checks follower count.")
                print("Follows if follower count is below your limit.")
                
                hashtag = input("Enter target hashtag (without #): ")
                count_input = input("How many users to FOLLOW? (Successful follows, not attempts): ")
                max_followers_input = input("Max follower count? (e.g. 3000): ")
                
                if count_input.isdigit() and max_followers_input.isdigit():
                    count = int(count_input)
                    max_f = int(max_followers_input)
                    bot.follow_users_by_criteria(hashtag, count, max_followers=max_f)
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter valid numbers.")
            elif mode == "7":
                letters_input = input("Alphabet (default: abc...): ").strip()
                if not letters_input:
                    letters_input = "abcdefghijklmnopqrstuvwxyz"
                target_input = input("How many users to follow?: ")
                max_followers_input = input("Max follower limit (optional): ")
                min_followers_input = input("Min follower limit (optional): ")
                only_private_input = input("Follow only private profiles? (Y/n): ").strip().lower()
                fast_mode_input = input("Enable fast mode (shorter waits)? (Y/n): ").strip().lower()
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
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid number.")
            elif mode == "8":
                target_input = input("How many users to follow?: ")
                max_followers_input = input("Max follower limit (optional): ")
                min_followers_input = input("Min follower limit (optional): ")
                only_private_input = input("Follow only private profiles? (Y/n): ").strip().lower()
                fast_mode_input = input("Enable fast mode (shorter waits)? (Y/n): ").strip().lower()
                turbo_mode_input = input("Enable Super Speed (Turbo)? (Y/n): ").strip().lower()
                foreign_input = input("Prefer foreign users? (Y/n): ").strip().lower()
                region_input = input("Region (NA/EU/APAC/LATAM/MENA, empty: global): ").strip().upper()
                min_posts_input = input("Min post count (optional, rec: 5): ").strip()
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
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid number.")
            elif mode == "9":
                letters_input = input("Alphabet (default: abc...): ").strip()
                if not letters_input:
                    letters_input = "abcdefghijklmnopqrstuvwxyz"
                target_input = input("Total users to follow?: ")
                max_followers_input = input("Max follower limit (optional): ")
                min_followers_input = input("Min follower limit (optional): ")
                only_private_input = input("Follow only private profiles? (Y/n): ").strip().lower()
                fast_mode_input = input("Enable fast mode (shorter waits)? (Y/n): ").strip().lower()
                turbo_mode_input = input("Enable Super Speed (Turbo)? (Y/n): ").strip().lower()
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
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid number.")
            elif mode == "10":
                target_input = input("Total actions? (Rec: 30): ").strip()
                region_input = input("Region focus (NA/EU/APAC/LATAM/MENA): ").strip().upper()
                if target_input.isdigit():
                    total = int(target_input)
                    region = region_input if region_input in ["NA","EU","APAC","LATAM","MENA"] else "EU"
                    bot.autopilot(total=total, region=region)
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid number.")
            elif mode == "11":
                build_input = input("Build indexes first? (Y/n): ").strip().lower()
                fast_mode_input = input("Enable fast mode? (Y/n): ").strip().lower()
                turbo_mode_input = input("Enable Super Speed? (Y/n): ").strip().lower()
                
                min_days_input = input("Unfollow only if followed for min X days? (e.g. 3, All: 0): ").strip()
                min_days = int(min_days_input) if min_days_input.isdigit() else 0

                confirm_input = input("Unfollow all non-followers? (Y/n): ").strip().lower()
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
                    print("Operation cancelled.")
                print("Operation completed.")
                bot.print_summary()
            elif mode == "12":
                print("\nTHIS MODE: Target Profile Followers (Fast & Unfiltered)")
                print("Enters follower list of target profile and follows sequentially.")
                
                target_username = input("Target Profile (Username): ").strip()
                limit_input = input("How many to FOLLOW?: ")
                
                if target_username and limit_input.isdigit():
                    bot.follow_target_followers(target_username, int(limit_input))
                    
                    print("Operation completed.")
                    bot.print_summary()
                else:
                    print("Please enter a valid username and number.")

            elif mode == "13":
                print("\nTHIS MODE: AI Smart Management Mode")
                print("Bot works by making its own decisions via AI.")
                print("Continuous mode, press CTRL+C to stop.")
                
                try:
                    bot.ai_manager.start_smart_mode()
                except KeyboardInterrupt:
                    print("\nAI Mode stopped by user.")
                except Exception as e:
                    print(f"AI Mode Error: {e}")

        else:
            print("Invalid choice.")
            
    except Exception as e:
        print(f"\nAN ERROR OCCURRED:\n{e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\nPress Enter to close program...")
        # bot.close_browser()
        input("\nPress Enter to close program...")
        # bot.close_browser()
