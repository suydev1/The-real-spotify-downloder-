# Deploy this app on KataBump with a permanent URL

This guide explains how to run this Flask app on **KataBump** and connect your InfinityFree domain (`suyash.gt.tc`) for a permanent public URL.

## 1) Prepare the repository

This repo is already ready for Python hosting:

- App entrypoint: `src.web_app:app`
- Start command in `Procfile`:

```bash
web: gunicorn -w 4 -b 0.0.0.0:$PORT "src.web_app:app"
```

Dependencies are in `requirements.txt`.

## 2) Create a KataBump app/service

In KataBump dashboard:

1. Create a new **Web Service** (or equivalent Python app type).
2. Connect your GitHub repo (this project).
3. Configure:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn -w 4 -b 0.0.0.0:$PORT "src.web_app:app"`
   - **Port**: KataBump usually injects `$PORT` automatically.
4. Set environment variables:
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`

Then deploy.

## 3) Verify your KataBump URL

After deploy, KataBump gives a default URL (example: `https://your-app.katabump.app`).

Check:

- `https://your-app.katabump.app/health`

Expected response includes:

```json
{"status":"ok", ...}
```

If that works, app hosting is done.

## 4) Connect your InfinityFree domain (permanent URL)

You already manage `suyash.gt.tc` in InfinityFree.

In InfinityFree:

1. Open **Domains** → `suyash.gt.tc` → **DNS Records**.
2. Add/update DNS:
   - `CNAME` for `www` → your KataBump hostname (for example `your-app.katabump.app`).
   - If KataBump gives static IP support, set `A` for `@` → that IP.
3. If root `@` cannot be pointed directly, use InfinityFree **Redirects**:
   - Redirect `https://suyash.gt.tc` → `https://www.suyash.gt.tc`.

After propagation, your permanent URL becomes your own domain.

## 5) Configure custom domain inside KataBump

In KataBump app settings:

1. Open **Custom Domains**.
2. Add:
   - `www.suyash.gt.tc` (recommended)
   - optionally `suyash.gt.tc` if supported
3. KataBump will verify DNS and issue SSL.

Use HTTPS once certificate is active.

## 6) Troubleshooting

- **DNS not resolving yet**: wait for propagation (can take minutes to 72h).
- **SSL pending**: keep DNS records unchanged and wait for domain verification.
- **Spotify features failing**: re-check env vars in KataBump.
- **500 errors on download routes**: verify `ffmpeg` is available on the hosting runtime (some providers require enabling/installing it).

## 7) Recommended final setup

- Public URL for users: `https://www.suyash.gt.tc`
- KataBump default URL kept for maintenance/monitoring.
- Health checks pointed to: `/health`
