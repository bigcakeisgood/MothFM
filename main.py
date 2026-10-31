"""MothFM — a desktop internet radio player with live station discovery.

Requires Python 3.10+, VLC media player, and python-vlc.
Run with: python main.py
"""
from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

APP_DIR = Path.home() / ".mothfm"
FAVORITES_FILE = APP_DIR / "favorites.json"
RADIO_API = "https://de1.api.radio-browser.info/json/stations/search"
USER_AGENT = "MothFM/0.2 (desktop internet radio player)"


class MothFM:
    BG = "#171923"
    PANEL = "#222635"
    FG = "#f2eee8"
    MUTED = "#a6adbb"
    ACCENT = "#c7a6ff"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MothFM")
        self.root.geometry("850x700")
        self.root.minsize(680, 580)
        self.root.configure(bg=self.BG)
        self.player = None
        self.vlc = None
        self.current_station: dict | None = None
        self.favorites = self._load_favorites()
        self.search_queue: queue.Queue = queue.Queue()
        self.searching = False
        self.results: list[dict] = []
        self._build_ui()
        self._init_audio()
        self.root.after(150, self._process_search_queue)

    def _button(self, parent, text, command, primary=False):
        return tk.Button(
            parent, text=text, command=command,
            bg=self.ACCENT if primary else self.PANEL,
            fg="#171923" if primary else self.FG,
            activebackground="#d7c2ff" if primary else "#30374a",
            activeforeground="#171923" if primary else self.FG,
            relief="flat", padx=13, pady=8,
            font=("TkDefaultFont", 9, "bold" if primary else "normal"),
            cursor="hand2",
        )

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Moth.Treeview", background=self.PANEL, foreground=self.FG,
            fieldbackground=self.PANEL, rowheight=27, borderwidth=0,
        )
        style.configure(
            "Moth.Treeview.Heading", background=self.BG, foreground=self.MUTED,
            relief="flat", font=("TkDefaultFont", 8, "bold"),
        )
        style.map("Moth.Treeview", background=[("selected", "#51466b")])

        outer = tk.Frame(self.root, bg=self.BG, padx=25, pady=19)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x")
        tk.Label(header, text="☾  MothFM", bg=self.BG, fg=self.FG,
                 font=("TkDefaultFont", 24, "bold")).pack(side="left")
        tk.Label(header, text="INTERNET RADIO", bg=self.BG, fg=self.MUTED,
                 font=("TkDefaultFont", 9, "bold")).pack(side="right", pady=(12, 0))
        tk.Label(outer, text="A little night music, from everywhere.",
                 bg=self.BG, fg=self.MUTED).pack(anchor="w", pady=(3, 14))

        now = tk.Frame(outer, bg=self.PANEL, padx=15, pady=12)
        now.pack(fill="x")
        tk.Label(now, text="NOW TUNED TO", bg=self.PANEL, fg=self.ACCENT,
                 font=("TkDefaultFont", 8, "bold")).pack(anchor="w")
        self.station_label = tk.Label(now, text="Nothing playing", bg=self.PANEL,
                                      fg=self.FG, font=("TkDefaultFont", 17, "bold"),
                                      anchor="w")
        self.station_label.pack(fill="x", pady=(4, 1))
        self.status_label = tk.Label(now, text="Search the airwaves to find a station.",
                                     bg=self.PANEL, fg=self.MUTED, anchor="w")
        self.status_label.pack(fill="x")

        controls = tk.Frame(outer, bg=self.BG)
        controls.pack(fill="x", pady=10)
        self.play_button = self._button(controls, "▶  Play", self.play, True)
        self.play_button.pack(side="left")
        self._button(controls, "■  Stop", self.stop).pack(side="left", padx=(7, 0))
        tk.Label(controls, text="VOLUME", bg=self.BG, fg=self.MUTED,
                 font=("TkDefaultFont", 8, "bold")).pack(side="left", padx=(18, 7))
        self.volume = tk.IntVar(value=75)
        ttk.Scale(controls, from_=0, to=100, variable=self.volume,
                  command=self.set_volume, length=115).pack(side="left")

        tk.Label(outer, text="DISCOVER STATIONS", bg=self.BG, fg=self.ACCENT,
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(7, 7))
        search = tk.Frame(outer, bg=self.BG)
        search.pack(fill="x")
        self.search_name = self._entry(search, "Station name")
        self.search_name.pack(side="left", fill="x", expand=True, ipady=8)
        self.search_country = self._entry(search, "Country")
        self.search_country.pack(side="left", fill="x", expand=True, ipady=8, padx=(7, 0))
        self.search_tag = self._entry(search, "Genre / tag")
        self.search_tag.pack(side="left", fill="x", expand=True, ipady=8, padx=(7, 0))
        self.search_button = self._button(search, "Search", self.search_stations, True)
        self.search_button.pack(side="left", padx=(7, 0))
        self.search_name.bind("<Return>", lambda _e: self.search_stations())
        self.search_country.bind("<Return>", lambda _e: self.search_stations())
        self.search_tag.bind("<Return>", lambda _e: self.search_stations())

        self.search_status = tk.Label(outer, text="Search by station, country, or genre.",
                                      bg=self.BG, fg=self.MUTED, anchor="w")
        self.search_status.pack(fill="x", pady=(6, 5))

        # Keep station actions above the results pane so they remain visible
        # on short laptop and small-monitor screens.
        actions = tk.Frame(outer, bg=self.BG)
        actions.pack(fill="x", pady=(2, 5))
        self._button(actions, "▶  Play selected", self.play_search_result, True).pack(side="left")
        self._button(actions, "♥  Add selected station to favorites", self.add_selected_favorite).pack(side="left", padx=7)

        results_frame = tk.Frame(outer, bg=self.PANEL)
        results_frame.pack(fill="both", expand=True)
        columns = ("name", "country", "tags", "bitrate")
        self.results_list = ttk.Treeview(results_frame, columns=columns,
                                         show="headings", style="Moth.Treeview")
        for col, label, width in (
            ("name", "STATION", 230), ("country", "COUNTRY", 130),
            ("tags", "GENRE / TAGS", 260), ("bitrate", "KBPS", 65),
        ):
            self.results_list.heading(col, text=label)
            self.results_list.column(col, width=width, minwidth=55,
                                     anchor="w", stretch=col in ("name", "tags"))
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical",
                                  command=self.results_list.yview)
        self.results_list.configure(yscrollcommand=scrollbar.set)
        self.results_list.pack(side="left", fill="both", expand=True, padx=(7, 0), pady=7)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=7)
        self.results_list.bind("<Double-Button-1>", self.play_search_result)
        self.results_list.bind("<<TreeviewSelect>>", self.select_search_result)

        tk.Label(outer, text="YOUR FAVORITES", bg=self.BG, fg=self.ACCENT,
                 font=("TkDefaultFont", 9, "bold")).pack(anchor="w", pady=(9, 5))
        fav_frame = tk.Frame(outer, bg=self.PANEL)
        fav_frame.pack(fill="x")
        self.station_list = tk.Listbox(
            fav_frame, bg=self.PANEL, fg=self.FG, selectbackground="#51466b",
            selectforeground=self.FG, relief="flat", borderwidth=0,
            highlightthickness=0, activestyle="none", font=("TkDefaultFont", 9), height=3,
        )
        self.station_list.pack(side="left", fill="both", expand=True, padx=7, pady=5)
        self.station_list.bind("<Double-Button-1>", self.play_favorite)
        self._button(fav_frame, "Remove", self.remove_favorite).pack(side="right", padx=7)
        self._refresh_favorites()

        tk.Label(outer, text="Powered by the community-maintained Radio Browser directory.",
                 bg=self.BG, fg=self.MUTED, font=("TkDefaultFont", 8)).pack(anchor="w", pady=(8, 0))

    def _entry(self, parent, placeholder):
        entry = tk.Entry(parent, bg=self.PANEL, fg=self.FG, insertbackground=self.FG,
                         relief="flat", font=("TkDefaultFont", 9))
        entry.insert(0, placeholder)
        entry.bind("<FocusIn>", lambda _e, w=entry, p=placeholder:
                   w.delete(0, "end") if w.get() == p else None)
        return entry

    def _init_audio(self) -> None:
        try:
            import vlc  # type: ignore
            self.vlc = vlc
            self.player = vlc.Instance("--no-video").media_player_new()
            self.player.audio_set_volume(self.volume.get())
            self.status_label.config(text="Audio engine ready. Find something good.")
        except (ImportError, OSError) as exc:
            self.status_label.config(text="Audio engine unavailable — install VLC and python-vlc.")
            self.play_button.config(state="disabled")
            self._audio_error = str(exc)

    def search_stations(self) -> None:
        if self.searching:
            return
        params = {
            "name": self.search_name.get().strip(),
            "country": self.search_country.get().strip(),
            "tag": self.search_tag.get().strip(),
            "limit": 80, "order": "votes", "reverse": "true", "hidebroken": "true",
        }
        params = {key: value for key, value in params.items()
                  if value and value not in ("Station name", "Country", "Genre / tag")}
        if not any(key in params for key in ("name", "country", "tag")):
            messagebox.showinfo("Find a station", "Enter a station name, country, or genre to search.")
            return
        self.searching = True
        self.search_button.config(state="disabled")
        self.search_status.config(text="Listening across the airwaves…")
        threading.Thread(target=self._search_worker, args=(params,), daemon=True).start()

    def _search_worker(self, params: dict) -> None:
        try:
            url = RADIO_API + "?" + urlencode(params)
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urlopen(request, timeout=15) as response:
                data = json.loads(response.read().decode("utf-8"))
            self.search_queue.put(("results", data))
        except (URLError, TimeoutError, OSError, ValueError) as exc:
            self.search_queue.put(("error", str(exc)))

    def _process_search_queue(self) -> None:
        try:
            while True:
                kind, payload = self.search_queue.get_nowait()
                self.searching = False
                self.search_button.config(state="normal")
                if kind == "error":
                    self.search_status.config(text="Search failed. Check your connection and try again.")
                    messagebox.showerror("Station search", f"Could not reach Radio Browser.\n\n{payload}")
                else:
                    self.results = [s for s in payload if s.get("url_resolved") or s.get("url")]
                    self.results_list.delete(*self.results_list.get_children())
                    for index, station in enumerate(self.results):
                        self.results_list.insert("", "end", iid=str(index), values=(
                            station.get("name") or "Unknown station",
                            station.get("country") or "—",
                            (station.get("tags") or "—")[:65],
                            station.get("bitrate") or "—",
                        ))
                    count = len(self.results)
                    self.search_status.config(
                        text=f"{count} station{'s' if count != 1 else ''} found. Double-click one to listen."
                        if count else "No stations found. Try a broader search."
                    )
        except queue.Empty:
            pass
        self.root.after(150, self._process_search_queue)

    def _selected_search_station(self) -> dict | None:
        selection = self.results_list.selection()
        if not selection:
            return None
        try:
            return self.results[int(selection[0])]
        except (ValueError, IndexError):
            return None

    def select_search_result(self, _event=None) -> None:
        station = self._selected_search_station()
        if station:
            self.search_status.config(text=f"Selected: {station.get('name', 'Unknown station')}")

    def play_search_result(self, _event=None) -> None:
        station = self._selected_search_station()
        if station:
            self.play_station(station)

    def play_station(self, station: dict) -> None:
        name = station.get("name") or "Unknown station"
        url = station.get("url_resolved") or station.get("url")
        if not url:
            messagebox.showerror("Stream unavailable", "This station has no playable stream URL.")
            return
        if not self.player:
            messagebox.showerror("Audio unavailable",
                                 "Install VLC media player and python-vlc to play streams.")
            return
        try:
            media = self.vlc.Instance("--no-video").media_new(url)
            self.player.set_media(media)
            self.player.play()
            self.player.audio_set_volume(self.volume.get())
            self.current_station = station
            self.station_label.config(text=name)
            country = station.get("country") or "Unknown country"
            tags = station.get("tags") or "No genre tags"
            self.status_label.config(text=f"{country}  •  {tags[:80]}  •  Connecting…")
            self.root.after(1500, self._update_playback_status)
        except Exception as exc:
            messagebox.showerror("Playback error", str(exc))

    def play(self) -> None:
        station = self._selected_search_station()
        if station:
            self.play_station(station)
            return
        messagebox.showinfo("Choose a station", "Select a station from search results or your favorites.")

    def _update_playback_status(self) -> None:
        if self.player and self.player.is_playing():
            self.status_label.config(text="Streaming live  •  Enjoy the frequencies.")
        elif self.player and self.current_station:
            self.status_label.config(text="Connecting or waiting for the stream…")

    def stop(self) -> None:
        if self.player:
            self.player.stop()
        self.current_station = None
        self.status_label.config(text="Stopped.")
        self.station_label.config(text="Nothing playing")

    def set_volume(self, _value: str = "") -> None:
        if self.player:
            self.player.audio_set_volume(self.volume.get())

    def add_selected_favorite(self) -> None:
        station = self._selected_search_station()
        if not station:
            messagebox.showinfo("Add favorite", "Select a station from the search results first.")
            return
        self._add_favorite(station)

    def _add_favorite(self, station: dict) -> None:
        item = {
            "name": station.get("name") or "Unknown station",
            "url": station.get("url_resolved") or station.get("url") or "",
            "country": station.get("country") or "",
            "tags": station.get("tags") or "",
            "stationuuid": station.get("stationuuid") or "",
        }
        if not item["url"]:
            messagebox.showerror("Favorite", "This station has no stream URL.")
            return
        if not any(f.get("url") == item["url"] for f in self.favorites):
            self.favorites.append(item)
            self._save_favorites()
            self._refresh_favorites()
            self.search_status.config(text=f"Saved {item['name']} to your favorites.")

    def play_favorite(self, _event=None) -> None:
        selection = self.station_list.curselection()
        if selection:
            self.play_station(self.favorites[selection[0]])

    def remove_favorite(self) -> None:
        selection = self.station_list.curselection()
        if selection:
            del self.favorites[selection[0]]
            self._save_favorites()
            self._refresh_favorites()

    def _load_favorites(self) -> list[dict]:
        try:
            data = json.loads(FAVORITES_FILE.read_text(encoding="utf-8"))
            return [item for item in data if isinstance(item, dict) and "name" in item and "url" in item]
        except (OSError, json.JSONDecodeError, TypeError):
            return []

    def _save_favorites(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        FAVORITES_FILE.write_text(json.dumps(self.favorites, indent=2), encoding="utf-8")

    def _refresh_favorites(self) -> None:
        self.station_list.delete(0, "end")
        for station in self.favorites:
            place = station.get("country") or "—"
            self.station_list.insert("end", f"  {station['name']}   ·   {place}")


def main() -> None:
    root = tk.Tk()
    MothFM(root)
    root.mainloop()


if __name__ == "__main__":
    main()
