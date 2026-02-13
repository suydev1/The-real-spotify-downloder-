# Build an Android APK for Spotify Downloader

This project now includes PWA support (`manifest.webmanifest` + service worker), which is the easiest path to an APK.

## Option 1 (Recommended): Build APK from your hosted web app with PWABuilder

1. Host the Flask app publicly over HTTPS (Render, Railway, VPS + Nginx, etc.).
2. Open your public URL in Chrome and confirm:
   - Manifest is detected
   - Service worker is active
3. Go to https://www.pwabuilder.com and paste your URL.
4. Choose **Android** package and download the generated project/APK.
5. (Optional) Open generated Android project in Android Studio to customize app name, icon, and splash screen.

## Option 2: Wrap local Flask URL with a WebView app (for testing only)

You can use tools like Android Studio to create a basic WebView app that loads your deployed URL.
This is quick for internal testing, but less reliable than a full PWA/TWA approach.

## Important Notes

- APK users still need the backend service running (this app is not fully offline).
- Playlist downloads and Spotify API operations require network access.
- For production, configure a strong Flask secret key and run behind a proper WSGI server.

## Quick checklist before generating APK

- [ ] App loads over HTTPS
- [ ] `manifest.webmanifest` is reachable
- [ ] Service worker (`/static/sw.js`) registers successfully
- [ ] Mobile viewport works and install prompt appears in Chrome Android
