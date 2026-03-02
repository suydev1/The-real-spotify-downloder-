# Spotify Downloader

A modern, glassmorphism-themed web application for downloading Spotify playlists and YouTube videos, built with Flask and optimized for Replit.

## Features
- **Spotify Playlist Downloader**: Search or paste URLs to download high-quality MP3s (320kbps) with full metadata and album art.
- **YouTube Video Downloader**: Direct video downloads from YouTube URLs.
- **Modern UI**: Beautiful glassmorphism design with real-time progress tracking and background processing.
- **Robust Downloading**: Multi-strategy search (artist + track, lyrics, official audio) with automatic retries for maximum reliability.
- **ZIP Packaging**: Downloads are automatically zipped for easy one-click retrieval.

## Project Structure
- `src/`: Core application source code
  - `web_app.py`: Flask web server and routing logic.
  - `main.py`: Core downloader engine with Spotify and YouTube integration.
  - `utils/`: 
    - `audio_quality.py`: FFmpeg-based audio extraction settings.
    - `termux_helpers.py`: Legacy support for mobile environments.
  - `templates/`: HTML5 templates with glassmorphism CSS.
  - `static/`: PWA manifest, icons, and service workers.
- `requirements.txt`: Python package dependencies.

## Setup
The application requires Spotify API credentials to be set in the Replit Secrets tool:
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

Get credentials at: https://developer.spotify.com/dashboard/

The app will start without these credentials and show a setup banner guiding users through the configuration.

## Running
The workflow installs dependencies from `requirements.txt` and starts the Flask server on port 5000.
