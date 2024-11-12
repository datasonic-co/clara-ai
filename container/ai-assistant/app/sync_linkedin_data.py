import openai
import os

from openai import OpenAI
from dotenv import load_dotenv
import requests
import json
import io

load_dotenv()

client = OpenAI(api_key=str(os.environ.get("OPENAI_API_KEY")))
LINKEDIN_API_TOKEN = str(os.environ.get("LINKEDIN_API_TOKEN"))
VECTOR_STORE_ID = str(os.environ.get("VECTOR_STORE_ID"))

profile_data_file_path = "linkedin_profile_data.json"

files_to_upload = []


def list_vector_store_files_by_source(scope):
    """
    List all files in a specific vector store.
    """
    # response = openai.beta.vector_stores.files.list(
    #     vector_store_id=vector_store_id,
    #     filter = "completed"
    # )
    files = client.files.list().to_dict()["data"]

    if not files:
        print("No files found in the vector store.")
    else:
        print("Files in the vector store:")
        linkedin_files_id = [file["id"] for file in files if scope in file["filename"]]
        print(linkedin_files_id)


def delete_files(vector_store_id, scope, linkedin_file_ids):


    if not linkedin_file_ids:
        print(f"No files related to the topic {scope} found in the vector store.")
    else:

        deleted_vector_store_file = client.beta.vector_stores.files.delete(
            vector_store_id=vector_store_id, file_id=linkedin_file_ids
        )
        print(deleted_vector_store_file)

def sync_my_profile():
    domains = [
        "POSITIONS",
        "SKILLS",
        "LANGUAGES",
        "EDUCATION",
        "MEMBER_HASHTAG",
        "REGISTRATION",
        "CONNECTIONS",
    ]

    for domain in domains:

        url = f"https://api.linkedin.com/rest/memberSnapshotData?q=criteria&domain={domain}"

        payload = ""
        headers = {
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202312",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINKEDIN_API_TOKEN}",
        }

        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:

            items = []

            for element in response.json().get("elements", []):
                items.extend(element.get("snapshotData", []))
            # print(items)

            json_bytes_name = f"linkedin_{domain.lower()}_data.json"
            json_bytes = io.BytesIO(json.dumps(items, indent=2).encode("utf-8"))
            files_to_upload.append((json_bytes_name, json_bytes))
            # Assign a name to the in-memory file with a .json extension
        else:
            print(
                f"Failed to retrieve data for {domain}. Status code: {response.status_code}, Response: {response.text}"
            )

    # Upload the JSON data directly to the vector store as a string in-memory
    if files_to_upload:

        # Append the in-memory file to the list for bulk upload
        response = openai.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=VECTOR_STORE_ID,
            files=files_to_upload,
        )
        print(f"Bulk upload status: {response.status}")
    else:
        print("No files to upload.")


def update_my_assistant():
    
    assistant = client.beta.assistants.update(
        name="Fakher's Assistant",
        instructions="You are supposed to be Fakher HANNAFI personal assistant, responding to all questions related to his profile. Moderate unsafe questions. Use you knowledge base to answer questions about Fakher's experience and skills.",
        model="gpt-4o-mini",
        tools=[{"type": "file_search"}],
        tool_resources={"file_search": {"vector_store_ids": [VECTOR_STORE_ID]}},
    )


# Main Worflow
scope = "linkedin"
# List files in the vector store
files_to_delete = list_vector_store_files_by_source(scope)
delete_files(VECTOR_STORE_ID, scope, files_to_delete)
sync_my_profile()
