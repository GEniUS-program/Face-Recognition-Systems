# -*- coding: utf-8 -*-
#<-----------------THIS FILE IS NOT CURRENTLY USED----------------->
import cv2
from PyQt6 import QtWidgets
from modules.utils.image_utils.frame_display import FrameDisplayWidget
from modules.utils.recognition_history import RecognitinonHistoryWorker


class MainView(QtWidgets.QWidget):
    def __init__(self):
        super(MainView, self).__init__()
        self.worker = RecognitinonHistoryWorker()
        self.initUI()

    def initUI(self):
        self.layout = QtWidgets.QHBoxLayout()

        self.array_layout = QtWidgets.QVBoxLayout()

        placeholder_image = cv2.imread('./source/images/placeholder-image.png')

        self.last_frame = FrameDisplayWidget(placeholder_image, 'n/a', 'n/a')
        self.layout.addWidget(self.last_frame)

        self.frames_array = list()
        for i in range(3):
            frame_widget = FrameDisplayWidget(placeholder_image, 'n/a', 'n/a')
            self.frames_array.append(frame_widget)
            self.array_layout.addWidget(frame_widget)

        self.layout.addLayout(self.array_layout)

        self.setLayout(self.layout)

        self.update_view()

    def update_view(self):
        frames = self.get_frames()
        self.last_frame1 = FrameDisplayWidget(frames[0], 'n/a', 'n/a')
        self.layout.replaceWidget(self.last_frame, self.last_frame1)
        self.frames_array1 = [None] * 3
        for i in range(3):
            self.frames_array1[i] = FrameDisplayWidget(
                frames[i + 1], 'n/a', 'n/a')
            self.array_layout.replaceWidget(self.frames_array[i], self.frames_array1[i])

    def get_frames(self):
        last_recognitions = self.worker.get(is_img='1')[-4::]
        print(last_recognitions)

        frames = list()
        for line in last_recognitions:
            image = cv2.imread(line[2])
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            frames.append(image)

        return frames
