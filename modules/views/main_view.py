# -*- coding: utf-8 -*-
import cv2
from PyQt6 import QtWidgets
from modules.utils.frame_display import FrameDisplayWidget

class MainView(QtWidgets.QWidget):
    def __init__(self):
        super(MainView, self).__init__()
        
        self.initUI()
        
    def initUI(self):
        self.layout = QtWidgets.QHBoxLayout()  # Main horizontal layout
        
        self.array_layout = QtWidgets.QVBoxLayout()  # Vertical layout for frame display
        
        # Load a placeholder image
        placeholder_image = cv2.imread('./source/images/placeholder-image.png')
        
        # Create the main frame display widget
        self.last_frame = FrameDisplayWidget(placeholder_image, 'n/a', 'n/a')
        self.layout.addWidget(self.last_frame)  # Add the last frame widget to the main layout
        
        # Create and add multiple frame display widgets to the vertical layout
        self.frames_array = list()
        for i in range(3):
            frame_widget = FrameDisplayWidget(placeholder_image, 'n/a', 'n/a')
            self.frames_array.append(frame_widget)
            self.array_layout.addWidget(frame_widget)  # Add each widget to the vertical layout

        # Add the vertical layout to the main layout
        self.layout.addLayout(self.array_layout)  # Add the array layout to the main layout
        
        # Set the layout for the MainView widget
        self.setLayout(self.layout)
