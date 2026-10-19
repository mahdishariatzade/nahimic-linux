"""Custom chrome with compositor-managed movement and resizing."""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QIcon, QColor, QPen
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QStyle, QDialog, QStylePainter, QStyleOptionToolButton

class ResizeEdge(QWidget):
    def __init__(self, window, edges, cursor):
        super().__init__(window)
        self.edges = edges
        self.setCursor(cursor)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self.window().windowHandle()
            if handle and handle.startSystemResize(self.edges):
                event.accept()
                return
        super().mousePressEvent(event)

class WindowButton(QToolButton):
    def __init__(self, symbol):
        super().__init__()
        self.symbol = symbol

    def paintEvent(self, event):
        option=QStyleOptionToolButton();self.initStyleOption(option)
        option.icon=QIcon();option.text=''
        painter=QStylePainter(self);painter.drawComplexControl(QStyle.CC_ToolButton,option)
        painter.setPen(QPen(QColor('#d5dfe8'),1))
        x,y=self.width()//2,self.height()//2
        if self.symbol==QStyle.SP_TitleBarCloseButton:
            painter.drawLine(x-4,y-4,x+4,y+4);painter.drawLine(x+4,y-4,x-4,y+4)
        elif self.symbol==QStyle.SP_TitleBarMinButton:painter.drawLine(x-5,y+3,x+5,y+3)
        elif self.symbol==QStyle.SP_TitleBarNormalButton:
            painter.drawRect(x-5,y-2,8,7);painter.drawLine(x-2,y-5,x+5,y-5);painter.drawLine(x+5,y-5,x+5,y+2)
        else:painter.drawRect(x-5,y-4,10,8)


class TitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.target = window
        self.setObjectName('titleBar'); self.setAttribute(Qt.WA_StyledBackground)
        self.setFixedHeight(38)
        row = QHBoxLayout(self); row.setContentsMargins(16, 0, 6, 0); row.setSpacing(0)
        if window.windowIcon().isNull() and window.parentWidget():
            window.setWindowIcon(window.parentWidget().windowIcon())
        self.app_icon = QLabel(); self.app_icon.setFixedSize(18, 18)
        self.app_icon.setPixmap(window.windowIcon().pixmap(18, 18))
        self.app_icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        window.windowIconChanged.connect(lambda icon: self.app_icon.setPixmap(icon.pixmap(18, 18)))
        row.addWidget(self.app_icon); row.addSpacing(8)
        self.title = QLabel(window.windowTitle()); self.title.setObjectName('windowTitle')
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents)
        row.addWidget(self.title); row.addStretch()
        window.windowTitleChanged.connect(self.title.setText)
        if not isinstance(window, QDialog):
            self.add_button(QStyle.SP_TitleBarMinButton, 'Minimize', window.showMinimized)
            self.maximize = self.add_button(QStyle.SP_TitleBarMaxButton, 'Maximize', self.toggle_maximized)
        self.add_button(QStyle.SP_TitleBarCloseButton, 'Close', window.close, 'closeWindow')
        self.edges = [ResizeEdge(window, edges, cursor) for edges, cursor in (
            (Qt.LeftEdge, Qt.SizeHorCursor), (Qt.RightEdge, Qt.SizeHorCursor),
            (Qt.TopEdge, Qt.SizeVerCursor), (Qt.BottomEdge, Qt.SizeVerCursor),
            (Qt.TopEdge|Qt.LeftEdge, Qt.SizeFDiagCursor), (Qt.BottomEdge|Qt.RightEdge, Qt.SizeFDiagCursor),
            (Qt.TopEdge|Qt.RightEdge, Qt.SizeBDiagCursor), (Qt.BottomEdge|Qt.LeftEdge, Qt.SizeBDiagCursor))]
        window.installEventFilter(self)

    def add_button(self, icon, label, callback, name='windowButton'):
        button = WindowButton(icon); button.setObjectName(name); button.setFixedSize(42,32)
        button.setAccessibleName(label); button.setToolTip(label)
        button.clicked.connect(callback); self.layout().addWidget(button)
        return button

    def toggle_maximized(self):
        self.target.showNormal() if self.target.isMaximized() else self.target.showMaximized()

    def eventFilter(self, watched, event):
        etype = event.type()
        if etype == QEvent.Resize:
            w, h = self.target.width(), self.target.height(); n = 6
            rects = ((0,n,n,h-2*n), (w-n,n,n,h-2*n), (n,0,w-2*n,n), (n,h-n,w-2*n,n),
                     (0,0,n,n), (w-n,h-n,n,n), (w-n,0,n,n), (0,h-n,n,n))
            for edge, rect in zip(self.edges, rects):
                edge.setGeometry(*rect)
        elif etype in (QEvent.Show, QEvent.WindowStateChange):
            w, h = self.target.width(), self.target.height(); n = 6
            rects = ((0,n,n,h-2*n), (w-n,n,n,h-2*n), (n,0,w-2*n,n), (n,h-n,w-2*n,n),
                     (0,0,n,n), (w-n,h-n,n,n), (w-n,0,n,n), (0,h-n,n,n))
            for edge, rect in zip(self.edges, rects):
                edge.setGeometry(*rect); edge.setVisible(not self.target.isMaximized()); edge.raise_()
            if hasattr(self, 'maximize'):
                icon = QStyle.SP_TitleBarNormalButton if self.target.isMaximized() else QStyle.SP_TitleBarMaxButton
                self.maximize.symbol = icon; self.maximize.update()
        return super().eventFilter(watched, event)

    def mousePressEvent(self,event):
        if event.button()==Qt.LeftButton:
            handle=self.target.windowHandle()
            if handle and handle.startSystemMove(): event.accept(); return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self,event):
        if event.button()==Qt.LeftButton and not isinstance(self.target,QDialog):
            self.toggle_maximized();event.accept();return
        super().mouseDoubleClickEvent(event)


def decorate(window, layout):
    window.setWindowFlag(Qt.FramelessWindowHint)
    bar=TitleBar(window)
    layout.insertWidget(0,bar)
    return bar
