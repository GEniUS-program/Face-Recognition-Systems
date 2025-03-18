import mysql.connector
import smtplib
import datetime
import secrets
import pickle
import os
from mysql.connector import Error
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
# Setup mail server
app.config["MAIL_SERVER"] = "smtp.mail.ru"  # mail.ru smtp server
app.config["MAIL_PORT"] = 465  # smtp port
app.config["MAIL_USE_SSL"] = True  # ssl/tls
app.config["MAIL_USERNAME"] = "eye-sentinel@mail.ru"
app.config["MAIL_PASSWORD"] = "0j4zPE3YBM3Rhe7vUgHX"
app.config["MAIL_DEFAULT_SENDER"] = "eye-sentinel@mail.ru"
# Connect to SMTP server
server = smtplib.SMTP_SSL('smtp.mail.ru', 465)
server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
server.auth_plain()

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


def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='Ndioksiatdian.mysql.pythonanywhere-services.com',
            user='Ndioksiatdian',
            password='KPks8kp3N2skABX',
            database='Ndioksiatdian$default'
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")

    return connection


connection = create_connection()


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


def encrypt_aes(data: bytes, user_id: int) -> list:
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


def get_user_id(username, password) -> int: # CONSERVED FOR LATER USE
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id, password, username FROM users;")
        rows = cursor.fetchall()

        for row in rows:
            if row[2] == username and row[1] == password:
                return row[0]
        else:
            return None

    except Error as e:
        print(f"The error '{e}' occurred")


def hash_data(data) -> str:
    data_hash = hashes.Hash(hashes.SHA256(), backend=default_backend())
    data_hash.update(data.encode())
    return data_hash.finalize().hex()


@app.route('/login', methods=['POST', 'GET'])
def establish_connection():
    global users, connection, PUBLIC_KEY_SERIALIZED
    data = request.get_json()

    client_public_key_pem = data.get("client_public_key")

    if client_public_key_pem:

        client_public_key = serialization.load_pem_public_key(
            bytes.fromhex(client_public_key_pem),
            backend=default_backend()
        )

    else:
        return jsonify({"error": "No public key provided."}), 400

    password = bytes.fromhex(data.get("password"))
    username = bytes.fromhex(data.get("username"))

    cursor = connection.cursor()

    try:
        cursor.execute("SELECT id, password, username FROM users;")
        rows = cursor.fetchall()

        for row in rows:
            if password == row[1].encode() and username == row[2].encode():
                user_id = row[0]
                break
        else:
            return jsonify({"error": "Access denied."}), 401

    except Error:
        return jsonify({"error": f"An error occurred"}), 500
    else:
        access_token = create_access_token(identity=str(user_id))
        users[user_id] = [access_token, client_public_key, os.urandom(32)]
        encrypted_token = encrypt_for_user_rsa(users[user_id][0].encode(), user_id)
        encrypted_server_public_key = encrypt_for_user_rsa(
            PUBLIC_KEY_SERIALIZED.encode(), user_id)
        encrypted_aes_key = encrypt_for_user_rsa(users[user_id][2], user_id)
        return jsonify({"token": encrypted_token.hex(), "server_public_key": encrypted_server_public_key.hex(), "user_id": user_id, "aes_key": encrypted_aes_key.hex()}), 200


@app.route('/register_user', methods=['POST'])
def register_new_user():
    global to_confirm, server  # connection,
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")

    try:
        cursor = connection.cursor()

        # Check if the user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user is not None:
            return jsonify({"error": "User already exists."}), 400
    except:
        pass
    token = create_access_token(
        identity=email, expires_delta=datetime.timedelta(hours=1))
    print('created token')
    to_confirm.update({email: [username, password]})

    confirmation_link = f'http://127.0.0.1:5000/confirm?jwt={token}'
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
@jwt_required(locations=['query_string']) # looks like http://host:port/confirm?jwt=token
def confirm_email():
    print('clicked conf link')
    global to_confirm, connection
    try:
        # Verify the token
        email = get_jwt_identity()  # Get the identity (email) from the token

        username, password = to_confirm.get(email)

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, email) VALUES (%s, %s, %s);", (username, password, email))

        del to_confirm[email]

        return jsonify({"message": "Email confirmed successfully!"}), 200
    except Exception as e:
        return jsonify({"message": "Invalid or expired confirmation link.", "error": str(e)}), 400


@app.route('/faces', methods=['POST', 'GET'])
@jwt_required(locations=['headers'])
def faces_table():
    global connection
    input_params = request.get_json()
    encryption = input_params['encrypted'] # aes, rsa, not
    target = input_params['target'] # add, edit, del, read
    user_id = int(get_jwt_identity())

    if target == 'add':
        if encryption == 'rsa':
            data = decrypt_user_rsa(bytes.fromhex(input_params['data']))
        elif encryption == 'aes':
            data = decrypt_aes(bytes.fromhex(input_params['data']), decrypt_user_rsa(bytes.fromhex(input_params['eiv'])), user_id)
        
        data = pickle.loads(data)# Convert data form bytes to dictionary

        access_level = data['access_level'] # int
        vector = data['vector'] # bytes
        image = data['image'] # bytes

        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO faces (acc_id, access_level, vector, image) VALUES (%s, %s);", (user_id, access_level, vector, image)
        )
    elif target == 'edit':
        if encryption == 'rsa':
            new_data = decrypt_user_rsa(bytes.fromhex(input_params['new_data']))
            old_data = decrypt_user_rsa(bytes.fromhex(input_params['old_data']))
        elif encryption == 'aes':
            new_data = decrypt_aes(bytes.fromhex(input_params['new_data']), decrypt_user_rsa(bytes.fromhex(input_params['new_eiv'])), user_id)
            old_data = decrypt_aes(bytes.fromhex(input_params['old_data']), decrypt_user_rsa(bytes.fromhex(input_params['old_eiv'])), user_id)

        data = pickle.loads(data) 

        face_id = data['face_id']
        access_level = data['access_level']
        vector = data['vector']
        image = data['image']
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO faces (acc_id, face_id, access_level, vector, image) VALUES (%s, %s);", (user_id, face_id, access_level, vector, image)
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





@app.route('/logout', methods=['POST'])
@jwt_required(locations=['headers'])
def logout():
    pass





app.run(host="127.0.0.1", port=5000, debug=True)