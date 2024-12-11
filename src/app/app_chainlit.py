import base64
import datetime
import os
import tempfile
import uuid
import plotly
from io import BytesIO
from pathlib import Path
from typing import List
from openai import AsyncOpenAI, OpenAI
from literalai.helper import utc_now
import chainlit as cl
from chainlit.config import config
from chainlit.element import Element
from openai.types.beta.threads.runs import RunStep
from dotenv import load_dotenv
from modules.EventHandler import EventHandler
import requests
from time import sleep
from tools import BasicToolNode
import ast

# from gtts import gTTS
from literalai import LiteralClient
from chainlit.element import ElementBased

load_dotenv()

literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
async_openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant = sync_openai_client.beta.assistants.retrieve(
    os.environ.get("OPENAI_ASSISTANT_ID")
)

GLADIA_API_URL = os.environ.get("GLADIA_API_URL")
GLADIA_API_KEY = os.environ.get("GLADIA_API_KEY")

config.ui.name = assistant.name


# Function to encode an image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def make_request(url, headers, method="GET", data=None, files=None):
    if method == "POST":
        response = requests.post(url, headers=headers, json=data, files=files)
    else:
        response = requests.get(url, headers=headers)
    return response.json()


@cl.step(type="tool")
async def generate_text_answer(transcription):
    try:
        # Retrieve the OpenAI thread ID from the user session
        openai_thread_id = cl.user_session.get("openai_thread_id")

        if not openai_thread_id:
            cl.logger.error("OpenAI thread ID is missing in session.")
            return (
                "Error: No active conversation thread found. Please restart the chat."
            )

        # Add the user message to the OpenAI thread
        response = await async_openai_client.beta.threads.messages.create(
            thread_id=openai_thread_id,
            role="user",
            content=transcription,
            # attachments=attachments,
        )

        # Process assistant response
        async with async_openai_client.beta.threads.runs.stream(
            thread_id=openai_thread_id,
            assistant_id=assistant.id,
            event_handler=EventHandler(assistant_name=assistant.name),
        ) as stream:
            final_response = await stream.get_final_messages()
            return final_response[0].content[0].text.value
        # return await text_to_speech(final_response[0].content[0].text.value)

    except Exception as e:
        cl.logger.error(f"Failed to generate text answer: {e}")
        return "I'm sorry, I couldn't generate a response at this time."

cl.instrument_openai()

# async def get_time_now() -> str:
#     """
#     Get current date and time.
#     """
#     return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")



# @cl.step(type="tool")
# async def call_tool(tool_call, message_history):
#     function_name = tool_call.function.name
#     arguments = ast.literal_eval(tool_call.function.arguments)

#     current_step = cl.context.current_step
#     current_step.name = function_name

#     current_step.input = arguments

#     function_response = get_time_now()

#     current_step.output = function_response
#     current_step.language = "json"

#     message_history.append(
#         {
#             "role": "function",
#             "name": function_name,
#             "content": function_response,
#             "tool_call_id": tool_call.id,
#         }
#     )


# @cl.set_chat_profiles
# async def chat_profile(current_user: cl.User):
#     profiles = []
#     return profiles


@cl.step(type="tool")
async def speech_to_text(audio_file):
    try:
        response = await async_openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        return response.text
    except Exception as e:
        cl.logger.error(f"Speech-to-Text failed: {e}")
        return "Sorry, I couldn't process the audio."


# @cl.step(type="tool")
# async def speech_to_text(audio_input):

#     try:
#         headers = {"x-gladia-key": f"{GLADIA_API_KEY}"}
#         files = {
#             "audio": (
#                 "input_audio.wav",
#                 audio_input,
#                 "audio/wav",
#             ),
#         }

#         upload_response = make_request(
#             f"{GLADIA_API_URL}/upload", headers, "POST", files=files
#         )

#         audio_url = upload_response.get("audio_url")
#         data = {
#             "audio_url": audio_url,
#             "diarization": True,
#         }
#         headers["Content-Type"] = "application/json"
#         post_response = make_request(
#             f"{GLADIA_API_URL}/transcription/", headers, "POST", data=data
#         )
#         result_url = post_response.get("result_url")

