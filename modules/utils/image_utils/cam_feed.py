from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QVBoxLayout, QSizePolicy, QMessageBox
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from facenet_pytorch import MTCNN
import numpy as np
import playsound
import logging
import torch
import time
import cv2
import gc


class CameraWorker(QObject):
    frameCaptured = pyqtSignal(object)

    def __init__(self, parent1=None, camera_index=0):
        super().__init__()
        print('initializing CameraWorker class')
        self.camera_index = camera_index
        self.object_trackers = []
        self.parent1 = parent1
        self.running = False
        self.frame_counter = 6
        self.sound_limiter = 15
        self.sound_ticks = 0
        self.max_sounds = 15
        self.sound_counter = 0
        self.reset_sound_frames = 250
        self.sound_frame_counter = 0
        self.mtcnn = MTCNN(keep_all=True, device='cuda' if torch.cuda.is_available() else 'cpu')
        self.bboxes = []
        self.names = []
        self.frame_count = 0
        self.face_detection_interval = 20  # Detect faces every 20 frames
        self.face_tracking_interval = 10  # Track faces every 10 frames
        self.movement_threshold = 150  # Define a threshold for sudden movement
        # Initialize your camera settings
        self.cam, self.cam_cl = 0, 0
        with open('./source/data/cameras.txt', 'r', encoding='utf-8') as f:
            cams = f.readlines()
            for line in cams:
                if line.split(';')[0] == str(self.camera_index):
                    self.cam = line.split(';')[1]
                    self.cam_cl = line.split(';')[2]

    def create_trackers(self, frame, faces): # this is where we send the frame to face_recognition to assign the correct names to the faces
        data = self.parent1.client.face_recognition(cv2.imencode('.jpg', cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))[1].tobytes(), self.cam_cl, self.cam, self.camera_index, faces)
        frame_new, locations, names, clearances = data[0], data[1], data[2], data[3]
        for i, (location, name, clearance_status) in enumerate(zip(locations, names, clearances)):
            if name != 'Unknown' and any(name in i for i in self.object_trackers):# checking if the tracker exists (only works with face recognition full - when faces get assigned correct names and not random ones)
                #delete the tracker and replace it with a new one
                top, right, bottom, left = location  # Unpack the coordinates
                tracker = cv2.TrackerCSRT_create()
                tracker.init(frame, (left, top, right - left, bottom - top))  # Initialize tracker with correct format
                ind = 0
                for i in range(len(self.object_trackers)):
                    if self.object_trackers[i][1] == name:
                        ind = i
                        break
                self.object_trackers[ind] = [tracker, name, (left, top), clearance_status]
                continue
            
            top, right, bottom, left = location  # Unpack the coordinates
            tracker = cv2.TrackerCSRT_create()
            tracker.init(frame, (left, top, right - left, bottom - top))  # Initialize tracker with correct format
            self.object_trackers.append([tracker, name, (left, top), clearance_status])  # Store the initial position
        
    def check_trackers(self, frame, bboxes=[], names=[]):
        bboxes = bboxes
        names = names
        if self.frame_count % self.face_detection_interval == 0:
            set_faces = []

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            #MTCNN detection
            boxes, _ = self.mtcnn.detect(rgb_frame)  # Pass the RGB to MTCNN
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box
                    top = int(y1)
                    right = int(x2)
                    bottom = int(y2)
                    left = int(x1)
                    set_faces.append((top, right, bottom, left))

            if len(set_faces) > len(self.object_trackers):
                self.create_trackers(frame, set_faces)

        if self.frame_count % self.face_tracking_interval == 0:
            bboxes = []
            # Update existing trackers
            if self.object_trackers == []: return frame, [], [] 
            for i in range(len(self.object_trackers)):
                try:
                    tracker, name, last_position = self.object_trackers[i][:3]
                except:
                    continue
                success, bbox = tracker.update(frame)
                if success:
                    bboxes.append(bbox)
                    names.append(name)
                    x, y, w, h = [int(v) for v in bbox]
                    current_position = (x, y)

                    # Calculate movement distance
                    distance_moved = np.sqrt((current_position[0] - last_position[0]) ** 2 + (current_position[1] - last_position[1]) ** 2)

                    # Check if the movement exceeds the threshold
                    if distance_moved > self.movement_threshold:
                        del self.object_trackers[i]  # Remove the tracker
                    else:
                        # Update the last known position
                        self.object_trackers[i][2] = current_position  # Update last_position

                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                else:
                    del self.object_trackers[i]
        else:
            for (box, name) in zip(bboxes, names):
                x, y, w, h = [int(v) for v in box]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        if any('Unknown' in i for i in self.object_trackers):
            if self.sound_ticks == self.sound_limiter:
                self.sound_ticks = 0
                if self.sound_counter != self.sound_limiter:
                    self.sound_counter += 1
                    try:
                        playsound.playsound('./source/sounds/alert_sound.mp3', block=True)
                    except Exception as e:
                        QMessageBox.critical(None, "Error", f"Error playing sound: {str(e)}")
                else:
                    if self.sound_frame_counter == self.reset_sound_frames:
                        self.sound_counter = 0
                    else:
                        self.sound_frame_counter += self.face_tracking_interval
                
            else:
                self.sound_ticks += 1
                
        else:
            self.sound_counter = 0

        return frame, bboxes, names

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

            frame, self.bboxes, self.names = self.check_trackers(frame, self.bboxes, self.names)
            self.frameCaptured.emit(frame)

            time.sleep(0.033)  # Limit to ~30 FPS
    
        self.cap.release()  # Release the camera when done


class VideoFeed(QWidget):
    def __init__(self, parent, camera_index=0):
        super().__init__()
        print('initializing VideoFeed class')
        self.thread = QThread()
        self.cameraWorker = CameraWorker(parent1=parent, camera_index=camera_index)
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
    
