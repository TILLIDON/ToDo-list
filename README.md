# FocusFlow for Windows

A clean, dark desktop to-do app built with Python's standard library.

## Features
- Dashboard with total, completed, due-today and overdue counts
- Create, edit, complete/undo and delete tasks
- Notes, categories, priority levels and due dates
- All tasks, Today, Upcoming and Completed views
- Search, category filtering and sorting
- CSV import/export and SQLite database backup
- Local SQLite storage — no account or internet connection required

## Run on Windows
1. Install Python 3.10 or newer from https://www.python.org/downloads/
2. During installation, enable **Add Python to PATH**.
3. Extract this folder.
4. Open Command Prompt in this folder and run:

   `python main.py`

Your tasks are stored in `focusflow.db` beside the app.

## Build a Windows EXE (optional)
Open Command Prompt in this folder and run:

   `python -m pip install pyinstaller`
   `python -m PyInstaller --noconfirm --onefile --windowed --name FocusFlow main.py`

The executable will be created in `dist\FocusFlow.exe`. Keep `focusflow.db` in the same folder as the EXE after first launch so your data remains easy to back up.
