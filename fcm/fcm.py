import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
from dotenv import load_dotenv

load_dotenv()  

firebase_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
if firebase_json:
    firebase_info = json.loads(firebase_json)
    firebase_info["private_key"] = firebase_info["private_key"].replace("\\n", "\n")  # 🔐 중요
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)
else:
    raise RuntimeError("❗ Firebase credentials not found in environment variables")

def send_fcm_push(token, title, body, data=None): 
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token,
        data=data or {}
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)