#!/usr/bin/env python3
"""
Web interface for Spotify to YouTube downloader
Allows users to download playlists as zip files
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
import os
import zipfile
import tempfile
import threading
import time
from datetime import datetime
import json
import shutil
import re
import sys
sys.path.append('.')
from main import TermuxSpotifyDownloader
from dotenv import load_dotenv
import yt_dlp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', os.urandom(24).hex())

# Global storage for download status
download_status_dict = {}

class WebDownloader:
    def __init__(self):
        self.downloader = None
        self._init_error = None
        self._try_init()

    def _try_init(self):
        try:
            self.downloader = TermuxSpotifyDownloader()
        except RuntimeError as e:
            self._init_error = str(e)
            print(f"WARNING: {e}")

    def is_ready(self):
        return self.downloader is not None and self._init_error is None
        
    def download_single_track(self, search_query, track_info, output_dir):
        """Download a single track using yt-dlp with retries and better error handling"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Sanitize filename
                safe_name = re.sub(r'[^\w\s-]', '', f"{track_info['artist']} - {track_info['name']}")
                safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-')
                
                # yt-dlp options for high quality
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': os.path.join(output_dir, f'{safe_name}.%(ext)s'),
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '320',
                    }],
                    'quiet': True,
                    'no_warnings': True,
                    'nocheckcertificate': True,
                    'ignoreerrors': False,
                    'logtostderr': False,
                    'no_color': True,
                    'socket_timeout': 30,
                    'retries': 5,
                }
                
                # Try multiple search queries on retry
                current_query = search_query
                if attempt == 1:
                    current_query = f"{track_info['name']} {track_info['artist']} lyrics"
                elif attempt == 2:
                    current_query = f"{track_info['artist']} {track_info['name']} official audio"

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Search and download
                    search_results = ydl.extract_info(f"ytsearch1:{current_query}", download=True)
                    if search_results and 'entries' in search_results and search_results['entries']:
                        # Find the downloaded file
                        for file in os.listdir(output_dir):
                            if safe_name in file and file.endswith('.mp3'):
                                return os.path.join(output_dir, file)
            except Exception as e:
                print(f"Attempt {attempt+1} failed for {track_info['name']}: {e}")
                time.sleep(2) # Increased pause
                
        return None
        
    def download_playlist_web(self, playlist_url, max_songs=300, download_id=None):
        """Download playlist with web progress tracking and enhanced reliability"""
        try:
            download_status_dict[download_id] = {
                'status': 'initializing',
                'progress': 0,
                'current_song': '',
                'downloaded': 0,
                'total': 0,
                'error': None,
                'zip_file': None,
                'started_at': datetime.now().isoformat(),
                'playlist_name': 'Loading...'
            }
            
            # Enhanced extraction logic
            playlist_id = None
            if 'playlist/' in playlist_url:
                playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
            elif 'spotify:playlist:' in playlist_url:
                playlist_id = playlist_url.split('spotify:playlist:')[1]
            
            if not playlist_id:
                raise ValueError("Invalid Spotify playlist URL. Please ensure it is a public playlist link.")
                
            download_status_dict[download_id]['status'] = 'fetching_playlist'
            
            playlist_data = self.downloader.spotify.playlist(playlist_id)
            tracks = []
            results = playlist_data['tracks']
            while results:
                for item in results['items']:
                    if item.get('track') and item['track'].get('type') == 'track':
                        track = item['track']
                        tracks.append({
                            'name': track['name'],
                            'artist': ', '.join([a['name'] for artist in [track['artists']] for a in artist] if isinstance(track['artists'], list) else [track['artists']['name']]),
                            'album': track['album']['name'],
                            'duration': track['duration_ms'],
                            'spotify_url': track['external_urls']['spotify']
                        })
                results = self.downloader.spotify.next(results) if results.get('next') else None
            
            if not tracks:
                raise ValueError("No tracks found in this playlist.")
                
            tracks = tracks[:max_songs]
            download_status_dict[download_id].update({
                'status': 'downloading',
                'total': len(tracks),
                'playlist_name': playlist_data.get('name', 'Spotify Playlist')
            })
            
            temp_dir = tempfile.mkdtemp(prefix=f'spotify_download_{download_id}_')
            downloaded_files = []
            
            for i, track in enumerate(tracks):
                download_status_dict[download_id].update({
                    'current_song': f"{track['name']} - {track['artist']}",
                    'progress': int((i / len(tracks)) * 100)
                })
                
                search_query = f"{track['artist']} {track['name']}"
                filename = self.download_single_track(search_query, track, temp_dir)
                if filename and os.path.exists(filename):
                    downloaded_files.append(filename)
                    download_status_dict[download_id]['downloaded'] = len(downloaded_files)
            
            if not downloaded_files:
                raise Exception("Could not download any songs. Please try another playlist or check the URL.")

            download_status_dict[download_id]['status'] = 'creating_zip'
            zip_filename = f"spotify_playlist_{playlist_id}_{int(time.time())}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in downloaded_files:
                    if os.path.exists(file_path):
                        zipf.write(file_path, os.path.basename(file_path))
            
            shutil.rmtree(temp_dir, ignore_errors=True)
            download_status_dict[download_id].update({
                'status': 'completed',
                'progress': 100,
                'zip_file': zip_path,
                'completed_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            download_status_dict[download_id].update({
                'status': 'error',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            })

web_downloader = WebDownloader()

