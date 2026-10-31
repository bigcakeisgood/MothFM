"""MothFM — a small desktop internet radio player.

Requires Python 3.10+, VLC media player, and the optional python-vlc package.
Run with: python main.py
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

APP_DIR = Path.home() / ".mothfm"
FAVORITES_FILE = APP_DIR / "favorites.json"


class MothFM:
    BG = "#171923"
    PANEL = "#222635"
    FG = "#f2eee8"
    MUTED = "#a6adbb"
    ACCENT = "#c7a6ff"
    GREEN = "#a6d9b5"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MothFM")
        self.root.geometry("620x520")
        self.root.minsize(500, 440)
        self.root.configure(bg=self.BG)

        self.player = None
        self.vlc = None
        self.current_station: dict[str, str] | None = None
        self.favorites = self._load_favorites()

        self._build_ui()
        self._init_audio()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Moth.Vertical.TScale",
            background=self.PANEL,
            troughcolor=self.BG,
        )

        outer = tk.Frame(self.root, bg=self.BG, padx=28, pady=22)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x")
        tk.Label(
            header, text="☾  MothFM", bg=self.BG, fg=self.FG,
            font=("TkDefaultFont", 24, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="INTERNET RADIO", bg=self.BG, fg=self.MUTED,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(side="right", pady=(12, 0))

        tk.Label(
            outer, text="A little night music, from everywhere.",
            bg=self.BG, fg=self.MUTED, font=("TkDefaultFont", 10),
        ).pack(anchor="w", pady=(4, 20))

        now = tk.Frame(outer, bg=self.PANEL, padx=18, pady=18)
        now.pack(fill="x")
        tk.Label(
            now, text="NOW TUNED TO", bg=self.PANEL, fg=self.ACCENT,
            font=("TkDefaultFont", 8, "bold"),
        ).pack(anchor="w")
        self.station_label = tk.Label(
            now, text="Nothing playing", bg=self.PANEL, fg=self.FG,
            font=("TkDefaultFont", 18, "bold"), anchor="w",
        )
        self.station_label.pack(fill="x", pady=(7, 2))
        self.status_label = tk.Label(
            now, text="Paste a stream URL below to get started.",
            bg=self.PANEL, fg=self.MUTED, font=("TkDefaultFont", 9), anchor="w",
        )
        self.status_label.pack(fill="x")

        controls = tk.Frame(outer, bg=self.BG)
        controls.pack(fill="x", pady=16)
        self.play_button = tk.Button(
            controls, text="▶  Play stream", command=self.play,
            bg=self.ACCENT, fg="#171923", activebackground="#d7c2ff",
            activeforeground="#171923", relief="flat", padx=18, pady=9,
            font=("TkDefaultFont", 10, "bold"), cursor="hand2",
        )
        self.play_button.pack(side="left")
        tk.Button(
            controls, text="■  Stop", command=self.stop,
            bg=self.PANEL, fg=self.FG, activebackground="#30374a",
            relief="flat", padx=16, pady=9, cursor="hand2",
        ).pack(side="left", padx=(8, 0))
        tk.Label(
            controls, text="VOLUME", bg=self.BG, fg=self.MUTED,
            font=("TkDefaultFont", 8, "bold"),
        ).pack(side="left", padx=(22, 8))
        self.volume = tk.IntVar(value=75)
        ttk.Scale(
            controls, from_=0, to=100, variable=self.volume,
            command=self.set_volume, length=110,
        ).pack(side="left")

        tk.Label(
            outer, text="TUNE IN", bg=self.BG, fg=self.ACCENT,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", pady=(8, 7))
        entry_row = tk.Frame(outer, bg=self.BG)
        entry_row.pack(fill="x")
        self.name_entry = tk.Entry(
            entry_row, bg=self.PANEL, fg=self.FG, insertbackground=self.FG,
            relief="flat", font=("TkDefaultFont", 10),
        )
        self.name_entry.insert(0, "Station name")
        self.name_entry.pack(side="left", fill="x", expand=True, ipady=9, padx=(0, 7))
        self.url_entry = tk.Entry(
            outer, bg=self.PANEL, fg=self.FG, insertbackground=self.FG,
            relief="flat", font=("TkDefaultFont", 10),
        )
        self.url_entry.insert(0, "https://example.com/radio-stream")
        self.url_entry.pack(fill="x", ipady=9, pady=(7, 7))

        tk.Button(
            entry_row, text="Add favorite", command=self.add_favorite,
            bg=self.PANEL, fg=self.FG, activebackground="#30374a",
            relief="flat", padx=12, cursor="hand2",
        ).pack(side="right")

        tk.Label(
            outer, text="YOUR FAVORITES", bg=self.BG, fg=self.ACCENT,
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor="w", pady=(13, 7))
        list_frame = tk.Frame(outer, bg=self.PANEL)
        list_frame.pack(fill="both", expand=True)
        self.station_list = tk.Listbox(
            list_frame, bg=self.PANEL, fg=self.FG, selectbackground="#51466b",
            selectforeground=self.FG, relief="flat", borderwidth=0,
            highlightthickness=0, activestyle="none",
            font=("TkDefaultFont", 10), height=5,
        )
        self.station_list.pack(side="left", fill="both", expand=True, padx=8, pady=7)
        self.station_list.bind("<Double-Button-1>", self.play_selected)
        self._refresh_favorites()

        footer = tk.Frame(outer, bg=self.BG)
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(
            footer, text="Made for the hours between.", bg=self.BG, fg=self.MUTED,
            font=("TkDefaultFont", 8),
        ).pack(side="left")
        tk.Button(
            footer, text="Remove selected", command=self.remove_favorite,
            bg=self.BG, fg=self.MUTED, activebackground=self.BG,
            activeforeground=self.FG, relief="flat", cursor="hand2",
        ).pack(side="right")

    def _init_audio(self) -> None:
        try:
            import vlc  # type: ignore
            self.vlc = vlc
            self.player = vlc.Instance("--no-video").media_player_new()
            self.player.audio_set_volume(self.volume.get())
            self.status_label.config(text="Audio engine ready. Add a stream URL.")
        except (ImportError, OSError) as exc:
            self.status_label.config(
                text="Audio engine unavailable — install VLC and python-vlc."
            )
            self.play_button.config(state="disabled")
            self._audio_error = str(exc)

    def play(self) -> None:
        if not self.player:
            messagebox.showerror(
                "Audio unavailable",
                "MothFM needs VLC media player and the python-vlc package. "
                "See the README for setup instructions.",
            )
            return
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()
        if not name or name == "Station name" or not url or url.startswith("https://example.com"):
            messagebox.showinfo("Tune in", "Enter a station name and a direct stream URL first.")
            return
        if not url.startswith(("http://", "https://")):
            messagebox.showinfo("Invalid URL", "Please enter an http:// or https:// stream URL.")
            return
        try:
            media = self.vlc.Instance("--no-video").media_new(url)
            self.player.set_media(media)
            self.player.play()
            self.player.audio_set_volume(self.volume.get())
            self.current_station = {"name": name, "url": url}
            self.station_label.config(text=name)
            self.status_label.config(text="Connecting to stream…")
            self.root.after(1200, self._update_playback_status)
        except Exception as exc:
            messagebox.showerror("Playback error", str(exc))

    def _update_playback_status(self) -> None:
        if self.player and self.player.is_playing():
            self.status_label.config(text="Streaming live  •  Enjoy the frequencies.")
        elif self.player and self.current_station:
            self.status_label.config(text="Connecting or waiting for the stream…")

    def stop(self) -> None:
        if self.player:
            self.player.stop()
        self.status_label.config(text="Stopped.")
        self.station_label.config(text="Nothing playing")

    def set_volume(self, _value: str = "") -> None:
        if self.player:
            self.player.audio_set_volume(self.volume.get())

    def add_favorite(self) -> None:
        name = self.name_entry.get().strip()
        url = self.url_entry.get().strip()
        if not name or name == "Station name" or not url or url.startswith("https://example.com"):
            messagebox.showinfo("Add favorite", "Enter a station name and stream URL first.")
            return
        if not url.startswith(("http://", "https://")):
            messagebox.showinfo("Invalid URL", "Please enter an http:// or https:// stream URL.")
            return
        station = {"name": name, "url": url}
        if station not in self.favorites:
            self.favorites.append(station)
            self._save_favorites()
            self._refresh_favorites()

    def play_selected(self, _event: tk.Event | None = None) -> None:
        selection = self.station_list.curselection()
        if not selection:
            return
        station = self.favorites[selection[0]]
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, station["name"])
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, station["url"])
        self.play()

    def remove_favorite(self) -> None:
        selection = self.station_list.curselection()
        if not selection:
            return
        del self.favorites[selection[0]]
        self._save_favorites()
        self._refresh_favorites()

    def _load_favorites(self) -> list[dict[str, str]]:
        try:
            data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            return [item for item in data if "name" in item and "url" in item]
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _save_favorites(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        FAVORITES_FILE.write_text(
            json.dumps(self.favorites, indent=2), encoding="utf-8"
        )

    def _refresh_favorites(self) -> None:
        self.station_list.delete(0, "end")
        for station in self.favorites:
            self.station_list.insert("end", f"  {station['name']}")


def main() -> None:
    root = tk.Tk()
    MothFM(root)
    root.mainloop()


if __name__ == "__main__":
    main()
