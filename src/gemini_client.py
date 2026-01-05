import os
import random
from pathlib import Path
from typing import Tuple
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
        self.prompts_dir = Path(__file__).parent.parent / "PROMPTS"

        # Get all markdown files but exclude the answer prompt
        self.prompt_files = [
            p for p in self.prompts_dir.glob("*.md") if p.name != "00_answer.md"
        ]

        if not self.prompt_files:
            raise ValueError("No topic prompt files found in PROMPTS directory")

        self.answer_prompt_path = self.prompts_dir / "00_answer.md"
        if not self.answer_prompt_path.exists():
            raise ValueError("Answer prompt file (00_answer.md) not found")

    def generate_topic(self) -> Tuple[str, str]:
        """
        Generates a text-based Ogiri topic using Gemini.
        Returns:
            Tuple[str, str]: (topic_text, prompt_filename)
        """
        prompt_file = random.choice(self.prompt_files)
        print(f"Selected prompt: {prompt_file.name}")

        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()

        instruction = """
# Task
このファイルの「Role」と「Topic Ideas」を踏まえて、面白い大喜利のお題を **1 つだけ** 生成してください。

# Requirements
- テキストのみで回答できる形式にする（画像を見て答える「写真で一言」形式は禁止）
- 回答者が自由に発想を膨らませられる余白を残す
- 専門用語を使う場合は、誰もがわかるレベルに留める

# Output Format
お題のテキストのみを出力してください。「【お題】」などの装飾は不要です。
"""

        # Format prompt for topic generation
        # Note: prompt files are expected to have {instruction} placeholder
        prompt = template.format(instruction=instruction)

        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt
            )
            text = response.text
            if text is None:
                return (
                    "申し訳ありません。お題の生成中にエラーが発生しました。",
                    prompt_file.name,
                )
            return text.strip(), prompt_file.name
        except Exception as e:
            print(f"Error generating topic: {e}")
            return (
                "申し訳ありません。お題の生成中にエラーが発生しました。",
                prompt_file.name,
            )

    def generate_answer(self, topic: str) -> str:
        """
        Generates answers for the given topic using the dedicated answer prompt file.
        """
        with open(self.answer_prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Format prompt for answer generation
        prompt = template.format(topic=topic)

        try:
            response = self.client.models.generate_content(
                model="gemini-3-pro-preview", contents=prompt
            )
            text = response.text
            if text is None:
                return "回答例の生成中にエラーが発生しました。"
            return text.strip()
        except Exception as e:
            print(f"Error generating answer: {e}")
            return "回答例の生成中にエラーが発生しました。"


if __name__ == "__main__":
    # Test execution
    client = GeminiClient()
    topic, filename = client.generate_topic()
    print(f"Topic: {topic}")
    print(f"Filename: {filename}")
    print("-" * 20)
    answer = client.generate_answer(topic)
    print(f"Answer:\n{answer}")
