# Jun Edu — Developer Documentation

> Desktop exam management app built with **PySide6**, **SQLAlchemy**, and **MVVM**.

---

## Documentation Index

| File | Description |
|---|---|
| [architecture.md](./architecture.md) | High-level MVVM overview, project structure, navigation, and tray/reminder flow |
| [mainwindow.md](./mainwindow.md) | `MainWindow` — entry point, navigation controller, system tray, close behavior |
| [models.md](./models.md) | `Exam` and `ExamSrtChunk` ORM models, database bootstrap |
| [viewmodels.md](./viewmodels.md) | All 4 ViewModels — signals, state, methods |
| [views.md](./views.md) | All Views and component Widgets — UI elements, signal bindings, widget behavior |

---

## Quick Start

```bash
pip install -r requirements.txt
python mainwindow.py
```

Copy `.env.example` (or create `.env`) and set:
```
TTS_AGENT_URL=https://api.jun-edu.shop
```

The SQLite database `exams.db` is created automatically on first run.

---

## Layer Responsibilities

```
┌─────────────────────────────────────────────────────────────────┐
│                         MainWindow                              │
│         Navigation · System Tray · Close/Reminder Flow          │
├──────────────────────┬──────────────────────────────────────────┤
│     Views            │          ViewModels                      │
│  (UI only, no DB)    │  (State + Business Logic + DB access)    │
├──────────────────────┴──────────────────────────────────────────┤
│                         Models                                  │
│             SQLAlchemy ORM · SQLite (exams.db)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Dependencies

| Package | Purpose |
|---|---|
| `PySide6` | Qt6 UI framework (widgets, signals/slots, multimedia, threading) |
| `qtawesome` | Font Awesome icon library for Qt buttons |
| `sqlalchemy` | ORM for SQLite database access |
| `requests` | HTTP client for TTS/alignment API calls |
| `python-dotenv` | Loads `.env` environment variables |
