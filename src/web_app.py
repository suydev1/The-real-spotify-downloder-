"""Flask web app for Spotify playlist and YouTube video downloads.

This module keeps dependencies optional and degrades gracefully when Spotify
credentials are not configured.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Flask, jsonify, redirect, render_template, request, send_file, url_for

import yt_dlp

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
except Exception:  # pragma: no cover - optional dependency failures are handled at runtime
    spotipy = None
    SpotifyClientCredentials = None


BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


@dataclass
class DownloadJob:
    id: str
    playlist_name: str = ""
    status: str = "initializing"
    progress: int = 0
    total: int = 0
    downloaded: int = 0
    current_song: str = ""
    error: str | None = None
    zip_path: str | None = None
    cleanup_paths: list[str] = field(default_factory=list)


download_jobs: dict[str, DownloadJob] = {}
_jobs_lock = threading.Lock()


class SpotifyService:
    def __init__(self) -> None:
        self.client = None
        self.error: str | None = None

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            self.error = "Spotify credentials are missing"
            return

        if not spotipy or not SpotifyClientCredentials:
            self.error = "spotipy is not available"
            return

        try:
            auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
            self.client = spotipy.Spotify(auth_manager=auth)
            self.client.search(q="test", type="playlist", limit=1)
        except Exception as exc:
            self.error = str(exc)
            self.client = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def search_playlists(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        if not self.client:
            raise RuntimeError(self.error or "Spotify is unavailable")

        result = self.client.search(q=query, type="playlist", limit=limit)
        playlists = result.get("playlists", {}).get("items", [])

        cleaned = []
        for item in playlists:
            if not item:
                continue
            cleaned.append(
                {
                    "name": item.get("name", "Unknown playlist"),
                    "url": item.get("external_urls", {}).get("spotify", ""),
                    "owner": item.get("owner", {}).get("display_name", "Unknown"),
                    "tracks": item.get("tracks", {}).get("total", 0),
                    "image": (item.get("images") or [{}])[0].get("url", ""),
                }
            )
        return [p for p in cleaned if p["url"]]

    def get_playlist_tracks(self, playlist_url: str, max_songs: int) -> tuple[str, list[dict[str, str]]]:
        if not self.client:
            raise RuntimeError(self.error or "Spotify is unavailable")

        match = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url)
        if not match:
            raise ValueError("Invalid Spotify playlist URL")

        playlist_id = match.group(1)
        info = self.client.playlist(playlist_id)
        playlist_name = info.get("name", "Spotify Playlist")

        tracks: list[dict[str, str]] = []
        offset = 0
        while len(tracks) < max_songs:
            page = self.client.playlist_items(playlist_id, offset=offset, limit=min(100, max_songs - len(tracks)))
            items = page.get("items", [])
            if not items:
                break
            for item in items:
                track = item.get("track") or {}
                if not track:
                    continue
                artists = ", ".join(a.get("name", "") for a in track.get("artists", []) if a.get("name"))
                name = track.get("name", "")
                if name:
                    tracks.append({"name": name, "artists": artists})
            offset += len(items)
            if not page.get("next"):
                break

        return playlist_name, tracks[:max_songs]


spotify_service = SpotifyService()


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-. ]", "", name).strip().replace(" ", "_")
    return cleaned[:120] or "download"


def _download_single_audio(query: str, output_dir: Path) -> Path | None:
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "retries": 2,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}
        ],
        "outtmpl": str(output_dir / "%(title).180s.%(ext)s"),
    }

    before_files = {p.name for p in output_dir.glob("*.mp3")}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"ytsearch1:{query}"])
    after_files = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)

    for file in after_files:
        if file.name not in before_files:
            return file
    return after_files[0] if after_files else None


def _zip_directory(source_dir: Path, destination_zip: Path) -> None:
    with ZipFile(destination_zip, "w", ZIP_DEFLATED) as zipf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zipf.write(path, arcname=path.relative_to(source_dir))


def _run_playlist_job(job_id: str, playlist_url: str, max_songs: int) -> None:
    with _jobs_lock:
        job = download_jobs[job_id]
        job.status = "fetching_playlist"

    work_dir = Path(tempfile.mkdtemp(prefix=f"spotify_job_{job_id}_"))
    with _jobs_lock:
        job.cleanup_paths.append(str(work_dir))

    try:
        playlist_name, tracks = spotify_service.get_playlist_tracks(playlist_url, max_songs)
        if not tracks:
            raise RuntimeError("No tracks found in playlist")

        safe_playlist_name = _safe_filename(playlist_name)
        playlist_dir = work_dir / safe_playlist_name
        playlist_dir.mkdir(parents=True, exist_ok=True)

        with _jobs_lock:
            job.playlist_name = playlist_name
            job.total = len(tracks)
            job.status = "downloading"

        for idx, track in enumerate(tracks, start=1):
            query = f"{track['artists']} - {track['name']} audio"
            with _jobs_lock:
                job.current_song = f"{track['artists']} - {track['name']}"

            audio_path = _download_single_audio(query, playlist_dir)
            if audio_path is None:
                continue

            desired_name = playlist_dir / f"{idx:03d}_{_safe_filename(track['artists'])}_{_safe_filename(track['name'])}.mp3"
            if audio_path != desired_name:
                audio_path.rename(desired_name)

            with _jobs_lock:
                job.downloaded += 1
                job.progress = int((idx / len(tracks)) * 100)

        zip_path = DOWNLOADS_DIR / f"{job_id}_{safe_playlist_name}.zip"
        _zip_directory(playlist_dir, zip_path)

        with _jobs_lock:
            job.zip_path = str(zip_path)
            job.status = "completed"
            job.progress = 100

    except Exception as exc:
        with _jobs_lock:
            job.status = "error"
            job.error = str(exc)


@app.route("/")
def index() -> str:
    return render_template("index.html", setup_error=not spotify_service.enabled)


@app.route("/health")
def health() -> Any:
    return jsonify(
        {
            "status": "ok",
            "spotify": "configured" if spotify_service.enabled else "missing_credentials",
        }
    )


@app.route("/test_connection")
def test_connection() -> Any:
    if spotify_service.enabled:
        return jsonify({"status": "success", "message": "Spotify API is configured and reachable."})
    return jsonify({"status": "error", "message": spotify_service.error or "Spotify is not configured."})


@app.route("/search_playlists")
def search_playlists() -> Any:
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"status": "error", "message": "Missing query"}), 400

    try:
        playlists = spotify_service.search_playlists(query)
        return jsonify({"status": "success", "count": len(playlists), "playlists": playlists})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)})


@app.route("/start_download", methods=["POST"])
def start_download() -> Any:
    playlist_url = (request.form.get("playlist_url") or "").strip()
    max_songs = request.form.get("max_songs", "50").strip()

    if not spotify_service.enabled:
        return jsonify({"status": "error", "message": spotify_service.error or "Spotify is not configured"}), 400

    if not playlist_url:
        return jsonify({"status": "error", "message": "Playlist URL is required"}), 400

    try:
        max_songs_int = max(1, min(int(max_songs), 300))
    except ValueError:
        return jsonify({"status": "error", "message": "max_songs must be a number"}), 400

    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        download_jobs[job_id] = DownloadJob(id=job_id)

    thread = threading.Thread(
        target=_run_playlist_job,
        args=(job_id, playlist_url, max_songs_int),
        daemon=True,
    )
    thread.start()

    return redirect(url_for("status_page", download_id=job_id))


@app.route("/status/<download_id>")
def status_page(download_id: str) -> str:
    return render_template("status.html", download_id=download_id)


@app.route("/api/status/<download_id>")
def api_status(download_id: str) -> Any:
    with _jobs_lock:
        job = download_jobs.get(download_id)
        if not job:
            return jsonify({"status": "not_found"}), 404

        return jsonify(
            {
                "status": job.status,
                "playlist_name": job.playlist_name,
                "progress": job.progress,
                "downloaded": job.downloaded,
                "total": job.total,
                "current_song": job.current_song,
                "error": job.error,
            }
        )


@app.route("/download/<download_id>")
def download_file(download_id: str) -> Any:
    with _jobs_lock:
        job = download_jobs.get(download_id)

    if not job or not job.zip_path or not Path(job.zip_path).exists():
        return jsonify({"status": "error", "message": "Download not available"}), 404

    return send_file(job.zip_path, as_attachment=True)


@app.route("/download_video", methods=["POST"])
def download_video() -> Any:
    video_url = (request.form.get("video_url") or "").strip()
    if not video_url:
        return jsonify({"status": "error", "message": "Video URL is required"}), 400

    temp_dir = Path(tempfile.mkdtemp(prefix="video_download_"))
    try:
        output_template = str(temp_dir / "%(title).180s.%(ext)s")
        opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = Path(ydl.prepare_filename(info))

        if file_path.suffix.lower() != ".mp4":
            mp4_candidate = file_path.with_suffix(".mp4")
            if mp4_candidate.exists():
                file_path = mp4_candidate

        persisted = DOWNLOADS_DIR / f"video_{uuid.uuid4().hex[:8]}_{_safe_filename(file_path.stem)}{file_path.suffix}"
        shutil.copy2(file_path, persisted)
        return send_file(persisted, as_attachment=True, download_name=persisted.name)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
