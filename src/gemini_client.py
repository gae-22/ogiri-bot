import os
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

    def generate_ogiri_topic(self) -> str:
        """
        Generates a text-based Ogiri topic using Gemini.
        """
        prompt = """
        あなたはユーモアのセンスがあり、大喜利が得意なAIアシスタントです。
        テキストだけで回答できる、面白い大喜利のお題を1つ考えてください。

        条件:
        - 画像を見て答える形式（写真で一言）はNGです。
        - 誰もが参加しやすい、少しひねりのある面白いお題にしてください。
        - 技術系の大学サークルに出題します。これに関連するとなお良いです。
        - お題のテキストのみを返してください。余計な前置きや説明は不要です。

        例:
        - サークルで代々引き継がれている、解読不能な『秘伝のスパゲッティコード』。 絶対に消してはいけない行に添えられていた、先代部長の恐ろしいコメントとは？「 // ここを消すと、なぜか〇〇 」
        - 徹夜続きの先輩が書いたコード。 変数名が index → tmp → a → aa とだんだん崩壊していき、 最後に定義されていた「限界すぎる変数名」とは？
        - このサークルに入ると、なぜかみんな〇〇になってしまう。その理由とは？
        - サークルの部会で突然始まった謎の儀式。その内容とは？
        - サークルの伝統行事で、毎年恒例の「〇〇大会」。今年の優勝者が披露した驚きの技とは？
        """

        try:
            response = self.client.models.generate_content(
                model="gemini-3-flash-preview", contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Error generating content: {e}")
            return "申し訳ありません。お題の生成中にエラーが発生しました。"


if __name__ == "__main__":
    # Test execution
    client = GeminiClient()
    print(client.generate_ogiri_topic())
