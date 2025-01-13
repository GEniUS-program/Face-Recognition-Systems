from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QImage, QPixmap
from modules.utils.face_recognition import FaceRecognition
from multiprocessing import Pool, Manager
import logging
import cv2
import time


class CameraWorker(QObject):
    frameCaptured = pyqtSignal(object)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.faces = list()
        self.frame_counter = 6
        self.pool = Pool(processes=8, maxtasksperchild=1)
        self.manager = Manager()
        self.queue = self.manager.Queue(15)
        # Initialize your camera settings
        with open('./source/data/cameras.txt', 'r', encoding='utf-8') as f:
            cams = f.readlines()
            for line in cams:
                if line.split(';')[0] == str(self.camera_index):
                    cam = line.split(';')[1]
                    cam_cl = line.split(';')[2]

        self.face_recognition = FaceRecognition(
            cam, self.camera_index, int(cam_cl), self.queue)

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.camera_index)
        i = 1
        while self.running:
            ret, frame = cap.read()
            if not ret:
                logging.error("Failed to capture frame from camera.")
                break

            self.frameCaptured.emit(frame)

            if i == self.frame_counter:
                logging.info("Attempting to call compare_faces...")

                try:
                    result = self.pool.apply_async(
                        func=self.face_recognition.compare_faces, args=(frame,))
                    # Use get() to retrieve the result
                    # Set a timeout to prevent hanging
                    result_data = result.wait(timeout=0.04)
                    if result_data is not None:
                        self.faces.append(result_data)
                        logging.info(
                            'Frame processed and accepted at CameraWorker')
                    else:
                        logging.warning('No faces detected in the frame.')
                except Exception as e:
                    logging.error(f'Error in compare_faces: {e}')

                i = 1
            else:
                i += 1

            time.sleep(0.033)  # Limit to ~30 FPS

        cap.release()


class VideoFeed(QWidget):
    def __init__(self, camera_index=0, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.cameraWorker = CameraWorker(camera_index=camera_index)
        self.cameraWorker.moveToThread(self.thread)
        self.cameraWorker.frameCaptured.connect(self.processFrame)
        self.thread.started.connect(self.cameraWorker.run)
        self.thread.start()

        # Set up the QGraphicsView and QGraphicsScene
        self.graphicsView = QGraphicsView(self)  # Set self as the parent
        self.graphicsView.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  # Allow resizing
        self.scene = QGraphicsScene(self)
        self.graphicsView.setScene(self.scene)
        self.scenePixmapItem = None

        # Layout
        layout = QVBoxLayout(self)  # Create a vertical layout
        # Add the graphics view to the layout
        layout.addWidget(self.graphicsView)
        self.setLayout(layout)  # Set the layout for the widget

    def processFrame(self, frame):
        # Convert the frame to QImage
        image = QImage(
            frame.data, frame.shape[1], frame.shape[0], QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(image)

        if self.scenePixmapItem is None:
            self.scenePixmapItem = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.scenePixmapItem)
            self.scenePixmapItem.setZValue(0)
        else:
            self.scenePixmapItem.setPixmap(pixmap)

        # Update the scene rectangle to match the new pixmap size
        self.scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

        # Fit the view to the new scene rectangle
        self.graphicsView.fitInView(
            self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def closeEvent(self, a0):
        self.cameraWorker.pool.close()
        self.cameraWorker.pool.join()
        return super().closeEvent(a0)
