from PySide6.QtCore import QObject, Signal, QTimer

class ReminderViewModel(QObject):
    # Signals for View binding
    show_study_window = Signal()
    tick_tock = Signal(int)  # Emits remaining seconds

    def __init__(self):
        super().__init__()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer_timeout)
        self.time_left_seconds = 0

    def start_countdown(self, minutes: int):
        """Triggered by the View when user sets the timer."""
        self.time_left_seconds = minutes * 60
        self.timer.start(1000)  # Ticks every 1 second (1000ms)

    def _on_timer_timeout(self):
        self.time_left_seconds -= 1
        self.tick_tock.emit(self.time_left_seconds)
        
        if self.time_left_seconds <= 0:
            self.timer.stop()
            self.show_study_window.emit()  # Notify View to wake up
