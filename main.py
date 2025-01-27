# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets
from modules.views.main_view import MainView
from modules.views.dbview import DataBaseView
from modules.views.cam_view import CamFeedView
from modules.views.recognition_history_view import RecognitionHistoryView
from modules.utils.camera_selection import CameraSelectorWidget
from modules.views.recognition_history_view import RecognitionHistoryView
from modules.utils.camera_selection import CameraSelectorWidget
from multiprocessing import freeze_support
import json
import json
import sys 


class MainUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainUI, self).__init__()
        self.read_config()

    def read_config(self):
        # Process cameras 
        with open('./source/data/config.json', 'r') as file:
            config = json.load(file)
        if config["select_cam_on_startup"] == 'True':
            self.get_cameras()
        else:
            with open('./source/data/cameras.txt', 'r') as fil:
                self.cameras = [int(i.strip().split(';')[0]) for i in fil.readlines()]
                
            # Write cam data to cameras.txt
            with open('./source/data/cameras.txt', 'w') as fil:
                to_write = list()
                for i in range(len(self.cameras)):
                    to_write.append(f'{i};name-{i};1')
                fil.writelines(to_write)
        self.init_mainUI()
        
    def init_mainUI(self):
        # Setting up the main layout
        self.layout = QtWidgets.QVBoxLayout()
        
        # A layout for buttons to switch views
        self.view_select_buttons_layout = QtWidgets.QHBoxLayout()
        
        # Button to switch to main view 
        self.main_view_button = QtWidgets.QPushButton("Главная")
        self.main_view_button.clicked.connect(self.show_main)
        self.view_select_buttons_layout.addWidget(self.main_view_button)
        
        # Cam feed view button
        self.cam_view_button = QtWidgets.QPushButton("Камеры")
        self.cam_view_button.clicked.connect(self.cam_view_show)
        self.view_select_buttons_layout.addWidget(self.cam_view_button)
        
        # Button to switch to database view
        self.database_view_button = QtWidgets.QPushButton("База данных")
        self.database_view_button.clicked.connect(self.show_db)
        self.view_select_buttons_layout.addWidget(self.database_view_button)
        
        # Recognition history view button
        self.recog_view_button = QtWidgets.QPushButton("История распознавания")
        self.recog_view_button.clicked.connect(self.recog_view_show)
        self.view_select_buttons_layout.addWidget(self.recog_view_button)
        
        # Settings tab
        self.settings_button = QtWidgets.QPushButton("Настройки")
        self.settings_button.clicked.connect(self.show_settings)
        self.view_select_buttons_layout.addWidget(self.settings_button)

        # Initializing the stacked widget
        self.main_stacked_widget = QtWidgets.QStackedWidget()
        
        # Initializing views
        self.main_view = MainView()
        self.database_view = DataBaseView()
        self.camera_view = CamFeedView(self, len(self.cameras), self.cameras)
        self.recog_history_view = RecognitionHistoryView()
        
        # Adding views to the stacked widget
        self.main_stacked_widget.addWidget(self.main_view)
        self.main_stacked_widget.addWidget(self.database_view)
        self.main_stacked_widget.addWidget(self.camera_view)
        self.main_stacked_widget.addWidget(self.recog_history_view)
        self.main_stacked_widget.addWidget(self.recog_history_view)

        # Adding widgets to the main layout
        self.layout.addLayout(self.view_select_buttons_layout)
        self.layout.addWidget(self.main_stacked_widget)

        # Set central widget
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(self.layout)
        self.setCentralWidget(central_widget)

    def show_main(self):
        self.main_stacked_widget.setCurrentWidget(self.main_view)
        
    def show_db(self):
        self.main_stacked_widget.setCurrentWidget(self.database_view)
    
    def cam_view_show(self):
        self.main_stacked_widget.setCurrentWidget(self.camera_view)
        
    def recog_view_show(self):
        # Uncomment this line when the recognition history view is defined
        self.main_stacked_widget.setCurrentWidget(self.recog_history_view)
        self.main_stacked_widget.setCurrentWidget(self.recog_history_view)
        pass  # Placeholder for the recognition history logic

    def show_settings(self):
        pass  # Placeholder for the settings logic

    def get_cameras(self):
        widget = CameraSelectorWidget()
        widget.seleted_cameras_signal.connect(lambda x: self.process_camera_selection(x))
        widget.exec() 

    def process_camera_selection(self, camera_indexes):
        self.cameras = [int(i) for i in camera_indexes]
        
    def closeEvent(self, a0):
        print('closing main window')
        self.camera_view.closeEvent(a0)
        a0.accept()

if __name__ == "__main__":
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    window = MainUI()
    window.setWindowTitle("Face recognition")
    window.setWindowTitle("Face recognition")
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())
