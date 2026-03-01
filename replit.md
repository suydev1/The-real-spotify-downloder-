# Spotify Playlist Downloader - Web App

A web-based Spotify playlist to YouTube downloader. Users paste a Spotify playlist URL and download all tracks as high-quality MP3 files bundled in a zip archive.

## How to Run

The app starts automatically on port 5000 via the "Start application" workflow using `.venv/bin/python3 web_app.py`.

## Required Secrets

Set these in Replit Secrets:
- `SPOTIFY_CLIENT_ID` - From https://developer.spotify.com/dashboard/
- `SPOTIFY_CLIENT_SECRET` - From https://developer.spotify.com/dashboard/
- `SESSION_SECRET` - A random secret string for Flask session security

## Architecture

- **web_app.py** - Flask web application, main entry point for the web interface
- **main.py** - Core downloader class (`TermuxSpotifyDownloader`) handling Spotify API + yt-dlp
- **templates/index.html** - Main UI with playlist URL input and search functionality
- **templates/status.html** - Download progress tracking page
- **static/** - Service worker, manifest, and icons for PWA support
- **utils/** - Audio quality, mobile optimization, and helper utilities

## Key Features

- Search Spotify public playlists by keyword
- Paste any public Spotify playlist URL directly
- Download up to 300 songs per playlist as MP3
- Tracks downloaded from YouTube via yt-dlp with high quality settings
- Songs bundled into a zip file for easy download
- Progress tracking page with real-time status updates

## Dependencies

Managed via `pyproject.toml` and installed in `.venv/`:
- flask, spotipy, yt-dlp, mutagen, pillow, requests, python-dotenv, psutil, tqdm, colorama, gunicorn

## Security Notes

- Spotify credentials stored in Replit Secrets (not .env file)
- Flask secret key loaded from SESSION_SECRET environment variable
- Debug mode off by default (set FLASK_DEBUG=true to enable)
- Spotify token cached in memory only (no file cache)
