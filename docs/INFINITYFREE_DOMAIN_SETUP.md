# InfinityFree domain setup for this Flask app

This project is a **Python/Flask** app. InfinityFree free hosting does not run persistent Python web apps (it is designed for PHP/static hosting).

## Recommended architecture

1. Deploy this app to a Python host (for example KataBump, Render, Railway, Fly.io, etc.).
2. Keep `suyash.gt.tc` managed in InfinityFree.
3. Point your domain DNS to the Python host.

## DNS settings in InfinityFree

Open:
- `Domains` → `suyash.gt.tc` → `DNS Records`

Then create/update:

- `CNAME` record for `www` → `<your-python-host-cname>`
- `A` record for `@` (root domain) → `<your-python-host-ip>` if your host gives an IPv4

If your host only supports CNAME and not root A records, use one of these:
- Redirect root (`suyash.gt.tc`) to `www.suyash.gt.tc` in InfinityFree redirects.
- Or use a provider feature like CNAME flattening/ALIAS (if available).

## SSL

After DNS points correctly:

1. In InfinityFree open `SSL Certificates` and issue/install cert if you terminate TLS there.
2. If TLS terminates on your Python host, set HTTPS there and keep DNS only in InfinityFree.

## App startup command

This repo already has a `Procfile`:

```bash
web: gunicorn -w 4 -b 0.0.0.0:$PORT "src.web_app:app"
```

Use that on your Python host.

## Health check

After deployment, verify:

- `https://<your-deployed-host>/health`

Expected JSON includes `status: ok`.

## Important note

DNS propagation can take up to 72 hours, but often updates begin working in minutes to a few hours.


For full KataBump steps, see `docs/KATABUMP_DEPLOYMENT.md`.
