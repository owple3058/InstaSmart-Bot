import datetime
import os
import json
import logging
from typing import Any, Dict, Optional

class JsonLogger:
    def __init__(self, name="InstaBot", log_file="activity_log.jsonl"):
        self.name = name
        self.log_file = log_file
        
        # Ensure log file exists or create it
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', encoding='utf-8') as f:
                pass

    def _format_log_entry(self, level: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Creates a structured log entry."""
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
        }
        
        if context:
            # Flatten context into the main dictionary or keep it nested?
            # Keeping it nested is cleaner for structured logs, but flattening is easier for some tools.
            # Let's keep it nested under 'context' but also promote key fields if needed.
            entry["context"] = context
            
        return entry

    def _write_to_file(self, entry: Dict[str, Any]):
        """Appends the JSON log entry to the file (JSON Lines format)."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # Fallback to print if file writing fails
            print(f"!!! LOGGING ERROR: {e}")

    def _print_to_console(self, entry: Dict[str, Any]):
        """Prints a readable version to the console."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        level = entry["level"]
        message = entry["message"]
        context = entry.get("context", {})
        
        # Color codes (simple ANSI)
        colors = {
            "INFO": "\033[94m",    # Blue
            "SUCCESS": "\033[92m", # Green
            "WARNING": "\033[93m", # Yellow
            "ERROR": "\033[91m",   # Red
            "DEBUG": "\033[90m",   # Grey
            "RESET": "\033[0m"
        }
        
        color = colors.get(level, colors["RESET"])
        
        # Base message
        console_msg = f"{colors['DEBUG']}[{timestamp}]{colors['RESET']} {color}[{level}]{colors['RESET']} {message}"
        
        # Add context info if interesting
        if context:
            # Filter out some verbose context for console if needed
            relevant_context = []
            for k, v in context.items():
                if v is not None:
                    relevant_context.append(f"{k}={v}")
            
            if relevant_context:
                console_msg += f" {colors['DEBUG']}({', '.join(relevant_context)}){colors['RESET']}"
                
        print(console_msg)

    def log(self, level: str, message: str, **kwargs):
        """
        Main logging method.
        Usage: logger.log("INFO", "Action started", action="LIKE", target="user1")
        """
        entry = self._format_log_entry(level, message, context=kwargs)
        self._write_to_file(entry)
        self._print_to_console(entry)

    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)

    def success(self, message: str, **kwargs):
        self.log("SUCCESS", message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log("DEBUG", message, **kwargs)

# Global instance for easy access
logger = JsonLogger()
