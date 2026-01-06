import time
import random
import datetime
import sys
import os

# To import config module from root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import config
except ImportError:
    import config

from src.utils.profile_analyzer import ProfileAnalyzer

class AIManager:
    """
    AI Manager:
    Main control mechanism that manages all bot actions intelligently, calculates limits,
    and exhibits human-like behavior.
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
        self.energy = 100 # Starts with 100% Energy
        self.strategy = None # User choice
        self.target_profile = None # Target profile (optional)
        self.unfollow_mode = "non_followers" # Default unfollow mode
        self.niche_tags = [] # User interests
        
    def start_smart_mode(self):
        """
        Starts AI Mode.
        Selects and applies the most logical action in a continuous loop.
        """
        print("\n" + "="*50)
        print("🤖 AI MANAGEMENT PANEL (ADVANCED v2.2)")
        print("="*50)
        
        # User Niche Input
        print("Please enter your interests or target audience separated by commas.")
        print("E.g.: fitness, software, travel, fashion, food")
        niche_input = input("Interests (Leave empty for general mode): ").strip()
        if niche_input:
            self.niche_tags = [t.strip() for t in niche_input.split(",") if t.strip()]
            print(f"✅ Interests saved: {', '.join(self.niche_tags)}")
        else:
            print("ℹ️ Continuing in general mode.")

        print("\nPlease set a priority for AI:")
        print("1 - Follow Focus (Hashtag/Explore Analysis)")
        print("2 - Like Focus (Increase Interaction)")
        print("3 - Unfollow / Cleanup (Remove Non-followers)")
        print("4 - Target Profile Analysis and Follow (Competitor Analysis)")
        print("5 - Comment Focus (Interaction and Visibility)")
        print("6 - Fully Autonomous (Let AI Decide - Hybrid Mode)")
        print("7 - Super Fan Mode (Story + Like + Follow) [NEW]")
        
        choice = input("\nYour Choice (1-7): ").strip()
        
        if choice == "1":
            self.strategy = "FOLLOW_FOCUS"
            print("✅ Mode Selected: Follow Focus")
        elif choice == "2":
            self.strategy = "LIKE_FOCUS"
            print("✅ Mode Selected: Like Focus")
        elif choice == "3":
            self.strategy = "UNFOLLOW_FOCUS"
            print("✅ Mode Selected: Cleanup Focus")
            
            # Sub Options
            print("\nCleanup Type:")
            print("1 - Only Non-Followers (Traitors) [Recommended]")
            print("2 - Delete Everyone (Except Whitelist)")
            
            sub_choice = input("Your Choice (1-2): ").strip()
            if sub_choice == "2":
                self.unfollow_mode = "all"
                print("⚠️ WARNING: Everyone except whitelist will be removed!")
            else:
                self.unfollow_mode = "non_followers"
                print("👍 Only non-followers will be removed.")

        elif choice == "4":
            self.strategy = "TARGET_FOCUS"
            self.target_profile = input("Target Profile (Username): ").strip()
            print(f"✅ Mode Selected: {self.target_profile} will be analyzed.")
        elif choice == "5":
            self.strategy = "COMMENT_FOCUS"
            print("✅ Mode Selected: Comment Focus")
        elif choice == "7":
            self.strategy = "SUPER_FAN"
            print("✅ Mode Selected: Super Fan Mode (High Interaction)")
        else:
            self.strategy = "AUTO"
            print("✅ Mode Selected: Fully Autonomous")

        print("\nSystem analysis in progress and operations starting...")
        print("="*50 + "\n")
        
        consecutive_low_activity = 0
        total_actions_session = 0
        
        while True:
            # 0. System Health Check (NEW)
            health = self.bot.browser_manager.check_system_health()
            if health != "OK":
                if health == "BLOCKED":
                    print("🛑 CRITICAL: Instagram action block detected. Stopping bot.")
                    break
                elif health == "NO_NET":
                    print("⚠️ Internet connection lost. Waiting 60 seconds...")
                    time.sleep(60)
                    continue

            # 1. State Analysis
            action = self.decide_next_action()
            
            if action == "SLEEP":
                self.take_smart_break()
                continue
                
            if action == "STOP":
                print("🛑 Daily limits or energy depleted. Terminating operation.")
                break
            
            # 2. Execute Action
            print(f"\n🔄 Loop Starting (Action: {action})")
            result = self.execute_action(action)
            total_actions_session += result
            
            # Inefficiency Check
            if result == 0:
                consecutive_low_activity += 1
            else:
                consecutive_low_activity = 0
                
            if consecutive_low_activity >= 3:
                print("\n⚠️ No actions performed 3 times in a row. Bot is taking a break or stopping.")
                if self.strategy == "UNFOLLOW_FOCUS":
                    print("🛑 Cleanup completed or cannot be performed. Exiting.")
                    break
                else:
                    self.take_smart_break()
                    consecutive_low_activity = 0 # Reset and continue
            
            # 3. Update Energy and State
            self.update_state()
            
            # 4. Loop Control (Stop if cleanup finished)
            if self.strategy == "UNFOLLOW_FOCUS" and action == "UNFOLLOW_CLEANUP":
                if result == 0:
                    print("\n✅ CLEANUP COMPLETED: No one left to remove.")
                    print("🛑 AI Mode terminating...")
                    break
                else:
                    print(f"✅ Removed {result} users this round. Continuing...")
                    time.sleep(5) # Short break between rounds
            
            # Info
            print(f"📊 Session Summary: Total {total_actions_session} actions performed. Energy: %{self.energy}")
            
    def decide_next_action(self):
        """
        Decides which action to take.
        Decision Criteria:
        - User Strategy (self.strategy)
        - Daily Limits
        - Energy State
        """
        # Limit Checks
        can_follow = self.bot.guard.action_allowed("FOLLOW")
        can_like = self.bot.guard.action_allowed("LIKE")
        can_unfollow = self.bot.guard.action_allowed("UNFOLLOW")
        
        if not can_follow and "FOLLOW" in str(self.strategy):
            print("⚠️ Follow limit reached.")
        if not can_like and "LIKE" in str(self.strategy):
            print("⚠️ Like limit reached.")
        if not self.bot.guard.action_allowed("COMMENT") and "COMMENT" in str(self.strategy):
            print("⚠️ Comment limit reached.")
            
        # --- DECISION BY STRATEGY ---
        
        if self.strategy == "FOLLOW_FOCUS":
            if can_follow and self.energy > 30:
                return "FOLLOW_HUNT"
            elif can_like: # If cannot follow, like
                return "LIKE_HUNT"
                
        elif self.strategy == "LIKE_FOCUS":
            if can_like and self.energy > 20:
                return "LIKE_HUNT"
                
        elif self.strategy == "UNFOLLOW_FOCUS":
            if can_unfollow and self.energy > 20:
                return "UNFOLLOW_CLEANUP"
                
        elif self.strategy == "TARGET_FOCUS":
            if can_follow and self.energy > 30:
                return "TARGET_FOLLOW" # Special action
            elif can_like:
                return "LIKE_HUNT" # Fallback
        
        elif self.strategy == "COMMENT_FOCUS":
            if self.bot.guard.action_allowed("COMMENT") and self.energy > 40:
                return "COMMENT_HUNT"
            elif can_like:
                return "LIKE_HUNT"
        
        elif self.strategy == "SUPER_FAN":
            if can_follow and can_like and self.energy > 40:
                return "DEEP_INTERACTION"
            elif can_like:
                return "LIKE_HUNT"
        
        # --- AUTO MODE or FALLBACK (If strategy cannot be executed) ---
        
        # If follow limit exists and energy is high -> FOLLOW FOCUS
        if can_follow and self.energy > 50:
            return "FOLLOW_HUNT"
            
        # If like limit exists -> LIKE FOCUS
        if can_like:
            return "LIKE_HUNT"
            
        # If unfollow limit exists and others are done -> UNFOLLOW
        if can_unfollow:
            # Only if followed ones are indexed or with a random chance
            if random.random() < 0.3: # 30% chance to cleanup
                return "UNFOLLOW_CLEANUP"
            
        # If nothing can be done -> SLEEP
        return "STOP"

    def execute_action(self, action_type):
        """Executes the selected action."""
        print(f"\n🧠 AI Decision: Executing {action_type}...")
        result = 0
        
        if action_type == "FOLLOW_HUNT":
            # Find target audience and follow
            target = self.find_smart_target()
            if target:
                print(f"🎯 Target Identified: {target}")
                self.bot.like_photos_by_hashtag(target, amount=random.randint(5, 15), follow=True)
                result = 1
                
        elif action_type == "LIKE_HUNT":
            target = self.find_smart_target()
            if target:
                print(f"❤️ Target Identified: {target}")
                self.bot.like_photos_by_hashtag(target, amount=random.randint(10, 20), follow=False)
                result = 1

        elif action_type == "COMMENT_HUNT":
            target = self.find_smart_target()
            if target:
                print(f"💬 Target Identified: {target}")
                self.execute_comment_strategy(target)
                result = 1

        elif action_type == "UNFOLLOW_CLEANUP":
            print(f"🧹 Cleanup Time: Smart Cleanup Mode ({self.unfollow_mode})...")
            # User request: Comparative and fast deletion
            # Let's do a cleanup of 50-70 people
            count = random.randint(50, 70)
            result = self.bot.smart_unfollow_cleanup(max_users=count, mode=self.unfollow_mode)
            
        elif action_type == "TARGET_FOLLOW":
            if self.target_profile:
                print(f"🎯 Target Profile Analysis: {self.target_profile}")
                # Use existing follow_target_followers function
                # But keep amount small and focused
                self.bot.follow_target_followers(self.target_profile, limit=random.randint(10, 20))
                result = 1
            else:
                print("⚠️ No target profile specified, switching to general mode.")
                self.strategy = "FOLLOW_FOCUS" # Change strategy
            
        elif action_type == "DEEP_INTERACTION":
            target = self.find_smart_target()
            if target:
                print(f"🌟 Super Fan Mode: Deep interaction on tag {target}...")
                self.execute_deep_interaction(target)
                result = 1
        
        return result

    def execute_deep_interaction(self, hashtag):
        """
        Super Fan Interaction:
        1. Go to Profile
        2. Watch Story (If exists)
        3. Like 2-3 Photos
        4. Follow
        """
        print(f"🚀 Scanning tag '{hashtag}'...")
        
        # Go to hashtag page
        self.bot.driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(5)
        
        # Select one of the first 9 posts (Popular usually top 9)
        try:
            posts = self.bot.driver.find_elements(self.bot.By.XPATH, "//a[contains(@href, '/p/')]")
            if not posts:
                print("❌ No posts found.")
                return

            # Randomly select 3 people
            selected_posts = random.sample(posts[:15], min(3, len(posts)))
            
            for post in selected_posts:
                try:
                    post_url = post.get_attribute("href")
                    print(f"🔎 Inspecting post: {post_url}")
                    
                    # Go to post
                    self.bot.driver.get(post_url)
                    time.sleep(3)
                    
                    # Get username
                    try:
                        username_element = self.bot.driver.find_element(self.bot.By.XPATH, "//header//div[contains(@class, '_aaqt')]//a")
                        username = username_element.text
                    except:
                        # Alternative selector
                        try:
                            username_element = self.bot.driver.find_element(self.bot.By.XPATH, "//h2/div/a")
                            username = username_element.text
                        except:
                            print("❌ Could not get username.")
                            continue
                            
                    print(f"👤 Target User: {username}")
                    
                    if self.bot.check_history(username):
                        print("   -> Already processed, skipping.")
                        continue
                        
                    # Go to profile
                    self.bot.browser_manager.navigate_to_profile(username)
                    time.sleep(3)
                    
                    # 1. Watch Story
                    watched = self.bot.browser_manager.watch_story()
                    if watched:
                        print("   -> 👁️ Story watched.")
                    else:
                        print("   -> No story or could not watch.")
                        
                    # 2. Like (Latest 2-3 posts)
                    self.bot.browser_manager.like_latest_post(limit=random.randint(2, 3))
                    print("   -> ❤️ Latest posts liked.")
                    
                    # 3. Follow
                    # Find follow button
                    try:
                        follow_btn = self.bot.driver.find_element(self.bot.By.XPATH, "//button[.//div[contains(text(), 'Takip Et') or contains(text(), 'Follow')]]")
                        follow_btn.click()
                        print("   -> ✅ Followed.")
                        self.bot.log_action("FOLLOW", username)
                    except:
                        print("   -> Follow button not found (Already following or requested).")
                        
                    # Wait after action
                    time.sleep(random.randint(10, 20))
                    
                except Exception as e:
                    print(f"Profile action error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Hashtag scan error: {e}")

    def execute_comment_strategy(self, hashtag):
        """Finds posts via hashtag and comments."""
        print("💬 Starting comment strategy...")
        
        # Comments by category
        general_comments = ["Awesome! 🔥", "Great post 👏", "Very good ✨", "Liked it 👍", "Successful 🌟"]
        
        niche_comments = {
            "fitness": ["Keep pushing! 💪", "Great form 🔥", "Motivation high! 🚀", "Strong stance 🦍"],
            "software": ["Clean code! 💻", "Successful project 🚀", "Good luck ☕", "Which language? 🤔"],
            "travel": ["Great view 🌍", "Happy holidays! ✈️", "Where is this? 😍", "Beautiful shot 📸"],
            "food": ["Bon appetit 😋", "Looks delicious 🍔", "Well done 👨‍🍳", "Recipe? 📝"],
            "fashion": ["Great style ✨", "Very chic 👌", "Super outfit 🔥", "Where did you get it? 😍"],
            "art": ["Great talent 🎨", "Very creative ✨", "Well done 🖌️", "Inspiring 🌟"]
        }
        
        # Select comments suitable for tag
        selected_comments = general_comments
        for key, comments in niche_comments.items():
            if key in hashtag.lower():
                selected_comments = comments + general_comments # Mix
                print(f"💡 Comments selected for category '{key}'.")
                break
        
        # Go to hashtag page
        self.bot.driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
        time.sleep(5)
        
        # Open first post
        try:
            first_post = self.bot.driver.find_element(self.bot.By.XPATH, "//a[contains(@href, '/p/')]")
            first_post.click()
            time.sleep(3)
            
            # Comment on 3-5 posts
            count = 0
            limit = random.randint(3, 5)
            
            while count < limit:
                try:
                    text = random.choice(selected_comments)
                    success = self.bot.post_comment(None, text) # URL None because already on post
                    
                    if success:
                        count += 1
                        print(f"[{count}/{limit}] Commented: {text}")
                    
                    # Next post
                    next_btn = self.bot.driver.find_element(self.bot.By.XPATH, "//button[contains(@aria-label, 'İleri') or contains(@aria-label, 'Next')]")
                    next_btn.click()
                    time.sleep(random.randint(5, 10))
                    
                except Exception as e:
                    print(f"Comment loop error: {e}")
                    break
                    
        except Exception as e:
            print(f"Hashtag open error: {e}")

    def find_smart_target(self):
        """Determines dynamic target based on interests."""
        
        # If user defined interests exist, choose from them
        if self.niche_tags and random.random() < 0.7: # 70% chance to use user's choice
            selected = random.choice(self.niche_tags)
            print(f"🎯 User Interest: '{selected}' selected.")
            return selected

        # Else or 30% chance to go general based on time
        # Extended Interests
        morning_tags = ["coffee", "breakfast", "goodmorning", "nature", "sunrise", "motivation"]
        work_tags = ["technology", "coding", "business", "work", "design", "developer"]
        evening_tags = ["food", "dinner", "relax", "movie", "music", "art"]
        night_tags = ["night", "stars", "sleep", "dream", "reading", "peace"]
        
        hour = datetime.datetime.now().hour
        
        selected_tag = "general"
        if 6 <= hour < 11:
            selected_tag = random.choice(morning_tags)
            print(f"🌅 Morning Mode: Analyzing tag '{selected_tag}'...")
        elif 11 <= hour < 18:
            selected_tag = random.choice(work_tags)
            print(f"💼 Mid-Day Mode: Analyzing tag '{selected_tag}'...")
        elif 18 <= hour < 23:
            selected_tag = random.choice(evening_tags)
            print(f"🌆 Evening Mode: Analyzing tag '{selected_tag}'...")
        else:
            selected_tag = random.choice(night_tags)
            print(f"🌙 Night Mode: Analyzing tag '{selected_tag}'...")
            
        return selected_tag

    def take_smart_break(self):
        """Takes a human-like break."""
        duration = random.randint(120, 600) # 2-10 minutes
        print(f"☕ AI Break: Resting for {duration//60} minutes...")
        time.sleep(duration)
        self.energy = min(100, self.energy + 10) # Renew energy

    def update_state(self):
        """Updates state after each action."""
        self.energy -= random.randint(5, 15)
        if self.energy < 20:
            print("🔋 Energy low, activating rest mode.")
            self.take_smart_break()

    def score_user(self, user_data):
        """
        Analyzes a user and gives a score between 0-100.
        """
        # Placeholder for scoring logic
        return 50
