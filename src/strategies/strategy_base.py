from abc import ABC, abstractmethod

class Strategy(ABC):
    """
    Base class for all bot strategies.
    A Strategy defines 'What to do' (e.g., Follow, Like, Unfollow).
    """
    def __init__(self, bot):
        self.bot = bot  # Reference to the main bot instance (for browser, db, etc.)

    @abstractmethod
    def execute(self, **kwargs):
        """
        Executes the strategy.
        """
        pass
