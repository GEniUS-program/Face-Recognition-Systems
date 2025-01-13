import face_recognition
import cv2
import numpy as np
import logging
import os


class DataBaseWorker:
    def __init__(self):
        logging.info('Database worker initialized...')
        self.names = list()
        self.clearances = list()
        self.vectors = list()
        self.faces = list()

        self.read_saved_data()

    def add(self, name, clearance, facepath):
        face_image = cv2.imread(facepath)
        encoding_vector = face_recognition.face_encodings(face_image)[0]

        with open(f"./faces/vectors/{'-'.join([name for name in name.split(' ')])}vector.txt", 'w', encoding='utf-8') as f:
            f.write(f"{encoding_vector}\n")

        self.names.append(name)
        self.clearances.append(clearance)
        self.vectors.append(encoding_vector)
        self.faces.append(facepath)

        try:
            with open('./faces/faces_list/faces.txt', 'a', encoding='utf-8') as f:
                f.write(
                    f"{name};{clearance};./faces/vectors/{'-'.join([name for name in name.split(' ')])}vector.txt;{facepath}\n")
            logging.info(f'Added data to ./faces/faces_list/faces.txt')

        except Exception as e:
            logging.critical(
                f'An error occured when adding data to ./faces/faces_list/faces.txt. Error details: {e}')

    def edit(self, *args):# name, clearance, filepath, line_index
        with open('./faces/faces_list/faces.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        line_index = args[-1]

        for i in range(len(args)):
            if args[i] == '':
                args[i] = lines[line_index].split(';')[0]

        name, clearance, filepath = args[:3:]
        if filepath != lines[line_index].split(';')[3]:
            new_vector = face_recognition.face_encodings(cv2.imread(filepath))[0]
            with open(f"./faces/vectors/{'-'.join([name for name in name.split(' ')])}vector.txt", 'w', encoding='utf-8') as f:
                f.write(f"{new_vector}\n")
            lines[line_index] = name + ';' + clearance + f';./faces/vectors/{"-".join([name for name in name.split()])}vector.txt;' + filepath + '\n'
        
        lines[line_index] = name + ';' + clearance + ';' + lines[line_index].split(';')[2] + ';' + filepath + '\n'
        
        with open('./faces/faces_list/faces.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def delete(self, name, clearance, filepath):
        logging.info(f'Deleting data for {name}...')
        with open('./faces/faces_list/faces.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        logging.debug(f'lines to process: {lines}')

        for line in lines:
            
            if name in line and clearance in line and filepath in line:
                lines.remove(line)
                break
        else:
            logging.warning(f'No data found to delete for {name}.')
            return
        
        with open('./faces/faces_list/faces.txt', 'w', encoding='utf-8') as f:
            f.writelines(lines)

        os.remove('./faces/vectors/' + '-'.join([name for name in name.split(' ')]) + 'vector.txt')

    def read_saved_data(self):
        logging.info('Reading saved data...')
        with open('./faces/faces_list/faces.txt', 'r', encoding='utf-8') as f:
            for line in f.readlines():
                line = line.strip().split(';')
                self.names.append(line[0])
                self.clearances.append(line[1])
                self.faces.append(line[3])
                with open(line[2], 'r') as fil:
                    self.vectors.append(
                        np.array([float(x) for x in fil.read().replace('[', '').replace(']', '').split()]))


    def clear_read_data(self):
        logging.info('Clearing read data...')
        self.names = list()
        self.clearances = list()
        self.vectors = list()
        self.faces = list()
        logging.info('Data cleared.')
        logging.warning('Database worker has no data.')
