from PySide6.QtWidgets import QLayout


def clear_layout(layout: QLayout, keep_tail: int = 0) -> None:
    """Recursively remove layout items, widgets, child layouts, and spacers."""
    while layout.count() > keep_tail:
        item = layout.takeAt(0)
        if item is None:
            continue

        child_layout = item.layout()
        if child_layout is not None:
            clear_layout(child_layout)
            child_layout.deleteLater()
            continue

        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
            continue

        # Spacer-only items need no explicit deletion; taking them out is enough.
