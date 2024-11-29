import base64
import mimetypes
import os
from email.message import EmailMessage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

load_dotenv()

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

def gmail_create_draft(to, subject, body, attachment_path=None):
    """
    Create and insert a draft email with an optional attachment.
    
    Args:
        to (str): Recipient email address.
        sender (str): Sender email address.
        subject (str): Subject of the email.
        body (str): Body of the email.
        attachment_path (str, optional): Path to the attachment file.
    
    Returns:
        dict: Draft object containing draft ID and message metadata.
    """
    creds, _ = google.auth.default()

    try:
        service = build("gmail", "v1", credentials=creds)
        mime_message = EmailMessage()

        # Set email headers
        mime_message["To"] = to
        mime_message["From"] = "clara@datasonic.co"
        mime_message["Subject"] = subject

        # Set email body
        mime_message.set_content(body)

        # Add attachment if provided
        if attachment_path:
            attachment_filename = os.path.basename(attachment_path)
            type_subtype, _ = mimetypes.guess_type(attachment_filename)
            maintype, subtype = type_subtype.split("/")

            with open(attachment_path, "rb") as fp:
                attachment_data = fp.read()
            mime_message.add_attachment(
                attachment_data,
                maintype=maintype,
                subtype=subtype,
                filename=attachment_filename
            )

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        create_draft_request_body = {"message": {"raw": encoded_message}}

        # Create draft
        draft = service.users().drafts().create(userId="me", body=create_draft_request_body).execute()
        print(f'Draft created with ID: {draft["id"]}')
        return draft
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None

def gmail_send_draft(draft_id):
    """
    Send a previously created draft.
    
    Args:
        draft_id (str): The ID of the draft to send.
    
    Returns:
        dict: Sent message object.
    """
    creds, _ = google.auth.default()

    try:
        service = build("gmail", "v1", credentials=creds)
        send_request = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
        print(f'Draft sent with Message ID: {send_request["id"]}')
        return send_request
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None