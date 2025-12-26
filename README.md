# Ohgiri

短い説明

Ohgiri はトピック生成や送信を支援する小さな Python ツールです。

**主なファイル**

-   `main.py`: エントリポイント（簡単な CLI/起動スクリプト）
-   `src/bot.py`: ボットの主要ロジック
-   `src/gemini_client.py`: Gemini API クライアント（外部モデル呼び出し）
-   `src/send_topic.py`: 生成したトピックを送信するユーティリティ
-   `src/check_models.py`: 利用可能なモデルや設定を確認するヘルパー

**要件**

-   Python 3.10+
-   必要な依存は `pyproject.toml` を参照してください。

**セットアップ**

1. 依存をインストールする:

```bash
uv sync
```

**使い方**

-   開発や実行はシンプルです:

```bash
uv run python -m src.send_topic
```

プロジェクトの各スクリプトは `src/` 配下にあり、用途に合わせて直接実行できます。

**次のステップ**

-   必要なら実行例や設定方法（API キー、環境変数）のセクションを追記します。
