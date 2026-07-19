import getpass
import json
import os
import subprocess
import sys
from pathlib import Path


MEMORY_FILE = Path("bgoal_memory.json")
ENV_FILE = Path(".env")
DEFAULT_MODEL = "gpt-5-mini"
FALLBACK_MODELS = ("gpt-5-mini", "gpt-5", "gpt-4.1-mini", "gpt-4o-mini")
LEVELS = [
    (1, "Academy", 0),
    (2, "Prospect", 100),
    (3, "First Team", 250),
    (4, "Star Player", 500),
    (5, "B-Goal Legend", 900),
]


def load_env_file():
    if not ENV_FILE.exists():
        return

    with ENV_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip().strip('"')


def save_api_key(api_key):
    lines = []
    found = False

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()

    updated_lines = []
    for line in lines:
        if line.startswith("OPENAI_API_KEY="):
            updated_lines.append(f"OPENAI_API_KEY={api_key}")
            found = True
        else:
            updated_lines.append(line)

    if not found:
        updated_lines.append(f"OPENAI_API_KEY={api_key}")

    ENV_FILE.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
    os.environ["OPENAI_API_KEY"] = api_key


def setup_api_key():
    load_env_file()

    if os.getenv("OPENAI_API_KEY"):
        return

    print("\nOpenAI key not found.")
    print("Paste your OpenAI API key now, or press Enter to skip for offline mode.")
    api_key = getpass.getpass("OpenAI API key: ").strip()

    if not api_key:
        print("Offline coach mode enabled.")
        return

    save_api_key(api_key)
    print("API key saved to .env. Keep this file private.")


def get_openai_client():
    if not os.getenv("OPENAI_API_KEY"):
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("OpenAI package is not installed yet. Offline coach mode enabled.")
        print("Install later with: pip install openai")
        return None

    return OpenAI()


def ask_openai(client, prompt):
    last_error = None
    model_choices = [os.getenv("BGOAL_MODEL", DEFAULT_MODEL)]

    for model in FALLBACK_MODELS:
        if model not in model_choices:
            model_choices.append(model)

    for model in model_choices:
        try:
            response = client.responses.create(model=model, input=prompt)
            return response.output_text.strip()
        except Exception as error:
            last_error = error

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as error:
        last_error = error

    raise last_error


def test_openai_key():
    load_env_file()
    client = get_openai_client()
    if client is None:
        return False, "OpenAI is not installed or no API key was found."

    try:
        text = ask_openai(client, "Reply with exactly: B-Goal ready")
        return True, text
    except Exception as error:
        return False, str(error)


def speak(text):
    print(text)

    try:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return
    except Exception:
        pass

    if sys.platform.startswith("win"):
        try:
            ps_script = (
                "Add-Type -AssemblyName System.Speech; "
                "$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$speak.Speak($args[0])"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script, text],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def listen_or_type(prompt):
    print(prompt)
    print("Trying voice input. If it does not work, you can type instead.")

    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
        try:
            words = recognizer.recognize_google(audio)
            print("You said:", words)
            return words
        except Exception:
            print("I could not understand the voice input.")
    except ImportError:
        print("SpeechRecognition is not installed yet.")
        print("Run: python -m pip install -r requirements.txt")
    except AttributeError:
        print("Microphone support is missing. You probably need PyAudio.")
        print("Run: python -m pip install PyAudio")
    except Exception as error:
        print("Voice input is not available right now.")
        print(f"Reason: {error}")

    return input("> ").strip()


def load_player():
    if MEMORY_FILE.exists():
        with MEMORY_FILE.open("r", encoding="utf-8") as file:
            player = json.load(file)
        speak("Memory loaded.")
        return player

    return {
        "name": "",
        "position": "",
        "style": "",
        "goal": "",
        "training_sessions": 0,
        "xp": 0,
        "badges": [],
        "training_history": [],
        "ratings": {
            "Shooting": 50,
            "Passing": 50,
            "Dribbling": 50,
            "Defending": 50,
            "Speed": 50,
        },
    }


def save_player(player):
    with MEMORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(player, file, indent=4)


