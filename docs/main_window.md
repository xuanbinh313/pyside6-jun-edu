# `MainWindow` — Entry Point & Navigation Controller

**File:** [`src/views/main_window.py`](../src/views/main_window.py)  
**Base class:** `QMainWindow`

`MainWindow` is the application shell. It owns all top-level ViewModels, controls navigation between screens via a `QStackedWidget`, manages the system tray, and wires up the reminder/wake-up flow.

---

## Startup Sequence

The startup sequence is executed from the root [`main.py`](../main.py):

```python
# main.py entry block
init_db()              # Create DB tables if missing
app = QApplication()
splash = create_startup_splash()
splash.show()
widget = MainWindow(splash=splash)
widget.show()
splash.finish(widget)
app.exec()
```

`main.py` shows a lightweight `QSplashScreen` from
`create_startup_splash()` while `MainWindow` builds the application shell.
`MainWindow` updates the splash message during setup, then the splash closes
once the main window is visible. It owns `AuthViewModel`, checks for a saved
Supabase session in the background, and opens `AuthView` as a modal account
dialog only when the user chooses Login / Register from the menu.

Inside `MainWindow.__init__`:
1. `ReminderViewModel` created (owns the countdown timer)
2. `QStackedWidget` set as central widget
3. `ExamListViewModel` + `ExamListView` created and added to stack slot 0
4. Menu bar configured
5. System tray configured
6. MVVM signal bindings applied
7. Plugin registry connections applied and enabled plugins loaded from `plugins/`

---

## Navigation Methods

### `navigate_to_details(exam_id)`

| `exam_id` | Behavior |
|---|---|
| `"EXTERNAL"` | Creates `ExamAddExternalViewModel` + `ExamAddExternalView`, pushes to stack slot 1 |
| `str` (UUID) | Creates `ExamDetailsViewModel(exam_id)` + `ExamDetailsView`, pushes to stack slot 1 |
| `None` | Creates `ExamDetailsViewModel(None)` + `ExamDetailsView` (new exam), pushes to slot 1 |

### `navigate_to_take_exam(exam_id)`

Creates `ExamTakeViewModel(exam_id)` + `ExamTakeView`, pushes it to stack slot 1, and shows the learner-facing overview/history/mode selection screen.

### `navigate_to_list()`

1. Calls `list_viewmodel.load_exams()` to refresh data
2. Sets stack to slot 0 (list view)
3. Removes and destroys the widget in slot 1 (`removeWidget` + `deleteLater`)

---

## Menu Bar

The menu bar includes a "Menu" entry with these actions:

| Action | Handler | Description |
|---|---|---|
| "Login / Register" | `show_auth_modal()` | Opens the auth modal without leaving the current app view |
| "Vocabulary List" | `navigate_to_vocabulary()` | Opens the searchable vocabulary status table |
| "Sync to Remote" | `sync_viewmodel.sync_to_supabase()` | Uploads local SQLite data to Supabase |
| "Sync to Local" | `sync_viewmodel.sync_to_local()` | Downloads Supabase data and R2 media into local SQLite/temp storage |
| "Settings" | `show_settings_modal()` | `QInputDialog.getInt` to set `close_event_minutes` (1–1440) |
| "Logout" | `auth_viewmodel.sign_out()` | Signs out and clears saved tokens while staying in the main app |

Plugins can add actions to the "Plugins" menu and plugin toolbar at runtime.
These actions are registered through `UIRegistry`; failed or disabled plugins do
not contribute actions.

It also includes a "Views" entry with these actions:

| Action | Handler | Description |
|---|---|---|
| "Zoom In" | `zoom_in()` | Increases the application font zoom level |
| "Zoom Out" | `zoom_out()` | Decreases the application font zoom level |

`close_event_minutes` controls how many minutes the reminder countdown runs when the user closes the window.

---

## System Tray

| Element | Description |
|---|---|
| Icon | `fa5s.graduation-cap` in `#1a73e8` blue (via `qtawesome`) |
| Context menu — "Mở ứng dụng" | `showNormal()` — restore window |
| Context menu — "Thoát hoàn toàn" | `QApplication.quit()` — full exit |
| Double-click | `showNormal()` — restore window |

---

## `closeEvent(event)`

Overrides default close behavior. When the window is closed:

1. Starts `ReminderViewModel.start_countdown(close_event_minutes)`
2. Calls `self.hide()` — hides the window (does **not** quit)
3. Shows a tray notification: *"Đã tự động hẹn giờ N phút và chạy ngầm dưới khay hệ thống!"*
4. Calls `event.ignore()` — prevents the app from actually quitting

---

## `wakeup_and_focus_app()`

Connected to `ReminderViewModel.show_study_window` signal. Called when the countdown hits zero.

1. Shows an urgent tray notification: *"ĐẾN GIỜ HỌC RỒI!"*
2. Restores and focuses the window:
   ```python
   self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
   self.showNormal()
   self.raise_()
   self.activateWindow()
   ```

---

## Signal Bindings Summary

| ViewModel Signal | Connected To |
|---|---|
| `ReminderViewModel.show_study_window` | `MainWindow.wakeup_and_focus_app` |

All other bindings (ViewModel → View) are set up inside the View constructors.

## Plugin Pages

Plugin pages are registered as factories and created only when requested. Opening
a plugin page clears the transient slot(s) above the exam list, then shows the
plugin widget in the main `QStackedWidget`. Plugin cleanup runs from
`QApplication.aboutToQuit` through `MainWindow.shutdown_plugins()`.
