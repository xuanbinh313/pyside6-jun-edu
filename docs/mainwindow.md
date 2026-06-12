# `MainWindow` — Entry Point & Navigation Controller

**File:** [`mainwindow.py`](../mainwindow.py)  
**Base class:** `QMainWindow`

`MainWindow` is the application shell. It owns all top-level ViewModels, controls navigation between screens via a `QStackedWidget`, manages the system tray, and wires up the reminder/wake-up flow.

---

## Startup Sequence

```python
# __main__ block
init_db()              # Create DB tables if missing
app = QApplication()
widget = MainWindow()
widget.show()
app.exec()
```

Inside `MainWindow.__init__`:
1. `ReminderViewModel` created (owns the countdown timer)
2. `QStackedWidget` set as central widget
3. `ExamListViewModel` + `ExamListView` created and added to stack slot 0
4. Menu bar configured
5. System tray configured
6. MVVM signal bindings applied

---

## Navigation Methods

### `navigate_to_details(exam_id)`

| `exam_id` | Behavior |
|---|---|
| `"EXTERNAL"` | Creates `ExamAddExternalViewModel` + `ExamAddExternalView`, pushes to stack slot 1 |
| `str` (UUID) | Creates `ExamDetailsViewModel(exam_id)` + `ExamDetailsView`, pushes to stack slot 1 |
| `None` | Creates `ExamDetailsViewModel(None)` + `ExamDetailsView` (new exam), pushes to slot 1 |

### `navigate_to_list()`

1. Calls `list_viewmodel.load_exams()` to refresh data
2. Sets stack to slot 0 (list view)
3. Removes and destroys the widget in slot 1 (`removeWidget` + `deleteLater`)

---

## Menu Bar

Single "Menu" entry with one action:

| Action | Handler | Description |
|---|---|---|
| "Settings" | `show_settings_modal()` | `QInputDialog.getInt` to set `close_event_minutes` (1–1440) |

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
