import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading
import os
import sys
import time
import re
import json

# =====================================================================
# HIER TRÄGST DU DEINE BITCOIN-WALLET EIN
BTC_WALLET = "DEINE_BTC_WALLET_HIER" # <-- BITTE EINTRAGEN
# =====================================================================

TEXTS = {
    "de": {
        "title": "Hörspiel-Rekorder",
        "step1": " SCHRITT 1: AUFNAHME ",
        "step2": " SCHRITT 2: ZUSCHNEIDEN & STILLE EINFÜGEN ",
        "lbl_title": "1. Titel des Hörspiels:",
        "ph_title": "z.B. Findet Nemo",
        "lbl_len": "2. Länge in Minuten:",
        "lbl_save": "Speichern unter:",
        "btn_change": "Ändern...",
        "btn_start": "Aufnahme starten",
        "btn_stop": "Aufnahme beenden",
        "btn_crop": "Datei zuschneiden",
        "btn_refresh": "Liste aktualisieren",
        "lbl_select": "Wähle eine aufgenommene Datei aus dem Ordner:",
        "status_ready": "Bereit",
        "status_wait": "Warte auf Ton...",
        "status_rec": "AUFNAHME LÄUFT...",
        "status_crop": "Schneide zu...",
        "status_done": "✅ FERTIG! Datei gespeichert & Temp gelöscht.",
        "msg_warn": "Bitte wähle eine Datei aus der Liste aus.",
        "msg_err_title": "Fehler",
        "msg_err_ffmpeg": "FEHLER: FFmpeg nicht gefunden.",
        "msg_play": "BITTE JETZT IN DER SPOTIFY-APP AUF PLAY DRÜCKEN!",
        "msg_timeout": "\nZeit abgelaufen! Beende Aufnahme...",
        "msg_stopping": "\nBeende Aufnahme...",
        "msg_success": "Die Datei wurde fertig zugeschnitten und gespeichert:",
        "msg_temp_del": "Die temporäre Datei wurde erfolgreich entfernt.",
        "btn_donate": "₿ Spenden (BTC)",
        "donate_title": "Unterstütze dieses Projekt",
        "donate_msg": "Wenn dir dieses Tool hilft, kannst du mich mit Bitcoin unterstützen:\n\n(Bitte kopieren)"
    },
    "en": {
        "title": "Radio Play Recorder",
        "step1": " STEP 1: RECORDING ",
        "step2": " STEP 2: CROP & ADD SILENCE ",
        "lbl_title": "1. Title of the play:",
        "ph_title": "e.g. Finding Nemo",
        "lbl_len": "2. Length in minutes:",
        "lbl_save": "Save to:",
        "btn_change": "Change...",
        "btn_start": "Start Recording",
        "btn_stop": "Stop Recording",
        "btn_crop": "Crop File",
        "btn_refresh": "Refresh List",
        "lbl_select": "Select a recorded file from the folder:",
        "status_ready": "Ready",
        "status_wait": "Waiting for sound...",
        "status_rec": "RECORDING...",
        "status_crop": "Cropping...",
        "status_done": "✅ DONE! File saved & temp deleted.",
        "msg_warn": "Please select a file from the list.",
        "msg_err_title": "Error",
        "msg_err_ffmpeg": "ERROR: FFmpeg not found.",
        "msg_play": "PLEASE PRESS PLAY IN THE SPOTIFY APP NOW!",
        "msg_timeout": "\nTime is up! Stopping recording...",
        "msg_stopping": "\nStopping recording...",
        "msg_success": "The file was successfully cropped and saved:",
        "msg_temp_del": "The temporary file was successfully removed.",
        "btn_donate": "₿ Donate (BTC)",
        "donate_title": "Support this project",
        "donate_msg": "If this tool helps you, you can support me with Bitcoin:\n\n(Please copy)"
    }
}

class SpotifyAutoRecorderApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("700x780")
        
        self.config_file = os.path.join(os.path.expanduser("~"), ".hoerspiel_rekorder_config.json")
        self.save_path = tk.StringVar(value=self.load_config())
        
        self.current_process = None
        self.is_recording = False
        self.timer_thread = None
        self.length_min = 60
        
        self.current_lang = "de"
        self.texts = TEXTS[self.current_lang]
        
        self.create_widgets()
        self.update_ui_language()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    return data.get("save_path", os.path.expanduser("~/Music"))
        except:
            pass
        return os.path.expanduser("~/Music")

    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump({"save_path": self.save_path.get()}, f)
        except:
            pass

    def create_widgets(self):
        top_bar = tk.Frame(self.root)
        top_bar.pack(fill=tk.X, padx=10, pady=5)
        
        self.lang_combo = ttk.Combobox(top_bar, values=["Deutsch", "English"], state="readonly", width=10)
        self.lang_combo.set("Deutsch")
        self.lang_combo.pack(side=tk.RIGHT)
        self.lang_combo.bind("<<ComboboxSelected>>", self.change_language)

        self.frame1 = tk.LabelFrame(self.root, font=("Arial", 11, "bold"), fg="#1DB954")
        self.frame1.pack(fill=tk.X, padx=15, pady=10)

        self.lbl_title = tk.Label(self.frame1, font=("Arial", 10))
        self.lbl_title.pack(pady=(10, 2), anchor="w", padx=10)
        
        self.title_entry = tk.Entry(self.frame1, width=75, font=("Arial", 10))
        self.title_entry.pack(pady=2, padx=10, fill=tk.X)
        self.title_entry.insert(0, "z.B. Findet Nemo")
        self.title_entry.config(fg="gray")
        self.title_entry.bind("<FocusIn>", self.on_entry_click)
        self.title_entry.bind("<FocusOut>", self.on_focusout)

        self.length_frame = tk.Frame(self.frame1)
        self.length_frame.pack(pady=5, fill=tk.X, padx=10)
        self.lbl_len = tk.Label(self.length_frame, font=("Arial", 10))
        self.lbl_len.pack(side=tk.LEFT)
        self.length_entry = tk.Entry(self.length_frame, width=10, font=("Arial", 10))
        self.length_entry.pack(side=tk.LEFT, padx=10)
        self.length_entry.insert(0, "60")

        self.frame_path = tk.Frame(self.frame1)
        self.frame_path.pack(pady=5, fill=tk.X, padx=10)
        self.lbl_save = tk.Label(self.frame_path, font=("Arial", 10))
        self.lbl_save.pack(side=tk.LEFT)
        tk.Entry(self.frame_path, textvariable=self.save_path, width=45, state='readonly').pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.btn_change = tk.Button(self.frame_path, command=self.select_folder)
        self.btn_change.pack(side=tk.LEFT)

        self.btn_frame1 = tk.Frame(self.frame1)
        self.btn_frame1.pack(pady=10)
        
        self.start_btn = tk.Button(self.btn_frame1, command=self.start_recording, bg="#1DB954", fg="white",
                                      font=("Arial", 12, "bold"), width=20, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(self.btn_frame1, command=self.force_stop, bg="#e74c3c", fg="white",
                                      font=("Arial", 12, "bold"), width=20, cursor="hand2", state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=10)

        self.frame2 = tk.LabelFrame(self.root, font=("Arial", 11, "bold"), fg="#3498db")
        self.frame2.pack(fill=tk.X, padx=15, pady=10)

        self.lbl_select = tk.Label(self.frame2, font=("Arial", 10))
        self.lbl_select.pack(pady=(10, 2), anchor="w", padx=10)
        
        self.file_listbox = tk.Listbox(self.frame2, width=75, height=5, font=("Arial", 10))
        self.file_listbox.pack(pady=5, padx=10, fill=tk.X)
        
        self.btn_frame2 = tk.Frame(self.frame2)
        self.btn_frame2.pack(pady=10)
        
        self.btn_refresh = tk.Button(self.btn_frame2, command=self.refresh_file_list, width=15)
        self.btn_refresh.pack(side=tk.LEFT, padx=10)
        
        self.crop_btn = tk.Button(self.btn_frame2, command=self.start_cropping, bg="#3498db", fg="white",
                  font=("Arial", 11, "bold"), width=25, cursor="hand2")
        self.crop_btn.pack(side=tk.LEFT, padx=10)

        self.status_label = tk.Label(self.root, fg="gray", font=("Arial", 11, "bold"))
        self.status_label.pack(pady=5)

        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text = tk.Text(log_frame, height=8, width=75, state='disabled', bg="#f4f4f4", font=("Consolas", 9), yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        bottom_bar = tk.Frame(self.root)
        bottom_bar.pack(fill=tk.X, padx=20, pady=(0, 10))
        self.donate_btn = tk.Button(bottom_bar, command=self.show_donate, bg="#f39c12", fg="white", font=("Arial", 10, "bold"))
        self.donate_btn.pack(side=tk.RIGHT)

        self.refresh_file_list()

    def change_language(self, event):
        selection = self.lang_combo.get()
        self.current_lang = "de" if selection == "Deutsch" else "en"
        self.texts = TEXTS[self.current_lang]
        self.update_ui_language()

    def update_ui_language(self):
        t = self.texts
        self.root.title(t["title"])
        self.frame1.config(text=t["step1"])
        self.frame2.config(text=t["step2"])
        self.lbl_title.config(text=t["lbl_title"])
        self.lbl_len.config(text=t["lbl_len"])
        self.lbl_save.config(text=t["lbl_save"])
        self.btn_change.config(text=t["btn_change"])
        self.start_btn.config(text=t["btn_start"])
        self.stop_btn.config(text=t["btn_stop"])
        self.btn_refresh.config(text=t["btn_refresh"])
        self.crop_btn.config(text=t["btn_crop"])
        self.lbl_select.config(text=t["lbl_select"])
        self.donate_btn.config(text=t["btn_donate"])
        
        if not self.is_recording:
            self.status_label.config(text=t["status_ready"])
            
        if self.title_entry.get() in ["z.B. Findet Nemo", "e.g. Finding Nemo"]:
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, t["ph_title"])
            self.title_entry.config(fg="gray")

    def on_entry_click(self, event):
        if self.title_entry.get() in [TEXTS["de"]["ph_title"], TEXTS["en"]["ph_title"]]:
            self.title_entry.delete(0, tk.END)
            self.title_entry.config(fg="black")

    def on_focusout(self, event):
        if self.title_entry.get() == "":
            self.title_entry.insert(0, self.texts["ph_title"])
            self.title_entry.config(fg="gray")

    def get_real_title(self):
        val = self.title_entry.get().strip()
        if val in [TEXTS["de"]["ph_title"], TEXTS["en"]["ph_title"]]:
            return ""
        return val

    def show_donate(self):
        don_win = tk.Toplevel(self.root)
        don_win.title(self.texts["donate_title"])
        don_win.geometry("500x200")
        
        tk.Label(don_win, text=self.texts["donate_msg"], font=("Arial", 10)).pack(pady=10)
        
        wallet_entry = tk.Entry(don_win, width=50, font=("Consolas", 10), justify="center")
        wallet_entry.insert(0, BTC_WALLET)
        wallet_entry.config(state="readonly")
        wallet_entry.pack(pady=5)
        
        def copy_wallet():
            self.root.clipboard_clear()
            self.root.clipboard_append(BTC_WALLET)
            messagebox.showinfo(self.texts["donate_title"], "Wallet copied!")

        tk.Button(don_win, text="Copy to Clipboard", command=copy_wallet, bg="#f39c12", fg="white", font=("Arial", 10, "bold")).pack(pady=10)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Wählen Sie den Speicherort")
        if folder:
            self.save_path.set(folder)
            self.save_config()
            self.refresh_file_list()

    def log(self, message):
        current_pos = self.log_text.yview()
        auto_scroll = current_pos[1] == 1.0
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        if auto_scroll:
            self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def refresh_file_list(self):
        self.file_listbox.delete(0, tk.END)
        save_dir = self.save_path.get()
        if os.path.exists(save_dir):
            files = [f for f in os.listdir(save_dir) if f.endswith(".mp3")]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(save_dir, x)), reverse=True)
            for file in files:
                self.file_listbox.insert(tk.END, file)

    # ==========================================
    # HIER IST DER FFMPEG-PFAD FÜR DIE EXE
    # ==========================================
    def get_ffmpeg_path(self):
        if getattr(sys, 'frozen', False):
            # Wir laufen als .exe
            base_path = sys._MEIPASS
        else:
            # Wir laufen als .py Skript
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")
        if not os.path.exists(ffmpeg_path):
            # Fallback, falls es nicht in der EXE gefunden wird
            ffmpeg_path = os.path.join(os.path.expanduser("~"), ".spotdl", "ffmpeg.exe")
        return ffmpeg_path

    def start_recording(self):
        if self.is_recording: return
        title = self.get_real_title()
        if not title:
            messagebox.showwarning("Hinweis", "Bitte gib einen Titel ein." if self.current_lang == "de" else "Please enter a title.")
            return
            
        try:
            self.length_min = int(self.length_entry.get().strip())
            self.max_duration = (self.length_min * 60) + 20
        except: 
            messagebox.showwarning("Hinweis", "Ungültige Länge." if self.current_lang == "de" else "Invalid length.")
            return

        save_dir = self.save_path.get()
        if not os.path.exists(save_dir): os.makedirs(save_dir)

        safe_title = re.sub(r'[\\/*?:"<>|]', '', title)
        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.temp_output_file = os.path.join(save_dir, f"tmp_{safe_title}_{timestamp}.mp3")

        # HIER WIRD DER PFAD GEHOLT
        ffmpeg_path = self.get_ffmpeg_path()

        cmd = [ffmpeg_path, "-y", "-f", "dshow", "-i", "audio=CABLE Output (VB-Audio Virtual Cable)", "-acodec", "libmp3lame", "-b:a", "192k", self.temp_output_file]

        self.log(f"Starte Aufnahme: {os.path.basename(self.temp_output_file)}")
        
        try:
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
        except FileNotFoundError:
            self.log(self.texts["msg_err_ffmpeg"])
            return

        self.is_recording = True
        self.start_btn.config(state='disabled', text=self.texts["status_rec"])
        self.stop_btn.config(state='normal')
        self.status_label.config(text=self.texts["status_wait"], fg="orange")
        time.sleep(2)
        self.log(self.texts["msg_play"])
        threading.Thread(target=self.monitor_audio, args=(self.current_process,), daemon=True).start()

    def monitor_audio(self, process):
        started = False
        for line in process.stdout:
            if line.strip():
                self.log(line.strip())
                if "size=" in line and not started:
                    started = True
                    self.status_label.config(text=self.texts["status_rec"], fg="red")
                    self.log(f"\n>>> OK. <<<\n")
                    self.timer_thread = threading.Timer(self.max_duration, self.auto_stop_timer)
                    self.timer_thread.start()
        process.wait()
        if self.is_recording:
            self.log("\nDone.")
            self.is_recording = False
            self.root.after(0, self.reset_recording_ui)
            self.root.after(0, self.refresh_file_list)

    def auto_stop_timer(self):
        if self.is_recording:
            self.log(self.texts["msg_timeout"])
            self.force_stop()

    def force_stop(self):
        if self.timer_thread: self.timer_thread.cancel()
        if self.current_process:
            self.log(self.texts["msg_stopping"])
            self.current_process.terminate()
            self.is_recording = False
            self.root.after(0, self.reset_recording_ui)
            self.root.after(0, self.refresh_file_list)

    def reset_recording_ui(self):
        self.start_btn.config(state='normal', text=self.texts["btn_start"])
        self.stop_btn.config(state='disabled')
        self.status_label.config(text=self.texts["status_ready"], fg="gray")

    def start_cropping(self):
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Hinweis", self.texts["msg_warn"])
            return
        
        filename = self.file_listbox.get(selection[0])
        file_path = os.path.join(self.save_path.get(), filename)
        if not os.path.exists(file_path): return

        final_name = filename.replace("tmp_", "")
        final_path = os.path.join(self.save_path.get(), final_name)

        self.status_label.config(text=self.texts["status_crop"], fg="blue")
        self.log(f"Schneide '{filename}' zu...")
        self.crop_btn.config(state='disabled', text=self.texts["status_crop"])
        
        try: length_min = int(self.length_entry.get().strip())
        except: length_min = 60

        threading.Thread(target=self.crop_audio_task, args=(file_path, final_path, length_min), daemon=True).start()

    def crop_audio_task(self, input_file, output_file, length_min):
        # HIER WIRD DER PFAD GEHOLT
        ffmpeg_path = self.get_ffmpeg_path()

        total_duration = (length_min * 60) + 6

        cmd = [
            ffmpeg_path, "-y",
            "-ss", "00:00:02.0",
            "-t", str(total_duration),
            "-i", input_file,
            "-af", "adelay=3000|3000",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            output_file
        ]

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
            process.wait()

            if process.returncode == 0:
                self.root.after(0, lambda: self.log("Zuschneiden erfolgreich!"))
                
                if os.path.exists(input_file):
                    try: os.remove(input_file)
                    except: pass

                self.root.after(0, lambda: self.crop_success(output_file))
            else:
                self.root.after(0, lambda: self.log("Fehler beim Zuschneiden."))
                self.root.after(0, self.reset_crop_ui)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"Fehler: {e}"))
            self.root.after(0, self.reset_crop_ui)

    def reset_crop_ui(self):
        self.crop_btn.config(state='normal', text=self.texts["btn_crop"])
        self.status_label.config(text=self.texts["status_ready"], fg="gray")
        self.refresh_file_list()

    def crop_success(self, final_file):
        self.reset_crop_ui()
        self.status_label.config(text=self.texts["status_done"], fg="green")
        self.log("\n" + "="*50)
        self.log(f"   >>> {self.texts['status_done']} <<<")
        self.log("="*50 + "\n")
        
        msg = f"{self.texts['msg_success']}\n\n{final_file}\n\n{self.texts['msg_temp_del']}"
        messagebox.showinfo("Erfolg" if self.current_lang == "de" else "Success", msg)

    def on_closing(self):
        if self.is_recording:
            if messagebox.askyesno("Abbrechen", "Die Aufnahme läuft noch. Beenden?" if self.current_lang == "de" else "Recording is active. Quit?"):
                if self.timer_thread: self.timer_thread.cancel()
                if self.current_process: self.current_process.terminate()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    try:
        import ctypes
        if sys.executable.endswith("python.exe"):
            pythonw = sys.executable.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw):
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
                subprocess.Popen([pythonw, sys.argv[0]])
                sys.exit(0)
    except Exception:
        pass

    root = tk.Tk()
    app = SpotifyAutoRecorderApp(root)
    root.mainloop()