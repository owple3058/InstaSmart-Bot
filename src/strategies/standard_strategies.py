from .strategy_base import Strategy
import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

class LikeHashtagStrategy(Strategy):
    """
    Strategy to like photos by hashtag.
    """
    def execute(self, hashtag, amount=5, follow=False, comment=False):
        driver = self.bot.driver
        print(f"Executing LikeHashtagStrategy for #{hashtag}...")
        
        url = f"https://www.instagram.com/explore/tags/{hashtag}/"
        driver.get(url)
        self.bot.rand_delay(True)

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
                self.bot.rand_delay()
            else:
                print("No posts found.")
                return

            for i in range(amount):
                # Get post URL (for logging)
                current_url = driver.current_url
                
                # History check
                if self.bot.check_history(current_url):
                    print(f"Post {i+1} processed before. Skipping.")
                else:
                    # 1. LIKE OPERATION
                    try:
                        if self.bot.action_allowed("LIKE"):
                            like_button = self.bot.wait.until(EC.element_to_be_clickable((By.XPATH, "//span/*[name()='svg' and (@aria-label='Beğen' or @aria-label='Like')]/..")))
                            
                            # Perform Action (Dry Run aware)
                            if self.bot.perform_action("LIKE", like_button, info={"url": current_url}):
                                print(f"Post {i+1} liked.")
                                self.bot.log_action("LIKE", current_url)
                                if self.bot.is_action_blocked():
                                    print("Action blocked. Waiting.")
                                    return
                    except Exception:
                        print(f"Post {i+1} might have been liked already.")

                    # 2. COMMENT OPERATION
                    if comment:
                        try:
                            if self.bot.guard.action_allowed("COMMENT"):
                                comment_text = self.bot.get_random_comment()
                                comment_area = self.bot.wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Yorum ekle...' or @aria-label='Add a comment…']")))
                                comment_area.click()
                                self.bot.rand_delay()
                                comment_area = self.bot.wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label='Yorum ekle...' or @aria-label='Add a comment…']")))
                                self.bot.browser_manager.humanizer.type_like_human(comment_area, comment_text)
                                self.bot.rand_delay()
                                
                                # Dry Run Check for Comment
                                if self.bot.dry_run:
                                    print(f"DRY RUN: Would post comment '{comment_text}'")
                                else:
                                    comment_area.send_keys(Keys.ENTER)
                                    print(f"   -> Commented: {comment_text}")
                                    self.bot.log_action("COMMENT", current_url)
                                
                                self.bot.rand_delay()
                                if self.bot.is_action_blocked():
                                    print("Action blocked. Waiting.")
                                    return
                        except Exception as e:
                            print(f"   -> Could not comment.")

                    # 3. FOLLOW OPERATION (If requested)
                    if follow:
                        try:
                            if self.bot.guard.action_allowed("FOLLOW"):
                                # Check for Follow button in the post modal header
                                # XPath searches for button containing 'Follow' or 'Takip Et'
                                follow_btn = None
                                try:
                                    follow_btn = driver.find_element(By.XPATH, "//header//button[.//div[contains(text(), 'Follow') or contains(text(), 'Takip Et')]]")
                                except:
                                    # Fallback: sometimes text is directly in button
                                    try:
                                        follow_btn = driver.find_element(By.XPATH, "//header//button[contains(., 'Follow') or contains(., 'Takip Et')]")
                                    except:
                                        pass
                                
                                if follow_btn:
                                    if self.bot.perform_action("FOLLOW", follow_btn, info={"context": "from_post"}):
                                        print(f"   -> Followed owner of post.")
                                        self.bot.log_action("FOLLOW", current_url)
                                    self.bot.rand_delay()
                                else:
                                    # Might be already following
                                    pass
                        except Exception as e:
                            print(f"   -> Could not follow: {e}")
                
                # Next Post
                try:
                    next_btn = driver.find_element(By.XPATH, "//div[@class=' _aaqg _aaqh']//button")
                    next_btn.click()
                    time.sleep(random.uniform(2, 4))
                except:
                    print("Next button not found or end of posts.")
                    break

        except Exception as e:
            print(f"Error in LikeHashtagStrategy: {e}")

