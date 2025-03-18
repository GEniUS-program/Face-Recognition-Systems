import face_recognition
import datetime as dt
import numpy as np
import json
import cv2
from modules.utils.database_worker import DataBaseWorker
from PIL import Image, ImageDraw, ImageFont
from playsound import playsound


class FaceRecognition:
    def __init__(self, camera_codename, camera_index, camera_clearance):
        self.camera_codename = camera_codename
        self.camera_index = camera_index
        self.camera_clearance = camera_clearance
        self.db_worker = DataBaseWorker()
        self.known_face_encodings = self.db_worker.vectors
        self.known_face_names = self.db_worker.names
        self.clearances = self.db_worker.clearances
        self.dt_format = '%Y-%m-%d %H-%M-%S'
        self.transcr = self.initialize_transliteration()
        self.configuration = self.load_configuration()
        self.saving_limit = int(
            self.configuration['save_recognition_image_every_x_minutes'])

    def initialize_transliteration(self):
        return {
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'Ye', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
            'Ъ': 'Hard sign', 'Ы': 'Y', 'Ь': 'Y', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya', ' ': ' '
        }

    def load_configuration(self):
        with open('./source/data/config.json') as f:
            return json.load(f)


    def compare_faces(self, frame, lock):
        self.recognition_times = self.load_recognition_history()
        face_locations = face_recognition.face_locations(frame)
        if not face_locations:
            return None

        face_encodings = face_recognition.face_encodings(frame, face_locations)

        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding)

            name, clearance = self.get_recognition_info(matches, face_encoding)

            if name == "Unknown":
                frame = self.draw_face_rectangle(
                    frame, (top, right, bottom, left), name, -1)
                self.save_image(lock, frame, None)
                return None
            frame = self.draw_face_rectangle(
                frame, (top, right, bottom, left), name, clearance)
            if clearance < self.camera_clearance:
                self.save_image(lock, frame, name, 1)
                return None

            last_saved_date_compared = self.compare_dates_by_name(name)
            if last_saved_date_compared[0] >= self.saving_limit:
                self.update_recognition_times(name, lock)
                self.save_image(lock, frame, name, 2)
            else:
                self.save_image(lock, frame=None)

    def get_recognition_info(self, matches, face_encoding):
        if True in matches:
            face_distances = face_recognition.face_distance(
                self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            name = self.known_face_names[best_match_index]
            clearance = int(self.clearances[best_match_index])
            return name, clearance
        return "Unknown", 0

    def draw_face_rectangle(self, frame, location, name, clearance):
        color = (0, 255, 0) if clearance >= self.camera_clearance else (0, 0, 255)
        cv2.rectangle(frame, (location[3], location[0]),
                      (location[1], location[2]), color, 2)
        frame = Image.fromarray(frame)
        draw_frame = ImageDraw.Draw(frame)
        draw_frame.text((location[3], location[0] - 10), f'{self.camera_codename}\n{name}',
                        (255, 255, 255), font=ImageFont.truetype('arial.ttf', 25))
        return np.array(frame)

    def save_image(self, lock, frame=None, name=None, intent=0):
        direct = './source/data/recognitions/'
        if frame is None:
            filename = f'{direct}placeholder-image.png'
        elif name is not None and intent == 2:  # recognition
            filename = f'{direct}{"".join([self.transcr.get(i, "") for i in name.upper()])}{dt.datetime.now().strftime(self.dt_format)}.jpg'
        elif intent in [0, 1]:  # 0 - tresspass, 1 - tlevel
            playsound('.\\source\\sounds\\alert_sound.mp3')
            filename = f'{direct}{("trespass" if intent == 0 else "level")}{dt.datetime.now().strftime(self.dt_format)}.jpg'

        cv2.imwrite(filename, frame)
        with lock:
            with open('./source/data/recognition.txt', 'a', encoding='utf-8') as f:
                f.write(f'{(name if intent in [1, 2] else "Unknown")};{dt.datetime.now().strftime(self.dt_format)};{filename};{int(intent == 2)};{self.camera_index}\n')
                f.flush()

    def update_recognition_times(self, name, lock):
        last_saved_date_compared = self.compare_dates_by_name(name)
        self.recognition_times[last_saved_date_compared[1]] = [
            name, dt.datetime.now().strftime(self.dt_format)]
        with lock:
            with open('./source/data/recognition.txt', 'w', encoding='utf-8') as f:
                for line in self.recognition_times:
                    f.write(';'.join(line) + '\n')
                f.flush()

    def compare_dates_by_name(self, name):
        for index, line in enumerate(self.recognition_times):
            if line[0] == name:
                last_saved_time = dt.datetime.strptime(line[1], self.dt_format)
                dt_compared = dt.datetime.now() - last_saved_time
                return [dt_compared.total_seconds() / 60, index]
        return [10**6, len(self.recognition_times)]
