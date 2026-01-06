import time
import random
import sys
import os
import datetime

# To import config module from main directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    import config
except ImportError:
    # Dummy config if not found
    class config:
        BASE_DELAY_MIN = 2
        BASE_DELAY_MAX = 5
        LONG_DELAY_MIN = 15
        LONG_DELAY_MAX = 30

class ActionScheduler:
    def __init__(self):
        self.last_action_time = time.time()
        self.action_count = 0
        
        # Default schedule settings (can be overridden by config)
        self.sleep_start_hour = getattr(config, "SLEEP_START_HOUR", 23)
        self.sleep_end_hour = getattr(config, "SLEEP_END_HOUR", 7)
        self.peak_start_hour = getattr(config, "PEAK_START_HOUR", 18)
        self.peak_end_hour = getattr(config, "PEAK_END_HOUR", 22)
        
    def check_working_hours(self):
        """
        Checks if the bot should be sleeping (Silence Period).
        Returns True if working, False if sleeping.
        """
        now = datetime.datetime.now()
        hour = now.hour
        
        # Simple logic: If current hour is between sleep start and end (crossing midnight handled)
        if self.sleep_start_hour > self.sleep_end_hour:
            # Case: 23 to 07 (Night crosses midnight)
            if hour >= self.sleep_start_hour or hour < self.sleep_end_hour:
                return False # Sleep time
        else:
            # Case: 01 to 05 (Unlikely but possible)
            if self.sleep_start_hour <= hour < self.sleep_end_hour:
                return False # Sleep time
                
        return True

    def get_time_multiplier(self):
        """
        Returns a delay multiplier based on time of day (Circadian Rhythm).
        """
        now = datetime.datetime.now()
        hour = now.hour
        
        # Late night: Very slow (2.0x delay)
        if 1 <= hour < 6:
            return 2.0
        
        # Morning: Slow (1.5x delay)
        if 6 <= hour < 9:
            return 1.5
            
        # Peak hours: Fast (0.8x delay)
        if self.peak_start_hour <= hour < self.peak_end_hour:
            return 0.8
            
        # Normal hours: Standard (1.0x delay)
        return 1.0

    def enforce_silence_period(self):
        """
        If currently in sleep time, sleeps until start time.
        """
        if not self.check_working_hours():
            print(">>> [Scheduler] Entering Silence Period (Sleep Mode)...")
            while not self.check_working_hours():
                # Sleep in 10-minute chunks to allow interruption if needed
                time.sleep(600) 
                print(f">>> [Scheduler] Zzz... ({datetime.datetime.now().strftime('%H:%M')})")
            print(">>> [Scheduler] Waking up from Silence Period!")

    def rand_delay(self, long=False):
        """
        Smart delay with circadian rhythm and micro-breaks.
        """
        # 1. Base Delay
        if long:
            mn = getattr(config, "LONG_DELAY_MIN", 15)
            mx = getattr(config, "LONG_DELAY_MAX", 30)
        else:
            mn = getattr(config, "BASE_DELAY_MIN", 2)
            mx = getattr(config, "BASE_DELAY_MAX", 5)
            
        base_delay = random.uniform(mn, mx)
        
        # 2. Apply Circadian Rhythm Multiplier
        multiplier = self.get_time_multiplier()
        final_delay = base_delay * multiplier
        
        # 3. Micro-break (Event-based)
        # Every 10-15 actions, take a slightly longer breath
        self.action_count += 1
        if self.action_count > random.randint(10, 20):
            print("   (Micro-break...)")
            final_delay += random.uniform(5, 10)
            self.action_count = 0

        time.sleep(final_delay)
    
    def fast_delay(self):
        time.sleep(random.randint(1, 2))
    
    def turbo_delay(self):
        time.sleep(random.uniform(0.2, 0.4))
