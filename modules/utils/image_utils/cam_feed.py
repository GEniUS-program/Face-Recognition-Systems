from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import QObject, QThread, pyqtSignal, Qt
from multiprocessing import Pool, Manager, Lock
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtGui import QImage, QPixmap
import face_recognition
import numpy as np
import logging
import time
import cv2
import gc


class CameraWorker(QObject):
    frameCaptured = pyqtSignal(object)

    def __init__(self, parent=None, camera_index=0):
        super(CameraWorker, self).__init__(parent=parent)
        print('initializing CameraWorker class')
        self.camera_index = camera_index
        self.object_trackers = []
        self.parent = parent
        self.running = False
        self.faces = list()
        self.frame_counter = 6
        self.pool = Pool(processes=5)
        self.manager = Manager()
        self.lock = self.manager.Lock()
        self.bboxes = []
        self.names = []
        self.frame_count = 0
        self.face_detection_interval = 15  # Detect faces every 15 frames
        self.face_tracking_interval = 5  # Track faces every 5 frames
        self.movement_threshold = 175  # Define a threshold for sudden movement
        # Initialize your camera settings
        self.cam, self.cam_cl = 0, 0
        with open('./source/data/cameras.txt', 'r', encoding='utf-8') as f:
            cams = f.readlines()
            for line in cams:
                if line.split(';')[0] == str(self.camera_index):
                    self.cam = line.split(';')[1]
                    self.cam_cl = line.split(';')[2]

    def create_trackers(self, frame): # this is where we send the frame to face_recognition to assign the correct names to the faces
        global example_names, trackers
        faces = face_recognition.face_locations(frame)
        
        data = self.parent.client.face_recognition(frame.imencode().tobytes(), self.cam_cl, self.cam, self.camera_index)
        frame_new, locations, names, clearances = data[0], data[1], data[2], data[3]
        for i, (location, name, clearance_status) in enumerate(zip(locations, names, clearances)):
            if any(name in i for i in self.object_trackers):# checking if the tracker exists (only works with face recognition full - when faces get assigned correct names and not random ones)
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

    def check_new_faces(self, frame):
        print('checking for new faces')
        trackers_int = len(self.object_trackers)
        faces = face_recognition.face_locations(frame)
        faces_int = len(faces)

        for i in trackers_int:
            success, _ = self.object_trackers[i][0].update(frame)
            if not success:
                del self.object_trackers[i]

        trackers_int_new = len(self.object_trackers)

        if trackers_int_new != faces_int:
            print('updating trackers, recognizing faces')
            
    def check_trackers(self, frame, bboxes=[], names=[]):
        global trackers
        new_faces = False
        bboxes = bboxes
        names = names
        if self.frame_count % self.face_detection_interval == 0:
            faces = face_recognition.face_locations(frame)
            if len(faces) > len(trackers):
                print('more faces detected than the amount of trackers')
                self.create_trackers(frame)
                new_faces = True

        if self.frame_count % self.face_tracking_interval == 0:
            bboxes = []
            # Update existing trackers
            for i, (tracker, name, last_position) in enumerate(trackers):
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
                        print(f'lost tracker for {name} to sudden movement')
                        cv2.putText(frame, f"Tracker for {name} lost due to sudden movement", (100, 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                        del trackers[i]  # Remove the tracker
                    else:
                        # Update the last known position
                        trackers[i][2] = current_position  # Update last_position
                        
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                else:
                    print('lost tracking for', name)
                    cv2.putText(frame, f"Tracker for {name} lost", (100, 80 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                    del trackers[i]
        else:
            for (box, name) in zip(bboxes, names):
                x, y, w, h = [int(v) for v in box]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, name, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)


        return frame, bboxes, names

    def draw_face_rectangle(self, frame, location, name, clearance):
        color = (0, 255, 0) if clearance else (0, 0, 255)
        cv2.rectangle(frame, (location[3], location[0]),
                      (location[1], location[2]), color, 2)
        frame = Image.fromarray(frame)
        draw_frame = ImageDraw.Draw(frame)
        draw_frame.text((location[3], location[0] - 10), f'{self.camera_codename}\n{name}',
                        (255, 255, 255), font=ImageFont.truetype('arial.ttf', 25))
        return np.array(frame)


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

            if i == self.frame_counter:
                logging.info("Attempting to call compare_faces...")
                try:
                    frame = self.check_new_faces(frame)
                except Exception as e:
                    logging.error(f'Error in compare_faces: {e}')
                self.frameCaptured.emit(frame)

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
        self.parent = parent
        self.cameraWorker = CameraWorker(parent=parent, camera_index=camera_index)
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
    