def ensure_player_defaults(player):
    player.setdefault("name", "")
    player.setdefault("position", "")
    player.setdefault("style", "")
    player.setdefault("goal", "")
    player.setdefault("training_sessions", 0)
    player.setdefault("xp", 0)
    player.setdefault("badges", [])
    player.setdefault("training_history", [])
    player.setdefault(
        "ratings",
        {"Shooting": 50, "Passing": 50, "Dribbling": 50, "Defending": 50, "Speed": 50},
    )
    return player


def get_level_info(player):
    xp = player.get("xp", 0)
    current = LEVELS[0]
    next_level = None

    for index, level in enumerate(LEVELS):
        if xp >= level[2]:
            current = level
            next_level = LEVELS[index + 1] if index + 1 < len(LEVELS) else None

    if next_level is None:
        progress = 100
        needed = 0
    else:
        span = next_level[2] - current[2]
        progress = int(((xp - current[2]) / span) * 100)
        needed = next_level[2] - xp

    return {
        "level": current[0],
        "title": current[1],
        "xp": xp,
        "progress": max(0, min(100, progress)),
        "next_needed": max(0, needed),
    }


def award_badges(player):
    ratings = player.get("ratings", {})
    badges = set(player.get("badges", []))

    checks = [
        ("First Session", player.get("training_sessions", 0) >= 1),
        ("Training Streak", player.get("training_sessions", 0) >= 5),
        ("Finisher", ratings.get("Shooting", 0) >= 60),
        ("Playmaker", ratings.get("Passing", 0) >= 60),
        ("Skill Star", ratings.get("Dribbling", 0) >= 60),
        ("Defensive Wall", ratings.get("Defending", 0) >= 60),
        ("Speed Boost", ratings.get("Speed", 0) >= 60),
        ("B-Goal Grinder", player.get("xp", 0) >= 250),
    ]

    unlocked = []
    for badge, earned in checks:
        if earned and badge not in badges:
            badges.add(badge)
            unlocked.append(badge)

    player["badges"] = sorted(badges)
    return unlocked


def build_training_plan(player):
    position = player.get("position", "").lower()

    if position == "striker":
        focus_days = [
            ("Day 1", "Finishing: 50 clean shots, both corners."),
            ("Day 2", "Movement: 10 near-post runs, 10 back-post runs."),
            ("Day 3", "First touch: receive, turn, shoot for 20 reps."),
            ("Day 4", "Speed: 8 short sprints, full rest between each one."),
            ("Day 5", "Weak foot: 30 passes and 20 shots."),
            ("Day 6", "1v1 practice: beat a player then finish."),
            ("Day 7", "Review: write what improved and one next target."),
        ]
    elif position == "midfielder":
        focus_days = [
            ("Day 1", "Passing: 100 wall passes, both feet."),
            ("Day 2", "Scanning: check shoulder before every touch."),
            ("Day 3", "Dribbling: tight cone turns for 15 minutes."),
            ("Day 4", "Fitness: 6 shuttle runs with clean recovery."),
            ("Day 5", "Long passing: 30 clipped or driven passes."),
            ("Day 6", "Control: receive under pressure and switch play."),
            ("Day 7", "Review: pick your best habit from the week."),
        ]
    elif position == "defender":
        focus_days = [
            ("Day 1", "Positioning: shadow defend and block the inside lane."),
            ("Day 2", "Tackling: time 20 clean standing tackles."),
            ("Day 3", "Headers: 20 clearances with safe technique."),
            ("Day 4", "Speed: recovery runs back to goal."),
            ("Day 5", "Passing: play out from the back for 50 passes."),
            ("Day 6", "1v1 defending: delay, angle, then win it."),
            ("Day 7", "Review: note your calmest defensive moment."),
        ]
    elif position == "goalkeeper":
        focus_days = [
            ("Day 1", "Handling: catch and secure 50 shots."),
            ("Day 2", "Footwork: quick steps across the goal line."),
            ("Day 3", "Distribution: 30 throws and 30 passes."),
            ("Day 4", "Diving shape: low saves both sides."),
            ("Day 5", "Communication: call early and loud."),
            ("Day 6", "Reaction saves: short-range shots."),
            ("Day 7", "Review: choose one save habit to keep."),
        ]
    else:
        focus_days = [
            ("Day 1", "Ball mastery: 15 minutes close control."),
            ("Day 2", "Passing: 100 accurate passes."),
            ("Day 3", "Shooting: 40 focused finishes."),
            ("Day 4", "Speed: sprint technique and recovery."),
            ("Day 5", "Defending: jockey and block passing lanes."),
            ("Day 6", "Weak foot: touches, passes, and shots."),
            ("Day 7", "Review: write one strength and one target."),
        ]

    goal = player.get("goal", "").strip()
    if goal:
        focus_days[-1] = ("Day 7", f"Review your goal: {goal}. Choose next week's focus.")

    return focus_days


