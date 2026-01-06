import os
import importlib.util
import inspect
import sys
from src.core.plugin_interface import BasePlugin
from src.logger.logger import logger

class PluginManager:
    def __init__(self, bot):
        self.bot = bot
        self.plugins = []
        self.plugin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src", "plugins")

    def load_plugins(self):
        """Loads all plugins from the src/plugins directory."""
        if not os.path.exists(self.plugin_dir):
            os.makedirs(self.plugin_dir)
            # Create __init__.py if it doesn't exist
            with open(os.path.join(self.plugin_dir, "__init__.py"), "w") as f:
                f.write("")

        logger.info(f"Loading plugins from: {self.plugin_dir}")

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                self._load_plugin_from_file(os.path.join(self.plugin_dir, filename))
            elif os.path.isdir(os.path.join(self.plugin_dir, filename)) and not filename.startswith("__"):
                # Support for folder-based plugins (must have __init__.py or main file)
                init_file = os.path.join(self.plugin_dir, filename, "__init__.py")
                if os.path.exists(init_file):
                    self._load_plugin_from_file(init_file, module_name=f"src.plugins.{filename}")

    def _load_plugin_from_file(self, file_path, module_name=None):
        try:
            if module_name is None:
                # Construct module name from file path relative to project root? 
                # Or just load dynamically using spec.
                module_name = os.path.basename(file_path).replace(".py", "")
            
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Find classes that inherit from BasePlugin
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BasePlugin) and obj is not BasePlugin:
                        try:
                            plugin_instance = obj(self.bot)
                            plugin_instance.on_load()
                            self.plugins.append(plugin_instance)
                            logger.success(f"Loaded plugin: {plugin_instance.name} v{plugin_instance.version}")
                        except Exception as e:
                            logger.error(f"Failed to instantiate plugin {name}: {e}")

        except Exception as e:
            logger.error(f"Error loading plugin from {file_path}: {e}")

    def trigger_hook(self, hook_name, *args, **kwargs):
        """Triggers a hook on all enabled plugins."""
        for plugin in self.plugins:
            if plugin.enabled:
                method = getattr(plugin, hook_name, None)
                if method and callable(method):
                    try:
                        method(*args, **kwargs)
                    except Exception as e:
                        logger.error(f"Error in plugin {plugin.name} hook {hook_name}: {e}")

    def trigger_before_action(self, action_type, target, info=None):
        """
        Special hook for before_action.
        If ANY plugin returns False, the action should be cancelled.
        """
        should_continue = True
        for plugin in self.plugins:
            if plugin.enabled:
                try:
                    result = plugin.before_action(action_type, target, info)
                    if result is False:
                        should_continue = False
                        logger.warning(f"Action {action_type} cancelled by plugin {plugin.name}")
                except Exception as e:
                    logger.error(f"Error in plugin {plugin.name} before_action: {e}")
        
        return should_continue
