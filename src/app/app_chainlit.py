import os
import plotly
from io import BytesIO
from pathlib import Path
from typing import List
# from chainlit.input_widget import Select, Switch, Slider

from openai import AsyncAssistantEventHandler, AsyncOpenAI, OpenAI

from literalai.helper import utc_now

import chainlit as cl
from chainlit.config import config
from chainlit.element import Element
from openai.types.beta.threads.runs import RunStep

from dotenv import load_dotenv

load_dotenv()


async_openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

assistant = sync_openai_client.beta.assistants.retrieve(
    os.environ.get("OPENAI_ASSISTANT_ID")
)

config.ui.name = assistant.name

class EventHandler(AsyncAssistantEventHandler):

    def __init__(self, assistant_name: str) -> None:
        super().__init__()
        self.current_message: cl.Message = None
        self.current_step: cl.Step = None
        self.current_tool_call = None
        self.assistant_name = assistant_name

    async def on_run_step_created(self, run_step: RunStep) -> None:
        cl.user_session.set("run_step", run_step)

    async def on_text_created(self, text) -> None:
        self.current_message = await cl.Message(author=self.assistant_name, content="").send()

    async def on_text_delta(self, delta, snapshot):
        if delta.value:
            await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()
        if text.annotations:
            print(text.annotations)
            for annotation in text.annotations:
                if annotation.type == "file_path":
                    response = await async_openai_client.files.with_raw_response.content(annotation.file_path.file_id)
                    file_name = annotation.text.split("/")[-1]
                    try:
                        fig = plotly.io.from_json(response.content)
                        element = cl.Plotly(name=file_name, figure=fig)
                        await cl.Message(
                            content="",
                            elements=[element]).send()
                    except Exception as e:
                        element = cl.File(content=response.content, name=file_name)
                        await cl.Message(
                            content="",
                            elements=[element]).send()
                    # Hack to fix links
                    if annotation.text in self.current_message.content and element.chainlit_key:
                        self.current_message.content = self.current_message.content.replace(annotation.text, f"/project/file/{element.chainlit_key}?session_id={cl.context.session.id}")
                        await self.current_message.update()

    async def on_tool_call_created(self, tool_call):
        self.current_tool_call = tool_call.id
        self.current_step = cl.Step(name=tool_call.type, type="tool", parent_id=cl.context.current_run.id)
        self.current_step.show_input = "python"
        self.current_step.start = utc_now()
        await self.current_step.send()

    async def on_tool_call_delta(self, delta, snapshot): 
        if snapshot.id != self.current_tool_call:
            self.current_tool_call = snapshot.id
            self.current_step = cl.Step(name=delta.type, type="tool",  parent_id=cl.context.current_run.id)
            self.current_step.start = utc_now()
            if snapshot.type == "code_interpreter":
                 self.current_step.show_input = "python"
            if snapshot.type == "function":
                self.current_step.name = snapshot.function.name
                self.current_step.language = "json"
            await self.current_step.send()
        
        if delta.type == "function":
            pass
        
        if delta.type == "code_interpreter":
            if delta.code_interpreter.outputs:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        self.current_step.output += output.logs
                        self.current_step.language = "markdown"
                        self.current_step.end = utc_now()
                        await self.current_step.update()
                    elif output.type == "image":
                        self.current_step.language = "json"
                        self.current_step.output = output.image.model_dump_json()
            else:
                if delta.code_interpreter.input:
                    await self.current_step.stream_token(delta.code_interpreter.input, is_input=True)  

    async def on_event(self, event) -> None:
        if event.event == "error":
            return cl.ErrorMessage(content=str(event.data.message)).send()

    async def on_exception(self, exception: Exception) -> None:
        return cl.ErrorMessage(content=str(exception)).send()

    async def on_tool_call_done(self, tool_call):       
        self.current_step.end = utc_now()
        await self.current_step.update()

    async def on_image_file_done(self, image_file):
        image_id = image_file.file_id
        response = await async_openai_client.files.with_raw_response.content(image_id)
        image_element = cl.Image(
            name=image_id,
            content=response.content,
            display="inline",
            size="large"
        )
        if not self.current_message.elements:
            self.current_message.elements = []
        self.current_message.elements.append(image_element)
        await self.current_message.update()




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
    response = await async_openai_client.audio.transcriptions.create(
        model="whisper-1", file=audio_file
    )

    return response.text


async def upload_files(files: List[Element]):
    file_ids = []
    for file in files:
        uploaded_file = await async_openai_client.files.create(
            file=Path(file.path), purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    return file_ids


async def process_files(files: List[Element]):
    # Upload files if any and get file_ids
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
    
@cl.on_stop
async def stop_chat():
    current_run_step: RunStep = cl.user_session.get("run_step")
    if current_run_step:
        await async_openai_client.beta.threads.runs.cancel(thread_id=current_run_step.thread_id, run_id=current_run_step.run_id)


@cl.on_message
async def main(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    attachments = await process_files(message.elements)

    # Add a Message to the Thread
    oai_message = await async_openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message.content,
        attachments=attachments,
    )

    # Create and Stream a Run
    async with async_openai_client.beta.threads.runs.stream(
        thread_id=thread_id,
        assistant_id=assistant.id,
        event_handler=EventHandler(assistant_name=assistant.name),
    ) as stream:
        await stream.until_done()