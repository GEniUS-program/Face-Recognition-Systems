import cv2
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
from modules.utils.communicator import Communicate
from PyQt6.QtCore import Qt

class CameraSelectorWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Camera Selector")
        self.setGeometry(100, 100, 400, 300)

        self.layout = QVBoxLayout()

        self.camera_list = QListWidget()
        self.layout.addWidget(QLabel("Select Cameras:"))
        self.layout.addWidget(self.camera_list)

        self.select_button = QPushButton("Select Cameras")
        self.select_button.clicked.connect(self.select_cameras)
        self.layout.addWidget(self.select_button)

        self.setLayout(self.layout)

        self.communicator = Communicate()
        self.seleted_cameras_signal = self.communicator.signal

        self.populate_camera_list()

    def populate_camera_list(self):
        not_detected = False
        for i in range(100):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                # Create a formatted string with camera information
                item_text = f"Camera {i}: {width}x{height}, {fps} FPS"
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.camera_list.addItem(item)
                cap.release()
                not_detected = False
            elif not_detected:
                break
            else:
                not_detected = True

    def select_cameras(self):
        selected_cameras = []
        for index in range(self.camera_list.count()):
            item = self.camera_list.item(index)
            if item.checkState() == Qt.CheckState.Checked:
                camera_index = item.text().split()[1]
                selected_cameras.append(camera_index)
                print(f"Selected Camera: {camera_index}")
        self.seleted_cameras_signal.emit(selected_cameras)