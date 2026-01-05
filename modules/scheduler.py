import time
import random
import config

class ActionScheduler:
    def __init__(self):
        pass

    def rand_delay(self, long=False):
        if long:
            mn = getattr(config, "LONG_DELAY_MIN", 5)
            mx = getattr(config, "LONG_DELAY_MAX", 12)
        else:
            mn = getattr(config, "BASE_DELAY_MIN", 2)
            mx = getattr(config, "BASE_DELAY_MAX", 5)
        time.sleep(random.randint(mn, mx))
    
    def fast_delay(self):
        time.sleep(random.randint(1, 2))
    
    def turbo_delay(self):
        time.sleep(random.uniform(0.2, 0.4))
