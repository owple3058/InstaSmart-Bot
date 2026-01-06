import subprocess
import os
import sys

def log_to_file(message):
    try:
        with open("git_deploy_log.txt", "a", encoding="utf-8") as f:
            f.write(str(message) + "\n")
    except:
        pass

def run_git_cmd(args):
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True, encoding='utf-8')
        output = result.stdout.strip()
        if result.returncode != 0:
            output += f"\nError (Code {result.returncode}): {result.stderr}"
        return output
    except Exception as e:
        return f"Exception: {str(e)}"

# Clear log file
with open("git_deploy_log.txt", "w", encoding="utf-8") as f:
    f.write("Starting Git Deploy...\n")

log_to_file("--- Git Remote ---")
log_to_file(run_git_cmd(['remote', '-v']))

log_to_file("\n--- Git Status ---")
log_to_file(run_git_cmd(['status']))

log_to_file("\n--- Git Add ---")
log_to_file(run_git_cmd(['add', '.']))

log_to_file("\n--- Git Commit ---")
subprocess.run(['git', 'config', 'user.email', 'trae@bot.com'], capture_output=True)
subprocess.run(['git', 'config', 'user.name', 'Trae Bot'], capture_output=True)

commit_msg = "feat: Upgrade to modular framework with Plugin system and Dry-Run mode"
log_to_file(run_git_cmd(['commit', '-m', commit_msg]))

log_to_file("\n--- Git Push ---")
log_to_file(run_git_cmd(['push', 'origin', 'main']))
