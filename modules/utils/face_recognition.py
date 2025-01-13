import face_recognition
import datetime as dt
import numpy as np
import logging
import cv2
from modules.utils.database_worker import DataBaseWorker
from PIL import Image, ImageDraw, ImageFont
from random import randrange

'''
TODO:
    -   add optimisation for saving images of recognized faces (every 30 minutes)
    -   add functionality for saving data in recognitions.txt (name, date, camera index, 1 or 0, image location)
    -   algorithm for displaying recognition history on the main view and recognition history view
    -   solve video feed optimisation issues (the video feed lags when face-recognition is in process, but it shouldn't or not so much - min 25 frames per second)
    -   solve problem with cv2 not supporting cyrillic characters (when saving images of recognized faces)
    -   decide what to do with queue information
'''


class FaceRecognition:
    def __init__(self, camera_codename, camera_index, camera_clearance, queue=None):
        self.camera_codename = camera_codename
        self.camera_index = camera_index
        self.camera_clearance = camera_clearance
        self.db_worker = DataBaseWorker()
        self.known_face_encodings = self.db_worker.vectors
        self.known_face_names = self.db_worker.names
        self.clearances = self.db_worker.clearances
        self.queue = queue
        #with open('./source/data/recognitions.txt', 'r', encoding='utf-8') as f:
        #    self.recog_history = [[elem for elem in ]]

    def compare_faces(self, frame):
        print('compare_faces called')
        face_locations = face_recognition.face_locations(frame)
        if not face_locations:  # Changed from `if face_locations is None`
            logging.info(
                'No faces found in frame. Skipping face recognition...')
            return None

        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            logging.info('Processing face...')
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding)
            name = "Unknown"
            clearance = 0

            if True in matches:
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]
                    clearance = int(self.clearances[best_match_index])
            else:
                cv2.imwrite('./source/data/recognitions/trespass.jpg', frame)
                try:
                    self.queue.put((name, clearance, frame, -2),
                                   block=True, timeout=3)
                except Exception as e:
                    logging.critical(
                        f'Error passing recognition to the queue: {e}')
                return None

            color = (0, 255, 0) if clearance >= self.camera_clearance else (0, 0, 255)
            code = 1 if clearance >= self.camera_clearance else -1
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            frame = Image.fromarray(frame)
            draw_frame = ImageDraw.Draw(frame)
            draw_frame.text((left, top - 10), f'{self.camera_codename}\n{name}',
                            (255, 255, 255), font=ImageFont.truetype('arial.ttf', 25))
            frame = np.array(frame)
            cv2.imwrite(
                f'./source/data/recognitions/{name}{code}{randrange(10000000)}.jpg', frame)
            try:
                self.queue.put((name, clearance, frame, code),
                               block=True, timeout=3)
            except Exception as e:
                logging.critical(
                    f'Error passing recognition to the queue: {e}')
