# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt


class FrameDisplayWidget(QtWidgets.QLabel):
    def __init__(self, frame, cam='n/a', zone='n/a'):
        super(FrameDisplayWidget, self).__init__()
        
        self.image_label = QtWidgets.QLabel(self)
        self.image_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        height, width, _ = frame.shape
        bytes_per_line = 3 * width
        q_image = QtGui.QImage(frame.data, width, height,
                               bytes_per_line, QtGui.QImage.Format.Format_RGB888)

        # Create a QPixmap from QImage
        pixmap = QtGui.QPixmap.fromImage(q_image)

        # Optionally, resize the image to fit the QLabel
        self.scaled_pixmap = pixmap.scaled(self.size(),
                                      QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                                      QtCore.Qt.TransformationMode.FastTransformation)

        # Set the scaled QPixmap to the QLabel
        self.image_label.setPixmap(self.scaled_pixmap)

        # Set the QLabel to expand with the widget
        self.image_label.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding,
                                       QtWidgets.QSizePolicy.Policy.Expanding)

        # Create a layout and add the label to it
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.image_label)

        # Resize the widget to fit the scaled image (optional)
        # self.resize(scaled_pixmap.size())  # Uncomment if you want to set size based on the image



class WindowDisplay(QtWidgets.QDialog):
    def __init__(self, frame):
        super().__init__()
        self.frame = frame
        self.resize(800, 600)
        self.display_frame()

    def display_frame(self):
        self.layout = QtWidgets.QVBoxLayout(self)

        display_frame = FrameDisplayWidget(self.frame)
        display_frame.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        display_frame.resize(display_frame.scaled_pixmap.size())
        self.layout.addWidget(display_frame)

        self.setLayout(self.layout)
