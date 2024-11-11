import chainlit as cl
from chainlit.input_widget import Select
import os
import requests
import urllib3
from dotenv import load_dotenv
import json
from typing import Dict, List, Optional

load_dotenv()

urllib3.disable_warnings()

ASSISTANT_RAG_URL = "https://" + str(os.getenv("ASSISTANT_RAG_ENDPOINT"))
ASSISTANT_USER = str(os.getenv("ASSISTANT_USER"))
ASSISTANT_PWD = str(os.getenv("ASSISTANT_PWD"))


@cl.set_chat_profiles
async def chat_profile(current_user: cl.User):
    profiles = [
        cl.ChatProfile(
            name="Public",
            markdown_description="""For General questions about me""",
            icon="public/general_user.png",
        ),
        cl.ChatProfile(
            name="Technical",
            markdown_description="""For Technical questions about me""",
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
                id="Model",
                label="AI Backend",
                values=[
                    "GPT 4o-mini augmented with my public data",
                    # "AZURE Gpt-4o-realtime-latest RAGLESS(upcoming features)",
                ],
                initial_index=0,
            )
        ]
    ).send()
    cl.user_session.set("settings", settings)


@cl.on_settings_update
async def setup_agent(settings):
    print("on_settings_update", settings)


@cl.step(name="Estimate Complexity", type="tool")
async def estimate_complexity(message):

    # Simulate a running task
    url = f"{ASSISTANT_RAG_URL}/prompt"
    evaluate_complexity_prompt = f"""
    ## Objective: Your role is to analyze user question and estimate the complexity of the problem or the task mentioned
    ## Guidelines:
    ### 1- Answer only with one word: name of the level of complexity.
    ### 2- this is the list of levels of complexity : [Low, Medium, High]
    ### 3- To help you optimize your estimation this is few shots examples to help:
    Example: 1 "Comment je configure une collecte d'une log applicative multi line Filebeat 
    sur le socle convergé " => Complexity : High
    Example 2: 
    "Comment je me connecte sur Logcraft?" => Complexity => Low
    Example 3:
    "Comment je rajoute une data source dans ASSISTANT Dashboarding?" => Complexity: Medium
    Exemple 4: "Comment rajouter un hostgroup sur un agent controlM?" > Complexity : Low
    #########################################
    ###Below is user question:
    #########################################
    {message.content}
    #########################################
    Answer:
    """
    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": evaluate_complexity_prompt,
            "llm": "maia-gpt-4o-mini-no-rag",
        },
        verify=False,
        timeout=10,
    )
    response = json.loads(output.text)["candidates"][0]["content"]

    # msg = cl.Message(content=response, author="Assistant")

    return response


@cl.step(name="Mutli Query", type="tool")
async def multi_query(message):
    # Simulate a running task
    url = f"{ASSISTANT_RAG_URL}/prompt"
    # msg = cl.Message(content="", author="Assistant")
    prompt = f"""
    ## Objective: I want to respond to complex user questions
    # Break Down the complex question into maximum 3 simple questions (not necessary 3)
    ## Guidelines:
    ### 1- The result must be in a semi column separated string values
    ### 2- This is few shots examples:
    Example 1: "Bonjour, j'ai un problème de parsing logportal, j'ai le tag DATEFAIL dans les resultats de test Logstash" => Comment accéder à Logportal?;C'est quoi un TAG Datefail dans Logportal?;Comment faire pour le résoudre?
    Example 2: "Bonjour, j'ai besoin de configurer Filebeat" => C'est quoi Logportal?;comment y accéder?;Est-ce que tu as Une démo Logportal?
    #########################################
    Question: {message.content}
    #########################################
    Answer:
    """
    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": prompt,
            "llm": "maia-gpt-4o-mini-no-rag",
        },
        verify=False,
        timeout=10,
    )
    step_questions = json.loads(output.text)["candidates"][0]["content"].split(";")
    aggregated_prompt = f"""
    Look at at intermediate Question/Responses to answer the initial question {message.content} \n
    Don't forget to refer to the link provided in the responses
    #############################
    """
    for question in step_questions:
        # Find Topic
        output = await find_topic(cl.Message(content=question))
        # Call the tool 2
        res = requests.request(
            "POST",
            url=url,
            params={
                "prompt_text": question,
                "llm": "maia-gpt-4o-mini",
                "topic": [output],
            },
            verify=False,
            timeout=10,
        )
        intermediate_response = json.loads(res.text)["candidates"][0]["content"]
        print("intermediate_response", intermediate_response)
        # await respond(message, output)
        aggregated_prompt += (
            f"Question: {question}\nResponse: {intermediate_response}\n\n"
        )

    aggregated_prompt += """
    #############################
    Answer:
    """

    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": aggregated_prompt,
            "llm": "maia-gpt-4o-mini-no-rag",
        },
        verify=False,
        timeout=10,
    )
    response = json.loads(output.text)["candidates"][0]["content"]
    msg = cl.Message(content=response, author="Assistant")
    return msg


