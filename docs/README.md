# Jun Edu Developer Guide

Jun Edu is a PySide6 desktop app that uses an MVVM-style structure with a
repository boundary between ViewModels and database implementations:

- `src/models/`: pure Python dataclasses shared by repositories, ViewModels, and Views.
- `src/repositories/`: repository interfaces plus SQLite/Supabase implementations.
- `src/viewmodels/`: application state, repository calls, background tasks, and QtCore signals.
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
| [models.md](./models.md) | Pure entities, repository interfaces, and database implementations |
| [viewmodels.md](./viewmodels.md) | ViewModel state, signals, and persistence behavior |
| [views.md](./views.md) | View classes, generated UI modules, and major widgets |

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

For local development/build machines, keep service settings in `.env`, then
generate the embedded config module:

```bash
python cmd/generate_config.py --env .env --out src/config.py
```

The app reads `src.config` at runtime. One-file builds run this generation step
before PyInstaller, so the executable does not need `.env` in `dist/`.

## Agent Checklist

1. Read `requirement.md` before making structural changes.
2. Edit behavior in `src/views/`, `src/viewmodels/`, `src/repositories/`, `src/models/`, or `src/utils/`.
3. Edit layout in `ui/*.ui`, then regenerate the matching `ui_gen/ui_*.py`.
4. Do not manually edit `ui_gen/`.
5. Keep ViewModels free of `PySide6.QtWidgets`; use `PySide6.QtCore` only for signals, timers, and QObject behavior.
6. Keep SQLAlchemy imports isolated to `src/repositories/sqlite/`.
7. Pass repository interfaces into ViewModels instead of importing concrete database sessions there.
8. Use `blockSignals(True)` around programmatic UI updates that would otherwise retrigger slots.
9. Use `src.utils.qt.clear_layout()` when clearing dynamic Qt layouts.
10. Follow `pyrightconfig.json` for strict Pyright typing rules when adding or changing Python code.

## Regenerating UI

Run from the project root:

```bash
pyside6-uic ui/exam_transcript_widget.ui -o ui_gen/ui_exam_transcript_widget.py
```

Generated modules are imported like this:

```python
from ui_gen.ui_main_window import Ui_MainWindow
```
