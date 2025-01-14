from PyQt6 import QtWidgets


class RecognitionHistoryView(QtWidgets.QWidget):
    def __init__(self):
        super(RecognitionHistoryView, self).__init__()
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        # search bar for recognition history
        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Поиск")
        self.layout.addWidget(self.search_bar)

        # table for recognition history
        self.recognition_history_table = QtWidgets.QTableWidget()
        self.recognition_history_table.setColumnCount(3)
        self.recognition_history_table.setHorizontalHeaderLabels(["ФИО", "Результат", "Время"])
        self.recognition_history_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(self.recognition_history_table)

        self.recognition_history_table.doubleClicked.connect(lambda x: self.on_row_selected(x))

        self.setLayout(self.layout)    


    def on_row_selected(self, index):
        print(index)