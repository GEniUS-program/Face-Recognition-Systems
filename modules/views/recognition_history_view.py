from PyQt6 import QtWidgets
from modules.utils.image_utils.frame_display import WindowDisplay
import cv2


class RecognitionHistoryView(QtWidgets.QWidget):
    def __init__(self, client):
        super(RecognitionHistoryView, self).__init__()
        self.client = client
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
        im = self.recognition_history_table.item(index.row(), 4).text()
        frame = self.images_data[im]
        print(type(frame))
        display_frame = WindowDisplay(frame)
        display_frame.exec()

    def update(self):
        data = self.get_data()
        self.update_recognition_table(data)

    def update_recognition_table(self, data):
        self.recognition_history_table.clear()
        self.recognition_history_table.setColumnCount(5)
        self.recognition_history_table.setHorizontalHeaderLabels(
            ["ФИО", 'Дата', 'Камера', 'Совпадение уровня доступа', 'Изображение'])
        for (name, datetime, cam_indexe, level, image) in zip(data[0], data[1], data[2], data[3], self.images_data.keys()):
            self.recognition_history_table.insertRow(0)  # Insert a new row at the top
            self.recognition_history_table.setItem(0, 0, QtWidgets.QTableWidgetItem(name))          # ФИО
            self.recognition_history_table.setItem(0, 1, QtWidgets.QTableWidgetItem(datetime))      # Дата
            self.recognition_history_table.setItem(0, 2, QtWidgets.QTableWidgetItem(str(cam_indexe)))  # Камера
            self.recognition_history_table.setItem(0, 3, QtWidgets.QTableWidgetItem(str(level)))     # Совпадение уровня доступа
            self.recognition_history_table.setItem(0, 4, QtWidgets.QTableWidgetItem(image))  

    def get_data(self):
        data = self.client.client.get_recognition_history() # name, datetime, cam_index, level, image
        self.images_data = {f'Нажмите два раза, чтобы просмотреть{i}':image for i, image in enumerate(data[4])}
        try:
            print(type(data[4]), type(data[4][0]))
        except:
            pass
        return data