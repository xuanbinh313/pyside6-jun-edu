# Architecture

Jun Edu is a desktop exam management app built with Python, PySide6, SQLAlchemy, and SQLite. The code is organized around MVVM boundaries.

## Directory Structure

```text
jun-edu/
├── main.py
├── requirement.md
├── pyproject.toml
├── requirements.txt
├── cmd/
├── docs/
├── resources/
├── ui/
│   ├── main_window.ui
│   ├── exam_list_view.ui
│   ├── exam_details_view.ui
│   └── ...
├── ui_gen/
│   ├── __init__.py
│   ├── ui_main_window.py
│   ├── ui_exam_list_view.py
│   └── ...
└── src/
    ├── models/
    │   ├── database.py
    │   └── exam.py
    ├── utils/
    │   ├── helpers.py
    │   └── qt.py
    ├── viewmodels/
    │   ├── exam_list_viewmodel.py
    │   ├── exam_take_viewmodel.py
    │   ├── exam_details_viewmodel.py
    │   ├── exam_add_external_viewmodel.py
    │   ├── exam_transcript_viewmodel.py
    │   └── reminder_viewmodel.py
    └── views/
        ├── main_window.py
        ├── exam_list_view.py
        ├── exam_take_view.py
        ├── exam_details_view.py
        ├── exam_add_external_view.py
        └── components/
            ├── exam_form_widget.py
            ├── exam_groups_widget.py
            ├── exam_transcript_widget.py
            └── ...
```

## Layer Rules

| Layer | Owns | Must avoid |
|---|---|---|
| Models | SQLAlchemy tables and DB bootstrap | Qt imports |
| ViewModels | State, persistence, background work, QtCore signals | `PySide6.QtWidgets` |
| Views | Generated UI setup, signal-slot wiring, user interaction, widget styling | Long-lived business logic |
| `ui_gen` | Generated `Ui_*` classes | Manual edits |

Views import generated UI classes from `ui_gen` only:

```python
from ui_gen.ui_exam_details_view import Ui_ExamDetailsView
```

## UI Generation

`ui/*.ui` files are the editable Qt Designer sources. `ui_gen/ui_*.py` files are generated with `pyside6-uic`.

When a `.ui` file changes, regenerate the matching module:

```bash
pyside6-uic ui/exam_details_view.ui -o ui_gen/ui_exam_details_view.py
```

After regeneration, behavior stays in `src/views/...`; do not add custom code to `ui_gen`.

## Data Flow

```text
View ──calls/slots──> ViewModel ──queries/commits──> Model/DB
View <──signals────── ViewModel
```

- Views create `Ui_*`, call `setupUi(self)`, then connect signals and apply custom widget behavior.
- ViewModels emit signals when state changes.
- Database sessions come from `src.models.database.get_session()` and must be closed by the caller.

## Navigation

`MainWindow` owns the `QStackedWidget`:

- Slot 0 is always `ExamListView`.
- Slot 1 is either `ExamDetailsView` or `ExamAddExternalView`.
- Returning to the list refreshes exams and removes slot 1.

## Robust Qt Practices

- Call `setupUi(self)` before using generated widgets.
- Check for missing widgets/items before calling methods on them.
- Use `blockSignals(True)` during programmatic table, list, combo, or text updates.
- Use `src.utils.qt.clear_layout()` for dynamic layout cleanup. It handles widgets, nested layouts, spacer items, and `None` items.
