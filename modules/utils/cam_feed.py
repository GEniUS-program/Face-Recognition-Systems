from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QImage, QPixmap
from modules.utils.face_recognition import FaceRecognition
from multiprocessing import Pool, Manager, Lock
import logging
import cv2
import time


class CameraWorker(QObject):
    frameCaptured = pyqtSignal(object)

    def __init__(self, camera_index=0):
        super().__init__()
        print('initializing CameraWorker class')
        self.camera_index = camera_index
        self.running = False
        self.faces = list()
        self.frame_counter = 6
        self.pool = Pool(processes=5)
        self.manager = Manager()
        self.lock = self.manager.Lock()
        # Initialize your camera settings
        cam, cam_cl = 0, 0
        with open('./source/data/cameras.txt', 'r', encoding='utf-8') as f:
            cams = f.readlines()
            for line in cams:
                if line.split(';')[0] == str(self.camera_index):
                    cam = line.split(';')[1]
                    cam_cl = line.split(';')[2]

        self.face_recognition = FaceRecognition(
            cam, self.camera_index, int(cam_cl))

    def run(self):
        self.running = True
        self.cap = cv2.VideoCapture(self.camera_index)
        i = 1
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logging.error(f"Failed to capture frame from camera with index: {self.camera_index}")
                break
            else:
                logging.info(f"Got frame on camera with index: {self.camera_index}")
    
            self.frameCaptured.emit(frame)
    
            if i == self.frame_counter:
                logging.info("Attempting to call compare_faces...")
    
                try:
                    result = self.pool.apply_async(
                        func=self.face_recognition.compare_faces, args=(frame,self.lock,))
                    result_data = result.wait(timeout=0.04)  # Wait for the result with timeout
                    if result_data is not None:
                        self.faces.append(result_data)
                        logging.info('Frame processed and accepted at CameraWorker')
                except Exception as e:
                    logging.error(f'Error in compare_faces: {e}')
    
                i = 1
            else:
                i += 1
    
            #time.sleep(0.033)  # Limit to ~30 FPS
    
        self.cap.release()  # Release the camera when done


class VideoFeed(QWidget):
    def __init__(self, parent, camera_index=0):
        super().__init__(parent)
        print('initializing VideoFeed class')
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

    def closeEvent(self, event):
        print('closeEvent triggered')
        # Signal the CameraWorker to stop running
        self.cameraWorker.running = False  # Stop the camera worker loop
        print('trying to close thread')
        # Wait for the thread to finish
        self.thread.quit()  # Request the thread to quit
        self.thread.wait()  # Wait for the thread to finish
        print('Thread closed. Closing Process Pool...')
        # Clean up the process pool
        self.cameraWorker.pool.terminate()  # Terminate the pool
        self.cameraWorker.pool.join()  # Wait for the pool to terminate
        print('Process Pool closed. Closing VideoCapture...')
        # Release the video capture resource
        if self.cameraWorker.cap.isOpened():
            self.cameraWorker.cap.release()  # Release the camera
            print('Capture closed')
        if self.cameraWorker.cap.isOpened():
            print('An error occured when trying to close the videocapture: cap was not released')
        event.accept()  # Accept the event to close the application
    
