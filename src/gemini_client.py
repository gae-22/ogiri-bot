import os
import random
from pathlib import Path
from typing import List, Optional, Tuple
from google import genai
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# お題のフォーマットメニュー（毎回ランダムに1つ指定して多様性を強制）
TOPIC_FORMATS = [
    "穴埋め形式 — 「〇〇に入る言葉は？」のように空欄を設ける",
    "シチュエーション → 行動形式 — 状況を描写し「何をした？」「何が起きた？」と問う",
    "「こんな〇〇は嫌だ」形式 — 定番フレームで意外性を出す",
    "もしも形式 — 「もし〇〇が××だったら？」と仮定を置く",
    "ランキング形式 — 「〇〇ランキング 第1位は？」と順位を問う",
    "架空の〇〇形式 — 架空のタイトル・商品名・制度・記録を考えさせる",
    "対比・選択形式 — 2つの選択肢を提示し比較させる",
    "ことわざ・格言パロディ形式 — 既存のことわざや名言を改変させる",
    "時系列形式 — 「〇〇の1日目→1ヶ月目→1年目」のように時間経過を使う",
    "無機物・概念の擬人化形式 — モノや概念に人格を与えて発言させる",
    "注意書き・取扱説明書形式 — 説明書風のフォーマットで問う",
    "かるた・辞書形式 — 特定の文字や単語の読み札・定義を考えさせる",
]

# 創造的な切り口（ランダムに1つ指定して発想の方向を変える）
CREATIVE_ANGLES = [
    "皮肉・風刺を効かせた切り口で",
    "日常の些細なことを壮大に語る切り口で",
    "真面目な状況でのギャップを活かす切り口で",
    "擬人化や感情移入を使う切り口で",
    "過去と現在、または理想と現実の対比を使う切り口で",
    "専門知識を意外な日常場面に応用する切り口で",
    "定番の展開を裏切るメタ的な切り口で",
    "数字・統計・ランキングを使った切り口で",
    "感動的な場面を台無しにする切り口で",
    "未来予想・SF的な想像を膨らませる切り口で",
    "誰もが経験したことのある「あるある」を誇張する切り口で",
    "異なる世界観を衝突させる切り口で",
]


class GeminiClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not found")

        self.client = genai.Client(api_key=api_key)
        # Use a stable model by default to reduce downtime from preview models
        self.model = "models/gemini-2.5-flash"

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

    def generate_topic(
        self, recent_topics: Optional[List[str]] = None
    ) -> Tuple[str, str]:
        """
        Generates a text-based Ogiri topic using Gemini.
        Args:
            recent_topics: List of recently generated topics to avoid repetition.
        Returns:
            Tuple[str, str]: (topic_text, prompt_filename)
        """
        prompt_file = random.choice(self.prompt_files)
        print(f"Selected prompt: {prompt_file.name}")

        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()

        # ランダムにフォーマットと切り口を選択
        format_hint = random.choice(TOPIC_FORMATS)
        angle = random.choice(CREATIVE_ANGLES)
        print(f"Format hint: {format_hint}")
        print(f"Creative angle: {angle}")

        # 最近のお題リスト（重複回避用）
        recent_topics_section = ""
        if recent_topics:
            topics_list = "\n".join(f"- {t}" for t in recent_topics)
            recent_topics_section = f"""
# Recent Topics（以下は最近出題済み。類似のお題を避けること）
{topics_list}
"""

        instruction = f"""
# Task
このファイルの「Role」「Topic Dimensions」「Format Examples」を踏まえ、面白い大喜利のお題を **1つだけ** 生成してください。

# Thinking Process（内部で実行し、出力には含めないこと）
1. Topic Dimensions の各軸からランダムに1つずつ要素を選び、組み合わせる
2. Format Examples を参考に、**今回は「{format_hint}」** の形式でお題を構成する
3. 候補を3つ内部で考え、最も意外性と回答の余白があるものを選ぶ
4. Anti-patterns に該当しないか確認する
{recent_topics_section}
# Requirements
- テキストのみで回答できる形式にする（「写真で一言」形式は禁止）
- 回答者が自由にボケを膨らませられる余白を残す
- 専門用語を使う場合は、誰もがわかるレベルに留める
- お題は1〜3文程度の簡潔さにする
- {angle}考える

# Output Format
お題のテキストのみを1つ出力してください。装飾・番号・解説は不要です。
"""

        # Format prompt for topic generation
        prompt = template.format(instruction=instruction)

        # Try with retries for transient errors (e.g., 503)
        max_attempts = 3
        backoff = 2
        last_exc = None
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt
                )
                text = response.text
                if text is None:
                    raise RuntimeError("Empty response from model")
                return text.strip(), prompt_file.name
            except Exception as e:
                last_exc = e
                print(f"Error generating topic (attempt {attempt}): {repr(e)}")
                # If transient-like error, retry
                if attempt < max_attempts and (
                    "503" in str(e) or "UNAVAILABLE" in str(e)
                ):
                    time.sleep(backoff * attempt)
                    continue
                # Non-retryable or max attempts reached -> raise
                raise

    def generate_answer(self, topic: str) -> str:
        """
        Generates answers for the given topic using the dedicated answer prompt file.
        """
        with open(self.answer_prompt_path, "r", encoding="utf-8") as f:
            template = f.read()

        # Format prompt for answer generation
        prompt = template.format(topic=topic)

        # Retry logic similar to generate_topic
        max_attempts = 3
        backoff = 2
        for attempt in range(1, max_attempts + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model, contents=prompt
                )
                text = response.text
                if text is None:
                    raise RuntimeError("Empty response from model")
                return text.strip()
            except Exception as e:
                print(f"Error generating answer (attempt {attempt}): {repr(e)}")
                if attempt < max_attempts and ("503" in str(e) or "UNAVAILABLE" in str(e)):
                    time.sleep(backoff * attempt)
                    continue
                raise


if __name__ == "__main__":
    # Test execution
    client = GeminiClient()
    topic, filename = client.generate_topic()
    print(f"Topic: {topic}")
    print(f"Filename: {filename}")
    print("-" * 20)
    answer = client.generate_answer(topic)
    print(f"Answer:\n{answer}")
