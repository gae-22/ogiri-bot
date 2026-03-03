#!/usr/bin/env python3
"""
List available Gemini models using google.genai client.

Usage:
  GEMINI_API_KEY=<your_key> python3 scripts/list_gemini_models.py

This script prints model ids and basic metadata. It requires network access
and a valid `GEMINI_API_KEY` environment variable.
"""
import json
import os

from dotenv import load_dotenv

try:
    from google import genai
except Exception as e:
    print("google.genai package not available:", e)
    raise


def main():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set. Export it or add to .env.")
        return

    client = genai.Client(api_key=api_key)

    try:
        # SDKs differ; try list() and fall back to raw attribute inspection
        models = None
        try:
            models = client.models.list()
        except Exception:
            # Some versions may expose a different interface
            models = getattr(client.models, "available", None)

        if models is None:
            print("Could not retrieve models via SDK. Inspecting client.models object:")
            print(repr(client.models))
            return

        # If models is an iterable, print entries
        if isinstance(models, (list, tuple)):
            for m in models:
                try:
                    print(json.dumps(m.__dict__, ensure_ascii=False, indent=2))
                except Exception:
                    print(m)
        else:
            # Try iterating
            try:
                for m in models:
                    print(m)
            except Exception:
                print(repr(models))

    except Exception as e:
        print("Error while listing models:", e)


if __name__ == "__main__":
    main()