#         if result_url:
#             while True:
#                 cl.logger.info(f"Polling for results...")
#                 poll_response = make_request(result_url, headers)
#                 if poll_response.get("status") == "done":
#                     cl.logger.info(
#                         f"- Transcription done: {poll_response.get('result')}"
#                     )
#                     return poll_response.get("result")["transcription"][
#                         "full_transcript"
#                     ]
#                 elif poll_response.get("status") == "error":
#                     cl.logger.error(f"- Transcription failed: {poll_response}")
#                 else:
#                     cl.logger.debug(
#                         f"- Transcription status: {poll_response.get('status')}"
#                     )
#                 sleep(5)
#         print("- End of work")
#     except Exception as e:
#         cl.logger.error(f"Speech-to-Text failed: {e}")
#         return "Sorry, I couldn't process the audio."


@cl.step(type="tool")
async def text_to_speech(text):
    try:
        # Convert text to speech using OpenAI TTS
        response = await async_openai_client.audio.speech.create(
            model="tts-1", voice="nova", input=text
        )
        audio_mime_type: str = cl.user_session.get("audio_mime_type")

        output_audio = cl.Audio(
            mime=audio_mime_type, content=response.read(), auto_play=True
        )
        return await cl.Message(
            author="assistant",
            type="assistant_message",
            content="",
            elements=[output_audio],
        ).send()

    except Exception as e:
        cl.logger.error(f"Text-to-Speech failed: {e}")
        return await cl.Message(
            content="Sorry, I couldn't convert the text to audio."
        ).update()


async def upload_files(files: List[Element]):
    file_ids = []
    for file in files:
        uploaded_file = await async_openai_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    return file_ids


async def process_files(files: List[Element]):
    file_ids = []
    if len(files) > 0:
        file_ids = await upload_files(files)

    return [
        {
            "file_id": file_id,
            "tools": (
                [{"type": "code_interpreter"}, {"type": "file_search"}]
                if file.mime
                in [
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    "text/markdown",
                    "application/pdf",
                    "text/plain",
                ]
                else [{"type": "code_interpreter"}]
            ),
        }
        for file_id, file in zip(file_ids, files)
    ]


@cl.on_chat_start
async def start_chat():
    try:
        # Create or retrieve OpenAI thread
        openai_thread_id = cl.user_session.get("openai_thread_id")
        if not openai_thread_id:
            thread = await async_openai_client.beta.threads.create()
            openai_thread_id = thread.id
            cl.user_session.set("openai_thread_id", openai_thread_id)

        # Generate a UUID for LiteralAI
        literalai_thread_id = str(uuid.uuid4())
        cl.user_session.set("literalai_thread_id", literalai_thread_id)

        user_language = cl.user_session.get("languages", "en-US").split(",")[0]
        # Display a welcome message to the user
        welcome_messages = {
            "en-US": "Hi there! I’m ✨Clara✨, Fakher’s secretary. I’m here to assist you. Feel free to ask anything about him. Over to you! 😊",
            "fr-FR": "Bonjour ! Je suis ✨Clara✨, la secrétaire de Fakher. Je suis là pour vous aider. C'est à vous ! 😊",
            # Add more languages here as needed
        }
        text_content = welcome_messages.get(user_language, welcome_messages["fr-FR"])

        image = cl.Image(path="public/clara.png", name="Logo", size="small")
        await cl.Message(
            content=text_content,
            elements=[image],
        ).send()

    except Exception as e:
        cl.logger.error(f"Failed to create threads: {e}")
        await cl.Message(
            content="Sorry, I couldn't start the chat session. Please try again later."
        ).send()


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.AudioChunk):
    if chunk.isStart:
        buffer = BytesIO()
        # This is required for whisper to recognize the file type
        buffer.name = f"input_audio.{chunk.mimeType.split('/')[1]}"
        # Initialize the session for a new audio stream
        cl.user_session.set("audio_buffer", buffer)
        cl.user_session.set("audio_mime_type", chunk.mimeType)

    # TODO: Use Gladia to transcribe chunks as they arrive would decrease latency
    # see https://docs-v1.gladia.io/reference/live-audio

    # For now, write the chunks to a buffer and transcribe the whole audio at the end
    cl.user_session.get("audio_buffer").write(chunk.data)


