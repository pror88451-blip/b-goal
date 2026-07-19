import os
from pathlib import Path

from bgoal_ai_v3_voice import load_env_file, test_openai_key


def masked_key(value):
    if not value:
        return "not found"
    if len(value) < 12:
        return "found, but too short"
    return f"{value[:7]}...{value[-4:]}"


def main():
    env_file = Path(".env")
    print("B-Goal OpenAI Check")
    print("-------------------")
    print(".env file:", "found" if env_file.exists() else "not found")

    load_env_file()
    api_key = os.getenv("OPENAI_API_KEY", "")
    print("API key:", masked_key(api_key))

    if not api_key:
        print("Problem: no OPENAI_API_KEY was found in .env.")
        return

    if not api_key.startswith("sk-"):
        print("Problem: the key does not start with sk-. Check that you copied the OpenAI API key.")
        return

    try:
        import openai

        print("OpenAI package:", openai.__version__)
    except Exception as error:
        print("Problem: OpenAI package is not installed.")
        print("Run: python -m pip install openai")
        print("Details:", error)
        return

    ok, message = test_openai_key()
    if ok:
        print("Success:", message)
        return

    print("API test failed:")
    print(message)


if __name__ == "__main__":
    main()
