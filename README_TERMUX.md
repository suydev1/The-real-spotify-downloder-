# Spotify to YouTube Downloader - Termux Edition

A powerful, mobile-optimized Spotify playlist downloader for Android devices using Termux.

## 🌟 Features

- **Maximum Audio Quality**: FLAC preferred, fallback to 320kbps MP3
- **Termux Optimized**: Designed specifically for Android/Termux environment
- **Mobile-Friendly**: Battery and memory aware with low-resource mode
- **Complete Metadata**: Album artwork, track info, and ID3 tags
- **Android Integration**: Notifications, storage access, and system awareness
- **Resume Capability**: Retry failed downloads and handle interruptions
- **Progress Tracking**: Real-time download progress and ETA

## 🚀 Quick Setup

### 1. Install Termux
Download from [F-Droid](https://f-droid.org/packages/com.termux/) (recommended) or Google Play Store.

### 2. Install Termux:API (Optional but Recommended)
Download from [F-Droid](https://f-droid.org/packages/com.termux.api/) for notifications and system integration.

### 3. Run Setup Script
```bash
chmod +x termux_setup.sh
./termux_setup.sh
```

### 4. Configure Spotify API
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Copy your Client ID and Client Secret
4. Create `.env` file:
```bash
cp .env.example .env
nano .env  # Edit with your credentials
```

### 5. Run the Downloader
```bash
python main.py
```

## 🎧 Audio Quality Features

This downloader is optimized for **maximum audio quality**:

### Quality Priority (Highest to Lowest):
1. **FLAC** - Lossless compression, identical to CD quality
2. **Opus (WebM)** - High-efficiency codec, often better than MP3
3. **AAC/M4A** - Advanced Audio Coding, high quality
4. **MP3** - 320kbps VBR for maximum compatibility

### Metadata Enhancement:
- Complete ID3 tags with track info, artists, album details
- High-resolution album artwork (optimized for mobile)
- ISRC codes for track identification
- Genre information from Spotify
- Release dates and track numbering

### Mobile Optimizations:
- Memory-aware downloading (pauses on low memory)
- Battery level monitoring
- Network connection awareness  
- Resume interrupted downloads
- Android storage integration

## 📱 Termux-Specific Features

### Storage Access:
- Automatically requests Android storage permissions
- Downloads to `/storage/emulated/0/Music/SpotifyDownloads`
- Handles Android file system limitations

### Notifications:
- Download progress notifications
- Completion status alerts  
- Battery/memory warnings
- Requires Termux:API for full functionality

### Performance:
- Single-threaded downloads (mobile CPU optimization)
- Smaller chunk sizes for mobile networks
- Automatic temp file cleanup
- Low-memory mode for older devices

## 🚨 Usage Examples

### Interactive Mode:
```bash
python main.py
# Enter playlist URL when prompted
```

### Command Line Mode:
```bash
python main.py "https://open.spotify.com/playlist/37i9dQZF1DXcBWFJp05Sa8"
```

### Batch Processing:
```bash
# Create a file with playlist URLs
echo "https://open.spotify.com/playlist/..." >> playlists.txt
while read url; do python main.py "$url"; done < playlists.txt
```

## 📦 Build an APK (Android App)

You can package the web UI into an APK via PWA tooling:

1. Run/host `web_app.py` on an HTTPS URL
2. Ensure the app manifest and service worker are active
3. Use PWABuilder to generate an Android APK

Detailed steps: see `ANDROID_APK_GUIDE.md`.
