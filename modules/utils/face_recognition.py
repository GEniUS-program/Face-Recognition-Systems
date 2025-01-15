import face_recognition
import datetime as dt
import numpy as np
import logging
import cv2
from modules.utils.database_worker import DataBaseWorker
from PIL import Image, ImageDraw, ImageFont

'''
TODO:
    -   add optimisation for saving images of recognized faces (every 30 minutes)
    -   add functionality for saving data in recognitions.txt (name, date, camera index, 1 or 0, image location)
    -   algorithm for displaying recognition history on the main view and recognition history view
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
        self.dt_format = 'yyyy-MM-dd hh:mm'
        self.transcr = {
            'А': 'A',
            'Б': 'B',
            'В': 'V',
            'Г': 'G',
            'Д': 'D',
            'Е': 'Ye',
            'Ё': 'Yo',
            'Ж': 'Zh',
            'З': 'Z',
            'И': 'I',
            'Й': 'Y',
            'К': 'K',
            'Л': 'L',
            'М': 'M',
            'Н': 'N',
            'О': 'O',
            'П': 'P',
            'Р': 'R',
            'С': 'S',
            'Т': 'T',
            'У': 'U',
            'Ф': 'F',
            'Х': 'Kh',
            'Ц': 'Ts',
            'Ч': 'Ch',
            'Ш': 'Sh',
            'Щ': 'Shch',
            'Ъ': 'Hard sign',
            'Ы': 'Y (as in "my")',
            'Ь': 'Y',
            'Э': 'E',
            'Ю': 'Yu',
            'Я': 'Ya'
        }
        self.queue = queue
        self.saving_limit = int(self.configuration['save_recognition_image_every_x_minutes'])
        with open('./source/data/recognitions.txt', 'r', encoding='utf-8') as f:
            self.recognition_times = [j.strip().split(';') for j in f.readlines()]

    def compare_faces(self, frame):
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
                cv2.imwrite(f'./source/data/recognition_tresspass/trespass{dt.datetime.now(dt._TzInfo())}.jpg', frame)
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
            last_saved_date_compared = self.compare_dates_by_name(name)
            if last_saved_date_compared[0] >= self.saving_limit:
                filepath =f'./source/data/recognitions/{''.join([self.transcr.get(i) for i in name.upper()])}{dt.datetime.now(dt._TzInfo())}.jpg'
                cv2.imwrite(
                    filepath, frame)
                self.recognition_times[last_saved_date_compared[1]] = [name, dt.datetime.now(dt._TzInfo()), filepath]
            try:
                self.queue.put((name, clearance, frame, code),
                               block=True, timeout=3)
            except Exception as e:
                logging.critical(
                    f'Error passing recognition to the queue: {e}')

    
    def compare_dates_by_name(self, name) -> int:
        date = 0
        override = False
        index = 0
        for line in self.recognition_times:
            if line[0] == name:
                date = line[1]
                break
            index += 1
        else:
            logging.warning(f'Name not found in recognition history, saving this recognition image file overriding saving limit.')
            override = True
        dt_compared = dt.datetime.now(dt._TzInfo()) - date

        return [10**6 if override else dt_compared.min // 2, index]