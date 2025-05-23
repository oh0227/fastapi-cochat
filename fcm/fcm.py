import firebase_admin
from firebase_admin import credentials, messaging
import os

cred_path = os.path.join(os.path.dirname(__file__), "../google-services.json")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

def send_fcm_push(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token
    )
    response = messaging.send(message)
    print('Successfully sent message:', response)