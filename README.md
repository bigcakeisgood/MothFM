# MothFM

A small desktop internet radio player built with Python and Tkinter, with live station discovery powered by the community-maintained Radio Browser directory.

## Features

- Search radio stations by name, country, or genre/tag
- Browse station country, tags, and reported bitrate in search results
- Double-click a result or select it and press **Play selected** to tune in
- Save stations to a local favorites list and play them later
- Stop playback and adjust volume
- Favorites stored locally in `~/.mothfm/favorites.json`
- Station searches run in the background so the interface stays responsive

## Requirements

- Python 3.10+
- Tkinter (on some Linux distributions, install `python3-tk`)
- VLC media player installed on your system
- Python VLC binding

## Run

1. Install VLC from https://www.videolan.org/vlc/.
2. Install the Python dependency: `python -m pip install -r requirements.txt`
3. Start the app: `python main.py`
4. Search by station name, country, and/or genre. Double-click a result to listen.

MothFM uses the Radio Browser API for station discovery. Directory availability depends on that community service and an internet connection. Some station streams may be offline, geo-restricted, or unsupported by the installed VLC build.

## Project direction

Next up: richer station browsing, better playback feedback, and a more polished listening experience.
