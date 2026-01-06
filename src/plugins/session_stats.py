from src.core.plugin_interface import BasePlugin
from src.logger.logger import logger
import time

class SessionStatsPlugin(BasePlugin):
    name = "SessionStats"
    version = "1.0.0"
    description = "Tracks session statistics and logs them on shutdown."

    def on_load(self):
        self.stats = {
            "LIKE": 0,
            "FOLLOW": 0,
            "UNFOLLOW": 0,
            "COMMENT": 0,
            "STORY_VIEW": 0
        }
        self.start_time = None

    def on_bot_start(self):
        self.start_time = time.time()
        logger.info(f"[{self.name}] Tracking started.")

    def after_action(self, action_type, target, success, info=None):
        if success:
            if action_type in self.stats:
                self.stats[action_type] += 1
            else:
                self.stats[action_type] = 1
            
            # Real-time simplified log from plugin
            # logger.info(f"[{self.name}] {action_type} count: {self.stats[action_type]}")

    def on_bot_stop(self):
        self._print_report()

    def on_unload(self):
        # Also print report when unloaded if bot was running
        if self.start_time:
            self._print_report()

    def _print_report(self):
        if not self.start_time:
            return
            
        duration = time.time() - self.start_time
        hours, rem = divmod(duration, 3600)
        minutes, seconds = divmod(rem, 60)
        
        report = f"\n--- [Session Stats Report] ---\n"
        report += f"Duration: {int(hours)}h {int(minutes)}m {int(seconds)}s\n"
        report += "Actions:\n"
        total = 0
        for action, count in self.stats.items():
            report += f"  - {action}: {count}\n"
            total += count
        report += f"Total Actions: {total}\n"
        report += "------------------------------\n"
        
        logger.info(report)