def require_spotify(f):
    """Decorator to check Spotify is configured before handling requests."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not web_downloader.is_ready():
            error_msg = web_downloader._init_error or "Spotify credentials not configured."
            flash(f'Setup required: {error_msg}')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    setup_error = None
    if not web_downloader.is_ready():
        setup_error = web_downloader._init_error
    return render_template('index.html', setup_error=setup_error)

@app.route('/start_download', methods=['POST'])
@require_spotify
def start_download():
    playlist_url = request.form.get('playlist_url', '').strip()
    max_songs = int(request.form.get('max_songs', 300))
    
    if not playlist_url:
        flash('Please enter a valid Spotify playlist URL')
        return redirect(url_for('index'))
    
    if not ('open.spotify.com/playlist/' in playlist_url):
        flash('Please enter a valid Spotify playlist URL')
        return redirect(url_for('index'))
    
    # Generate download ID
    download_id = f"download_{int(time.time())}_{hash(playlist_url) % 10000}"
    
    # Start download in background thread
    thread = threading.Thread(
        target=web_downloader.download_playlist_web,
        args=(playlist_url, max_songs, download_id)
    )
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('download_status', download_id=download_id))

@app.route('/status/<download_id>')
def download_status(download_id):
    return render_template('status.html', download_id=download_id)

@app.route('/api/status/<download_id>')
def get_download_status(download_id):
    status = download_status_dict.get(download_id, {
        'status': 'not_found',
        'error': 'Download not found'
    })
    return jsonify(status)

@app.route('/download/<download_id>')
def download_file(download_id):
    status = download_status_dict.get(download_id, {})
    
    if status.get('status') != 'completed' or not status.get('zip_file'):
        flash('Download not ready or not found')
        return redirect(url_for('index'))
    
    zip_path = status['zip_file']
    if not os.path.exists(zip_path):
        flash('Download file not found')
        return redirect(url_for('index'))
    
    playlist_name = status.get('playlist_name', 'playlist')
    safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"{safe_name}.zip"
    
    return send_file(zip_path, as_attachment=True, download_name=filename)

@app.route('/search_playlists')
@require_spotify
def search_playlists():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'status': 'error', 'message': 'Search query is required'})
    
    try:
        # Search for playlists
        results = web_downloader.downloader.spotify.search(q=query, type='playlist', limit=20)
        
        playlists = []
        if results and 'playlists' in results and results['playlists']['items']:
            for playlist in results['playlists']['items']:
                if playlist and 'id' in playlist:
                    try:
                        # Test if we can access this playlist
                        test_playlist = web_downloader.downloader.spotify.playlist(
                            playlist['id'], 
                            fields="name,tracks.total,owner.display_name,images"
                        )
                        
                        if test_playlist['tracks']['total'] > 0:
                            image_url = None
                            if test_playlist.get('images') and len(test_playlist['images']) > 0:
                                image_url = test_playlist['images'][0]['url']
                            
                            playlists.append({
                                'id': playlist['id'],
                                'name': test_playlist['name'],
                                'tracks': test_playlist['tracks']['total'],
                                'owner': test_playlist.get('owner', {}).get('display_name', 'Unknown'),
                                'url': f"https://open.spotify.com/playlist/{playlist['id']}",
                                'image': image_url
                            })
                            
                    except Exception:
                        continue  # Skip inaccessible playlists
        
        return jsonify({
            'status': 'success',
            'playlists': playlists,
            'count': len(playlists)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Search failed: {str(e)}'})

@app.route('/test_connection')
def test_connection():
    if not web_downloader.is_ready():
        return jsonify({'status': 'error', 'message': web_downloader._init_error or 'Not configured'})
    try:
        results = web_downloader.downloader.spotify.search(q='test', type='artist', limit=1)
        return jsonify({'status': 'success', 'message': 'Spotify API connected successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Connection failed: {str(e)}'})

@app.route('/download_video', methods=['POST'])
def download_video():
    video_url = request.form.get('video_url', '').strip()
    if not video_url:
        flash('Please enter a valid YouTube URL')
        return redirect(url_for('index'))
    
    download_id = f"video_{int(time.time())}_{hash(video_url) % 10000}"
    
    def background_video_download(url, d_id):
        try:
            download_status_dict[d_id] = {
                'status': 'downloading',
                'progress': 0,
                'current_song': 'Preparing video download...',
                'started_at': datetime.now().isoformat()
            }
            
            temp_dir = tempfile.mkdtemp(prefix=f'video_download_{d_id}_')
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'nocheckcertificate': True,
                'ignoreerrors': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_title = info.get('title', 'video')
                filename = ydl.prepare_filename(info)
                
                # If extension changed during download
                base, ext = os.path.splitext(filename)
                for f in os.listdir(temp_dir):
                    if f.startswith(os.path.basename(base)):
                        filename = os.path.join(temp_dir, f)
                        break

                download_status_dict[d_id].update({
                    'status': 'completed',
                    'progress': 100,
                    'zip_file': filename, # Reusing zip_file field for simplicity
                    'playlist_name': video_title,
                    'completed_at': datetime.now().isoformat()
                })
        except Exception as e:
            download_status_dict[d_id] = {
                'status': 'error',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }

    thread = threading.Thread(target=background_video_download, args=(video_url, download_id))
    thread.daemon = True
    thread.start()
    
    return redirect(url_for('download_status', download_id=download_id))

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)