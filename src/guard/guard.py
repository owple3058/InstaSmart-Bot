import datetime
import os
import sys
import time
from selenium.webdriver.common.by import By

# To import config module from main directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import config
except ImportError:
    import config
    
from src.utils.profile_analyzer import ProfileAnalyzer
from src.logger.logger import logger

class Guard:
    def __init__(self, database):
        self.db = database
        self.whitelist = self.load_whitelist()
        self.analyzer = ProfileAnalyzer()
        
        # Risk Layer State
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.suspicious_mode = False
        self.suspicious_cooldown = 0
        self.error_history = []
        self.ui_change_detected = False

    def load_whitelist(self):
        """Loads the whitelist.txt file."""
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
        """Checks if the user is in the whitelist."""
        return username.lower() in self.whitelist

    def report_error(self, error_msg):
        """
        Reports an error to the Guard.
        If errors accumulate, triggers Suspicious Mode.
        """
        self.consecutive_errors += 1
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.error_history.append(f"[{timestamp}] {error_msg}")
        
        logger.error(f"Guard: Error reported", 
                     error_msg=error_msg, 
                     consecutive_errors=self.consecutive_errors, 
                     max_errors=self.max_consecutive_errors)
        
        if self.consecutive_errors >= self.max_consecutive_errors:
            self.trigger_suspicious_mode("Too many consecutive errors")

    def report_success(self):
        """
        Resets error counter on successful action.
        """
        if self.consecutive_errors > 0:
            logger.info("Guard: Error counter reset", previous_errors=self.consecutive_errors)
            self.consecutive_errors = 0

    def trigger_suspicious_mode(self, reason):
        """
        Activates suspicious mode (stops actions).
        """
        if not self.suspicious_mode:
            logger.warning("GUARD: SUSPICIOUS MODE ACTIVATED!", reason=reason, action="SUSPEND_BOT")
            self.suspicious_mode = True
            self.suspicious_cooldown = time.time() + (30 * 60) # 30 Minutes cooldown

    def check_ui_change(self, driver):
        """
        Checks for major UI changes (e.g., popups, different layouts).
        """
        try:
            # Check for "Unusual Login Attempt" or "Verify it's you"
            src = driver.page_source.lower()
            if "verify it's you" in src or "bize sen olduğunu onayla" in src:
                self.trigger_suspicious_mode("Verification Screen Detected")
                return True
            
            if "automated behavior" in src or "otomasyon davranışı" in src:
                self.trigger_suspicious_mode("Automation Warning Detected")
                return True

            return False
        except:
            return False

    def is_safe_to_proceed(self):
        """
        Global check before any action.
        """
        if self.suspicious_mode:
            remaining = int(self.suspicious_cooldown - time.time())
            if remaining > 0:
                logger.info("Guard: Bot is in Suspicious Mode. Waiting...", remaining_seconds=remaining)
                return False
            else:
                logger.success("Guard: Suspicious Mode cooldown ended. Resuming carefully.")
                self.suspicious_mode = False
                self.consecutive_errors = 0
                return True
        return True

    def action_allowed(self, action):
        """Checks if the action is allowed based on daily limits AND risk state."""
        # 0. Safety First
        if not self.is_safe_to_proceed():
            return False

        # 1. Daily Limits
        max_map = {
            "LIKE": getattr(config, "MAX_LIKES_PER_DAY", 150),
            "FOLLOW": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "COMMENT": getattr(config, "MAX_COMMENTS_PER_DAY", 60),
            "FOLLOW_ALPHA": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "FOLLOW_FROM_POST": getattr(config, "MAX_FOLLOWS_PER_DAY", 100),
            "UNFOLLOW": getattr(config, "MAX_UNFOLLOWS_PER_DAY", 120),
        }
        max_allowed = max_map.get(action, 1000)
        
        # Get today's action count from database
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        stats = self.db.get_stats(today)
        
        if not stats:
            return True # Allow if no record yet
            
        # stats table structure: date, likes, follows, unfollows, comments
        # indexes: 0: date, 1: likes, 2: follows, 3: unfollows, 4: comments
        
        current_count = 0
        if action == "LIKE":
            current_count = stats[1]
        elif "FOLLOW" in action: # FOLLOW, FOLLOW_ALPHA, FOLLOW_FROM_POST
            current_count = stats[2]
        elif action == "UNFOLLOW":
            current_count = stats[3]
        elif action == "COMMENT":
            current_count = stats[4]
            
        if current_count >= max_allowed:
            logger.warning("Guard: Daily limit reached", action=action, current=current_count, limit=max_allowed)
            return False
            
        return True

    def add_to_whitelist(self, username):
        """Adds a user to the whitelist and updates the file."""
        username = username.strip().lower()
        if not username:
            return
        
        self.whitelist.add(username)
        
        try:
            with open("whitelist.txt", "a", encoding="utf-8") as f:
                f.write(f"\n{username}")
        except Exception as e:
            logger.error(f"Could not write to whitelist file", error=str(e))

    def should_unfollow(self, username, is_following_me, min_days_followed=None, keep_verified=False, is_verified=False, keep_min_followers=0, follower_count=0, ignore_relationship=False):
        """Decides whether to unfollow a user."""
        # 1. Whitelist Check
        if self.is_whitelisted(username):
            return False
            
        # 2. If following me and policy is "don't delete followers" (default)
        if is_following_me and not ignore_relationship:
            return False

        # 3. Duration Check (Smart Unfollow)
        if min_days_followed and min_days_followed > 0:
            follow_time = self.db.get_follow_timestamp(username)
            if follow_time:
                days_diff = (datetime.datetime.now() - follow_time).days
                if days_diff < min_days_followed:
                    return False
            else:
                pass
        
        # 4. Verified Check
        if keep_verified and is_verified:
            return False
            
        # 5. Follower Count Check (Protect popular accounts)
        if keep_min_followers > 0 and follower_count > keep_min_followers:
            return False
            
        return True

    def should_follow(self, user_data, criteria=None):
        """
        Decides whether to follow a user.
        """
        # 1. Numerical Criteria (Config)
        min_followers = getattr(config, "MIN_FOLLOWER_COUNT", 50)
        max_followers = getattr(config, "MAX_FOLLOWER_COUNT", 5000)
        
        if criteria:
            if "max_followers" in criteria:
                max_followers = criteria["max_followers"]
            if "min_followers" in criteria:
                min_followers = criteria["min_followers"]
        
        if user_data.get("follower_count", 0) < min_followers:
            logger.info("Guard: Rejecting follow", reason="low_followers", 
                        current=user_data.get('follower_count', 0), min=min_followers)
            return False
            
        if user_data.get("follower_count", 0) > max_followers:
            logger.info("Guard: Rejecting follow", reason="high_followers", 
                        current=user_data.get('follower_count', 0), max=max_followers)
            return False
            
        # 3. Ratio Check (Spam/Bot Analysis)
        # If following / followers ratio is too high (e.g. 200 followers, 5000 following), likely spam.
        followers = user_data.get("follower_count", 1)
        following = user_data.get("following_count", 0)
        
        if followers > 0:
            ratio = following / followers
            if ratio > 5.0: # If following is 5x followers
                logger.info("Guard: Rejecting follow", reason="spam_suspected_ratio", ratio=round(ratio, 2))
                return False
                
        # 4. Advanced Profile Analysis (Gender and Nationality)
        if criteria:
            analysis = self.analyzer.analyze(user_data)
            logger.debug("Guard: Profile Analysis", gender=analysis['gender'], nationality=analysis['nationality'])
            
            # Gender Filter
            target_gender = criteria.get("gender")
            if target_gender:
                if analysis["gender"] != target_gender and analysis["gender"] != "unknown":
                    logger.info("Guard: Rejecting follow", reason="gender_mismatch", 
                                wanted=target_gender, found=analysis['gender'])
                    return False
                if analysis["gender"] == "unknown":
                    # Optional: Skip if unknown?
                    logger.info("Guard: Rejecting follow", reason="gender_unknown")
                    return False

            # Nationality Filter
            target_nationality = criteria.get("nationality")
            if target_nationality:
                if analysis["nationality"] != target_nationality and analysis["nationality"] != "unknown":
                    return False
                if analysis["nationality"] == "unknown" and target_nationality == "turkish":
                    # If no Turkish chars and Turkish wanted, risky.
                    return False
                    
        return True
