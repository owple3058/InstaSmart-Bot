# 🤖 InstaSmart Framework (Open Source)

![Version](https://img.shields.io/badge/version-3.0.0-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg) ![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)

**InstaSmart** is a modular, safe, and intelligent Instagram automation framework developed using Python and Selenium. It is designed not just as a simple "bot", but as a **simulation framework** that mimics human behavior with high fidelity.

It features a **Plugin System**, **Dry-Run (Simulation) Mode**, **Smart Guard**, and **Behavioral Strategies** to ensure safety and extensibility.

## 🚀 Key Features

### 🛡️ Safety & Guard System
- **Smart Guard**: Monitors action limits, UI changes, and risks in real-time.
- **Dry-Run Mode**: `DRY_RUN = True` enables a full simulation where the bot navigates, finds elements, and decides actions **without actually clicking** or modifying data. Perfect for testing and education.
- **Structured Logging**: Detailed JSON logs for every action, decision, and error.

### 🧩 Modular Architecture
- **Plugin System**: Easily extend functionality without modifying the core code. (e.g., Session Statistics).
- **Behavioral Strategies**:
  - **Passive Growth**: Low intensity, focuses on keeping the account active.
  - **Observation Only**: Just scrolls and watches (zero risk).
  - **Manual Assist**: Automates tedious tasks like unfollowing carefully.
- **Centralized Action Manager**: All clicks go through a central handler that respects Dry-Run and Guard rules.

### 🧠 Intelligence
- **Human-Like Navigation**: Uses random delays, mouse movements, and "Turbo" modes for realistic patterns.
- **Context Awareness**: Knows *why* it is performing an action (e.g., "from_explore", "batch_follow").
- **Smart Unfollow**: Detects who follows you back and filters by activity/verified status.

---

## 🛠️ Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/owple3058/InstaSmart-Bot.git
   cd InstaSmart-Bot
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration:**
   Copy the example config and edit it with your credentials.
   ```bash
   # Windows
   copy config.example.py config.py
   copy comments.example.txt comments.txt
   copy whitelist.example.txt whitelist.txt
   ```

   **Edit `config.py`:**
   ```python
   USERNAME = "your_username"
   PASSWORD = "your_password"
   
   # Enable Simulation Mode for testing
   DRY_RUN = True 
   ```

---

## ▶️ Usage

Run the main script:
```bash
python main.py
```

### Menu Options
1. **Autopilot**: Runs a mix of strategies automatically.
2. **Target Analysis**: Follows users from a target profile's followers.
3. **Smart Unfollow**: Cleans up non-followers safely.
4. **Behavior Modes**: Select specific behavioral patterns (Passive, Observation, etc.).

---

## 🔌 Plugin System

InstaSmart supports plugins to extend functionality. Plugins live in `src/plugins/`.

**Example: Creating a Simple Plugin**
Create `src/plugins/my_plugin.py`:

```python
from src.core.plugin_interface import BasePlugin

class MyPlugin(BasePlugin):
    name = "MyCustomPlugin"
    
    def on_bot_start(self):
        print("Bot started! My plugin is running.")
        
    def before_action(self, action_type, target, info=None):
        # Return False to cancel an action
        return True
```

The bot will automatically load this plugin on startup.

---

## 📂 Project Structure

```
InstaSmart/
├── main.py                 # Entry point
├── config.py               # Settings (User created)
├── src/
│   ├── core/               # Core logic (Browser, Database, PluginManager)
│   ├── guard/              # Safety & Risk Management
│   ├── plugins/            # Custom Plugins
│   ├── strategies/         # Action Strategies (Like, Follow, etc.)
│   ├── scheduler/          # Time management
│   └── logger/             # Structured logging
```

---

## ⚠️ Disclaimer

This project is for **educational purposes only**. The user is responsible for any account bans or restrictions resulting from actions that violate Instagram's terms of use. 

We highly recommend using **Dry-Run Mode** (`DRY_RUN = True`) to understand how the bot works without risking your account.

## 🤝 Contributing

Pull requests are welcome! Please check the `src/strategies` folder if you want to add new behaviors.

## 📄 License

[MIT](LICENSE)