# @cl.step(type="tool")
@cl.on_audio_end
async def on_audio_end(elements: list[ElementBased]):
    try:
        openai_thread_id = cl.user_session.get("openai_thread_id")
        literalai_thread_id = cl.user_session.get("literalai_thread_id")

        if not openai_thread_id or not literalai_thread_id:
            cl.logger.warning("Thread IDs missing in session. Restarting chat.")
            await cl.Message(content="Session expired. Starting a new chat.").send()
            openai_thread_id = cl.user_session.get("openai_thread_id")
            literalai_thread_id = cl.user_session.get("literalai_thread_id")

        cl.logger.info(
            f"Processing Audio Message for OpenAI Thread ID: {openai_thread_id} and LiteralAI Thread ID: {literalai_thread_id}"
        )
        with literalai_client.thread(
            name=literalai_thread_id, thread_id=literalai_thread_id
        ) as thread:

            # Get the audio buffer from the session
            audio_buffer: BytesIO = cl.user_session.get("audio_buffer")
            audio_buffer.seek(0)  # Move the file pointer to the beginning
            audio_file = audio_buffer.read()
            audio_mime_type: str = cl.user_session.get("audio_mime_type")

            audio_input = (audio_buffer.name, audio_file, audio_mime_type)

            # Transcribe the audio
            transcription = await speech_to_text(audio_input)
            cl.logger.info(f"Transcription: {transcription}")

            # images = [file for file in elements if "image" in file.mime]

            # Generate text answer from transcription
            text_answer = await generate_text_answer(transcription)

            cl.logger.info(f"Text Answer: {text_answer}")
            # Convert response to audio and send to the user
            await text_to_speech(text_answer)

            # Reset the audio buffer and mime type
            cl.user_session.set("audio_buffer", None)
            cl.user_session.set("audio_mime_type", None)
    except Exception as e:
        cl.logger.error(f"Error processing Audio Message: {e}", exc_info=True)
        await cl.Message(
            content="An error occurred while processing your audio message. Please try again."
        ).send()


@cl.on_stop
async def stop_chat():
    current_run_step: RunStep = cl.user_session.get("run_step")
    if current_run_step:
        try:
            await cl.Message(
                content="The current session has ended. You can start a new session if needed."
            ).send()
            await async_openai_client.beta.threads.runs.cancel(
                thread_id=current_run_step.thread_id, run_id=current_run_step.run_id
            )
        except Exception as e:
            cl.logger.error(f"Failed to cancel run: {e}", exc_info=True)


@cl.on_message
async def main(message: cl.Message):
    try:
        openai_thread_id = cl.user_session.get("openai_thread_id")
        literalai_thread_id = cl.user_session.get("literalai_thread_id")

        if not openai_thread_id or not literalai_thread_id:
            cl.logger.warning("Thread IDs missing in session. Restarting chat.")
            await start_chat()
            openai_thread_id = cl.user_session.get("openai_thread_id")

        attachments = await process_files(message.elements)

        # Add the user message to the OpenAI thread
        response = await async_openai_client.beta.threads.messages.create(
            thread_id=openai_thread_id,
            role="user",
            content=message.content,
            attachments=attachments,
        )
        # Process assistant response
        async with async_openai_client.beta.threads.runs.stream(
            thread_id=openai_thread_id,
            assistant_id=assistant.id,
            event_handler=EventHandler(assistant_name=assistant.name),
        ) as stream:
            await stream.until_done()

    except Exception as e:
        cl.logger.error(f"Error processing message: {e}", exc_info=True)
        await cl.Message(
            content="An error occurred while processing your message. Please try again."
        ).send()
