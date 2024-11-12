import os

from dotenv import load_dotenv
from openai import OpenAI
import openai
import hashlib
import datetime

load_dotenv()

client = OpenAI(api_key=str(os.environ.get("OPENAI_API_KEY")))
VECTOR_STORE_ID = str(os.environ.get("VECTOR_STORE_ID"))
OPENAI_ASSISTANT_ID = str(os.environ.get("OPENAI_ASSISTANT_ID"))


def generate_session_id(ip_address):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unique_string = f"{ip_address}_{timestamp}"
    return hashlib.md5(unique_string.encode()).hexdigest()


# Simulated data store (use Redis or a proper database in production)
session_threads = {}


def get_or_create_thread(ip_address):
    # Generate session ID
    session_id = generate_session_id(ip_address)

    # Check if a thread already exists for this session
    if session_id in session_threads:
        return session_threads[session_id]

    # Create a new thread if it doesn't exist
    response = openai.Assistant.create_thread(
        assistant_id="your_assistant_id", title="User Session Thread"
    )

    # Store the session ID and associated thread ID
    thread_id = response["id"]
    session_threads[session_id] = thread_id

    return thread_id


def chat_with_assistant(assistant_id, user_message):
    """
    Ask a question to the assistant without creating or using a thread.
    Each interaction is stateless and independent.
    """
    stream = client.beta.threads.create_and_run(
        assistant_id=assistant_id,
        thread={"messages": [{"role": "user", "content": user_message}]},
        # stream=True
    )
    # stream = openai.Assistant.chat(
    #     assistant_id=assistant_id,
    #     thread={"messages": [{"role": "user", "content": user_message}]},
    #     # stream=True
    # )
    return stream



# Example interaction
user_message = input("Ask about Fakher's profile")
assistant_response = chat_with_assistant(OPENAI_ASSISTANT_ID, user_message)
print(assistant_response)
