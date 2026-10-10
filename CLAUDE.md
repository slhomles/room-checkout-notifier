# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A small internal Flask web app for Someli Property Management's housekeeping team. It pulls bookings from the Someli admin API (`https://ad.someli.vn/api/bookings/calendar`) and turns them into per-branch room-cleaning schedules. The output is plain text that staff copy and paste into chat, plus a monthly evening-checkout table they can export to Excel. All UI strings, comments and output text are in Vietnamese.

## Commands

The project uses a Windows venv at `./venv`. There are no tests, linter or formatter.

```bash
venv\Scripts\activate
pip install -r requirements.txt
python app.py                 # http://127.0.0.1:5000 (port from $PORT, default 5000)
build.bat                     # PyInstaller one-file exe -> dist/RoomCheckApp.exe
```

- Production runs on Render with `gunicorn app:app`. Gunicorn does not run on Windows, so use `python app.py` locally.
- `build.bat` needs `pyinstaller`, which is installed in the venv but is not listed in `requirements.txt`. The script regenerates `RoomCheckApp.spec`, which is gitignored and only bundles `templates/`. Do not rely on a hand-edited local spec.

To check processing logic without a token, run it on the sample API dump `schedule.json` (checkouts from 2026-08-14 to 2026-09-15):

```bash
PYTHONIOENCODING=utf-8 venv/Scripts/python.exe -c "import json,core; d=json.load(open('schedule.json',encoding='utf-8'))['data']; b='HN03 - 24 Thổ Quan, Khâm Thiên'; r=core.process_data(d,'2026-08-15'); print(core.generate_branch_text(b,r[b],'2026-08-15'))"
```

## Architecture

- **`app.py`**: Flask routes only. It has `/` (the template) and two POST JSON endpoints, `/api/fetch` (`{date: YYYY-MM-DD, token}`) and `/api/month-evening-stats` (`{month: YYYY-MM, token}`). It builds the API config per request. A token containing `session_id=` is sent as a `Cookie` header; anything else goes in a Bearer `Authorization` header (`core` adds the `Bearer ` prefix if missing). When frozen by PyInstaller, it rebuilds the `Flask` app with template and static folders under `sys._MEIPASS`.
- **`core.py`**: All business logic, with no Flask dependency.
  - `fetch_data` / `fetch_month_data`: convert Vietnam local dates (`Asia/Ho_Chi_Minh`) to a UTC range padded by ±1 day.
  - `process_data` + `generate_branch_text`: the daily report.
  - `process_month_evening_stats`: the monthly table.
  - `load_config`/`save_config` and `config.json` are not used by the web app.
- **`templates/index.html`**: One self-contained page (inline CSS and JS, Google Fonts, and SheetJS from cdnjs for the Excel export). It has two tabs, daily and monthly. The token is stored only in the browser's `localStorage` under `room_check_token`; the server never saves it. The daily date defaults to tomorrow after 20:00.
- **`room_report.py`**: A legacy standalone CLI that writes `report.txt` from `config.json`. Its shift rules and date window differ from `core.py`, and the web app does not use it. Do not take behavior from it.

## Business rules in `core.py` (easy to break)

Each branch has an evening cutoff. For branch codes in `LATE_EVENING_BRANCH_CODES` (HN05, HN07, HN09, HN10, HN11, HN12), the cutoff is **22:30 inclusive**. For all other branches it is **22:00**. Branches are matched by code prefix with `branch_code()`, so sub-addresses such as `HN07 - 7/34/67 Lê Thanh Nghị` count too. Times are compared as (hour, minute); seconds are ignored.

Daily report (`process_data`):
- A checkout after the cutoff is pushed to the next day's report. So the window for date D is the cutoff on D-1 to the cutoff on D (VN time), not the calendar day.
- Shifts depend on the checkout time:
  - **Sáng**: pushed checkouts, plus hours 0–12.
  - **Chiều**: 13–17.
  - **Tối**: 18:00 up to the cutoff.
- Pushed checkouts and checkouts before 08:00 (`is_night`) display as `"<room> - 8h dọn"` instead of a checkout time and sort to the top.
- Sort order:
  1. Checkout time, truncated to the minute.
  2. Next check-in time for the same room; rooms with none go last.
  3. Room code (string compare).
- The `(HHhMM vào)` suffix appears when the next check-in is within 12h of checkout, or within 24h for night-cleaning rooms.
- `ALL_BRANCHES` is a hard-coded list of branch names (including sub-addresses such as `HN01 - 4A/119 Đình Thôn`). Every branch in it gets an entry even when it has no checkouts. Unknown branch names from the API are appended.

Monthly evening stats (`process_month_evening_stats`):
- A checkout counts as "evening" from **18:00 to 21:30** inclusive. For `LATE_EVENING_BRANCH_CODES` branches the range is **18:00 to 22:30**. The sidebar hint in `index.html` repeats these times, so update it when they change.
- Branches are merged by code prefix (`HN01`, `HN03`, and so on) through `CANONICAL_BRANCHES`, so sub-address branches count toward their parent.

Branch names must match the API's `branchId.name` exactly. When adding or renaming a branch, update **both** `ALL_BRANCHES` and `CANONICAL_BRANCHES`.

The text layout from `generate_branch_text` (the `Sáng:` / `Chiều:` / `Tối:` labels and the continuation indent aligned under the first room) is what staff paste into chat. Keep it stable.
