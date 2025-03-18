from PyQt6 import QtWidgets
from modules.utils.recognition_history import RecognitinonHistoryWorker
from modules.utils.image_utils.frame_display import WindowDisplay
import cv2


class RecognitionHistoryView(QtWidgets.QWidget):
    def __init__(self):
        super(RecognitionHistoryView, self).__init__()
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QVBoxLayout()

        self.search_bar = QtWidgets.QLineEdit()
        self.search_bar.setPlaceholderText("Поиск")
        self.search_bar.textChanged.connect(self.update)
        self.layout.addWidget(self.search_bar)

        self.recognition_history_table = QtWidgets.QTableWidget()
        self.recognition_history_table.setColumnCount(5)
        self.recognition_history_table.setHorizontalHeaderLabels(
            ["ФИО", 'Дата', 'Камера', 'Совпадение уровня доступа', 'Изображение'])
        self.recognition_history_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.layout.addWidget(self.recognition_history_table)

        self.recognition_history_table.doubleClicked.connect(
            lambda x: self.on_row_selected(x))

        self.setLayout(self.layout)

        self.update()

    def on_row_selected(self, index):
        frame = cv2.imread(self.recognition_history_table.item(index.row(), 4).text())
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        display_frame = WindowDisplay(frame)
        display_frame.exec()

    def update(self):
        text = self.search_bar.text()
        data = self.get_data(text)
        self.update_recognition_table(data)

    def update_recognition_table(self, data):
        self.recognition_history_table.clear()
        self.recognition_history_table.setColumnCount(5)
        self.recognition_history_table.setHorizontalHeaderLabels(
            ["ФИО", 'Дата', 'Камера', 'Совпадение уровня доступа', 'Изображение'])
        for line in data:
            self.recognition_history_table.insertRow(0)
            j = 0
            for i in [0, 1, 4, 3, 2]:
                self.recognition_history_table.setItem(
                    0, j, QtWidgets.QTableWidgetItem(line[i]))
                j += 1

    def get_data(self, parameters=None):
        worker = RecognitinonHistoryWorker()
        if parameters is not None:
            if '$' in parameters:
                parameters = parameters.strip('$')
                param_pairs = parameters.split(';')

                name = None
                is_suf_clearance = None
                camera_index = None
                date = None
                is_img = None

                for pair in param_pairs:
                    if ':' in pair:
                        key, value = pair.split(':', 1)
                        key = key
                        value = value

                        if key == 'name':
                            name = value
                        elif key == 'clear':
                            is_suf_clearance = value
                        elif key == 'index':
                            camera_index = value
                        elif key == 'date':
                            date = value
                        elif key == 'img':
                            print('GOT VALUE FOR IMAGE')
                            is_img = value

                data = worker.get(name=name, is_suf_clearance=is_suf_clearance,
                                  camera_index=camera_index, date=date, is_img=is_img)
            else:
                data = worker.search(parameters)
        else:
            data = worker.get()

        return data
