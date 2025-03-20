import numpy as np

import face_recognition
import mysql.connector
import sqlalchemy
import smtplib
import datetime
import secrets
import pickle
import cv2
import os

from mysql.connector import Error
from PIL import Image, ImageDraw, ImageFont
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, url_for
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import rsa
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


app = Flask(__name__)

sql_engine = sqlalchemy.create_engine(
    'mysql+mysqlconnector://Ndioksiatdian:KPks8kp3N2skABX@Ndioksiatdian.mysql.pythonanywhere-services.com/Ndioksiatdian$default'
)
# Setup mail server
app.config["MAIL_SERVER"] = "smtp.gmail.com"  # gmail.ru smtp server
app.config["MAIL_PORT"] = 465  # smtp port
app.config["MAIL_USE_SSL"] = True  # ssl/tls
app.config["MAIL_USERNAME"] = "romannikitin081@gmail.com"
app.config["MAIL_PASSWORD"] = "kztc ezms iijl fvws"
app.config["MAIL_DEFAULT_SENDER"] = "romannikitin081@gmail.com"
# Connect to SMTP server
server = smtplib.SMTP_SSL(app.config["MAIL_SERVER"], 465)
server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
server.auth_plain()
#server.connect(host=app.config["MAIL_SERVER"], port=app.config["MAIL_PORT"])

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

padder = padding.PKCS7(algorithms.AES.block_size).padder()
unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()


def encrypt_for_user_rsa(data: bytes, user_id: int) -> bytes:
    global users
    return users[user_id][1].encrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def decrypt_user_rsa(data: bytes) -> bytes:
    return PRIVATE_KEY.decrypt(
        data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )


def encrypt_aes(data: bytes, user_id: int) -> tuple[bytes, bytes]:
    global users, padder
    iv = os.urandom(16)  # AES block size is 16 bytes

    padded_data = padder.update(data) + padder.finalize()

    cipher = Cipher(algorithms.AES(users[user_id][2]), modes.CFB(
        iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    enc_iv = encrypt_for_user_rsa(iv, user_id)

    return [enc_iv, ciphertext]


def decrypt_aes(data: bytes, iv: bytes, user_id: int) -> bytes:
    global users, unpadder

    cipher = Cipher(algorithms.AES(users[user_id][2]), modes.CFB(iv))
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

    if client_public_key_pem:

        client_public_key = serialization.load_pem_public_key(
            bytes.fromhex(client_public_key_pem),
            backend=default_backend()
        )

    else:
        return jsonify({"error": "No public key provided."}), 400

    password = data.get("password")
    username = data.get("username")
    try:
        with sql_engine.connect() as connection:
            rows = connection.execute(sqlalchemy.text(
                "SELECT id, username, password FROM users;"))
            rows = rows.fetchall()

        for row in rows:
            if password == row['password'].hex() and username == row['username'].hex():
                user_id = row[0]
                break
        else:
            return jsonify({"error": "Access denied."}), 401
    except Error as e:
        print(e)
        return jsonify({"error": f"An error occurred"}), 500
    else:
        access_token = create_access_token(identity=str(user_id))
        users[user_id] = [access_token, client_public_key, os.urandom(32)]
        encrypted_token = encrypt_for_user_rsa(
            users[user_id][0].encode(), user_id)
        encrypted_server_public_key = encrypt_for_user_rsa(
            PUBLIC_KEY_SERIALIZED.encode(), user_id)
        encrypted_aes_key = encrypt_for_user_rsa(users[user_id][2], user_id)
        return jsonify({"token": encrypted_token.hex(), "server_public_key": encrypted_server_public_key.hex(), "user_id": user_id, "aes_key": encrypted_aes_key.hex()}), 200


@app.route('/register_user', methods=['POST'])
def register_new_user():
    global to_confirm, server, sql_engine  # connection,
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    try:
        with sql_engine.connect() as connection:
            # Check if the user already exists
            user = connection.execute(
                "SELECT * FROM users WHERE email = :s", {'s': email}).fetchone()

        if user is not None:
            return jsonify({"error": "User already exists."}), 400
    except:
        pass
    token = create_access_token(
        identity=email, expires_delta=datetime.timedelta(hours=1))
    print('created token')
    to_confirm.update(
        {email: [bytes.fromhex(username), bytes.fromhex(password)]})

    confirmation_link = f'https://ndioksiatdian.pythonanywhere.com/confirm?jwt={token}'
    print('sending message')
    msg = MIMEMultipart()
    msg['From'] = app.config['MAIL_DEFAULT_SENDER']
    msg['To'] = email
    msg['Subject'] = "Подтвердите почтовый адрес"
    msg.attach(MIMEText(
        f"Пройдите по ссылке, чтобы подтвердить свой аккаунт: {confirmation_link}\nЕсли вы не запрашивали подтверждение, то просто проигнорируйте это сообщение.\n*Это автоматически сгенерированное сообщение, не отвечайте на него", 'plain'))
    server.send_message(msg)

    print('message sent')
    return jsonify({"message": "User awaits confirmation."}), 200


@app.route('/confirm', methods=['GET'])
# looks like http://host:port/confirm?jwt=token
@jwt_required(locations=['query_string'])
def confirm_email():
    print('clicked conf link')
    global to_confirm, sql_engine
    try:
        # Verify the token
        email = get_jwt_identity()  # Get the identity (email) from the token

        username, password = to_confirm.get(email)[0], to_confirm.get(email)[1]

        with sql_engine.connect() as connection:
            connection.execute(
                "INSERT INTO users (username, password, email) VALUES (:username, :password, :email);", {
                    'username': username,
                    'password': password,
                    'email': email
                })
            del to_confirm[email]

        return jsonify({"message": "Email confirmed successfully!"}), 200
    except Exception as e:
        return jsonify({"message": "Invalid or expired confirmation link.", "error": str(e)}), 400


@app.route('/faces', methods=['POST', 'GET'])
@jwt_required(locations=['headers'])
def faces_table():
    global sql_engine
    input_params = request.get_json()
    encryption = input_params['encrypted']  # aes, rsa, not
    target = input_params['target']  # add, edit, del, read
    user_id = int(get_jwt_identity())

    if target == 'add':
        if encryption == 'rsa':
            data = decrypt_user_rsa(bytes.fromhex(input_params['data']))
        elif encryption == 'aes':
            data = decrypt_aes(bytes.fromhex(input_params['data']), decrypt_user_rsa(
                bytes.fromhex(input_params['eiv'])), user_id)

        data = pickle.loads(data)  # Convert data form bytes to dictionary

        access_level = data['access_level']  # int
        vector = data['vector']  # bytes
        image = data['image']  # bytes

        with sql_engine.connect() as connection:
            connection.execute(
                "INSERT INTO faces (acc_id, access_level, vector, image) VALUES (:user_id, :access_level, :vector, :image);", {
                    'user_id': user_id,
                    'access_level': access_level,
                    'vector': vector,
                    'image': image}
            )
    elif target == 'edit':
        if encryption == 'rsa':
            new_data = decrypt_user_rsa(
                bytes.fromhex(input_params['new_data']))
            old_data = decrypt_user_rsa(
                bytes.fromhex(input_params['old_data']))
        elif encryption == 'aes':
            new_data = decrypt_aes(bytes.fromhex(input_params['new_data']), decrypt_user_rsa(
                bytes.fromhex(input_params['new_eiv'])), user_id)
            old_data = decrypt_aes(bytes.fromhex(input_params['old_data']), decrypt_user_rsa(
                bytes.fromhex(input_params['old_eiv'])), user_id)

        data = pickle.loads(data)

        access_level = data['access_level']
        vector = data['vector']
        image = data['image']
        with sql_engine.connect() as connection:
            connection.execute(
                "INSERT INTO faces (acc_id, access_level, vector, image) VALUES (:user_id, :access_level, :vector, :image);", {
                    'user_id': user_id,
                    'access_level': access_level,
                    'vector': vector,
                    'image': image}
            )

    elif target == 'del':
        if encryption == 'rsa':
            pass
        elif encryption == 'aes':
            pass
    elif target == 'read':
        if encryption == 'rsa':
            pass
        elif encryption == 'aes':
            pass


@app.route('/face_recognition', methods=['POST'])
@jwt_required(locations=['headers'])
def face_recognition_api():
    input_data = request.get_json()
    frame = input_data['frame']
    eiv = input_data['eiv']
    camera_index = input_data['camera_index']
    camera_clearance = input_data['camera_clearance']
    camera_codename = input_data['camera_name']
    data_to_send = []
    user_id = int(get_jwt_identity())

    frame = decrypt_aes(bytes.fromhex(
        frame), decrypt_user_rsa(bytes.fromhex(eiv)), user_id)
    encoded_frame_np = np.frombuffer(frame, dtype=np.uint8)

    frame = cv2.imdecode(encoded_frame_np, cv2.IMREAD_UNCHANGED)

    face_locations = face_recognition.face_locations(frame)
    data_to_send.append(face_locations)
    known_face_encodings, known_face_names, clearances = get_faces(user_id)
    if not face_locations:
        return jsonify({"return": "empty"}), 200

    face_encodings = face_recognition.face_encodings(frame, face_locations)

    names = []
    rec_clear = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):

        matches = face_recognition.compare_faces(
            known_face_encodings, face_encoding)

        name, clearance = get_recognition_info(
            clearances, known_face_names, known_face_encodings, matches, face_encoding)

        names.append(name)
        rec_clear.append(clearance)
        intent = 1
        if name == "Unknown":
            intent = 0
        elif clearance < camera_clearance:
            intent = 0
        else:
            intent = 1

        save_recognition_info(user_id, name, frame, intent, camera_index)

    data_to_send = [frame, face_locations, names, rec_clear]
    data_to_send = pickle.dumps(data_to_send)
    eiv, data_to_send = encrypt_aes(data_to_send, user_id)

    return jsonify({"return": data_to_send.hex(), "eiv": eiv.hex()}), 200


def save_recognition_info(user_id, name, image, level, cam_index):
    global sql_engine
    image = cv2.imencode('.jpg', image)[1].tobytes()
    eiv, image = encrypt_aes(image, user_id)
    with sql_engine.connect() as connection:  # Connect to the database
        connection.execute(
            "INSERT INTO recognition_history (acc_id, name, date_time, image, sufficient_livel, cam_index, eiv) VALUES (:user_id, :name, :date_time, :image, :level, :cam_index, :eiv);", {
                'user_id': user_id,
                'name': name,
                'date_time': datetime.datetime.now(),
                'image': image,
                'level': level,
                'cam_index': cam_index,
                'eiv': eiv
            }
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
            "SELECT vector, eiv, name, access_level FROM faces WHERE acc_id = :user_id;", {
                'user_id': user_id
            }
        )

    face_encodings = []
    names = []
    clearances = []
    for row in rows:
        # face_encoding, name, clearance
        face_encodings.append(decrypt_aes(row[0], row[1], user_id))
        names.append(decrypt_aes(row[2], row[1], user_id))
        clearances.append(row[3])
    return face_encodings, names, clearances


@app.route('/logout', methods=['POST'])
@jwt_required(locations=['headers'])
def logout():
    global users
    user_id = get_jwt_identity()
    del users[user_id]
    return jsonify({"message": "Logout successful!"}), 200