def create_profile(player):
    if player["name"]:
        return

    player["name"] = input("Your name: ").strip()
    player["position"] = input("Your position: ").strip()
    player["style"] = input("Your play style: ").strip()
    player["goal"] = input("Your football goal: ").strip()


def offline_advice(player, training_note):
    position = player["position"].lower()

    if position == "striker":
        focus = "finishing, movement, first touch, and shooting under pressure"
    elif position == "midfielder":
        focus = "passing, scanning, vision, and controlling the tempo"
    elif position == "defender":
        focus = "positioning, tackling timing, marking, and calm clearances"
    elif position == "goalkeeper":
        focus = "handling, footwork, shot stopping, and communication"
    else:
        focus = "speed, dribbling, passing, defending, and shooting"

    if training_note:
        return f"Today, connect your goal to this note: {training_note}. Focus on {focus}."

    return f"Focus on {focus}. Keep the session sharp and track one thing you improved."


def ai_advice(client, player, training_note):
    if client is None:
        return offline_advice(player, training_note)

    prompt = (
        "You are B-Goal AI, a positive youth football coach. "
        "Give short, practical training advice in 2-4 sentences. "
        "Keep it encouraging and specific.\n\n"
        f"Player name: {player['name']}\n"
        f"Position: {player['position']}\n"
        f"Style: {player['style']}\n"
        f"Goal: {player['goal']}\n"
        f"Training sessions completed: {player['training_sessions']}\n"
        f"Ratings: {json.dumps(player['ratings'])}\n"
        f"Today's note: {training_note or 'No note'}"
    )

    try:
        return ask_openai(client, prompt)
    except Exception as error:
        return f"AI coach is unavailable right now, so offline mode is taking over. {offline_advice(player, training_note)}"


def improve_ratings(player):
    ensure_player_defaults(player)
    position = player["position"].lower()
    ratings = player["ratings"]

    if position == "striker":
        boosts = {"Shooting": 2, "Speed": 1}
    elif position == "midfielder":
        boosts = {"Passing": 2, "Dribbling": 1}
    elif position == "defender":
        boosts = {"Defending": 2, "Passing": 1}
    elif position == "goalkeeper":
        boosts = {"Defending": 2, "Passing": 1}
    else:
        boosts = {"Dribbling": 1, "Speed": 1}

    for skill, boost in boosts.items():
        ratings[skill] = min(100, ratings.get(skill, 50) + boost)

    player["xp"] = player.get("xp", 0) + 25
    return award_badges(player)


def show_profile(player):
    print("\nWelcome back,", player["name"])
    print("Position:", player["position"])
    print("Style:", player["style"])
    print("Goal:", player["goal"])
    print("\nRatings:")
    for skill, rating in player["ratings"].items():
        print(f"- {skill}: {rating}")


def main():
    print("B-GOAL AI")
    print("Be Good On All Learning")
    print("-----------------------")

    setup_api_key()
    client = get_openai_client()

    player = load_player()
    create_profile(player)
    show_profile(player)

    player["training_sessions"] += 1
    speak(f"Training session {player['training_sessions']} is starting.")

    training_note = listen_or_type("\nTell B-Goal what you trained today.")
    improve_ratings(player)

    advice = ai_advice(client, player, training_note)
    speak("\nB-Goal Coach:")
    speak(advice)

    save_player(player)
    speak("\nB-Goal remembered your progress. Keep improving.")


if __name__ == "__main__":
    main()