@cl.step(name="FIND TOPIC", type="tool")
async def find_topic(message):
    run_labels = [
        "filebeat_support",
    ]
    # Simulate a running task
    url = f"{ASSISTANT_RAG_URL}/prompt"
    # msg = cl.Message(content="", author="Assistant")
    classif_prompt = f"""
    ## Objective: You have to select the best topic that summarize a user ticket
    ## Guidelines:
    ### 1- Answer only with the name of labels.
    ### 2- this is a list of labels : {run_labels}
    ### 3- This are some concepts related to above labels, use them to tune your classification;there is no order in the list:
    specific_access: Access to a kibana space, to a specific index, ASSISTANT transverse
    ### 4- This is few shots examples:
    #########################################
    Question: {message.content}
    #########################################
    Answer:
    """
    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": classif_prompt,
            "llm": "maia-gpt-4o-mini-no-rag",
        },
        verify=False,
        timeout=10,
    )
    response = json.loads(output.text)["candidates"][0]["content"]

    # msg = cl.Message(content=response, author="Assistant")

    return response


@cl.step(name="RESPONSE", type="tool")
async def respond(message, auto_topic):

    # Simulate a running task
    url = f"{ASSISTANT_RAG_URL}/prompt"
    if ":::" in message.content:
        topic = message.content.split(":::")[0].strip()
    else:
        topic = auto_topic

    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": message.content,
            "llm": "maia-gpt-4o-mini",
            "topics": [topic],
        },
        verify=False,
        timeout=10,
    )
    response = json.loads(output.text)["candidates"][0]["content"]

    # update_memory("assistant", response)
    msg = cl.Message(content=response, author="Assistant")
    return msg


@cl.on_message
async def main(message: cl.Message):
    msg = "no response"
    # Update memory with user's message
    memory = update_memory("user", message.content)

    # Retrieve the selected AI Backend setting
    settings = cl.user_session.get("settings")
    ai_backend = settings.get("Model")

    if ai_backend == "AI Backend":
        msg = await respond_no_rag(message)

    await msg.send()


async def respond_no_rag(message: cl.Message):

    # Simulate a running task
    update_memory("user", message.content)

    url = f"{ASSISTANT_RAG_URL}/prompt"
    output = requests.request(
        "POST",
        url=url,
        params={
            "prompt_text": message.content,
            "llm": "maia-gpt-4o-mini-no-rag",
        },
        verify=False,
        timeout=10,
    )
    response = json.loads(output.text)["candidates"][0]["content"]

    update_memory("assistant", response)
    msg = cl.Message(content=response, author="Assistant")
    return msg


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
    # profiles = settings.get("Model")
    # print()
    return [
        cl.Starter(
            label="Teklab E-Learning Platform",
            message="useful_links::: (complexity:low) Give Me Link to access to Teklab",
            icon="/public/teklab.png",
        ),
        cl.Starter(
            label="Filebeat",
            message="filebeat::: (complexity:low) Give me links to configure Filebeat",
            icon="/public/filebeat.svg",
        ),
        cl.Starter(
            label="ASSISTANT Dashboarding",
            message="ASSISTANT-dashboarding::: (complexity:low) What Is ASSISTANT Dashboarding?",
            icon="/public/grafana.svg",
        ),
        cl.Starter(
            label="Access To ASSISTANT",
            message="spacecraft:::(complexity:low) How to request access to ASSISTANT?",
            icon="/public/access.png",
        ),
        cl.Starter(
            label="Elastic APM",
            message="apm::: (complexity:low) How to subscribe to Elastic APM?",
            icon="/public/elastic_apm.png",
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
