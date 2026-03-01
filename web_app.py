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
        self.downloader = TermuxSpotifyDownloader()
        
    def download_single_track(self, search_query, track_info, output_dir):
        """Download a single track using yt-dlp"""
        try:
            # Sanitize filename
            safe_name = re.sub(r'[^\w\s-]', '', f"{track_info['artist']} - {track_info['name']}")
            safe_name = re.sub(r'[-\s]+', '-', safe_name).strip('-')
            
            # yt-dlp options for high quality
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
                'outtmpl': os.path.join(output_dir, f'{safe_name}.%(ext)s'),
                'extractaudio': True,
                'audioformat': 'mp3',
                'audioquality': '320K',
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Search and download
                search_results = ydl.extract_info(f"ytsearch1:{search_query}", download=False)
                if search_results and 'entries' in search_results and search_results['entries']:
                    video_info = search_results['entries'][0]
                    ydl.download([video_info['webpage_url']])
                    
                    # Find the downloaded file
                    for file in os.listdir(output_dir):
                        if safe_name in file and (file.endswith('.mp3') or file.endswith('.m4a')):
                            return os.path.join(output_dir, file)
                            
        except Exception as e:
            print(f"Error downloading {track_info['name']}: {e}")
            
        return None
        
    def download_playlist_web(self, playlist_url, max_songs=300, download_id=None):
        """Download playlist with web progress tracking"""
        try:
            # Update status
            download_status_dict[download_id] = {
                'status': 'initializing',
                'progress': 0,
                'current_song': '',
                'downloaded': 0,
                'total': 0,
                'error': None,
                'zip_file': None,
                'started_at': datetime.now().isoformat()
            }
            
            # Extract playlist ID
            if 'playlist/' in playlist_url:
                playlist_id = playlist_url.split('playlist/')[1].split('?')[0]
            else:
                raise ValueError("Invalid playlist URL")
                
            download_status_dict[download_id]['status'] = 'fetching_playlist'
            
            # Get playlist tracks
            playlist_data = self.downloader.spotify.playlist(playlist_id)
            tracks = []
            
            # Get tracks from playlist
            results = playlist_data['tracks']
            while results:
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        track_info = {
                            'name': track['name'],
                            'artist': ', '.join([artist['name'] for artist in track['artists']]),
                            'album': track['album']['name'],
                            'duration': track['duration_ms'],
                            'spotify_url': track['external_urls']['spotify']
                        }
                        tracks.append(track_info)
                        
                if results['next']:
                    results = self.downloader.spotify.next(results)
                else:
                    results = None
            
            if not tracks:
                raise ValueError("No tracks found or playlist not accessible")
                
            # Limit tracks
            tracks = tracks[:max_songs]
            
            download_status_dict[download_id].update({
                'status': 'downloading',
                'total': len(tracks),
                'playlist_name': playlist_data.get('name', 'Unknown Playlist')
            })
            
            # Create temp directory for this download
            temp_dir = tempfile.mkdtemp(prefix=f'spotify_download_{download_id}_')
            downloaded_files = []
            
            for i, track in enumerate(tracks):
                try:
                    download_status_dict[download_id].update({
                        'current_song': f"{track['name']} - {track['artist']}",
                        'progress': int((i / len(tracks)) * 100)
                    })
                    
                    # Download the track using YouTube search
                    search_query = f"{track['artist']} {track['name']}"
                    filename = self.download_single_track(search_query, track, temp_dir)
                    if filename and os.path.exists(filename):
                        downloaded_files.append(filename)
                        download_status_dict[download_id]['downloaded'] = len(downloaded_files)
                        
                except Exception as e:
                    print(f"Error downloading {track['name']}: {e}")
                    continue
            
            # Create zip file
            download_status_dict[download_id]['status'] = 'creating_zip'
            
            zip_filename = f"spotify_playlist_{playlist_id}_{int(time.time())}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in downloaded_files:
                    if os.path.exists(file_path):
                        # Use just the filename in the zip
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            download_status_dict[download_id].update({
                'status': 'completed',
                'progress': 100,
                'zip_file': zip_path,
                'completed_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            download_status_dict[download_id] = {
                'status': 'error',
                'error': str(e),
                'completed_at': datetime.now().isoformat()
            }

web_downloader = WebDownloader()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_download', methods=['POST'])
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
    try:
        # Test Spotify connection
        results = web_downloader.downloader.spotify.search(q='test', type='artist', limit=1)
        return jsonify({'status': 'success', 'message': 'Spotify API connected successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Connection failed: {str(e)}'})

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug)