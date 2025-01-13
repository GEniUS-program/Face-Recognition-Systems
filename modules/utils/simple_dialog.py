from PyQt6 import QtWidgets
from modules.utils.communicator import Communicate


class DialogWindow(QtWidgets.QDialog):
    def __init__(self, text, type, parent=None):
        super(DialogWindow, self).__init__(parent)

        self.setWindowTitle('Подтвердите операцию')
        self.setFixedSize(300, 150)

        self.dialog_communicator = Communicate()
        self.dialog_signal = self.dialog_communicator.signal

        layout = QtWidgets.QVBoxLayout()

        self.label = QtWidgets.QLabel(text)
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.button_yes = QtWidgets.QPushButton('Да')
        self.button_yes.clicked.connect(self.yes_action)
        self.button_no = QtWidgets.QPushButton('Нет')
        self.button_no.clicked.connect(self.no_action)
        self.button_layout.addWidget(self.button_no)
        self.button_layout.addWidget(self.button_yes)
        layout.addLayout(self.button_layout)

        self.setLayout(layout)

    def yes_action(self):
        self.dialog_signal.emit('a')
        self.close()

    def no_action(self):
        self.dialog_signal.emit('r')
        self.close()