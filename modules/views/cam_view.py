from PyQt6 import QtWidgets
from modules.utils.cam_feed import VideoFeed


class CamFeedView(QtWidgets.QWidget):
    def __init__(self, parent, cam_number=0, cam_indexes=None):
        super(CamFeedView, self).__init__()
        self.cam_number = cam_number
        self.parent = parent
        self.cam_indexes = cam_indexes if cam_indexes else list(range(cam_number))  # List of camera indexes
        print(self.cam_indexes)
        self.initUI()

    def initUI(self):
        main_layout = QtWidgets.QHBoxLayout(self)

        if self.cam_number < 1:
            self.cam_select()
            return
        # Focused cam
        self.focused_feed = VideoFeed(self.parent, self.cam_indexes[0])
        self.focused_feed.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        main_layout.addWidget(self.focused_feed)

        
        side_layout = QtWidgets.QVBoxLayout()

        # Unfocused cams
        self.unfcsd_feeds = list()
        for cam_index in self.cam_indexes[1:]:
            unfocused_feed = VideoFeed(self.parent, cam_index)
            unfocused_feed.setSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
            self.unfcsd_feeds.append(unfocused_feed)
            side_layout.addWidget(unfocused_feed)

        main_layout.addLayout(side_layout)

        self.setLayout(main_layout)
    def closeEvent(self, event):
        self.focused_feed.closeEvent(event)
        for feed in self.unfcsd_feeds:
            feed.closeEvent(event)
        event.accept()  # Accept the event to close the application
    
    
