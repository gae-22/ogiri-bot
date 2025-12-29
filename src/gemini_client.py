import os
import random
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Try getting it from google.genai env var compatibility if needed,
            # but usually explicit init is safer.
            raise ValueError("GEMINI_API_KEY environment variable not found")

        self.client = genai.Client(api_key=api_key)

        # Load all prompt files from PROMPTS directory
        prompts_dir = Path(__file__).parent.parent / "PROMPTS"
        self.prompt_files = list(prompts_dir.glob("*.md"))
        if not self.prompt_files:
            raise ValueError("No prompt files found in PROMPTS directory")

    def generate_ogiri_topic(self) -> str:
        """
        Generates a text-based Ogiri topic using Gemini.
        """
        # Randomly select a prompt file
        prompt_file = random.choice(self.prompt_files)
        print(f"Selected prompt: {prompt_file.name}")

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt = f.read()

        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt
            )
            text = response.text
            if text is None:
                return "申し訳ありません。お題の生成中にエラーが発生しました。"
            return text.strip()
        except Exception as e:
            print(f"Error generating content: {e}")
            return "申し訳ありません。お題の生成中にエラーが発生しました。"


if __name__ == "__main__":
    # Test execution
    client = GeminiClient()
    print(client.generate_ogiri_topic())
