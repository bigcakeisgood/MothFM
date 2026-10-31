# MothFM

A small desktop internet radio player built with Python and Tkinter.

## Features

- Play internet radio from direct HTTP(S) stream URLs
- Save and remove favorite stations
- Double-click a favorite to tune in
- Stop and volume controls
- Favorites stored locally in `~/.mothfm/favorites.json`

## Requirements

- Python 3.10+
- Tkinter (on some Linux distributions, install `python3-tk`)
- VLC media player installed on your system
- Python VLC binding

## Run

1. Install VLC from https://www.videolan.org/vlc/.
2. Install the Python dependency: `python -m pip install -r requirements.txt`
3. Start the app: `python main.py`
4. Enter a station name and a direct stream URL, then choose **Play stream**. Use **Add favorite** to save it.

MothFM expects a direct audio stream URL, not a station-directory webpage. Some streams may require particular VLC builds or network configuration.

## Next steps

The first version is intentionally small. A searchable station directory and a more polished listening view are natural next steps.
