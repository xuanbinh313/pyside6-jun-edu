# Agent Guide

Use this file as the first stop before changing the Jun Edu source tree. It points to the durable docs and project-local agent skills that explain how this repository is organized.

## Read Order

1. `requirement.md`
   - Refactoring rules, MVVM boundaries, generated UI constraints, and validation expectations.
2. `docs/README.md`
   - High-level developer guide and links to focused docs.
3. `docs/architecture.md`
   - Project map, layer rules, UI generation, data flow, and navigation.
4. Task-specific docs:
   - `docs/views.md` for widgets, dialogs, generated UI imports, and view behavior.
   - `docs/viewmodels.md` for ViewModel responsibilities, signals, persistence, and background work.
   - `docs/models.md` for SQLAlchemy models and database session usage.
   - `docs/main_window.md` for navigation, tray behavior, and reminder flow.
5. `.agent/skills/`
   - Project-local skills for repeatable agent workflows. Read the relevant `SKILL.md` before doing matching work.

## Project-Local Skills

Use `.agent/skills/integrate-mvvm-view/SKILL.md` when adding or refactoring a PySide6 view, dialog, widget, generated UI module, ViewModel, or related model code.

That skill covers the expected flow across:

- `ui/`: editable Qt Designer `.ui` files.
- `ui_gen/`: generated `ui_*.py` modules from `pyside6-uic`.
- `src/views/`: hand-written widget, dialog, window, and signal-slot behavior.
- `src/viewmodels/`: presentation state, actions, and `QtCore` signals.
- `src/models/`: database, persistence, sync, and domain operations.

## Repository Map

- `main.py`: application entry point.
- `src/models/`: SQLAlchemy models, database setup, and domain data operations.
- `src/viewmodels/`: MVVM ViewModels. Keep these free of `PySide6.QtWidgets`.
- `src/views/`: hand-written PySide6 UI behavior.
- `src/views/components/`: reusable widgets and dialogs.
- `src/utils/`: shared utilities such as safe Qt layout cleanup.
- `ui/`: raw Qt Designer files.
- `ui_gen/`: generated UI Python modules. Treat this directory as read-only.
- `resources/`: icons, styles, fonts, and images.
- `cmd/`: helper commands for agents and developers.
- `docs/`: source-of-truth documentation for agents.
- `.agent/`: project-local agent instructions and skills.

## MVVM Rules

- Views own `QtWidgets`, generated UI setup, signal-slot wiring, widget state, dialogs, menus, layout changes, and styling.
- ViewModels own state, validation decisions, actions, model calls, background task coordination, and `QtCore` signals.
- Models own database setup, SQLAlchemy tables, persistence, sync, and domain data operations.
- Generated UI classes are imported from `ui_gen`, never from `src.views`.
- Call `setupUi(self)` before accessing generated widgets or connecting custom signals.
- Use `blockSignals(True)` during programmatic widget updates that would otherwise trigger slots.
- Use `src.utils.qt.clear_layout()` for dynamic layout cleanup.
- Do not edit `ui_gen/` by hand. Edit the matching `.ui` file in `ui/`, then regenerate.

## Typing Rules

- Treat `pyrightconfig.json` as the source of truth for static typing expectations.
- The project uses Pyright `strict` mode with Python 3.9 compatibility.
- New or changed code must include concrete parameter, return, variable, and generic type annotations where Pyright would otherwise report unknown or missing types.
- Avoid introducing unused imports or unused variables; Pyright reports both.
- Keep annotations compatible with Python 3.9 syntax. Use `Optional[...]` / `Union[...]` instead of PEP 604 `|` unions in runtime-evaluated annotations unless the file already enables postponed annotations safely.

## Common Commands

Regenerate one UI module:

```powershell
.\.venv\Scripts\pyside6-uic.exe ui\example_view.ui -o ui_gen\ui_example_view.py
```

Run syntax validation:

```powershell
.\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"
```

Run Ruff when installed:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
```

Run Pyright when installed:

```powershell
.\.venv\Scripts\python.exe -m pyright
```

## Change Checklist

- Read the closest existing implementation before adding a new pattern.
- Keep generated files in `ui_gen/`.
- Keep hand-written behavior in `src/views/`.
- Keep ViewModels free of `QtWidgets`.
- Keep database and external data work out of views.
- Follow `pyrightconfig.json` strict typing rules for new or changed Python code.
- Update `docs/` when structure, navigation, or integration behavior changes.
- Report validation commands that passed, failed, or could not run.
