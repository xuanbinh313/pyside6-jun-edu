# Architecture

Jun Edu is a desktop exam management app built with Python and PySide6. The code
is organized around MVVM boundaries, with database-specific work hidden behind
repository interfaces so SQLite and Supabase can coexist.

## Directory Structure

```text
jun-edu/
|-- main.py
|-- requirement.md
|-- pyproject.toml
|-- requirements.txt
|-- cmd/
|-- docs/
|-- resources/
|-- ui/
|   |-- main_window.ui
|   |-- exam_list_view.ui
|   |-- exam_details_view.ui
|   `-- ...
|-- ui_gen/
|   |-- __init__.py
|   |-- ui_main_window.py
|   |-- ui_exam_list_view.py
|   `-- ...
`-- src/
    |-- models/
    |   `-- exam.py
    |-- repositories/
    |   |-- base_repo.py
    |   |-- sqlite/
    |   |   |-- database.py
    |   |   |-- orm_models.py
    |   |   `-- sqlite_repo.py
    |   `-- supabase/
    |       |-- auth.py
    |       |-- client.py
    |       |-- sync.py
    |       `-- supabase_repo.py
    |-- utils/
    |   |-- helpers.py
    |   `-- qt.py
    |-- viewmodels/
    |   |-- auth_viewmodel.py
    |   |-- exam_list_viewmodel.py
    |   |-- exam_take_viewmodel.py
    |   |-- exam_details_viewmodel.py
    |   |-- exam_add_external_viewmodel.py
    |   |-- exam_transcript_viewmodel.py
    |   `-- reminder_viewmodel.py
    `-- views/
        |-- auth_view.py
        |-- main_window.py
        |-- exam_list_view.py
        |-- exam_take_view.py
        |-- exam_details_view.py
        |-- exam_add_external_view.py
        `-- components/
            |-- exam_form_widget.py
            |-- exam_groups_widget.py
            |-- exam_transcript_widget.py
            `-- ...
```

## Layer Rules

| Layer | Owns | Must avoid |
|---|---|---|
| Models | Pure dataclasses and framework-agnostic entities | SQLAlchemy, PySide6, sessions |
| Repositories | Data access interfaces, SQLite ORM, Supabase mapping | Widget/UI concerns |
| ViewModels | State, validation, repository calls, background work, QtCore signals | `PySide6.QtWidgets`, SQLAlchemy sessions |
| Views | Generated UI setup, signal-slot wiring, user interaction, widget styling | Database/session logic |
| `ui_gen` | Generated `Ui_*` classes | Manual edits |

Views import generated UI classes from `ui_gen` only:

```python
from ui_gen.ui_exam_details_view import Ui_ExamDetailsView
```

## UI Generation

`ui/*.ui` files are the editable Qt Designer sources. `ui_gen/ui_*.py` files are
generated with `pyside6-uic`.

When a `.ui` file changes, regenerate the matching module:

```bash
pyside6-uic ui/exam_details_view.ui -o ui_gen/ui_exam_details_view.py
```

After regeneration, behavior stays in `src/views/...`; do not add custom code to
`ui_gen`.

## Data Flow

```text
View -> calls/slots -> ViewModel -> repository interface -> Repository -> SQLite/Supabase
View <- signals <- ViewModel
```

- Views create `Ui_*`, call `setupUi(self)`, then connect signals and apply custom widget behavior.
- ViewModels emit signals when state changes.
- ViewModels receive repository instances through constructor injection. The default local implementation is `SQLiteExamRepository`.
- SQLite sessions are owned and closed inside repository methods.
- SQLAlchemy ORM classes live in `src.repositories.sqlite.orm_models`, not in `src.models`.

## Navigation

`main.py` opens `MainWindow` directly so the local exam tools remain available
without logging in. `MainWindow` owns account state and opens `AuthView` as a
modal login/register dialog from the menu. A valid saved Supabase session
restores the signed-in menu state in the background.

`MainWindow` owns the exam `QStackedWidget`:

- Slot 0 is always `ExamListView`.
- Slot 1 is either `ExamDetailsView` or `ExamAddExternalView`.
- Returning to the list refreshes exams and removes slot 1.

## Robust Qt Practices

- Call `setupUi(self)` before using generated widgets.
- Check for missing widgets/items before calling methods on them.
- Use `blockSignals(True)` during programmatic table, list, combo, or text updates.
- Use `src.utils.qt.clear_layout()` for dynamic layout cleanup. It handles widgets, nested layouts, spacer items, and `None` items.

## Repository Migration

- Pure entities live in `src.models.exam` as dataclasses. They are safe to pass through repositories, ViewModels, and Views.
- SQLAlchemy engine/session setup lives in `src.repositories.sqlite.database`.
- SQLAlchemy ORM declarations live in `src.repositories.sqlite.orm_models`.
- Repository interfaces live in `src.repositories.base_repo`; ViewModels should receive these through constructor injection.
- `ExamListViewModel`, `ExamDetailsViewModel`, and `ExamTranscriptViewModel` now use `IExamRepository` and default to `SQLiteExamRepository`.
- Some legacy views and larger ViewModels still call SQLite infrastructure directly during the incremental migration. New work should move those calls behind repository methods rather than adding new direct session usage.
