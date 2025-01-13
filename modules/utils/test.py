from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QApplication
from PyQt6.QtGui import QImage, QPixmap
import cv2
import time


class CameraWorker(QObject):
    frameCaptured = pyqtSignal(object)  # Emit frame data

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_index)
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frameCaptured.emit(frame)
                time.sleep(0.033)  # Limit to ~30 FPS
            else:
                break
        cap.release()

    def stop(self):
        self.running = False

# In your main application class


class VideoFeed(QObject):
    def __init__(self):
        super().__init__()
        self.thread = QThread()
        self.cameraWorker = CameraWorker()
        self.cameraWorker.moveToThread(self.thread)
        self.cameraWorker.frameCaptured.connect(self.processFrame)
        self.thread.started.connect(self.cameraWorker.run)
        self.thread.start()
        # add a qdialog with a qgraphicsview
        self.graphicsView = QGraphicsView()
        self.graphicsView.show()
        self.graphicsView.setGeometry(100, 100, 800, 600)

        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)
        self.scenePixmapItem = None

    def processFrame(self, frame):
        # Convert the frame to a format that Qt can use

        image = QImage(
            frame.data,
            frame.shape[1],
            frame.shape[0],
            QImage.Format.Format_BGR888,
        )
        pixmap = QPixmap.fromImage(image)

        if self.scenePixmapItem is None:
            self.scenePixmapItem = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.scenePixmapItem)
            self.scenePixmapItem.setZValue(0)
            self.fitInView(self.scene.sceneRect(),
                           Qt.AspectRatioMode.KeepAspectRatio)
        else:
            self.scenePixmapItem.setPixmap(pixmap)

    def stopCamera(self):
        self.cameraWorker.stop()
        self.thread.quit()
        self.thread.wait()

    def fitInView(self, rect, aspectRatioMode):
        self.graphicsView.fitInView(rect, aspectRatioMode)
