from dataclasses import dataclass
import logging
import os
from pathlib import Path
import random
import re
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Creativity pools — one item is picked at random for each generation
# ---------------------------------------------------------------------------

TOPIC_FORMATS: list[str] = [
    "穴埋め形式 — 「〇〇に入る言葉は？」のように空欄を設ける",
    "シチュエーション → 行動形式 — 状況を描写し「何をした？」「何が起きた？」と問う",
    "「こんな〇〇は嫌だ」形式 — 定番フレームで意外性を出す",
    "もしも形式 — 「もし〇〇が××だったら？」と仮定を置く",
    "ランキング形式 — 「〇〇ランキング 第1位は？」と順位を問う",
    "架空の〇〇形式 — 架空のタイトル・商品名・制度・記録を考えさせる",
    "対比・選択形式 — 2つの選択肢を提示し比較させる",
    "ことわざ・格言パロディ形式 — 既存のことわざや名言を改変させる",
    "時系列形式 — 「〇〇の1日目→1ヶ月目→1年後」のように時間経過を使う",
    "無機物・概念の擬人化形式 — モノや概念に人格を与えて発言させる",
    "注意書き・取扱説明書形式 — 説明書風のフォーマットで問う",
    "かるた・辞書形式 — 特定の文字や単語の読み札・定義を考えさせる",
]

