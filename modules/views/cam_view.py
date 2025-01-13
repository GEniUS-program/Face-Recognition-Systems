from PyQt6 import QtWidgets
from modules.utils.cam_feed import VideoFeed


class CamFeedView(QtWidgets.QWidget):
    def __init__(self, cam_number=1, cam_indexes=None):
        super(CamFeedView, self).__init__()
        self.cam_number = cam_number
        self.cam_indexes = cam_indexes if cam_indexes else list(range(cam_number))  # List of camera indexes
        self.initUI()

    def initUI(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        if self.cam_number < 1:
            self.cam_select()
            return
        # Focused cam
        focused_feed = VideoFeed(self.cam_indexes[0])
        focused_feed.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        main_layout.addWidget(focused_feed)

        
        side_layout = QtWidgets.QVBoxLayout()

        # Unfocused cams
        for cam_index in self.cam_indexes[1:]:
            unfocused_feed = VideoFeed(cam_index)
            unfocused_feed.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
            side_layout.addWidget(unfocused_feed)

        main_layout.addLayout(side_layout)

        self.setLayout(main_layout)

    def cam_select(self):
        pass
