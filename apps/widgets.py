from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QSpinBox,
    QToolButton,
)
from PySide6.QtCore import Qt


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
