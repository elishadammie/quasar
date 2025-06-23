# debug_openai.py

import httpx
import openai
from app.core.config import settings

print("--- OpenAI Connection Debugger ---")

try:
    print("Initializing OpenAI client with custom httpx settings...")
    # This is the same setup we used in our agent, to ensure an identical test
    insecure_client = httpx.Client(verify=False)
    client = openai.OpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=insecure_client
    )
    print("Client initialized successfully.")

    print("\nMaking simple API call to GPT-3.5-Turbo...")
    # We use a simple model and prompt to ensure a fast response from OpenAI's side
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hello, world!"}
        ]
    )

    print("--- SUCCESS! ---")
    print("API call finished successfully.")
    print("Response:", response.choices[0].message.content)

except Exception as e:
    print("\n--- FAILURE ---")
    print(f"An error occurred: {e}")