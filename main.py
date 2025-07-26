from fastapi import FastAPI
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from gtts import gTTS
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import uuid
import os

app = FastAPI()
OUTPUT_DIR = "output_audio"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Google Drive settings
SCOPES = ['https://www.googleapis.com/auth/drive.file']
GOOGLE_DRIVE_FOLDER_ID = "1tTBqMul2NwJcZUMPhQhapbvbcFj7rmXm"

class TranslationRequest(BaseModel):
    text: str
    input_language: str
    output_language: str

def upload_to_drive(file_path: str, drive_folder_id: str) -> str:
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': os.path.basename(file_path),
        'parents': [drive_folder_id]
    }

    media = MediaFileUpload(file_path, mimetype='audio/mpeg')

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')

    # Make file publicly accessible
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    # Return downloadable link
    link = f'https://drive.google.com/file/d/{file_id}/view?usp=sharing'
    return link

@app.post("/translate-speech")
def translate_and_speak(request: TranslationRequest):
    # Translate the text
    translated_text = GoogleTranslator(
        source=request.input_language,
        target=request.output_language
    ).translate(request.text)

    # Convert translated text to speech
    tts = gTTS(text=translated_text, lang=request.output_language)
    file_name = f"{uuid.uuid4()}.mp3"
    file_path = os.path.join(OUTPUT_DIR, file_name)
    tts.save(file_path)

    # Upload to Google Drive and get public link
    public_link = upload_to_drive(file_path, GOOGLE_DRIVE_FOLDER_ID)

    return {
        "translated_text": translated_text,
        "file_path": file_path,
        "google_drive_link": public_link
    }

@app.get("/")
def read_root():
    return {"message": "Hello World"}
