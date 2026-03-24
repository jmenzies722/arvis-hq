#!/usr/bin/env python3
"""
Runs as a LaunchAgent to cache Apple Reminders to a JSON file.
Flask server reads this cache — avoids TCC issues with background processes.
"""
import json, subprocess
from datetime import datetime
from pathlib import Path

CACHE = Path.home() / "agent-hq" / "data" / "reminders_cache.json"

script = (
    'tell application "Reminders"\n'
    '  set output to ""\n'
    '  repeat with theList in lists\n'
    '    set lName to name of theList\n'
    '    repeat with r in (reminders of theList whose completed is false)\n'
    '      set rDue to ""\n'
    '      try\n'
    '        set rDue to due date of r as string\n'
    '      end try\n'
    '      set output to output & lName & "||" & (name of r) & "||" & rDue & "~~"\n'
    '    end repeat\n'
    '  end repeat\n'
    '  return output\n'
    'end tell'
)

result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=90)
raw    = result.stdout.strip()
items  = []
for chunk in raw.split("~~"):
    chunk = chunk.strip()
    if not chunk:
        continue
    parts = chunk.split("||")
    if len(parts) >= 2:
        items.append({
            "list": parts[0].strip(),
            "name": parts[1].strip(),
            "due":  parts[2].strip() if len(parts) > 2 else "",
        })

CACHE.parent.mkdir(parents=True, exist_ok=True)
CACHE.write_text(json.dumps({"reminders": items, "updated": datetime.now().isoformat()}, indent=2))
print(f"Cached {len(items)} reminders")
