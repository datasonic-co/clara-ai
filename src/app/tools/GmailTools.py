import base64
import mimetypes
import os
from email.message import EmailMessage

import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import chainlit as cl

load_dotenv()

GOOGLE_APPLICATION_CREDENTIAL_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIAL_FILE")
GOOGLE_REDIRECT_URL_PORT = int(os.getenv("GOOGLE_REDIRECT_URL_PORT"))
GOOGLE_SEND_MAIL_SCOPE = os.getenv("GOOGLE_SEND_MAIL_SCOPE")
GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE")
GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_JAVASCRIPT_ORIGIN = os.getenv("OAUTH_GOOGLE_AUTH_URI")
GOOGLE_AUTH_PROVIDER_X509_CERT_URL = os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL")
OAUTH_GOOGLE_CLIENT_ID = os.getenv("OAUTH_GOOGLE_CLIENT_ID")
OAUTH_GOOGLE_CLIENT_SECRET = os.getenv("OAUTH_GOOGLE_CLIENT_SECRET")
OAUTH_GOOGLE_TOKEN_URI = os.getenv("OAUTH_GOOGLE_TOKEN_URI")
OAUTH_GOOGLE_AUTH_URI = os.getenv("OAUTH_GOOGLE_AUTH_URI")


# Create Format Google API Creds for Web Apps
google_config = {
    "web": {
        "client_id": OAUTH_GOOGLE_CLIENT_ID,
        "project_id": GOOGLE_PROJECT_ID,
        "auth_uri": OAUTH_GOOGLE_AUTH_URI,
        "token_uri": OAUTH_GOOGLE_TOKEN_URI,
        "auth_provider_x509_cert_url": GOOGLE_AUTH_PROVIDER_X509_CERT_URL,
        "client_secret": OAUTH_GOOGLE_CLIENT_SECRET,
        "javascript_origins": [GOOGLE_JAVASCRIPT_ORIGIN, "http://localhost:8000"],
    }
}


async def gmail_send_mail(subject, cc, body, attachment_path=None) -> str:
    """
    Create and insert a draft email with an optional attachment. The draft is then sent to the recipient.

    Args:
        service (Resource): The authorized Gmail API service instance.
        to (str): The email address of the recipient.
        sender (str): The email address of the sender.
        subject (str): The subject of the email.
        body (str): The body content of the email.
        attachment_path (str, optional): The file path of the attachment to be sent with the email. Defaults to None.

    Returns:
        dict: A dictionary containing the draft ID and message metadata of the sent email.

    Raises:
        FileNotFoundError: If the attachment file is not found at the specified path.
        Exception: For any other errors that occur during the email creation and sending process.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(GOOGLE_TOKEN_FILE):
        # creds = Credentials.from_authorized_user_info(info=google_config, scopes=[GOOGLE_SEND_MAIL_SCOPE])
        creds = Credentials.from_authorized_user_file(
            GOOGLE_TOKEN_FILE, [GOOGLE_SEND_MAIL_SCOPE]
        )
        if not creds.refresh_token:  # Check for refresh_token
            # Re-authorize or handle the error appropriately
            cl.logger.error(
                "Error: refresh_token is missing. Please re-authorize the application."
            )
            # You can trigger the authorization flow here or exit with an error message

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                client_config=google_config, scopes=[GOOGLE_SEND_MAIL_SCOPE]
            )
            creds = flow.run_local_server(
                port=GOOGLE_REDIRECT_URL_PORT,
                redirect_uri_trailing_slash=False,
                # open_browser=False,
                bind_addr="0.0.0.0"

            )

        # Save the credentials for the next run
        with open(GOOGLE_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        mime_message = EmailMessage()

        # Set email headers
        mime_message["To"] = "contact@datasonic.co"
        mime_message["Cc"] = cc
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
                filename=attachment_filename,
            )

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

        create_draft_request_body = {"message": {"raw": encoded_message}}

        # Create draft
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body=create_draft_request_body)
            .execute()
        )
        cl.logger.info(f'Draft created with ID: {draft["id"]}')
        draft_id = draft["id"]

        send_request = (
            service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
        )
        cl.logger.info(f'Email sent ID: {send_request["id"]}')
        current_step = cl.context.current_step
        response = f'Email with body {body} has been successfully sent with id {send_request["id"]}'
        current_step.input = {
            "Subject": subject,
            "body": body,
            "from": mime_message["From"],
            "cc": cc,
            "To": mime_message["To"],
        }

        current_step.output = {
            "Request Id": f"Request ID {send_request['id']}",
            "Request Labels Email ": send_request["labelIds"],
        }

        current_step.language = "json"
        return response

    except HttpError as error:

        cl.logger.error(
            f"An error occurred when sending or creadting draft Mail {error}"
        )
        return str(error)
