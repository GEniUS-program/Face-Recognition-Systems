import numpy as np

import face_recognition
import sqlalchemy
import datetime
import pickle
import cv2
import os

from mysql.connector import Error
from PIL import Image, ImageDraw, ImageFont
from flask import Flask, request, jsonify, url_for
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


app = Flask(__name__)

sql_engine = sqlalchemy.create_engine(
    'mysql+mysqlconnector://Ndioksiatdian:KPks8kp3N2skABX@Ndioksiatdian.mysql.pythonanywhere-services.com/Ndioksiatdian$default'
)

app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this in production
jwt = JWTManager(app)
# user_id:int:[access_token: str, public_key_pem: PublicKeyTypes, aes_key: bytes]
users = {}
to_confirm = {}  # email: [password, username]

PRIVATE_KEY = rsa.generate_private_key(  # KEYS FOR RSA (ASYMMETRIC ENCRYPTION)
    public_exponent=65537,
    key_size=2048,
    backend=default_backend()
)

PUBLIC_KEY = PRIVATE_KEY.public_key()  # KEYS FOR RSA (ASYMMETRIC ENCRYPTION)

PUBLIC_KEY_SERIALIZED = PUBLIC_KEY.public_bytes(  # KEYS FOR RSA (ASYMMETRIC ENCRYPTION)
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

GLOBAL_ASYMMETRIC_KEY = os.urandom(32)


def encrypt_for_user_rsa(data: bytes, user_id: int) -> bytes:
    global users
    return users[user_id][1].encrypt(
        data,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def decrypt_user_rsa(data: bytes) -> bytes:
    return PRIVATE_KEY.decrypt(
        data,
        rsa_padding.OAEP(
            mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def encrypt_aes(data: bytes, user_id: int, iv=None) -> tuple[bytes, bytes]:
    global users
    if iv is None:
        iv = os.urandom(16)  # AES block size is 16 bytes

    padder = padding.PKCS7(algorithms.AES.block_size).padder()

    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(users[user_id][2]), modes.CFB(
        iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return [iv, ciphertext]


def decrypt_aes(data: bytes, iv: bytes, user_id: int) -> bytes:
    global users

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

    cipher = Cipher(algorithms.AES(users[user_id][2]), modes.CFB(iv))
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(data) + decryptor.finalize()

    decrypted_data = unpadder.update(decrypted_data) + unpadder.finalize()

    return decrypted_data


def encrypt_aes_global(data: bytes, iv=None) -> bytes:
    global GLOBAL_ASYMMETRIC_KEY
    if iv is None:
        iv = os.urandom(16)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()

    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(GLOBAL_ASYMMETRIC_KEY), modes.CFB(
        iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    return iv, ciphertext


def decrypt_aes_global(data: bytes, iv: bytes) -> bytes:
    global GLOBAL_ASYMMETRIC_KEY
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()

    cipher = Cipher(algorithms.AES(GLOBAL_ASYMMETRIC_KEY), modes.CFB(iv))
    decryptor = cipher.decryptor()
    decrypted_data = decryptor.update(data) + decryptor.finalize()

    decrypted_data = unpadder.update(decrypted_data) + unpadder.finalize()

    return decrypted_data


def hash_data(data) -> str:
    data_hash = hashes.Hash(hashes.SHA256(), backend=default_backend())
    data_hash.update(data.encode())
    return data_hash.finalize().hex()


@app.route('/login', methods=['POST', 'GET'])
def establish_connection():
    global users, sql_engine, PUBLIC_KEY_SERIALIZED
    data = request.get_json()

    client_public_key_pem = data.get("client_public_key")

    client_public_key = serialization.load_pem_public_key(
        bytes.fromhex(client_public_key_pem),
        backend=default_backend()
    )

    password = data.get("password")
    username = data.get("username")
    try:
        with sql_engine.connect() as connection:
            rows = connection.execute(sqlalchemy.text(
                "SELECT id, username, password FROM users"))
            rows = rows.fetchall()

        for row in rows:
            if password == row['password'].hex() and username == row['username'].hex():
                user_id = row[0]
                break
        else:
            return jsonify({"error": "Отказано в доступе. Неверный логин или пароль"}), 401
    except Error as e:
        print(e)
        return jsonify({"error": f"Возникла непредвиденная ошибка. Попробуйте позже."}), 500
    else:
        access_token = create_access_token(identity=str(user_id))
        users[user_id] = [access_token, client_public_key, os.urandom(32)]
        iv, encrypted_token = encrypt_aes(
            users[user_id][0].encode(), user_id)
        eiv = encrypt_for_user_rsa(iv, user_id)
        iv, encrypted_server_public_key = encrypt_aes(
            PUBLIC_KEY_SERIALIZED.encode(), user_id, iv)
        encrypted_aes_key = encrypt_for_user_rsa(users[user_id][2], user_id)
        return jsonify({"token": encrypted_token.hex(), "server_public_key": encrypted_server_public_key.hex(), "user_id": user_id, "aes_key": encrypted_aes_key.hex(), "eiv": eiv.hex()}), 200


@app.route('/register_user', methods=['POST'])
def register_new_user():
    global to_confirm, sql_engine  # connection,
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    try:
        with sql_engine.connect() as connection:
            connection.execute(
                "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
                (bytes.fromhex(username), bytes.fromhex(
                    password), 'placeholder@mail.ru')
            )
            connection.commit()
        return jsonify({"success": True, "reason": "User registered successfully"}), 200
    except Exception as e:
        if 'Duplicate entry' in str(e):
            return jsonify({"success": False, "reason": "server error "}), 400
        else:
            return jsonify({"success": False, "reason": "server error "}), 500


@app.route('/face_recognition', methods=['POST'])
@jwt_required(locations=['headers'])
def face_recognition_api():
    input_data = request.get_json()
    frame = input_data['frame']
    eiv = input_data['eiv']
    camera_index = input_data['camera_index']
    camera_clearance = input_data['camera_clearance']
    camera_codename = input_data['camera_name']
    face_locations = pickle.loads(bytes.fromhex(input_data['faces']))
    data_to_send = []
    user_id = int(get_jwt_identity())

    frame = decrypt_aes(bytes.fromhex(
        frame), decrypt_user_rsa(bytes.fromhex(eiv)), user_id)
    encoded_frame_np = np.frombuffer(frame, dtype=np.uint8)

    frame = cv2.imdecode(encoded_frame_np, cv2.IMREAD_UNCHANGED)
    data_to_send.append(face_locations)
    known_face_encodings, known_face_names, clearances = get_faces(user_id)[:3]
    if not face_locations:
        return jsonify({"return": "empty"}), 200

    face_encodings = face_recognition.face_encodings(frame, face_locations)

    names = []
    rec_clear = []
    for face_encoding in face_encodings:

        matches = face_recognition.compare_faces(
            known_face_encodings, face_encoding)

        name, clearance = get_recognition_info(
            clearances, known_face_names, known_face_encodings, matches, face_encoding)

        names.append(name)
        rec_clear.append(clearance)
        intent = 1
        if name == "Unknown":
            intent = 0
        elif clearance < int(camera_clearance):

            intent = 0
        else:
            intent = 1

        save_recognition_info(user_id, name, frame, intent, camera_index)

    data_to_send = [frame, face_locations, names, rec_clear]
    data_to_send = pickle.dumps(data_to_send)
    iv, data_to_send = encrypt_aes(data_to_send, user_id)

    eiv = encrypt_for_user_rsa(iv, user_id)

    return jsonify({"return": data_to_send.hex(), "eiv": eiv.hex()}), 200


def save_recognition_info(user_id, name, image, level, cam_index):
    global sql_engine
    image = cv2.imencode('.jpg', image)[1].tobytes()
    iv, image = encrypt_aes_global(image)
    with sql_engine.connect() as connection:  # Connect to the database
        connection.execute(
            "INSERT INTO recognition_history (acc_id, name, date_time, image, sufficient_level, cam_index, eiv) VALUES (%s, %s, %s, %s, %s, %s, %s)", (
                user_id, name, datetime.datetime.now(), image, level, cam_index, iv)
        )


def get_recognition_info(clearances, known_face_names, known_face_encodings, matches, face_encoding):
    if True in matches:
        face_distances = face_recognition.face_distance(
            known_face_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        name = known_face_names[best_match_index]
        clearance = int(clearances[best_match_index])
        return name, clearance
    return "Unknown", 0


def get_faces(user_id):
    global sql_engine
    with sql_engine.connect() as connection:
        rows = connection.execute(
            "SELECT vector, eiv, name, access_level, face_id, image FROM faces WHERE acc_id = %s", (
                user_id,)
        )

    face_encodings = []
    names = []
    clearances = []
    face_ids = []
    images = []
    for row in rows:
        # face_encoding, name, clearance
        face_encodings.append(pickle.loads(
            decrypt_aes_global(row[0], row[1])))
        names.append(decrypt_aes_global(row[2], row[1]).decode())
        clearances.append(row[3])
        face_ids.append(row[4])
        image = decrypt_aes_global(row[5], row[1])
        nparr = np.frombuffer(image, np.uint8)
        images.append(cv2.imdecode(nparr, cv2.IMREAD_COLOR))
    return face_encodings, names, clearances, face_ids, images


@app.route('/get_recognition_history', methods=['POST'])
@jwt_required(locations=['headers'])
def get_recognition_history():
    global sql_engine
    user_id = int(get_jwt_identity())

    with sql_engine.connect() as connection:
        rows = connection.execute(
            "SELECT name, date_time, cam_index, sufficient_level, image, eiv FROM recognition_history WHERE acc_id = %s", (user_id,))
        result = rows.fetchall()

    names, datetimes, cam_indexes, levels, images, eivs = list(
    ), list(), list(), list(), list(), list()
    for row in result:
        names.append(row[0])
        datetimes.append(row[1])
        cam_indexes.append(row[2])
        levels.append(row[3])
        image = decrypt_aes_global(row[4], row[5])
        iv = os.urandom(16)
        image = encrypt_aes(image, user_id, iv)
        eivs.append(iv)
        images.append(row[4])

    data_to_send = [names, datetimes, cam_indexes, levels, images, eivs]
    data_to_send1 = pickle.dumps(data_to_send)
    # iv, data_to_send2 = encrypt_aes(data_to_send1, user_id)
    # eiv = encrypt_for_user_rsa(iv, user_id)

    return jsonify({"return": data_to_send1.hex()}), 200  # , "eiv": eiv.hex()}


@app.route('/get_faces', methods=['POST'])
@jwt_required(locations=['headers'])
def get_faces_list():
    global sql_engine
    user_id = int(get_jwt_identity())

    _, names, clearances, face_ids, images = get_faces(user_id)
    ivs = list()
    for i, image in enumerate(images):
        image = cv2.imencode('.jpg', image)[1].tobytes()
        iv, image = encrypt_aes(image, user_id)
        images[i] = image
        ivs.append(iv)
    data_to_send = [face_ids, names, clearances, images, ivs]
    data_to_send = pickle.dumps(data_to_send)

    return jsonify({"return": data_to_send.hex()}), 200


@app.route('/add_face', methods=['POST'])
@jwt_required(locations=['headers'])
def add_face():
    global sql_engine
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        data1 = data['data']
        iv = bytes.fromhex(data['eiv'])
        dec_data = decrypt_aes(bytes.fromhex(
            data1), decrypt_user_rsa(iv), user_id)
    except Exception as e:
        return jsonify({"reason": f"server error, {e}"}), 500
    try:
        data = pickle.loads(dec_data)
        name, clearance, encoding_vec, image = data
        iv1, image = encrypt_aes_global(image)
        _, encoding_vec = encrypt_aes_global(
            pickle.dumps(encoding_vec), iv1)
        _, name = encrypt_aes_global(name.encode('utf-8'), iv1)
    except Exception as e:
        return jsonify({"reason": f"server error, {e}"}), 500
    try:

        with sql_engine.connect() as connection:
            connection.execute(
                "INSERT INTO faces (acc_id, name, access_level, vector, image, eiv) VALUES (%s, %s, %s, %s, %s, %s)", (
                    user_id, name, clearance, encoding_vec, image, iv1)
            )

        return jsonify({"message": "Face added successfully!"}), 200
    except Exception as e:
        return jsonify({"reason": f"server error, {e}"}), 500


@app.route('/logout', methods=['POST'])
@jwt_required(locations=['headers'])
def logout():
    global users
    user_id = get_jwt_identity()
    del users[user_id]
    return jsonify({"message": "Logout successful!"}), 200
