import face_recognition
import datetime as dt
import numpy as np
import logging
import json
import cv2
import os
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
        self.recognition_times = self.load_recognition_history()
        self.recognition_times_a = self.load_all_recognitions()

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

    def load_recognition_history(self):
        with open('./source/data/recognition_history.txt', 'r', encoding='utf-8') as f:
            return [j.strip('\n').split(';') for j in f.readlines()]

    def load_all_recognitions(self):
        with open('./source/data/recognition.txt', 'r', encoding='utf-8') as f:
            return [j.strip('\n').split(';') for j in f.readlines()]

    def compare_faces(self, frame, lock):
        self.recognition_times = self.load_recognition_history()
        print('comparing faces')
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
                self.save_trespass_image(frame, lock)
                return None

            frame = self.draw_face_rectangle(
                frame, (top, right, bottom, left), name, clearance)

            if clearance < self.camera_clearance:
                self.save_tlevel_image(frame, name, lock)
                return None

            last_saved_date_compared = self.compare_dates_by_name(name)
            print(last_saved_date_compared)
            with lock:
                with open('./source/data/recognition.txt', 'a', encoding='utf-8') as f:
                    f.write(
                        f"{name};{dt.datetime.now().strftime(self.dt_format)};'.\\source\\images\\placeholder-image.png';1;{self.camera_index}\n")
                    f.flush()

            if last_saved_date_compared[0] >= self.saving_limit:
                self.save_recognition_image(frame, name, lock)

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

    def save_trespass_image(self, frame, lock):
        playsound('.\\source\\sounds\\alert_sound.mp3')
        filename = f'./source/data/recognition_trespass/trespass{dt.datetime.now().strftime(self.dt_format)}.jpg'
        cv2.imwrite(filename, frame)
        with lock:
            with open('./source/data/recognition.txt', 'a', encoding='utf-8') as f:
                f.write(
                    f'Unknown;{dt.datetime.now().strftime(self.dt_format)};{filename};0;{self.camera_index}\n')
                f.flush()

    def save_tlevel_image(self, frame, name, lock):
        playsound('.\\source\\sounds\\alert_sound.mp3')
        filename = f'./source/data/recognitions/level{dt.datetime.now().strftime(self.dt_format)}.jpg'
        cv2.imwrite(filename, frame)
        with lock:
            with open('./source/data/recognition.txt', 'a', encoding='utf-8') as f:
                f.write(
                    f'{name};{dt.datetime.now().strftime(self.dt_format)};{filename};0;{self.camera_index}\n')
                f.flush()

    def save_recognition_image(self, frame, name, lock):
        save_directory = './source/data/recognitions/'
        os.makedirs(save_directory, exist_ok=True)  # Ensure directory exists

        transliterated_name = "".join(
            [self.transcr.get(i, '') for i in name.upper()])
        filename = f'{transliterated_name} {dt.datetime.now().strftime(self.dt_format)}.jpg'
        full_path = os.path.join(save_directory, filename)

        success = cv2.imwrite(full_path, frame)
        if success == True:
            print('updating recognition times')
            self.update_recognition_times(name, full_path, lock)
        else:
            logging.error('Failed to save image.')
        with lock:
            with open('./source/data/recognition.txt', 'a', encoding='utf-8') as f:
                f.write(
                    f'{name};{dt.datetime.now().strftime(self.dt_format)};{full_path};1;{self.camera_index}\n')
                f.flush()

    def update_recognition_times(self, name, full_path, lock):
        last_saved_date_compared = self.compare_dates_by_name(name)
        self.recognition_times[last_saved_date_compared[1]] = [
            name, dt.datetime.now().strftime(self.dt_format), full_path
        ]
        with lock:
            with open('./source/data/recognition_history.txt', 'w', encoding='utf-8') as f:
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
