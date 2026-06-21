# Jun Edu Developer Guide

Jun Edu is a PySide6 desktop app that uses an MVVM-style structure:

- `src/models/`: SQLAlchemy models and database setup.
- `src/viewmodels/`: application state, database work, background tasks, and QtCore signals.
- `src/views/`: hand-written Qt widgets/windows. Put signal wiring, slots, validation, and styling here.
- `ui/`: Qt Designer `.ui` source files.
- `ui_gen/`: generated `ui_*.py` files from `pyside6-uic`. Treat this directory as read-only.
- `resources/`: icons, styles, fonts, and images.
- `cmd/`: helper commands for agents/developers.

Start with these docs:

| File | Use it for |
|---|---|
| [architecture.md](./architecture.md) | Project map, MVVM boundaries, and UI generation rules |
| [main_window.md](./main_window.md) | Navigation, system tray, and reminder flow |
| [models.md](./models.md) | ORM tables and database session usage |
| [viewmodels.md](./viewmodels.md) | ViewModel state, signals, and persistence behavior |
| [views.md](./views.md) | View classes, generated UI modules, and major widgets |

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` (or `SUPABASE_KEY`) in `.env` for login/register/logout. Set `TTS_AGENT_URL` when using the external audio import flow. The default API base URL is `https://api.jun-edu.shop`.

## Agent Checklist

1. Read `requirement.md` before making structural changes.
2. Edit behavior in `src/views/`, `src/viewmodels/`, `src/models/`, or `src/utils/`.
3. Edit layout in `ui/*.ui`, then regenerate the matching `ui_gen/ui_*.py`.
4. Do not manually edit `ui_gen/`.
5. Keep ViewModels free of `PySide6.QtWidgets`; use `PySide6.QtCore` only for signals, timers, and QObject behavior.
6. Use `blockSignals(True)` around programmatic UI updates that would otherwise retrigger slots.
7. Use `src.utils.qt.clear_layout()` when clearing dynamic Qt layouts.

## Regenerating UI

Run from the project root:

```bash
pyside6-uic ui/exam_transcript_widget.ui -o ui_gen/ui_exam_transcript_widget.py
```

Generated modules are imported like this:

```python
from ui_gen.ui_main_window import Ui_MainWindow
```
