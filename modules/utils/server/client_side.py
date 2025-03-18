import requests
import face_recognition
import cv2
import os
from modules.utils.communicator import Communicate
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa


class Client:
    def __init__(self):
        self.username = None
        self.password = None
        self.email = None
        self.token = None  # JWT token
        self.enc_key = None
        self.decr_key = None
        self.large_data_key = None
        self.padder = padding.PKCS7(algorithms.AES.block_size).padder()
        self.unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
        self.acc_id = None

        reg_com = Communicate()
        self.successful_reg_signal = reg_com.signal

    def decrypt_rsa(self, data: bytes) -> bytes:
        return self.decr_key.decrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        ).decode()

    def encrypt_rsa(self, data: bytes) -> bytes:
        return self.enc_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

    def decrypt_aes(self, data: bytes, iv: bytes) -> bytes:
        cipher = Cipher(algorithms.AES(self.large_data_key), modes.CFB(iv))
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(data) + decryptor.finalize()

        decrypted_data = self.unpadder.update(
            decrypted_data) + self.unpadder.finalize()

        return decrypted_data

    def encrypt_aes(self, data: bytes) -> list:
        iv = os.urandom(16)

        padded_data = self.padder.update(
            data) + self.padder.finalize()

        cipher = Cipher(algorithms.AES(self.large_data_key),
                        modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        enc_iv = self.encrypt_rsa(iv)

        return [enc_iv, ciphertext]

    def hash_data(self, data) -> str:
        data_hash = hashes.Hash(hashes.SHA256(), backend=default_backend())
        data_hash.update(data.encode())
        return data_hash.finalize().hex()

    def establish_connection(self, username: str, password: str, email: str) -> None:

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
        hashed_password = self.hash_data(password)
        hashed_username = self.hash_data(username)

        response = requests.post("http://127.0.0.1:5000/establish_connection", json={
            "client_public_key": self.other_enc_key.hex(),
            "password": hashed_password,
            "username": hashed_username,
            "email": email
        })

        if response.status_code != 200:
            print('error code', response.status_code)
            pass
        response = response.json()
        encrypted_server_key = bytes.fromhex(response["server_public_key"])
        decrypted_server_key = self.decrypt_rsa(encrypted_server_key)
        self.enc_key = serialization.load_pem_private_key(
            decrypted_server_key,
            backend=default_backend()
        )

        # acquire token
        self.token = bytes.fromhex(response["token"])
        self.token = self.decrypt_rsa(self.token).decode()

        self.acc_id = response["user_id"]

        self.large_data_key = bytes.fromhex(response["aes_key"])
        self.large_data_key = self.decrypt_rsa(self.large_data_key)

    def register_user(self, username: str, password: str, email: str) -> None:
        hashed_password = self.hash_data(password)
        hashed_username = self.hash_data(username)

        response = requests.post("http://127.0.0.1:5000/register_user", json={
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

    def send_request(self, url, data: bytes, encrypted='rsa', target='read'):
        eiv = None
        if data is not None:
            if encrypted == 'rsa':
                data = self.encrypt_rsa(data)
            elif encrypted == 'aes':
                eiv, data = self.encrypt_aes(data)

        response = requests.post(url, json={
            "encrypted": encrypted,
            "target": target,
            "data": data,
            "token": self.token,
            "eiv": eiv
        }, headers={"Authorization": f"Bearer {self.token}"})

        response_data = response.json()

        if response.status_code == 200:
            if encrypted == 'rsa':
                return self.decrypt_rsa(response_data["data"])
            elif encrypted == 'aes':
                return self.decrypt_aes(response_data["data"], self.decrypt_rsa(response_data[eiv]))
        else:
            return

    def send_faces_request(self, data=None, old_data=None, encrypted='rsa', target='read'):
        """
        Send request for the faces table in the db.\n
        For delete, use old_data.\n
        For edit use data, old_data.\n
        For add use data.
        Args:
            data (bytes): data to send to server
            encrypted (str): choose an encyption algorithm. Can be: "rsa", "aes" or "not" for no encryption
            target (str): tells the server what to do with the db. Can be: "add", "read", "edit", "del".
        """

        index = 'http://127.0.0.1:5000/faces/'

        if target == "add":
            eiv = None
            if encrypted == 'rsa':
                data = self.encrypt_rsa(data)
            elif encrypted == 'aes':
                eiv, data = self.encrypt_aes(data)

            response = requests.post(index, json={
                "encrypted": encrypted,
                "target": "add",
                "data": data.hex(),
                "eiv": eiv.hex()
            }, headers={"Authorization": f"Bearer {self.token}"})

            if response.status_code == 200:
                return {"success": True, "reason": "added"}
            else:
                return {"success": False, "reason": "unknown"}
            
        elif target == "read":
            response = requests.post(index, json={
                "target": "read"
            }, headers={"Authorization": f"Bearer {self.token}"})

            if response.status_code == 200:
                return {"success": True, "reason": "read_data", "data": response.json()} # acc_id, face_id, name, access_level, vector, image
            else:
                return {"success": False, "reason": "unknown"}
            
        elif target == "edit":
            eiv_old, eiv_new = None, None
            if encrypted == "rsa":
                data = self.encrypt_rsa(data)
                old_data = self.encrypt_rsa(old_data)
            elif encrypted == 'aes':
                eiv_new, data = self.encrypt_aes(data)
                eiv_old, old_data = self.encrypt_aes(old_data)

            response = requests.post(index, json={
                "encrypted": encrypted,
                "target": "edit",
                "new_data": data.hex(),
                "old_data": old_data.hex(),
                "new_eiv": eiv_new.hex(),
                "old_eiv": eiv_old.hex()
            }, headers={"Authorization": f"Bearer {self.token}"})

            if response.status_code == 200:
                return {"success": True, "reason": "edited"}
            else:
                return {"success": False, "reason": "unknown"}
        elif target == "del":
            eiv = None
            if encrypted == 'rsa':
                data = self.encrypt_rsa(old_data)
            elif encrypted == 'aes':
                eiv, data = self.encrypt_aes(old_data)

            response = requests.post(index, json={
                "encrypted": encrypted,
                "target": "del",
                "data": data.hex(),
                "eiv": eiv.hex()
            }, headers={"Authorization": f"Bearer {self.token}"})

            if response.status_code == 200:
                return {"success": True, "reason": "deleted"}
            else:
                return {"success": False, "reason": "unknown"}
            
        else:
            return {"success": False, "reason":"invalid target"}