from abc import ABC, abstractmethod
import random
import time

class BehaviorStrategy(ABC):
    """
    Base class for high-level bot behaviors.
    Determines the mix and frequency of actions (Behavior).
    """
    def __init__(self, bot):
        self.bot = bot

    @abstractmethod
    def perform_cycle(self):
        """
        Executes one cycle of the behavior.
        Returns True if cycle completed successfully, False otherwise.
        """
        pass

class PassiveGrowthStrategy(BehaviorStrategy):
    """
    Low activity, safe growth.
    Focuses on liking (low volume) to keep account active but safe.
    """
    def perform_cycle(self):
        print(">>> [PassiveGrowth] Starting cycle (Low Intensity)...")
        
        # 1. Random Delay (Simulate idle time)
        self.bot.scheduler.rand_delay(long=True)
        
        # 2. Like some posts by hashtag (Conservative)
        hashtags = ["life", "nature", "minimal", "art", "view"]
        tag = random.choice(hashtags)
        
        # 2-4 likes per cycle
        amount = random.randint(2, 4)
        
        print(f">>> [PassiveGrowth] Liking {amount} posts in #{tag}")
        self.bot.like_photos_by_hashtag(tag, amount=amount, follow=False, comment=False)
        
        # 3. Small chance to check own profile (Human behavior)
        if random.random() < 0.3:
            self.bot.browser_manager.navigate_to_profile(self.bot.username)
            time.sleep(random.uniform(3, 6))
            
        return True

class ObservationOnlyStrategy(BehaviorStrategy):
    """
    No interactions (Likes/Follows/Comments). 
    Only data gathering, login checks, or watching feed.
    """
    def perform_cycle(self):
        print(">>> [ObservationOnly] Monitoring cycle...")
        
        # 1. Just scroll feed or explore
        actions = ["FEED", "EXPLORE", "USER_VISIT"]
        action = random.choice(actions)
        
        if action == "FEED":
            print(">>> [ObservationOnly] Scrolling Feed...")
            self.bot.driver.get("https://www.instagram.com/")
            time.sleep(random.uniform(3, 5))
            for _ in range(3):
                self.bot.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(random.uniform(2, 4))
                
        elif action == "EXPLORE":
            print(">>> [ObservationOnly] Browsing Explore...")
            self.bot.driver.get("https://www.instagram.com/explore/")
            time.sleep(random.uniform(3, 5))
            self.bot.driver.execute_script("window.scrollBy(0, 500);")
            
        elif action == "USER_VISIT":
            # Visit a random popular user but do nothing
            targets = ["instagram", "natgeo", "nike"]
            target = random.choice(targets)
            print(f">>> [ObservationOnly] Visiting {target}...")
            self.bot.browser_manager.navigate_to_profile(target)
            time.sleep(random.uniform(4, 8))
            
        self.bot.scheduler.rand_delay(long=True)
        return True

class ManualAssistStrategy(BehaviorStrategy):
    """
    Assists manual usage. 
    Performs tedious tasks (like Unfollowing) slowly and carefully.
    """
    def perform_cycle(self):
        print(">>> [ManualAssist] Running assistant tasks...")
        
        # Priority: Clean up non-followers
        if self.bot.action_allowed("UNFOLLOW"):
            print(">>> [ManualAssist] Cleaning non-followers (Batch of 5)...")
            # Unfollow small batch
            self.bot.unfollow_non_followers(count=5, fast=False)
        else:
            print(">>> [ManualAssist] Unfollow limit reached or not allowed.")
            # Fallback: Like a few posts
            tag = random.choice(["news", "tech", "daily"])
            self.bot.like_photos_by_hashtag(tag, amount=3)
            
        self.bot.scheduler.rand_delay(long=True)
        return True
