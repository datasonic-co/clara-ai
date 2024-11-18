import os
import uuid
import plotly
from io import BytesIO
from pathlib import Path
from typing import List
# from chainlit.input_widget import Select, Switch, Slider

from openai import AsyncOpenAI, OpenAI

from literalai.helper import utc_now

import chainlit as cl
from chainlit.config import config
from chainlit.element import Element
from openai.types.beta.threads.runs import RunStep

from dotenv import load_dotenv

from modules.EventHandler import EventHandler
from literalai import LiteralClient

load_dotenv()
    
literalai_client = LiteralClient(api_key=os.getenv("LITERAL_API_KEY"))
async_openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant = sync_openai_client.beta.assistants.retrieve(
    os.environ.get("OPENAI_ASSISTANT_ID")
)

config.ui.name = assistant.name

def is_valid_uuid(uuid_to_test, version=4):
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    profiles = [
        cl.ChatProfile(
            name="Public Profile",
            markdown_description="""For General questions about Fakher's profile""",
            icon="public/general_user.png",
        ),
        cl.ChatProfile(
            name="Technical Profile",
            markdown_description="""If you want to deep dive about Fakher's IT profile""",
            icon="public/technical_user.png",
        ),
    ]
    return profiles
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
            "tools": [{"type": "code_interpreter"}, {"type": "file_search"}] if file.mime in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/markdown", "application/pdf", "text/plain"] else [{"type": "code_interpreter"}],
        }
        for file_id, file in zip(file_ids, files)
    ]


@cl.set_starters
async def set_starters():
    # await cl.Message(
    #     content="Hi there, my name is ✨*ASSISTANT ASSISTANT*✨ I would be happy to help you 😊"
    # ).send()
    return [
        cl.Starter(
            label="Who am I",
            message="Who is Fakher HANNAFI? Introduce to me Fakher in few words",
            # icon="/public/teklab.png",
        ),
        cl.Starter(
            label="Highlights and Success",
            message="What are your Fakher's biggest project? Tell me some few stories",
            # icon="/public/teklab.png",
        ),
        cl.Starter(
            label="My Value Add in AI",
            message="How can you help companies build their AI services? Give me some examples based on Fakher's experience",
            # icon="/public/teklab.png",
        ),
        # cl.Starter(
        #     label="My impact within my previous experiences",
        #     message="What was your impact in your previous experiences?",
        #     # icon="/public/teklab.png",
        # ),
        cl.Starter(
            label="What Drives Me",
            message="What are examples of measurable impacts from integrating data-driven solutions?",
            # icon="/public/teklab.png",
        ),
        cl.Starter(
            label="Professional Milestones",
            message="List me your track record of your certifications. Categorize them by Technology and level of expertise",
            # icon="/public/filebeat.svg",
        ),
        cl.Starter(
            label="What People Say About Me",
            message="Give me some references about Fakher's profile",
            # icon="/public/filebeat.svg",
        ),
        cl.Starter(
            label="Challenges and Growth",
            message="What are your Fakher's major projects? Tell me some few stories",
            # icon="/public/teklab.png",
        ),
        cl.Starter(
            label="Passions That Fuel My Work",
            message="Talk me about Fakher's passions",
            # icon="/public/grafana.svg",
        ),
    ]



@cl.on_chat_start
async def start_chat():
    # Create a Thread
    thread = await async_openai_client.beta.threads.create()
    # Store thread ID in user session for later use
    cl.user_session.set("thread_id", thread.id)
    try:
        # Create a thread with OpenAI
        thread = await async_openai_client.beta.threads.create()
        openai_thread_id = thread.id
        cl.user_session.set("openai_thread_id", openai_thread_id)

        # Generate a UUID for LiteralAI
        literalai_thread_id = str(uuid.uuid4())
        cl.user_session.set("literalai_thread_id", literalai_thread_id)
        cl.logger.info(f"LiteralAI Thread ID: {literalai_thread_id}, OpenAI Thread ID: {openai_thread_id}")
        
        # Validate UUID
        if not is_valid_uuid(literalai_thread_id):
            raise ValueError(f"Generated LiteralAI Thread ID is invalid: {literalai_thread_id}")

    except Exception as e:
        cl.logger.error(f"Failed to create threads: {e}")
        await cl.Message(content="Sorry, I couldn't start the chat session. Please try again later.").send()
    
@cl.on_stop
async def stop_chat():
    current_run_step: RunStep = cl.user_session.get("run_step")
    if current_run_step:
        try:
            await async_openai_client.beta.threads.runs.cancel(
                thread_id=current_run_step.thread_id,
                run_id=current_run_step.run_id
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
            await cl.Message(content="Session expired. Starting a new chat.").send()
            await start_chat()
            openai_thread_id = cl.user_session.get("openai_thread_id")
            literalai_thread_id = cl.user_session.get("literalai_thread_id")

        cl.logger.info(f"Processing message for OpenAI Thread ID: {openai_thread_id} and LiteralAI Thread ID: {literalai_thread_id}")

        with literalai_client.thread(name=literalai_thread_id, thread_id=literalai_thread_id) as thread:
            attachments = await process_files(message.elements)
            literalai_client.message(content=message.content, type="user_message", name="User")
            
            # Add a Message to the OpenAI Thread
            oai_message = await async_openai_client.beta.threads.messages.create(
                thread_id=openai_thread_id,
                role="user",
                content=message.content,
                attachments=attachments,
            )

            # Create and Stream a Run for OpenAI
            async with async_openai_client.beta.threads.runs.stream(
                thread_id=openai_thread_id,
                assistant_id=assistant.id,
                event_handler=EventHandler(assistant_name=assistant.name),
            ) as stream:
                await stream.until_done()
    except Exception as e:
        cl.logger.error(f"Error processing message: {e}", exc_info=True)
        await cl.Message(content="An error occurred while processing your message. Please try again.").send()
