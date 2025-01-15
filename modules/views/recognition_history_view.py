from PyQt6 import QtWidgets
import cv2


class RecognitionHistoryView(QtWidgets.QWidget):
    def __init__(self):
        super(RecognitionHistoryView, self).__init__()
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Поиск")
        self.layout.addWidget(self.search_bar)

        self.recognition_history_table = QtWidgets.QTableWidget()
        self.recognition_history_table.setColumnCount(4)
        self.recognition_history_table.setHorizontalHeaderLabels(["ФИО", 'Дата', 'Камера', 'Совпадение уровня доступа'])
        self.recognition_history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(self.recognition_history_table)

        self.recognition_history_table.doubleClicked.connect(lambda x: self.on_row_selected(x))

        self.setLayout(self.layout)    


    def on_row_selected(self, index):
        print(index)

    def update_recognition_table(self):
        self.recognition_history_table.setColumnCount(0)
        self.recognition_history_table.setColumnCount(4)
        self.recognition_history_table.setHorizontalHeaderLabels(["ФИО", 'Дата', 'Камера', 'Совпадение уровня доступа'])
