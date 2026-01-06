# Instagram Credentials
USERNAME = "YOUR_USERNAME"
PASSWORD = "YOUR_PASSWORD"

# Bot Settings
HEADLESS = False          # Run browser in headless mode (True/False)
DISABLE_IMAGES = False    # Disable images to save RAM/Bandwidth
SAFE_MODE = True          # Safe Mode: Increases wait times (Recommended: True)
DRY_RUN = False           # Dry Run / Simulation Mode: Logs actions without clicking (True/False)

# Daily Limits (Do not exaggerate for safety)
MAX_LIKES_PER_DAY = 150
MAX_FOLLOWS_PER_DAY = 100
MAX_COMMENTS_PER_DAY = 60
MAX_UNFOLLOWS_PER_DAY = 120

# Target Audience Filters
MIN_FOLLOWER_COUNT = 50
MAX_FOLLOWER_COUNT = 5000

# Scheduler & Time Settings
# ----------------------------------------------------------
# Silence Period (Sleep Mode) - Bot will pause between these hours
SLEEP_START_HOUR = 23   # 23:00 (11 PM)
SLEEP_END_HOUR = 7      # 07:00 (7 AM)

# Activity Peaks (Bot works faster during these hours)
PEAK_START_HOUR = 18    # 18:00 (6 PM)
PEAK_END_HOUR = 22      # 22:00 (10 PM)

# Wait Times (Seconds) - Base delays
BASE_DELAY_MIN = 2
BASE_DELAY_MAX = 5
LONG_DELAY_MIN = 15     # Increased for safety
LONG_DELAY_MAX = 30

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 13; SM-G996B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Mobile Safari/537.36"
]
