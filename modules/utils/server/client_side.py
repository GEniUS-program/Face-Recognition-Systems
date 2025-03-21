import face_recognition
import numpy as np
import requests
import pickle
import cv2
import os
from modules.utils.communicator import Communicate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding


class Client:
    def __init__(self):
        self.username = None
        self.password = None
        self.email = None
        self.token = None  # JWT token
        self.enc_key = None
        self.decr_key = None
        self.large_data_key = None
        self.acc_id = None

        self.reg_com = Communicate()
        self.successful_reg_signal = self.reg_com.signal

    def decrypt_rsa(self, data: bytes) -> bytes:
        return self.decr_key.decrypt(
            data,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def encrypt_rsa(self, data: bytes) -> bytes:
        return self.enc_key.encrypt(
            data,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def decrypt_aes(self, data: bytes, iv: bytes) -> bytes:
        
        cipher = Cipher(algorithms.AES(self.large_data_key), modes.CFB(iv))
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(data) + decryptor.finalize()


        return decrypted_data

    def encrypt_aes(self, data: bytes, iv: None|bytes=None) -> tuple[bytes, bytes]:
        if iv is None:
            iv = os.urandom(16)
        

        cipher = Cipher(algorithms.AES(self.large_data_key),
                        modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()

        enc_iv = self.encrypt_rsa(iv)

        return [enc_iv, ciphertext]

    def hash_data(self, data: bytes) -> str:
        data_hash = hashes.Hash(hashes.SHA256(), backend=default_backend())
        data_hash.update(data)
        return data_hash.finalize().hex()

    def establish_connection(self, username: str, password: str) -> None:

        self.decr_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        public_key = self.decr_key.public_key()

        self.other_enc_key = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        self.username = username
        self.password = password
        hashed_password = self.hash_data(password.encode())
        hashed_username = self.hash_data(username.encode())

        response = requests.post("https://ndioksiatdian.pythonanywhere.com/login", json={
            "client_public_key": self.other_enc_key.hex(),
            "password": hashed_password,
            "username": hashed_username
        })

        if response.status_code != 200:
            print('error code', response.status_code)
            print(response.json()["error"])
            return {"success": False, "reason": response.json()["error"]}
        
        res_data = response.json()

        iv = self.decrypt_rsa(bytes.fromhex(res_data["eiv"]))
        
        self.large_data_key = bytes.fromhex(res_data["aes_key"])
        self.large_data_key = self.decrypt_rsa(self.large_data_key)

        decrypted_server_key = self.decrypt_aes(bytes.fromhex(res_data["server_public_key"]), iv)

        self.enc_key = serialization.load_pem_public_key(
            decrypted_server_key,
            backend=default_backend()
        )
                
        # acquire token
        self.token = bytes.fromhex(res_data["token"])
        self.token = self.decrypt_aes(self.token, iv).decode()

        self.acc_id = res_data["user_id"]

        return {"success": True}

    def register_user(self, username: str, password: str, email: str) -> None:
        hashed_password = self.hash_data(password)
        hashed_username = self.hash_data(username)

        response = requests.post("https://ndioksiatdian.pythonanywhere.com/register_user", json={
            "username": hashed_username,
            "password": hashed_password,
            "email": email
        })

        if response.status_code == 200:
            self.successful_reg_signal.emit({"success": True})
        elif response.status_code == 400:
            self.successful_reg_signal.emit(
                {"success": False, "reason": "alredy exists"})
        elif response.status_code == 500:
            self.successful_reg_signal.emit(
                {"success": False, "reason": "server error"})
            return
        else:
            self.successful_reg_signal.emit(
                {"success": False, "reason": "request_error"})

    def face_recognition(self, frame, camera_clearance: int, camera_name: str, camera_index: int, faces: list):
        eiv, encrypted_frame = self.encrypt_aes(frame)
        json = {
            "frame": encrypted_frame.hex(),
            "eiv": eiv.hex(),
            "camera_clearance": camera_clearance,
            "camera_name": camera_name,
            "camera_index": camera_index,
            "faces": pickle.dumps(faces).hex()
        }
        print('Sending face recognition request...')
        response = requests.post("https://ndioksiatdian.pythonanywhere.com/face_recognition", json=json, headers={"Authorization": f"Bearer {self.token}"})

        data = response.json()

        status = data['return']
        if status != 'empty':
            data = self.decrypt_aes(bytes.fromhex(data["return"]), self.decrypt_rsa(bytes.fromhex(data["eiv"])))

            data = pickle.loads(data)

        return data if status != 'empty' else []
    
    def get_recognition_history(self):        
        names, datetimes, cam_indexes, levels, images = list(), list(), list(), list(), list()
        response = requests.post("https://ndioksiatdian.pythonanywhere.com/get_recognition_history", headers={"Authorization": f"Bearer {self.token}"}) # name, datetime, cam_index, level, image

        data = response.json()

        hash1 = data['hashf']

        eivs = data['eivs']
        eivs = bytes.fromhex(eivs)
        hash2 = self.hash_data(eivs)
        eivs = pickle.loads(eivs)

        returned_data1 = data['return']
        returned_data2 = bytes.fromhex(returned_data1)
        returned_data4 = pickle.loads(returned_data2)

        print('hash1:', hash1)
        print('hash2:', hash2)

        print(returned_data4[0], returned_data4[1], returned_data4[2], returned_data4[3], returned_data4[5])
        for (name, cam_index, level) in zip(returned_data4[0], returned_data4[2], returned_data4[3]):
            names.append(name)
            cam_indexes.append(cam_index)
            levels.append(level)

        for (image, eiv1) in zip(returned_data4[4], eivs):
            print(f'image type: {type(image)}; eiv type: {type(eiv1)}; eiv: {eiv1}; len eiv: {len(eiv1)}')
            image = self.decrypt_aes(image, eiv1)
            print(f'Decrypted bytes length: {len(image)}')
            print(f'Decrypted data sample: {image[:10]}')  # Debug: Check the length of the decrypted data

            npa = np.frombuffer(image, np.uint8)
            print(f'npa shape: {npa.shape}')  # Debug: Check the shape of the numpy array

            image = cv2.imdecode(npa, cv2.IMREAD_COLOR)
            if image is None:
                print("Error: cv2.imdecode returned None. Invalid image data.")
            else:
                print(f'Decoded image shape: {image.shape}')  # Debug: Check the shape of the decoded image
                images.append(image)

        for datetime in returned_data4[1]:
            datetime = datetime.strftime('%Y-%m-%d %H:%M:%S')
            datetimes.append(datetime)

        return names, datetimes, cam_indexes, levels, images
    
    def get_faces(self):
        response = requests.post("https://ndioksiatdian.pythonanywhere.com/get_faces", headers={"Authorization": f"Bearer {self.token}"}) # name, clearance, face image
        
        response_data = response.json()

        data = response_data['return']
        data1 = bytes.fromhex(data)
        data2 = pickle.loads(data1)

        ids = data2[0]
        names = data2[1]
        clearances = data2[2]
        faces = data2[3]
        ivs = data2[4]
        for i, face in enumerate(faces):
            face = self.decrypt_aes(face, ivs[i])
            npa = np.frombuffer(face, np.uint8)
            face = cv2.imdecode(npa, cv2.IMREAD_COLOR)
            faces[i] = face

        return (ids, names, clearances, faces)
    
    def add_face(self, name: str, clearance: str, face: str):
        face_img = cv2.imread(face)
        face_img1 = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        try:
            encoding_vec = face_recognition.face_encodings(face_img1)[0]
        except IndexError:
            return {'success': False, 'reason': 'no face'}
        clearance = int(clearance)

        iv, data = self.encrypt_aes(pickle.dumps((name, clearance, encoding_vec, cv2.imencode('.jpg', face_img)[1].tobytes())))

        response = requests.post("https://ndioksiatdian.pythonanywhere.com/add_face", json={
            "data": data.hex(),
            "eiv": iv.hex()
        }, headers={"Authorization": f"Bearer {self.token}"})

        sc = response.status_code
        responsed = response.json()
        if sc == 200:
            return {'success': True}
        elif sc == 500:
            print(responsed["reason"])
            return {'success': False, 'reason': responsed['reason']}