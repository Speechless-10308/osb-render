from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QWidget, QSizeGrip, QFrame, QHBoxLayout


class CustomGrip(QWidget):
    """Invisible resize handles for frameless windows.

    Ported from PyDracula (MIT licensed) and adapted for OSBoard.
    """

    def __init__(self, parent, position, disable_color=False):
        super().__init__()
        self._parent = parent
        self.setParent(parent)
        self._wi = _GripWidgets()

        if position == Qt.TopEdge:
            self._wi.top(self)
            self.setGeometry(0, 0, self._parent.width(), 10)
            self.setMaximumHeight(10)

            QSizeGrip(self._wi.top_left)
            QSizeGrip(self._wi.top_right)

            def resize_top(event):
                delta = event.pos()
                h = max(self._parent.minimumHeight(), self._parent.height() - delta.y())
                geo = self._parent.geometry()
                geo.setTop(geo.bottom() - h)
                self._parent.setGeometry(geo)
                event.accept()
            self._wi.top.mouseMoveEvent = resize_top

            if disable_color:
                self._wi.top_left.setStyleSheet("background: transparent")
                self._wi.top_right.setStyleSheet("background: transparent")
                self._wi.top.setStyleSheet("background: transparent")

        elif position == Qt.BottomEdge:
            self._wi.bottom(self)
            self.setGeometry(0, self._parent.height() - 10, self._parent.width(), 10)
            self.setMaximumHeight(10)

            QSizeGrip(self._wi.bottom_left)
            QSizeGrip(self._wi.bottom_right)

            def resize_bottom(event):
                delta = event.pos()
                h = max(self._parent.minimumHeight(), self._parent.height() + delta.y())
                self._parent.resize(self._parent.width(), h)
                event.accept()
            self._wi.bottom.mouseMoveEvent = resize_bottom

            if disable_color:
                self._wi.bottom_left.setStyleSheet("background: transparent")
                self._wi.bottom_right.setStyleSheet("background: transparent")
                self._wi.bottom.setStyleSheet("background: transparent")

        elif position == Qt.LeftEdge:
            self._wi.left(self)
            self.setGeometry(0, 10, 10, self._parent.height())
            self.setMaximumWidth(10)

            def resize_left(event):
                delta = event.pos()
                w = max(self._parent.minimumWidth(), self._parent.width() - delta.x())
                geo = self._parent.geometry()
                geo.setLeft(geo.right() - w)
                self._parent.setGeometry(geo)
                event.accept()
            self._wi.leftgrip.mouseMoveEvent = resize_left

            if disable_color:
                self._wi.leftgrip.setStyleSheet("background: transparent")

        elif position == Qt.RightEdge:
            self._wi.right(self)
            self.setGeometry(self._parent.width() - 10, 10, 10, self._parent.height())
            self.setMaximumWidth(10)

            def resize_right(event):
                delta = event.pos()
                w = max(self._parent.minimumWidth(), self._parent.width() + delta.x())
                self._parent.resize(w, self._parent.height())
                event.accept()
            self._wi.rightgrip.mouseMoveEvent = resize_right

            if disable_color:
                self._wi.rightgrip.setStyleSheet("background: transparent")

    def resizeEvent(self, event):
        if hasattr(self._wi, "container_top"):
            self._wi.container_top.setGeometry(0, 0, self.width(), 10)
        elif hasattr(self._wi, "container_bottom"):
            self._wi.container_bottom.setGeometry(0, 0, self.width(), 10)
        elif hasattr(self._wi, "leftgrip"):
            self._wi.leftgrip.setGeometry(0, 0, 10, self.height() - 20)
        elif hasattr(self._wi, "rightgrip"):
            self._wi.rightgrip.setGeometry(0, 0, 10, self.height() - 20)


class _GripWidgets:
    """Internal helper that builds the grip frame layouts."""

    def top(self, form):
        if not form.objectName():
            form.setObjectName("Form")
        self.container_top = QFrame(form)
        self.container_top.setObjectName("container_top")
        self.container_top.setGeometry(QRect(0, 0, 500, 10))
        self.container_top.setMinimumSize(QSize(0, 10))
        self.container_top.setMaximumSize(QSize(16777215, 10))
        self.container_top.setFrameShape(QFrame.NoFrame)
        self.container_top.setFrameShadow(QFrame.Raised)
        layout = QHBoxLayout(self.container_top)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.top_left = QFrame(self.container_top)
        self.top_left.setObjectName("top_left")
        self.top_left.setMinimumSize(QSize(10, 10))
        self.top_left.setMaximumSize(QSize(10, 10))
        self.top_left.setCursor(QCursor(Qt.SizeFDiagCursor))
        self.top_left.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.top_left)
        self.top = QFrame(self.container_top)
        self.top.setObjectName("top")
        self.top.setCursor(QCursor(Qt.SizeVerCursor))
        self.top.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.top)
        self.top_right = QFrame(self.container_top)
        self.top_right.setObjectName("top_right")
        self.top_right.setMinimumSize(QSize(10, 10))
        self.top_right.setMaximumSize(QSize(10, 10))
        self.top_right.setCursor(QCursor(Qt.SizeBDiagCursor))
        self.top_right.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.top_right)

    def bottom(self, form):
        if not form.objectName():
            form.setObjectName("Form")
        self.container_bottom = QFrame(form)
        self.container_bottom.setObjectName("container_bottom")
        self.container_bottom.setGeometry(QRect(0, 0, 500, 10))
        self.container_bottom.setMinimumSize(QSize(0, 10))
        self.container_bottom.setMaximumSize(QSize(16777215, 10))
        self.container_bottom.setFrameShape(QFrame.NoFrame)
        layout = QHBoxLayout(self.container_bottom)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.bottom_left = QFrame(self.container_bottom)
        self.bottom_left.setObjectName("bottom_left")
        self.bottom_left.setMinimumSize(QSize(10, 10))
        self.bottom_left.setMaximumSize(QSize(10, 10))
        self.bottom_left.setCursor(QCursor(Qt.SizeBDiagCursor))
        self.bottom_left.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.bottom_left)
        self.bottom = QFrame(self.container_bottom)
        self.bottom.setObjectName("bottom")
        self.bottom.setCursor(QCursor(Qt.SizeVerCursor))
        self.bottom.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.bottom)
        self.bottom_right = QFrame(self.container_bottom)
        self.bottom_right.setObjectName("bottom_right")
        self.bottom_right.setMinimumSize(QSize(10, 10))
        self.bottom_right.setMaximumSize(QSize(10, 10))
        self.bottom_right.setCursor(QCursor(Qt.SizeFDiagCursor))
        self.bottom_right.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.bottom_right)

    def left(self, form):
        if not form.objectName():
            form.setObjectName("Form")
        self.leftgrip = QFrame(form)
        self.leftgrip.setObjectName("left")
        self.leftgrip.setGeometry(QRect(0, 10, 10, 480))
        self.leftgrip.setMinimumSize(QSize(10, 0))
        self.leftgrip.setCursor(QCursor(Qt.SizeHorCursor))
        self.leftgrip.setFrameShape(QFrame.NoFrame)

    def right(self, form):
        if not form.objectName():
            form.setObjectName("Form")
        form.resize(500, 500)
        self.rightgrip = QFrame(form)
        self.rightgrip.setObjectName("right")
        self.rightgrip.setGeometry(QRect(0, 0, 10, 500))
        self.rightgrip.setMinimumSize(QSize(10, 0))
        self.rightgrip.setCursor(QCursor(Qt.SizeHorCursor))
        self.rightgrip.setFrameShape(QFrame.NoFrame)
