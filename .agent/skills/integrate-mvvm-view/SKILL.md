---
name: integrate-mvvm-view
description: Add or refactor Jun Edu PySide6 views in the project MVVM structure. Use when integrating new Qt Designer .ui files from ui/, generated UI modules from ui_gen/, data/model code from src/models/, viewmodels from src/viewmodels/, and hand-written view behavior from src/views/.
---

# Integrate MVVM View

## Goal

Integrate a new screen, dialog, or reusable widget while preserving the project structure:

- `ui/`: source Qt Designer `.ui` files.
- `ui_gen/`: generated `ui_*.py` files. Treat as read-only output.
- `src/models/`: persistence, data access, and domain operations.
- `src/viewmodels/`: presentation state and application actions. Use `QtCore`, not `QtWidgets`.
- `src/views/`: hand-written PySide6 widgets, dialogs, windows, navigation, and signal-slot wiring.

## Workflow

1. Read `requirement.md`, `docs/README.md`, `docs/architecture.md`, `docs/views.md`, and nearby existing files before editing.
2. Locate the closest existing pattern:
   - Full page: compare `src/views/exam_list_view.py`, `src/views/exam_details_view.py`, or `src/views/exam_add_external_view.py`.
   - Component or dialog: compare files under `src/views/components/`.
   - ViewModel: compare the matching file under `src/viewmodels/`.
   - Model/data code: compare `src/models/exam.py`, `src/models/database.py`, or `src/models/sync.py`.
3. Keep generated code out of `src/views/`. Generate or place `ui_*.py` files under `ui_gen/`.
4. Import generated UI classes from `ui_gen`, never from `src.views`:

```python
from ui_gen.ui_example_view import Ui_ExampleView
```

5. In the hand-written view, call `self.ui.setupUi(self)` before custom widget access, signal wiring, or layout changes.
6. Put widget behavior in the view. Put state transitions, validation decisions, and model calls in the viewmodel. Put storage and external data concerns in models.
7. Register navigation in `src/views/main_window.py` only when the new view is a navigable page.
8. Update docs when the structure, navigation, or integration pattern changes.
9. Follow `pyrightconfig.json` for strict typing expectations while integrating code.
10. Validate with syntax checks, UI setup checks, Pyright, and Ruff when available.

## Layer Rules

### UI files

- Edit `.ui` files in `ui/`.
- Regenerate generated modules into `ui_gen/` with:

```powershell
.\.venv\Scripts\pyside6-uic.exe ui\example_view.ui -o ui_gen\ui_example_view.py
```

- Do not hand-edit files in `ui_gen/` except for emergency diagnosis; fix the `.ui` source instead.
- Do not leave generated `ui_*.py` files in `src/views/` or `src/views/components/`.

### Views

- Subclass the correct PySide6 widget type for the generated UI root.
- Own all `QtWidgets` imports, signal-slot connections, widget state changes, dialogs, menus, and layout manipulation.
- Use a `self.ui = Ui_...()` field and call `self.ui.setupUi(self)` first.
- Use `blockSignals(True)` around programmatic widget updates that could trigger slots.
- Use `src.utils.qt.clear_layout` for dynamic layout cleanup so widgets, nested layouts, spacers, and `None` items are handled consistently.
- Convert UI events into viewmodel method calls. Keep database queries and API calls out of views.

### ViewModels

- Inherit from `QObject` only when signals are needed.
- Import from `PySide6.QtCore`; do not import `PySide6.QtWidgets`.
- Expose state through plain attributes, return values, dataclasses, and Qt signals.
- Call model/service functions for persistence and external work.
- Avoid direct widget access, dialogs, layouts, or generated UI classes.

### Typing

- Treat `pyrightconfig.json` as the source of truth for static typing rules.
- The project uses Pyright `strict` mode with Python 3.9 compatibility.
- Add concrete parameter, return, variable, and generic type annotations when new or changed code would otherwise produce unknown or missing types.
- Avoid unused imports and unused variables; Pyright reports both in this repo.
- Keep annotations compatible with Python 3.9 syntax. Prefer `Optional[...]` and `Union[...]` for runtime-evaluated annotations unless the file already enables postponed annotations safely.

### Models

- Keep database, sync, and domain logic in `src/models/`.
- Return plain Python data structures or dataclasses suitable for viewmodels.
- Avoid imports from `src/views`, `src/viewmodels`, or `ui_gen`.

## Naming Pattern

Use consistent names across layers:

- `ui/example_view.ui`
- `ui_gen/ui_example_view.py`
- `src/views/example_view.py`
- `src/viewmodels/example_viewmodel.py`
- Optional model support in `src/models/example.py`

For components and dialogs:

- `ui/example_dialog.ui`
- `ui_gen/ui_example_dialog.py`
- `src/views/components/example_dialog.py`

## Minimal View Template

```python
from PySide6.QtWidgets import QWidget

from ui_gen.ui_example_view import Ui_ExampleView
from src.viewmodels.example_viewmodel import ExampleViewModel


class ExampleView(QWidget):
    def __init__(self, viewmodel: ExampleViewModel | None = None, parent=None):
        super().__init__(parent)
        self.ui = Ui_ExampleView()
        self.ui.setupUi(self)
        self.viewmodel = viewmodel or ExampleViewModel()

        self._connect_signals()
        self._refresh()

    def _connect_signals(self) -> None:
        self.ui.reload_button.clicked.connect(self._refresh)

    def _refresh(self) -> None:
        self.ui.status_label.setText(self.viewmodel.status_text())
```

## Minimal ViewModel Template

```python
from PySide6.QtCore import QObject, Signal


class ExampleViewModel(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

    def status_text(self) -> str:
        return "Ready"
```

## Integration Checklist

- The `.ui` source exists in `ui/`.
- The generated `ui_*.py` module exists in `ui_gen/`.
- Hand-written views import generated UI from `ui_gen`.
- The view calls `setupUi(self)` before custom setup.
- Viewmodels have no `QtWidgets` imports.
- Models do not import views, viewmodels, or generated UI modules.
- Dynamic layouts use `clear_layout` where relevant.
- Programmatic widget updates block signals where needed.
- New or changed Python code follows `pyrightconfig.json` strict typing rules.
- `docs/README.md`, `docs/architecture.md`, or `docs/views.md` are updated for new structure or navigation.
- Validation commands have been run or their blockers are reported.

## Validation Commands

Prefer module-style commands from the project root:

```powershell
.\.venv\Scripts\python.exe -B -c "import pathlib; [compile(path.read_text(encoding='utf-8-sig'), str(path), 'exec') for root in ('src','ui_gen') for path in pathlib.Path(root).rglob('*.py')]; print('syntax ok')"
.\.venv\Scripts\python.exe -m pyright
.\.venv\Scripts\python.exe -m ruff check .
```

For UI setup smoke tests, set `QT_QPA_PLATFORM=offscreen` before constructing widgets.
