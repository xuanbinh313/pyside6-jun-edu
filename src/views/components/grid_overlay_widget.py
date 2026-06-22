from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class GridOverlayWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Khởi tạo vị trí và kích thước mặc định cho Khung lưới
        self.grid_rect = QRect(50, 50, 400, 500)

        self.is_resizing = False
        self.is_moving = False
        self.drag_start_pos = QPoint()

        # Cấu hình lưới trắc nghiệm (Ví dụ: Đề 100 câu chia làm 4 cột x 25 dòng)
        self.COLS = 10
        self.ROWS_PER_COL = 10
        self.OPTIONS = 4  # A, B, C, D

        # Bật tính năng theo dõi chuột
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Vẽ vùng mờ bên ngoài khung lưới để user tập trung
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(
            self.grid_rect, Qt.GlobalColor.transparent
        )  # Đục lỗ phần khung lưới
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # 2. Vẽ viền Khung lớn (Màu xanh neon cho nổi bật)
        pen_main = QPen(QColor(0, 255, 0), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen_main)
        painter.drawRect(self.grid_rect)

        # Vẽ handle nhỏ ở góc dưới bên phải để user biết chỗ kéo
        painter.fillRect(
            self.grid_rect.right() - 10,
            self.grid_rect.bottom() - 10,
            10,
            10,
            QColor(0, 255, 0),
        )

        # 3. VẼ LƯỚI TỰ ĐỘNG BÊN TRONG (Toán học chia tỷ lệ)
        pen_grid = QPen(QColor(0, 255, 0, 100), 1, Qt.PenStyle.DashLine)
        painter.setPen(pen_grid)

        w_col = self.grid_rect.width() / self.COLS
        h_row = self.grid_rect.height() / self.ROWS_PER_COL

        # Vẽ các cột dọc chính
        for c in range(1, self.COLS):
            x_pos = self.grid_rect.x() + int(c * w_col)
            painter.drawLine(x_pos, self.grid_rect.y(), x_pos, self.grid_rect.bottom())

        # Vẽ các hàng ngang (25 dòng)
        for r in range(1, self.ROWS_PER_COL):
            y_pos = self.grid_rect.y() + int(r * h_row)
            painter.drawLine(self.grid_rect.x(), y_pos, self.grid_rect.right(), y_pos)

    def mousePressEvent(self, event):
        mouse_pos = event.position().toPoint()

        # Kiểm tra nếu bấm vào góc dưới-phải (Vùng kích thước 15x15 pixel) để resize
        handle_rect = QRect(
            self.grid_rect.right() - 15, self.grid_rect.bottom() - 15, 15, 15
        )
        if handle_rect.contains(mouse_pos):
            self.is_resizing = True
        # Nếu bấm vào bên trong khung thì là di chuyển khung
        elif self.grid_rect.contains(mouse_pos):
            self.is_moving = True
            self.drag_start_pos = mouse_pos - self.grid_rect.topLeft()

    def mouseMoveEvent(self, event):
        mouse_pos = event.position().toPoint()

        # Thay đổi con trỏ chuột khi đi qua vùng góc để gợi ý user
        handle_rect = QRect(
            self.grid_rect.right() - 15, self.grid_rect.bottom() - 15, 15, 15
        )
        if handle_rect.contains(mouse_pos) or self.is_resizing:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)  # Con trỏ mũi tên chéo
        elif self.grid_rect.contains(mouse_pos):
            self.setCursor(Qt.CursorShape.SizeAllCursor)  # Con trỏ bốn hướng
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        # Thực thi Resize
        if self.is_resizing:
            new_width = max(100, mouse_pos.x() - self.grid_rect.x())
            new_height = max(100, mouse_pos.y() - self.grid_rect.y())
            self.grid_rect.setSize(QSize(new_width, new_height))
            self.update()

        # Thực thi Di chuyển
        elif self.is_moving:
            self.grid_rect.moveTopLeft(mouse_pos - self.drag_start_pos)
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_resizing = False
        self.is_moving = False
