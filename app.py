import os, sys
# ensure src in path
sys.path.append(os.path.join(os.path.dirname(__file__), "spotify", "The-real-spotify-downloder--main"))

from flask import Flask, request, jsonify, send_file
# try common downloader entry points that the project may expose
download_func = None
try:
    # many projects expose a function in downloader.py
    from downloader import download_track, download_song, download
    # pick first available name
    for name in ("download_song", "download_track", "download"):
        if name in globals():
            download_func = globals()[name]
except Exception:
    # try importing main
    try:
        from main import download_track as download_func
    except Exception:
        download_func = None

app = Flask(__name__)

@app.route("/")
def home():
    return "Spotify Downloader Server Running"

@app.route("/download", methods=["POST"])
def download_route():
    if download_func is None:
        return jsonify({
            "error": ("download function not found. "
                      "Open spotify/The-real-spotify-downloder--main and expose a function "
                      "named download_song(link) or download_track(link) or download(link).")
        }), 500

    data = request.get_json() or {}
    link = data.get("link") or data.get("url")
    if not link:
        return jsonify({"error": "no 'link' supplied in JSON body"}), 400

    try:
        result = download_func(link)
        # If function returns a file path, send file
        if isinstance(result, str) and os.path.exists(result):
            return send_file(result, as_attachment=True)
        return jsonify({"status":"ok", "result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
