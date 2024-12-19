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


@cl.step(type="tool", name="Thinking...")
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

    except Exception as e:
        cl.logger.error(f"Failed to generate text answer: {e}")
        return "I'm sorry, I couldn't generate a response at this time."


@cl.step(type="tool", name="Transcribing...")
async def speech_to_text(audio_file):
    try:
        response = await async_openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        response = await async_openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        return response.text
    except Exception as e:
        cl.logger.error(f"Speech-to-Text failed: {e}")
        return "Sorry, I couldn't process the audio."


@cl.step(type="tool", name="Converting Text to Audio...")
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

        response = await async_openai_client.audio.speech.create(
            model="tts-1", voice="nova", input=text
        )
        audio_mime_type = cl.user_session.get("audio_mime_type")
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

        return await cl.Message(
            content="Sorry, I couldn't convert the text to audio."
        ).update()


async def upload_files(files: List[Element]):
    file_ids = []
    for file in files:
        uploaded_file = await async_openai_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
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
            "fr-FR": "Bonjour ! Je suis ✨Clara✨, la secrétaire de Fakher. Je suis là pour répondre à vos questions concernant son profil. C'est à vous ! 😊",
            # Add more languages here as needed
        }

        original_actions = [
            {
                "en-US": {
                    "name": "Professional experience",
                    "value": "What is his professional experience and career history?",
                    "description": "What is his professional experience and career history?",
                },
                "fr-FR": {
                    "name": "Expériences professionnelles",
                    "value": "Quelle est votre expérience professionnelle et votre parcours professionnel?",
                    "description": "Quelle est votre expérience professionnelle et votre parcours professionnel?",
                },
            },
            {
                "en-US": {
                    "name": "Skills",
                    "value": "What are his key skills and qualifications?",
                    "description": "What are his key skills and qualifications?",
                },
                "fr-FR": {
                    "name": "Compétences clés",
                    "value": "Quelles sont ses compétences clés et ses qualifications?",
                    "description": "Quelles sont ses compétences clés et ses qualifications?",
                },
            },
            {
                "en-US": {
                    "name": "Significant achievement",
                    "value": "Can you describe a significant achievement or project in sa career?",
                    "description": "Can you describe a significant achievement or project in your career?",
                },
                "fr-FR": {
                    "name": "Réalisations",
                    "value": "Pouvez-vous décrire une réalisation ou un projet significatif dans sa carrière?",
                    "description": "Pouvez-vous décrire une réalisation ou un projet significatif dans sa carrière?",
                },
            },
            {
                "en-US": {
                    "name": "Certifications",
                    "value": "What are his certifications and professional qualifications?",
                    "description": "What are his certifications and professional qualifications?",
                },
                "fr-FR": {
                    "name": "Certifications",
                    "value": "Quels sont ses certifications professionnelles?",
                    "description": "Quels sont ses certifications professionnelles?",
                },
            },
            {
                "en-US": {
                    "name": "Passions",
                    "value": "What are his passions?",
                    "description": "What are your passions?",
                },
                "fr-FR": {
                    "name": "Passions",
                    "value": "Quelles sont ses passions?",
                    "description": "Quelles sont ses passions?",
                },
            },
        ]

        welcome_messages = {
            "en-US": "Hi there! I’m ✨Clara✨, Fakher’s AI assistant. I’m here to assist you. Feel free to ask anything about his profile. Over to you! 😊",
            "fr-FR": "Bonjour ! Je suis ✨Clara✨, l'assistante IA de Fakher. Je suis là pour vous aider. C'est à vous ! 😊",
        }
        text_content = welcome_messages.get(user_language, welcome_messages["fr-FR"])

        actions = [
            cl.Action(
                name=action.get(user_language, action["en-US"])["name"],
                value=action.get(user_language, action["en-US"])["value"],
                description=action.get(user_language, action["en-US"])["description"],
            )
            for action in original_actions
        ]

        # image = cl.Image(path="public/clara.png", name="Logo", size="small")
        await cl.Message(content=text_content, actions=actions).send()

        # Register action callbacks
        for action in original_actions:
            action_obj= action.get(user_language, action["en-US"])
            @cl.action_callback(action_obj["name"])
            @cl.step(type="tool", name=f"Let me search for {action_obj['name']}...")
            async def on_action(action_obj):
                await send_message(cl.Message(author="user", content=action_obj.value))

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
            audio_buffer = cl.user_session.get("audio_buffer")
            audio_buffer.seek(0)
            audio_file = audio_buffer.read()
            audio_mime_type: str = cl.user_session.get("audio_mime_type")

            audio_input = (audio_buffer.name, audio_file, audio_mime_type)

            # Transcribe the audio
            transcription = await speech_to_text(audio_input)
            cl.logger.debug(f"Transcription: {transcription}")

            # images = [file for file in elements if "image" in file.mime]

            # Generate text answer from transcription
            text_answer = await generate_text_answer(transcription)

            cl.logger.debug(f"Text Answer: {text_answer}")
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
    await send_message(message)


async def send_message(message: cl.Message):
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
