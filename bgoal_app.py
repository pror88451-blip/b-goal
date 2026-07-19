import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from bgoal_ai_v3_voice import (
    ai_advice,
    award_badges,
    build_training_plan,
    ensure_player_defaults,
    get_level_info,
    get_openai_client,
    improve_ratings,
    load_env_file,
    load_player,
    save_api_key,
    save_player,
    speak,
    test_openai_key,
)


LOGO_IMAGE = Path("assets") / "bgoal_world_ball_logo.png"
BACKGROUND_IMAGE = Path("assets") / "bgoal_app_background.png"
MEDIA_DIR = Path("media")

THEMES = {
    "Pitch": {
        "bg": "#eef5ed",
        "panel": "#ffffff",
        "text": "#152016",
        "muted": "#4d5f50",
        "accent": "#1d7d3b",
        "bar": "#1d7d3b",
    },
    "Night": {
        "bg": "#11161d",
        "panel": "#1c2430",
        "text": "#eef4f2",
        "muted": "#aebbc0",
        "accent": "#35a8ff",
        "bar": "#35a8ff",
    },
    "Gold": {
        "bg": "#f6f2e8",
        "panel": "#ffffff",
        "text": "#251f16",
        "muted": "#6d604c",
        "accent": "#b98218",
        "bar": "#b98218",
    },
}


class BGoalApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("B-Goal AI")
        self.geometry("1040x720")
        self.minsize(900, 620)

        load_env_file()
        self.client = get_openai_client()
        self.player = ensure_player_defaults(load_player())
        self.theme_name = self.player.get("theme", "Pitch")
        self.theme = THEMES.get(self.theme_name, THEMES["Pitch"])

        self.rating_widgets = {}
        self.badge_var = tk.StringVar()
        self.level_var = tk.StringVar()
        self.session_var = tk.StringVar()
        self.api_status_var = tk.StringVar()
        self.camera_status_var = tk.StringVar(value="Camera stopped")
        self.current_training_note = ""

        self.logo_image = None
        self.small_logo = None
        self.background_image = None
        self.cap = None
        self.cv2 = None
        self.image_tk_module = None
        self.video_writer = None
        self.recording = False
        self.last_frame = None

        self.load_images()
        self.configure(bg=self.theme["bg"])
        self.build_styles()
        self.build_ui()
        self.load_player_into_form()
        self.update_api_status()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_images(self):
        if LOGO_IMAGE.exists():
            self.logo_image = tk.PhotoImage(file=str(LOGO_IMAGE))
            try:
                self.iconphoto(True, self.logo_image)
            except tk.TclError:
                pass

        if BACKGROUND_IMAGE.exists():
            self.background_image = tk.PhotoImage(file=str(BACKGROUND_IMAGE))

    def build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=self.theme["bg"])
        style.configure("Panel.TFrame", background=self.theme["panel"], borderwidth=1, relief="solid")
        style.configure("TLabel", background=self.theme["bg"], foreground=self.theme["text"], font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.theme["panel"], foreground=self.theme["text"], font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=self.theme["bg"], foreground=self.theme["text"], font=("Segoe UI", 25, "bold"))
        style.configure("Sub.TLabel", background=self.theme["bg"], foreground=self.theme["muted"], font=("Segoe UI", 11))
        style.configure("Stat.TLabel", background=self.theme["panel"], foreground=self.theme["text"], font=("Segoe UI", 15, "bold"))
        style.configure("Muted.Panel.TLabel", background=self.theme["panel"], foreground=self.theme["muted"], font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=(11, 8))
        style.configure("Accent.TButton", background=self.theme["accent"], foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", self.theme["accent"])])
        style.configure("TNotebook", background=self.theme["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.configure("Horizontal.TProgressbar", troughcolor="#dfe7de", background=self.theme["bar"])

    def build_ui(self):
        if self.background_image:
            self.bg_label = tk.Label(self, image=self.background_image, borderwidth=0)
            self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        root = ttk.Frame(self, padding=18)
        root.place(relx=0, rely=0, relwidth=1, relheight=1)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 14))
        if self.logo_image:
            self.small_logo = self.logo_image.subsample(8, 8)
            ttk.Label(header, image=self.small_logo).pack(side="left", padx=(0, 12))

        title_box = ttk.Frame(header)
        title_box.pack(side="left", fill="x", expand=True)
        ttk.Label(title_box, text="B-Goal AI", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Be Good On All Learning", style="Sub.TLabel").pack(anchor="w")

        theme_box = ttk.Frame(header)
        theme_box.pack(side="right")
        ttk.Label(theme_box, text="Theme").pack(anchor="e")
        self.theme_var = tk.StringVar(value=self.theme_name)
        theme_menu = ttk.Combobox(theme_box, textvariable=self.theme_var, values=list(THEMES), state="readonly", width=12)
        theme_menu.pack(anchor="e")
        theme_menu.bind("<<ComboboxSelected>>", self.change_theme)

        self.tabs = ttk.Notebook(root)
        self.tabs.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(self.tabs, padding=14)
        self.training_tab = ttk.Frame(self.tabs, padding=14)
        self.plan_tab = ttk.Frame(self.tabs, padding=14)
        self.camera_tab = ttk.Frame(self.tabs, padding=14)
        self.settings_tab = ttk.Frame(self.tabs, padding=14)

        self.tabs.add(self.dashboard_tab, text="Dashboard")
        self.tabs.add(self.training_tab, text="Training")
        self.tabs.add(self.plan_tab, text="Plan")
        self.tabs.add(self.camera_tab, text="Camera")
        self.tabs.add(self.settings_tab, text="Settings")

        self.build_dashboard()
        self.build_training()
        self.build_plan()
        self.build_camera()
        self.build_settings()

    def panel(self, parent, row, column, **grid):
        frame = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        frame.grid(row=row, column=column, sticky="nsew", **grid)
        return frame

    def build_dashboard(self):
        self.dashboard_tab.columnconfigure(0, weight=1)
        self.dashboard_tab.columnconfigure(1, weight=1)
        self.dashboard_tab.rowconfigure(1, weight=1)

        profile = self.panel(self.dashboard_tab, 0, 0, padx=(0, 8), pady=(0, 12))
        progress = self.panel(self.dashboard_tab, 0, 1, padx=(8, 0), pady=(0, 12))
        ratings = self.panel(self.dashboard_tab, 1, 0, padx=(0, 8))
        badges = self.panel(self.dashboard_tab, 1, 1, padx=(8, 0))

        ttk.Label(profile, text="Player Card", style="Stat.TLabel").pack(anchor="w")
        self.player_card_var = tk.StringVar()
        ttk.Label(profile, textvariable=self.player_card_var, style="Panel.TLabel", justify="left").pack(anchor="w", pady=(8, 0))

        ttk.Label(progress, text="Level", style="Stat.TLabel").pack(anchor="w")
        ttk.Label(progress, textvariable=self.level_var, style="Panel.TLabel").pack(anchor="w", pady=(8, 6))
        self.level_bar = ttk.Progressbar(progress, maximum=100)
        self.level_bar.pack(fill="x")
        ttk.Label(progress, textvariable=self.session_var, style="Muted.Panel.TLabel").pack(anchor="w", pady=(8, 0))

        ttk.Label(ratings, text="Ratings", style="Stat.TLabel").pack(anchor="w")
        for skill in ["Shooting", "Passing", "Dribbling", "Defending", "Speed"]:
            row = ttk.Frame(ratings, style="Panel.TFrame")
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=skill, style="Panel.TLabel", width=11).pack(side="left")
            bar = ttk.Progressbar(row, maximum=100)
            bar.pack(side="left", fill="x", expand=True, padx=8)
            value = ttk.Label(row, text="50", style="Panel.TLabel", width=4)
            value.pack(side="right")
            self.rating_widgets[skill] = (bar, value)

        ttk.Label(badges, text="Badges", style="Stat.TLabel").pack(anchor="w")
        self.badges_text = tk.Text(badges, height=12, wrap="word", font=("Segoe UI", 11), relief="flat")
        self.badges_text.pack(fill="both", expand=True, pady=(8, 0))

    def build_training(self):
        self.training_tab.columnconfigure(0, weight=1)
        self.training_tab.rowconfigure(1, weight=1)
        self.training_tab.rowconfigure(4, weight=1)

        ttk.Label(self.training_tab, text="What did you train today?").grid(row=0, column=0, sticky="w")
        self.training_text = tk.Text(self.training_tab, height=7, wrap="word", font=("Segoe UI", 11), relief="solid", borderwidth=1)
        self.training_text.grid(row=1, column=0, sticky="nsew", pady=(4, 10))

        buttons = ttk.Frame(self.training_tab)
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        self.coach_button = ttk.Button(buttons, text="Coach Me", style="Accent.TButton", command=self.start_training)
        self.coach_button.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(buttons, text="Speak Advice", command=self.speak_advice).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Label(self.training_tab, text="B-Goal Coach").grid(row=3, column=0, sticky="w", pady=(14, 4))
        self.advice_text = tk.Text(self.training_tab, height=12, wrap="word", font=("Segoe UI", 11), relief="solid", borderwidth=1)
        self.advice_text.grid(row=4, column=0, sticky="nsew")

    def build_plan(self):
        self.plan_tab.columnconfigure(0, weight=1)
        self.plan_tab.rowconfigure(1, weight=1)

        buttons = ttk.Frame(self.plan_tab)
        buttons.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(buttons, text="Generate 7-Day Plan", style="Accent.TButton", command=self.generate_plan).pack(side="left")

        self.plan_text = tk.Text(self.plan_tab, wrap="word", font=("Segoe UI", 11), relief="solid", borderwidth=1)
        self.plan_text.grid(row=1, column=0, sticky="nsew")

    def build_camera(self):
        self.camera_tab.columnconfigure(0, weight=1)
        self.camera_tab.rowconfigure(1, weight=1)

        controls = ttk.Frame(self.camera_tab)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Button(controls, text="Start Camera", style="Accent.TButton", command=self.start_camera).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Stop Camera", command=self.stop_camera).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Snapshot", command=self.capture_snapshot).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Start Recording", command=self.start_recording).pack(side="left", padx=(0, 8))
        ttk.Button(controls, text="Stop Recording", command=self.stop_recording).pack(side="left", padx=(0, 8))
        ttk.Label(controls, textvariable=self.camera_status_var).pack(side="right")

        self.camera_view = tk.Label(self.camera_tab, text="Camera preview", bg="#12171e", fg="#dce6e8", font=("Segoe UI", 18, "bold"))
        self.camera_view.grid(row=1, column=0, sticky="nsew")

    def build_settings(self):
        self.settings_tab.columnconfigure(0, weight=1)

        profile = self.panel(self.settings_tab, 0, 0, pady=(0, 12))
        api = self.panel(self.settings_tab, 1, 0)

        self.name_var = tk.StringVar()
        self.position_var = tk.StringVar()
        self.style_var = tk.StringVar()
        self.goal_var = tk.StringVar()
        self.api_key_var = tk.StringVar()

        ttk.Label(profile, text="Profile", style="Stat.TLabel").pack(anchor="w")
        fields = [("Name", self.name_var), ("Position", self.position_var), ("Play style", self.style_var), ("Football goal", self.goal_var)]
        for label, variable in fields:
            ttk.Label(profile, text=label, style="Panel.TLabel").pack(anchor="w", pady=(10, 3))
            ttk.Entry(profile, textvariable=variable).pack(fill="x")
        ttk.Button(profile, text="Save Profile", style="Accent.TButton", command=self.save_profile).pack(fill="x", pady=(14, 0))

        ttk.Label(api, text="OpenAI Key", style="Stat.TLabel").pack(anchor="w")
        ttk.Label(api, textvariable=self.api_status_var, style="Muted.Panel.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Entry(api, textvariable=self.api_key_var, show="*").pack(fill="x")
        ttk.Button(api, text="Save API Key", command=self.save_key).pack(fill="x", pady=(8, 0))
        ttk.Button(api, text="Test API Key", command=self.start_key_test).pack(fill="x", pady=(8, 0))

    def change_theme(self, _event=None):
        self.player["theme"] = self.theme_var.get()
        save_player(self.player)
        messagebox.showinfo("B-Goal AI", "Theme saved. Restart the app to fully apply it.")

    def load_player_into_form(self):
        self.name_var.set(self.player.get("name", ""))
        self.position_var.set(self.player.get("position", ""))
        self.style_var.set(self.player.get("style", ""))
        self.goal_var.set(self.player.get("goal", ""))
        self.refresh_dashboard()

    def form_to_player(self):
        self.player = ensure_player_defaults(self.player)
        self.player["name"] = self.name_var.get().strip()
        self.player["position"] = self.position_var.get().strip()
        self.player["style"] = self.style_var.get().strip()
        self.player["goal"] = self.goal_var.get().strip()

    def refresh_dashboard(self):
        ensure_player_defaults(self.player)
        level = get_level_info(self.player)
        self.level_var.set(f"Level {level['level']} - {level['title']} | {level['xp']} XP | {level['next_needed']} XP to next")
        self.level_bar["value"] = level["progress"]
        self.session_var.set(f"Training sessions completed: {self.player.get('training_sessions', 0)}")
        self.player_card_var.set(
            f"Name: {self.player.get('name') or 'New player'}\n"
            f"Position: {self.player.get('position') or 'Not set'}\n"
            f"Style: {self.player.get('style') or 'Not set'}\n"
            f"Goal: {self.player.get('goal') or 'Not set'}"
        )

        for skill, (bar, value) in self.rating_widgets.items():
            rating = self.player["ratings"].get(skill, 50)
            bar["value"] = rating
            value.configure(text=str(rating))

        badges = self.player.get("badges", [])
        self.badges_text.delete("1.0", "end")
        self.badges_text.insert("1.0", "\n".join(f"- {badge}" for badge in badges) if badges else "No badges yet. Train to unlock your first one.")

    def update_api_status(self):
        if self.client:
            self.api_status_var.set("OpenAI ready")
        else:
            self.api_status_var.set("Offline mode. Add API credits later if you want AI replies.")

    def save_profile(self):
        self.form_to_player()
        award_badges(self.player)
        save_player(self.player)
        self.refresh_dashboard()
        messagebox.showinfo("B-Goal AI", "Profile saved.")

    def save_key(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("B-Goal AI", "Paste your API key first.")
            return
        save_api_key(api_key)
        self.api_key_var.set("")
        self.client = get_openai_client()
        self.update_api_status()
        messagebox.showinfo("B-Goal AI", "API key saved.")

    def start_key_test(self):
        self.api_status_var.set("Testing OpenAI key...")
        threading.Thread(target=self.run_key_test, daemon=True).start()

    def run_key_test(self):
        ok, message = test_openai_key()
        self.after(0, lambda: self.finish_key_test(ok, message))

    def finish_key_test(self, ok, message):
        if ok:
            self.client = get_openai_client()
            self.api_status_var.set("OpenAI ready")
            messagebox.showinfo("B-Goal AI", f"API key works: {message}")
        else:
            self.client = None
            self.api_status_var.set("OpenAI key test failed")
            messagebox.showerror("B-Goal AI", f"API key test failed:\n\n{message}")

    def start_training(self):
        self.form_to_player()
        if not self.player["name"]:
            messagebox.showwarning("B-Goal AI", "Add your name in Settings first.")
            return
        self.coach_button.configure(state="disabled", text="Coaching...")
        self.set_advice("B-Goal is thinking...")
        self.current_training_note = self.training_text.get("1.0", "end").strip()
        threading.Thread(target=self.run_training, daemon=True).start()

    def run_training(self):
        self.player["training_sessions"] += 1
        unlocked = improve_ratings(self.player)
        self.player["training_history"].append(
            {"time": time.strftime("%Y-%m-%d %H:%M"), "note": self.current_training_note}
        )
        advice = ai_advice(self.client, self.player, self.current_training_note)
        save_player(self.player)
        self.after(0, lambda: self.finish_training(advice, unlocked))

    def finish_training(self, advice, unlocked):
        if unlocked:
            advice = advice + "\n\nNew badge unlocked: " + ", ".join(unlocked)
        self.set_advice(advice)
        self.refresh_dashboard()
        self.coach_button.configure(state="normal", text="Coach Me")

    def set_advice(self, text):
        self.advice_text.delete("1.0", "end")
        self.advice_text.insert("1.0", text)

    def speak_advice(self):
        advice = self.advice_text.get("1.0", "end").strip()
        if not advice:
            messagebox.showwarning("B-Goal AI", "Get coach advice first.")
            return
        threading.Thread(target=speak, args=(advice,), daemon=True).start()

    def generate_plan(self):
        self.form_to_player()
        plan = build_training_plan(self.player)
        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", "\n\n".join(f"{day}\n{task}" for day, task in plan))

    def load_camera_modules(self):
        if self.cv2:
            return True
        try:
            import cv2
            from PIL import Image, ImageTk
        except Exception as error:
            messagebox.showerror(
                "B-Goal Camera",
                "Camera needs extra packages.\n\nRun this:\npython -m pip install opencv-python pillow\n\n"
                f"Details: {error}",
            )
            return False
        self.cv2 = cv2
        self.image_module = Image
        self.image_tk_module = ImageTk
        return True

    def start_camera(self):
        if self.cap is not None:
            return
        if not self.load_camera_modules():
            return
        self.cap = self.cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cap = None
            messagebox.showerror("B-Goal Camera", "Could not open the camera.")
            return
        MEDIA_DIR.mkdir(exist_ok=True)
        self.camera_status_var.set("Camera live")
        self.update_camera_frame()

    def update_camera_frame(self):
        if self.cap is None:
            return
        ok, frame = self.cap.read()
        if not ok:
            self.camera_status_var.set("Camera frame failed")
            self.after(250, self.update_camera_frame)
            return

        self.last_frame = frame
        if self.recording and self.video_writer:
            self.video_writer.write(frame)

        frame_rgb = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2RGB)
        image = self.image_module.fromarray(frame_rgb)
        image.thumbnail((900, 470))
        self.camera_photo = self.image_tk_module.PhotoImage(image=image)
        self.camera_view.configure(image=self.camera_photo, text="")
        self.after(33, self.update_camera_frame)

    def capture_snapshot(self):
        if self.last_frame is None:
            messagebox.showwarning("B-Goal Camera", "Start the camera first.")
            return
        MEDIA_DIR.mkdir(exist_ok=True)
        path = MEDIA_DIR / f"snapshot_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        self.cv2.imwrite(str(path), self.last_frame)
        self.camera_status_var.set(f"Saved {path.name}")

    def start_recording(self):
        if self.last_frame is None:
            messagebox.showwarning("B-Goal Camera", "Start the camera first.")
            return
        if self.recording:
            return
        MEDIA_DIR.mkdir(exist_ok=True)
        height, width = self.last_frame.shape[:2]
        path = MEDIA_DIR / f"training_{time.strftime('%Y%m%d_%H%M%S')}.avi"
        fourcc = self.cv2.VideoWriter_fourcc(*"XVID")
        self.video_writer = self.cv2.VideoWriter(str(path), fourcc, 20.0, (width, height))
        self.recording = True
        self.recording_path = path
        self.camera_status_var.set("Recording...")

    def stop_recording(self):
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
        if self.recording:
            self.recording = False
            self.camera_status_var.set(f"Saved {self.recording_path.name}")

    def stop_camera(self):
        self.stop_recording()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.camera_view.configure(image="", text="Camera preview")
        self.camera_status_var.set("Camera stopped")

    def on_close(self):
        self.stop_camera()
        self.destroy()


if __name__ == "__main__":
    app = BGoalApp()
    app.mainloop()
