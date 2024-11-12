import openai
import os

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=str(os.environ.get("OPENAI_API_KEY")))


def detect_secrets_with_llm(input_string):
    prompt = f"""
    Role: Security Operation Analyst
    Task: Analyze in order Identify any sensitive information or secrets in the following text:\n\n{input_string}\n\nIndicate any API keys, tokens, passwords, or other secrets . If you have doubt or you are sure that there is no secret, respond NO otherwise YES
    Instructions: Respond only by YES or NO
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant skilled at identifying sensitive information."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=200
    )
    
    # Extract the response from GPT
    output = response.choices[0].message.content.strip()
    return output

# Example string with a mock secret
example_string = """I have a trouble connecting to artifactory with API this is information that can help: {'USER_API': mytechnical account,
'INSTANCE_NAME': 'artifactory.contoso.com', 'API_KEY' = 'sk_test_4eC39HqLyjWDarjtT1zdp7dc'}
"""
output = detect_secrets_with_llm(example_string)
print("Detection Result:")
print(output)