class FollowStrategy(Strategy):
    """
    Strategy to follow users.
    """
    def execute(self, target_user, amount=10):
        print(f"Executing FollowStrategy for target: {target_user}")
        driver = self.bot.driver
        wait = self.bot.wait
        
        # REAL INCREASE: Daily actions should be fluctuating (Limit +/- 10%)
        variance = int(amount * 0.10)
        actual_limit = amount + random.randint(-variance, variance)
        if actual_limit < 1: actual_limit = 1
        
        print(f"Target Profile: {target_user}")
        print(f"Target Follow (Fluctuating): ~{amount} (Planned: {actual_limit})")
        
        try:
            # 1. Go to Profile
            self.bot.browser_manager.navigate_to_profile(target_user)
            
            # 2. Click Followers button
            try:
                # Find link containing "/followers/"
                f_link = wait.until(EC.element_to_be_clickable((By.XPATH, f"//a[contains(@href, '/followers/')]")))
                f_link.click()
            except:
                print("Follower list could not be opened (Private profile or no button).")
                return

            # 3. Detect List Structure (Modal vs Full Page)
            dialog = None
            scrollable_element = None
            is_full_page = False

            try:
                # A) Modal Dialog Check
                # Wait for dialog to open (Max 5 sec)
                # We use a temporary wait here to avoid hanging too long
                from selenium.webdriver.support.ui import WebDriverWait
                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']")))
                
                dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
                print("   -> Modal view detected.")
                
                # Find scrollable area (via JS)
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
                # B) Full Page Check
                if "/followers" in driver.current_url or "/following" in driver.current_url:
                    print("   -> Full page view detected.")
                    is_full_page = True
                    dialog = driver.find_element(By.TAG_NAME, "body") # Search buttons on full page
                else:
                    print("Modal dialog or list page not found.")
                    return

            followed_count = 0
            consecutive_no_buttons = 0
            last_scroll_pos = -1
            same_scroll_count = 0
            
            while followed_count < actual_limit:
                # Check limits first
                if not self.bot.guard.action_allowed("FOLLOW"):
                    print("Follow limit reached (Guard).")
                    break

                # Scroll position check (To detect end of list)
                try:
                    if is_full_page:
                        current_pos = driver.execute_script("return window.pageYOffset;")
                    else:
                        current_pos = driver.execute_script("return arguments[0].scrollTop;", scrollable_element)
                    
                    if current_pos == last_scroll_pos:
                        same_scroll_count += 1
                        if same_scroll_count > 15: # If stuck for 15 turns (tolerant for load delays)
                            print("End of list reached (Scroll not moving), exiting.")
                            break
                    else:
                        same_scroll_count = 0
                        last_scroll_pos = current_pos
                except:
                    pass

                try:
                    # Find buttons (Takip Et / Follow / Takiptesin / Following)
                    buttons = dialog.find_elements(By.XPATH, ".//button[.//div[contains(text(), 'Takip') or contains(text(), 'Follow')]]")
                except:
                    buttons = []
                
                # If no buttons, scroll
                if not buttons:
                    consecutive_no_buttons += 1
                    if consecutive_no_buttons > 20:
                        print("End of list reached or no buttons found, exiting.")
                        break
                        
                    if is_full_page:
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    else:
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                    time.sleep(1.5)
                    continue
                else:
                    consecutive_no_buttons = 0

                # Random Scroll (Skip)
                if random.random() < 0.10:
                     print("   -> Random: Scrolling list (Skipping)...")
                     if is_full_page:
                         driver.execute_script("window.scrollBy(0, 600);")
                     else:
                         driver.execute_script("arguments[0].scrollTop += 600;", scrollable_element)
                     time.sleep(random.uniform(0.5, 1.0))
                     continue

                for btn in buttons:
                    if followed_count >= actual_limit:
                        break
                    
                    try:
                        # Check if already followed
                        txt = (btn.text or "").lower()
                        
                        # 1. Negative Check: Skip if already followed
                        if "takiptesin" in txt or "following" in txt or "istek" in txt or "requested" in txt:
                            continue
                            
                        # 2. Positive Check: Only 'Takip' or 'Follow'
                        if "takip" not in txt and "follow" not in txt:
                            continue
                            
                        # RANDOMNESS: 50% chance to skip this person
                        if random.random() < 0.50:
                            continue

                        # Visibility
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                        time.sleep(0.3) 
                        
                        # Click Follow
                        if self.bot.guard.action_allowed("FOLLOW"):
                            if self.bot.perform_action("FOLLOW", btn, info={"context": "batch_follow"}):
                                followed_count += 1
                                print(f"[{followed_count}/{actual_limit}] Followed.")
                                self.bot.log_action("FOLLOW", driver.current_url) 
                            
                            # Speed (Old: 3-7 sec -> New: 1-2 sec)
                            time.sleep(random.uniform(1, 2))
                        else:
                            print("Follow limit reached during batch.")
                            return
                        
                    except Exception:
                        pass
                
                # Scroll after batch
                if is_full_page:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                else:
                    if buttons:
                        try:
                            last_btn = buttons[-1]
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_btn)
                        except:
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                    else:
                        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable_element)
                
                time.sleep(random.uniform(1.5, 2.0))
                
        except Exception as e:
            print(f"Error in FollowStrategy: {e}")