CREATIVE_ANGLES: list[str] = [
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

# ---------------------------------------------------------------------------
# Return-type dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TopicResult:
    text: str
    prompt_file: str
    model_used: str
    format_hint: str
    creative_angle: str


@dataclass
class AnswerResult:
    text: str
    model_used: str


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GeminiClient:
    _FALLBACK_MODEL = "models/gemini-2.5-flash"
    _PRO_MODEL_RE = re.compile(r"gemini-(\d+(?:\.\d+)?)-pro")

    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not found")

        self.client = genai.Client(api_key=api_key)
        self.models_to_try: list[str] = self._build_model_list()
        logger.info("Primary model: %s", self.models_to_try[0])

        prompts_dir = Path(__file__).parent.parent / "PROMPTS"
        self.prompt_files = [p for p in prompts_dir.glob("*.md") if p.name != "00_answer.md"]
        if not self.prompt_files:
            raise ValueError("No topic prompt files found in PROMPTS directory")

        self.answer_prompt_path = prompts_dir / "00_answer.md"
        if not self.answer_prompt_path.exists():
            raise ValueError("Answer prompt file (00_answer.md) not found")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_model_list(self) -> list[str]:
        """Return stable Pro models sorted by descending version, with a flash fallback."""

        def _version(name: str) -> float:
            m = self._PRO_MODEL_RE.search(name)
            return float(m.group(1)) if m else 0.0

        stable_pro = sorted(
            (
                m.name
                for m in self.client.models.list()
                if m.name is not None
                and self._PRO_MODEL_RE.search(m.name)
                and "preview" not in m.name
                and "exp" not in m.name
                and "latest" not in m.name
            ),
            key=_version,
            reverse=True,
        )
        return [*stable_pro, self._FALLBACK_MODEL]

    def _generate_with_retry(self, prompt: str) -> tuple[str, str]:
        """
        Try each model in *models_to_try* with up to 3 attempts per model.

        Returns:
            (response_text, model_name_used)
        Raises:
            The last exception encountered if every model/attempt fails.
        """
        max_attempts = 3
        backoff_base = 2
        last_exc: Exception | None = None

        for model in self.models_to_try:
            for attempt in range(1, max_attempts + 1):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=genai.types.GenerateContentConfig(temperature=1.2),
                    )
                    if response.text is None:
                        raise RuntimeError("Empty response from model")
                    return response.text.strip(), model

                except Exception as exc:
                    last_exc = exc
                    error_msg = str(exc)

                    # Hard quota exhaustion — no point retrying this model
                    if "429" in error_msg and "limit: 0" in error_msg:
                        logger.warning("Model %s has no quota; trying next model.", model)
                        break

                    logger.warning(
                        "Generation failed (model=%s, attempt=%d/%d): %r",
                        model, attempt, max_attempts, exc,
                    )

                    retryable = any(code in error_msg for code in ("503", "UNAVAILABLE", "429"))
                    if retryable and attempt < max_attempts:
                        time.sleep(backoff_base * attempt)
                        continue

                    # Non-retryable or max attempts reached for this model
                    break

        assert last_exc is not None  # always set if we reach here
        raise last_exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_topic(self, recent_topics: list[str] | None = None) -> TopicResult:
        """
        Generate a single Ogiri topic.

        Args:
            recent_topics: Previously generated topics used to avoid repetition.
        Returns:
            TopicResult with topic text and all generation metadata.
        """
        prompt_file = random.choice(self.prompt_files)
        template = prompt_file.read_text(encoding="utf-8")

        format_hint = random.choice(TOPIC_FORMATS)
        angle = random.choice(CREATIVE_ANGLES)
        logger.info(
            "Generating topic | prompt=%s | format=%s | angle=%s",
            prompt_file.name, format_hint, angle,
        )

        recent_section = ""
        if recent_topics:
            topics_list = "\n".join(f"- {t}" for t in recent_topics)
            recent_section = (
                "\n# Recent Topics（以下は最近出題済み。類似のお題を避けること）\n"
                f"{topics_list}\n"
            )

        instruction = f"""\
# Task
このファイルの「Role」「Topic Dimensions」「Format Examples」を踏まえ、テレビ番組『IPPONグランプリ』で出題されるような、回答者のセンスが光る最高に面白い大喜利のお題を **1つだけ** 生成してください。

# Thinking Process（内部で実行し、出力には含めないこと）
1. Topic Dimensions の各軸からランダムに1つずつ要素を選び、組み合わせる
2. Format Examples を参考に、**今回は「{format_hint}」** の形式でお題を構成する
3. 候補を3つ内部で考え、最も意外性と回答の余白があるものを選ぶ
4. Anti-patterns に該当しないか確認する
{recent_section}
# Requirements
- テキストのみで回答できる形式にする（「写真で一言」形式は禁止）
- 回答者が自由にボケを膨らませられる余白を残す
- 専門用語を使う場合は、誰もがわかるレベルに留める
- お題はIPPONグランプリのフリップのように、1〜3文程度で極めてシンプルかつ想像力をかきたてるものにする
- {angle}考える

# Output Format
お題のテキストのみを1つ出力してください。装飾・番号・解説は不要です。
"""

        text, model_used = self._generate_with_retry(template.format(instruction=instruction))
        logger.info("Topic generated | model=%s", model_used)
        return TopicResult(
            text=text,
            prompt_file=prompt_file.name,
            model_used=model_used,
            format_hint=format_hint,
            creative_angle=angle,
        )

    def generate_answer(self, topic: str) -> AnswerResult:
        """
        Generate a model answer for the given topic.

        Args:
            topic: The Ogiri topic text.
        Returns:
            AnswerResult with the answer text and the model used.
        """
        template = self.answer_prompt_path.read_text(encoding="utf-8")
        text, model_used = self._generate_with_retry(template.format(topic=topic))
        logger.info("Answer generated | model=%s", model_used)
        return AnswerResult(text=text, model_used=model_used)


# ---------------------------------------------------------------------------
# Manual test entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    gc = GeminiClient()
    result = gc.generate_topic()
    print(f"Topic      : {result.text}")
    print(f"Prompt file: {result.prompt_file}")
    print(f"Model      : {result.model_used}")
    print(f"Format     : {result.format_hint}")
    print(f"Angle      : {result.creative_angle}")
    print("-" * 40)
    answer = gc.generate_answer(result.text)
    print(f"Answer : {answer.text}")
    print(f"Model  : {answer.model_used}")
