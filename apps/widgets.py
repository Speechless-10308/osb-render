from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSpinBox,
    QToolButton,
    QCheckBox,
)
from PySide6.QtCore import Qt, QSize, QRectF
from PySide6.QtGui import QColor, QPainter


class ToggleSwitch(QCheckBox):
    """A compact accessible checkbox painted as a modern sliding switch."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._dark_mode = True
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(28)

    def set_theme(self, dark_mode: bool) -> None:
        self._dark_mode = dark_mode
        self.update()

    def sizeHint(self) -> QSize:
        text_width = self.fontMetrics().horizontalAdvance(self.text()) if self.text() else 0
        return QSize(48 + text_width, 28)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        enabled = self.isEnabled()
        checked = self.isChecked()

        track_width, track_height = 38.0, 22.0
        track_x = 0.0
        track_y = (self.height() - track_height) / 2
        if checked:
            track = QColor("#ff5c9e" if self._dark_mode else "#e84f91")
        else:
            track = QColor("#3a414d" if self._dark_mode else "#c7ced8")
        if not enabled:
            track.setAlpha(120)

        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(
            QRectF(track_x, track_y, track_width, track_height), 11, 11
        )

        knob_diameter = 16.0
        knob_margin = 3.0
        knob_x = (track_width - knob_diameter - knob_margin) if checked else knob_margin
        knob_y = track_y + knob_margin
        painter.setBrush(QColor("#ffffff" if enabled else "#c8cbd1"))
        painter.drawEllipse(QRectF(knob_x, knob_y, knob_diameter, knob_diameter))

        if self.text():
            text_color = QColor("#f2f4f7" if self._dark_mode else "#28303b")
            if not enabled:
                text_color.setAlpha(130)
            painter.setPen(text_color)
            text_rect = self.rect().adjusted(48, 0, 0, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, self.text())
        painter.end()


class ResolutionWidget(QWidget):
    def __init__(self, width: int, height: int, parent=None):
        super().__init__(parent)
        self.output_width = width
        self.output_height = height
        self.aspect_ratio = width / height

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        input_layout = QVBoxLayout()
        input_layout.setSpacing(8)

        width_row = QHBoxLayout()
        width_row.setSpacing(8)
        w_label = QLabel("Width")
        self.width_spin = QSpinBox()
        self.width_spin.setObjectName("resSpinBox")
        self.width_spin.setRange(100, 7680)
        self.width_spin.setValue(self.output_width)
        self.width_spin.valueChanged.connect(self.on_width_changed)
        width_row.addWidget(w_label)
        width_row.addWidget(self.width_spin)

        height_row = QHBoxLayout()
        height_row.setSpacing(8)
        h_label = QLabel("Height")
        self.height_spin = QSpinBox()
        self.height_spin.setObjectName("resSpinBox")
        self.height_spin.setRange(100, 4320)
        self.height_spin.setValue(self.output_height)
        self.height_spin.valueChanged.connect(self.on_height_changed)
        height_row.addWidget(h_label)
        height_row.addWidget(self.height_spin)

        input_layout.addLayout(width_row)
        input_layout.addLayout(height_row)

        self.link_btn = QToolButton()
        self.link_btn.setObjectName("linkBtn")
        self.link_btn.setText("\U0001F517")
        self.link_btn.setCheckable(True)
        self.link_btn.setChecked(True)
        self.link_btn.setToolTip("Lock Aspect Ratio")
        self.link_btn.toggled.connect(self.on_link_toggled)
        self.link_btn.setCursor(Qt.PointingHandCursor)

        layout.addLayout(input_layout)
        layout.addWidget(self.link_btn)

    def on_link_toggled(self, checked: bool):
        if checked:
            h = self.height_spin.value()
            if h > 0:
                self.aspect_ratio = self.width_spin.value() / h

    def on_width_changed(self, value: int):
        if self.link_btn.isChecked():
            new_height = round(value / self.aspect_ratio)
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(new_height)
            self.height_spin.blockSignals(False)

    def on_height_changed(self, value: int):
        if self.link_btn.isChecked():
            new_width = round(value * self.aspect_ratio)
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(new_width)
            self.width_spin.blockSignals(False)

    def set_values(self, width: int, height: int):
        self.width_spin.setValue(width)
        self.height_spin.setValue(height)
        self.aspect_ratio = width / height

    def get_values(self) -> tuple[int, int]:
        return self.width_spin.value(), self.height_spin.value()
