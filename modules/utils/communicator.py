from PyQt6.QtCore import QObject, pyqtSignal


class Communicate(QObject):
    signal = pyqtSignal(object)
