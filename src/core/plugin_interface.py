from abc import ABC, abstractmethod

class BasePlugin(ABC):
    """
    Base class for all plugins.
    Plugins must inherit from this class and implement necessary methods.
    """
    
    name = "BasePlugin"
    version = "1.0.0"
    description = "Base plugin description"
    
    def __init__(self, bot):
        self.bot = bot
        self.enabled = True

    def on_load(self):
        """Called when the plugin is loaded."""
        pass

    def on_unload(self):
        """Called when the plugin is unloaded."""
        pass

    def on_enable(self):
        """Called when the plugin is enabled."""
        self.enabled = True

    def on_disable(self):
        """Called when the plugin is disabled."""
        self.enabled = False

    # --- Hooks ---
    # Plugins can override these methods to react to events.

    def on_bot_start(self):
        """Called when the bot starts its main loop."""
        pass

    def on_bot_stop(self):
        """Called when the bot stops."""
        pass

    def before_action(self, action_type, target, info=None):
        """
        Called before an action is performed.
        Return False to cancel the action.
        """
        return True

    def after_action(self, action_type, target, success, info=None):
        """Called after an action is performed (success or fail)."""
        pass

    def on_error(self, error, context=None):
        """Called when an error occurs in the bot."""
        pass
