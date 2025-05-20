from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

GMAIL_CREDS = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])

service = build('gmail', 'v1', credentials=GMAIL_CREDS)
request = {
    'labelIds': ['INBOX'],
    'topicName': 'projects/your-project-id/topics/your-topic'
}
service.users().watch(userId='me', body=request).execute()
