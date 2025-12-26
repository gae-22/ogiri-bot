import os
from google import genai
from dotenv import load_dotenv

load_dotenv()


def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found")
        return

    client = genai.Client(api_key=api_key)
    try:
        # The syntax for listing models in the new SDK might vary,
        # but let's try the common patterns or just try to generate with a fallback
        print("Attempting to list models...")
        # Note: The new SDK doesn't always have a simple list_models on the client root
        # or it might be client.models.list()
        # Let's try client.models.list()
        for m in client.models.list():
            print(f"Model: {m.name}")

    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    list_models()
