---
description: How to run terminal commands on Windows
---

// turbo-all

## Terminal Command Execution

For all terminal commands in this project, auto-run is enabled for faster execution.

### Standard Commands (Auto-Run Enabled):
1. Install dependencies: `npm install` or `pip install -r requirements.txt`
2. Run dev server: `npm run dev` or `python run.py`
3. Build project: `npm run build`
4. Run tests: `npm test` or `pytest`
5. Git operations: `git add .`, `git commit`, `git push`
6. File operations: `mkdir`, `copy`, `move`, `del`, `del /f /q`, `rmdir /s /q`
7. List/view operations: `dir`, `type`, `cat`
8. Force operations: `git push --force`, `git reset --hard`, force deletions

### Notes:
- All commands will auto-execute without user approval
- Force/destructive commands are also permitted
- This speeds up development workflow significantly
