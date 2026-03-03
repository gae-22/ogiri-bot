import os
import re

from dotenv import load_dotenv
from google import genai

load_dotenv()


def get_latest_model(prefer_keyword="flash"):
    """
    Retrieves the latest available Gemini model.
    Prioritizes higher version numbers, then models containing the preferred keyword (default: "flash").
    Excludes embeddings and image/video generation models.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found")
        return None

    client = genai.Client(api_key=api_key)
    try:
        models = list(client.models.list())
    except Exception as e:
        print(f"Error listing models: {e}")
        return None

    valid_models = []
    # Regex to capture version. Matches "gemini-" followed by digits and dots.
    version_pattern = re.compile(r"gemini-(\d+(?:\.\d+)*)")

    for m in models:
        name = m.name

        # Filter for gemini models only (name can be None per the SDK type stubs)
        if name is None or "gemini" not in name:
            continue

        # Exclude specific types
        exclude_keywords = ["embedding", "image", "imagen", "veo", "video", "audio"]
        if any(keyword in name for keyword in exclude_keywords):
            continue

        # Extract version
        match = version_pattern.search(name)
        if match:
            version_str = match.group(1)
            try:
                # Convert version string to tuple for comparison (e.g. 1.5 -> (1, 5))
                version_tuple = tuple(map(int, version_str.split(".")))
                valid_models.append(
                    {
                        "name": name,
                        "version": version_tuple,
                        "is_preferred": prefer_keyword in name,
                        "is_experimental": "exp" in name or "preview" in name,
                    }
                )
            except ValueError:
                continue

    if not valid_models:
        return None

    # Sort criteria:
    # 1. Version (Descending)
    # 2. Preferred keyword (True > False)
    # 3. Stability (Experimental/Preview is less preferred than Stable) -> False > True
    # 4. Name length (shorter valid names often imply main versions, e.g. gemini-1.5-flash vs gemini-1.5-flash-001)

    valid_models.sort(
        key=lambda x: (
            x["version"],
            x["is_preferred"],
            not x["is_experimental"],
            -len(x["name"]),
        ),
        reverse=True,
    )

    best_model = valid_models[0]["name"]

    # Strip 'models/' prefix if present for cleaner usage
    if best_model.startswith("models/"):
        best_model = best_model.replace("models/", "")

    return best_model


def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key found")
        return

    client = genai.Client(api_key=api_key)
    try:
        print("Attempting to list models...")
        for m in client.models.list():
            print(f"Model: {m.name}")

    except Exception as e:
        print(f"Error listing models: {e}")


if __name__ == "__main__":
    # list_models() # Uncomment if you want to see the full list
    print("-" * 20)
    latest = get_latest_model()
    print(f"Selected Latest Model: {latest}")
