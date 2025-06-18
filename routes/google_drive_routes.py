# google_drive_upload.py

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

SERVICE_ACCOUNT_FILE = r'C:\studentStack-main\studentStack-main\credentials\studentstack-6204842c7804.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

drive_service = build('drive', 'v3', credentials=credentials)

def upload_file_to_drive(file_storage, folder_id=None):
    file_metadata = {'name': file_storage.filename}
    if folder_id:
        file_metadata['parents'] = [folder_id]

    media = MediaIoBaseUpload(io.BytesIO(file_storage.read()), mimetype=file_storage.mimetype)
    
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id,webViewLink'
    ).execute()

    return file.get('webViewLink')
