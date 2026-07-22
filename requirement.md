# Zoom In / Out Shortcuts

Add application-wide zoom capability to the application, allowing users to zoom in/out with `Ctrl +` and `Ctrl -`, and reset zoom to default using `Ctrl 0`.

## Proposed Changes

We will modify [main_window.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/main_window.py) to declare zoom actions, register keyboard shortcuts, and scale the application-wide default font size.

### Views

#### [MODIFY] [main_window.py](file:///d:/my-project/workspace-anki/jun-edu/src/views/main_window.py)
- Import `QKeySequence` from `PySide6.QtGui`.
- Initialize zoom state and actions in `MainWindow.__init__`.
- Register the shortcuts:
  - **Zoom In**: `Ctrl +` and `Ctrl =`
  - **Zoom Out**: `Ctrl -`
  - **Reset**: `Ctrl 0`
- Implement scaling logic by adjusting the application-wide font point size via `QApplication.setFont()`.

## Verification Plan

### Manual Verification
1. Run the application:
   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```
2. Press `Ctrl +` (or `Ctrl =`) several times and verify that all UI fonts, layouts, and text elements scale up accordingly.
3. Press `Ctrl -` several times and verify that all UI elements scale down accordingly.
4. Press `Ctrl 0` to verify that the font sizes return to their default sizes.
5. Check that the status bar shows the temporary zoom feedback messages (e.g., `Zoom level: +1 (Font size: 13pt)`).
