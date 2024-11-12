import chainlit as cl
from chainlit.input_widget import Select, Switch, Slider, NumberInput, Tags
import os
import urllib3
from dotenv import load_dotenv
import json
from typing import Dict, List
from openai import AsyncOpenAI
import traceback

load_dotenv()

urllib3.disable_warnings()

client = AsyncOpenAI(api_key=str(os.environ.get("OPENAI_API_KEY")))


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


@cl.on_chat_start
async def start():
    # current_user = cl.user_session.get("user")
    # print("current_user", current_user)
    # cl.user_session.set("chat_profile", "ASSISTANT Explorer")

    # await cl.Message(
    #     content=f"starting chat with {user.identifier} using the {chat_profile} chat profile"
    # ).send()
    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
    )
    memory = []
    cl.user_session.set("memory", memory)
    # chat_profile = cl.user_session.get("chat_profile")

    # res = await cl.AskUserMessage(content="What is your name?", timeout=30).send()
    # if res:
    #     await cl.Message(
    #         content=f"Welcome {res['output'].capitalize()}! Ask me anything about 🌌🚀 ASSISTANT Universe 🌌🚀",
    #     ).send()
    settings = await cl.ChatSettings(
        [
            Select(
                id="model",
                label="GPT augmented with My Public Data",
                values=["gpt-4o-mini", "gpt-4o"],
                initial_index=0,
            ),
            Switch(id="stream", label="OpenAI - Stream Tokens", initial=True),
            Slider(
                id="temperature",
                label="OpenAI - Temperature",
                initial=0.7,
                min=0,
                max=1,
                step=0.1,
                tooltip="Control the randomness of the response",
            ),
            Slider(
                id="max_tokens",
                label="OpenAI - Output Tokens",
                initial=300,
                min=100,
                max=500,
                step=50,
                tooltip="Maximum Output Tokens delivered by the model",
            ),
            # Tags(id="stop", label="OpenAI - StopSequence", initial=[""]),
            Slider(
                id="top_p",
                label="Top-p sampling",
                initial=1,
                min=1,
                max=5,
                step=1,
                tooltip="In Top-p sampling chooses from the smallest possible set of words whose cumulative probability exceeds the probability p",
            ),
            Slider(
                id="n",
                label="Completion number",
                initial=1,
                min=1,
                max=5,
                step=1,
                tooltip="Generate one completion",
            ),
        ]
    ).send()
    cl.user_session.set("settings", settings)


@cl.on_settings_update
async def setup_agent(settings):
    print("on_settings_update", settings)


# settings = {
#     "model": "gpt-4o-mini",
#     "temperature": 0.7,
#     "max_tokens": 500,
#     "top_p": 1,
#     "n" : 1,
#     "frequency_penalty": 0,
#     "presence_penalty": 0,
#     "stream": True
# }


@cl.on_message
async def handle_message(message: cl.Message):

    # Get Message history
    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})
    # Update memory with user's message
    update_memory("user", message.content)

    msg = cl.Message(content="")

    # Retrieve the selected AI Backend setting
    settings = cl.user_session.get("settings")
    settings['max_tokens'] = int(settings['max_tokens'])
    settings['top_p'] = int(settings['top_p'])
    settings['n'] = int(settings['n'])

    print(settings)
    ai_backend = str(settings.get("Model"))
    print(ai_backend)


    stream = await client.chat.completions.create(
        messages=message_history,
        **settings,
        stop =None
    )

    async for chunk in stream:
        if token := chunk.choices[0].delta.content or "":
            await msg.stream_token(token)

    message_history.append({"role": "assistant", "content": msg.content})
    await msg.update()


def update_memory(role: str, content: str) -> List[Dict[str, str]]:
    """
    Handle small memory by keeping only the last 2 messages and truncating assistant's response
    """
    memory = cl.user_session.get("memory")
    memory.append({"role": role, "content": content})
    if role == "assistant":
        content = content[:150]  # Truncate assistant's response to 150 characters
    cl.user_session.set("memory", memory[-2:])  # Keep only the last 2 messages
    return memory


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
            message="What are your Fakher's major failures? Tell me some few stories",
            # icon="/public/teklab.png",
        ),
        cl.Starter(
            label="Passions That Fuel My Work",
            message="Talk me about Fakher's passions",
            # icon="/public/grafana.svg",
        ),
    ]


# @cl.password_auth_callback
# def auth_callback(username: str, password: str) -> Optional[cl.User]:
#     if (username, password) == (ASSISTANT_USER, ASSISTANT_PWD):
#         return cl.User(identifier=ASSISTANT_USER, metadata={"role": "ADMIN"})
#     else:
#         return None


@cl.on_stop
def on_stop():
    print("The user wants to stop the task!")


@cl.on_chat_end
def on_chat_end():
    print("The user disconnected!")
