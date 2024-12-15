import json
import plotly
import chainlit as cl
from openai import AsyncAssistantEventHandler
from openai.types.beta.threads.runs import RunStep
from literalai.helper import utc_now
import os

from openai import AsyncOpenAI, OpenAI

async_openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
sync_openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
from tools.time import get_time_now
from tools.GmailTools import gmail_send_mail


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
        self.current_message = await cl.Message(
            author=self.assistant_name, content=""
        ).send()

    async def on_text_delta(self, delta, snapshot):
        if delta.value:
            await self.current_message.stream_token(delta.value)

    async def on_text_done(self, text):
        await self.current_message.update()
        if text.annotations:
            print(text.annotations)
            for annotation in text.annotations:
                if annotation.type == "file_path":
                    response = (
                        await async_openai_client.files.with_raw_response.content(
                            annotation.file_path.file_id
                        )
                    )
                    file_name = annotation.text.split("/")[-1]
                    try:
                        fig = plotly.io.from_json(response.content)
                        element = cl.Plotly(name=file_name, figure=fig)
                        await cl.Message(content="", elements=[element]).send()
                    except Exception as e:
                        element = cl.File(content=response.content, name=file_name)
                        await cl.Message(content="", elements=[element]).send()
                    # Hack to fix links
                    if (
                        annotation.text in self.current_message.content
                        and element.chainlit_key
                    ):
                        self.current_message.content = self.current_message.content.replace(
                            annotation.text,
                            f"/project/file/{element.chainlit_key}?session_id={cl.context.session.id}",
                        )
                        await self.current_message.update()

    # async def on_tool_call_created(self, tool_call):
    #     self.current_tool_call = tool_call.id
    #     self.current_step = cl.Step(
    #         name=tool_call.type, type="tool", parent_id=cl.context.current_run.id
    #     )
    #     self.current_step.show_input = "python"
    #     self.current_step.start = utc_now()
    #     await self.current_step.send()

    # async def on_tool_call_delta(self, delta, snapshot):
    #     if snapshot.id != self.current_tool_call:
    #         self.current_tool_call = snapshot.id
    #         self.current_step = cl.Step(
    #             name=delta.type, type="tool", parent_id=cl.context.current_run.id
    #         )
    #         self.current_step.start = utc_now()
    #         if snapshot.type == "code_interpreter":
    #             self.current_step.show_input = "python"
    #         if snapshot.type == "function":
    #             self.current_step.name = snapshot.function.name
    #             self.current_step.language = "json"
    #         await self.current_step.send()

    #     if delta.type == "function":
    #         pass

    #     if delta.type == "code_interpreter":
    #         if delta.code_interpreter.outputs:
    #             for output in delta.code_interpreter.outputs:
    #                 if output.type == "logs":
    #                     self.current_step.output += output.logs
    #                     self.current_step.language = "markdown"
    #                     self.current_step.end = utc_now()
    #                     await self.current_step.update()
    #                 elif output.type == "image":
    #                     self.current_step.language = "json"
    #                     self.current_step.output = output.image.model_dump_json()
    #         else:
    #             if delta.code_interpreter.input:
    #                 await self.current_step.stream_token(
    #                     delta.code_interpreter.input, is_input=True
    #                 )

    async def on_event(self, event) -> None:
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == "thread.run.requires_action":
            run_id = event.data.id  # Retrieve the run ID from the event data
            await self.handle_requires_action(event.data, run_id)
        elif event.event == "error":
            return cl.ErrorMessage(content=str(event.data.message)).send()

    @cl.step(type="tool")
    async def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            current_step = cl.context.current_step
            current_step.name = tool.function.name

            if tool.function.name == "get_time_now":
                tool_outputs.append(
                    {"tool_call_id": tool.id, "output": await get_time_now()}
                )
            if tool.function.name == "gmail_send_mail":
                arguments = json.loads(tool.function.arguments)

                subject = arguments["subject"]
                cc = arguments["cc"]
                body = arguments["body"]
                # Parse the arguements from the tool call

                tool_outputs.append(
                    {
                        "tool_call_id": tool.id,
                        "output": await gmail_send_mail(subject, cc, body),
                    }
                )
        # Submit all tool_outputs at the same time
        await self.submit_tool_outputs(tool_outputs, run_id)

    async def submit_tool_outputs(self, tool_outputs, run_id):

        # Use the submit_tool_outputs_stream helper
        async with async_openai_client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(self.assistant_name),
        ) as stream:
            await stream.until_done()

    async def on_exception(self, exception: Exception) -> None:
        return cl.ErrorMessage(content=str(exception)).send()

    # async def on_tool_call_done(self, tool_call):
    #     self.current_step.end = utc_now()
    #     await self.current_step.update()

    async def on_image_file_done(self, image_file):
        image_id = image_file.file_id
        response = await async_openai_client.files.with_raw_response.content(image_id)
        image_element = cl.Image(
            name=image_id, content=response.content, display="inline", size="large"
        )
        if not self.current_message.elements:
            self.current_message.elements = []
        self.current_message.elements.append(image_element)
        await self.current_message.update()
