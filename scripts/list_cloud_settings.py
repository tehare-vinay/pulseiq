from pathlib import Path
import re

root = Path("Task 5 - First Dashboard")
files = [root / "app.py"] + list((root / "pages").glob("*.py"))

patterns = [
    r'os\.getenv\(\s*["\']([^"\']+)',
    r'os\.environ\.get\(\s*["\']([^"\']+)',
    r'st\.secrets\[\s*["\']([^"\']+)',
]

keys = set()

for file in files:
    if not file.exists():
        continue
    content = file.read_text(encoding="utf-8", errors="ignore")
    for pattern in patterns:
        keys.update(re.findall(pattern, content))

print("Setting names used by dashboard (values hidden):")
for key in sorted(keys):
    print("-", key)

example = root / ".env.example"
if example.exists():
    print("\nKeys listed in .env.example (values hidden):")
    for line in example.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            print("-", line.split("=", 1)[0].strip())
