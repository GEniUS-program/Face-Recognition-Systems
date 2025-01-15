# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets
from modules.views.main_view import MainView
from modules.views.dbview import DataBaseView
from modules.views.cam_view import CamFeedView
from modules.views.recognition_history_view import RecognitionHistoryView
from multiprocessing import freeze_support
import sys 


class MainUI(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainUI, self).__init__()
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
        # Uncomment these lines when the views are defined
        self.camera_view = CamFeedView()
        self.recog_history_view = RecognitionHistoryView()
        
        # Adding views to the stacked widget
        self.main_stacked_widget.addWidget(self.main_view)
        self.main_stacked_widget.addWidget(self.database_view)
        self.main_stacked_widget.addWidget(self.camera_view)
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
        pass  # Placeholder for the recognition history logic

    def show_settings(self):
        pass  # Placeholder for the settings logic

if __name__ == "__main__":
    freeze_support()
    app = QtWidgets.QApplication(sys.argv)
    window = MainUI()
    window.setWindowTitle("Face recognition")
    window.resize(400, 300)
    window.show()
    sys.exit(app.exec())
