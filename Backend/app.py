from flask import Flask, request, jsonify, send_file
import yt_dlp
import os
import uuid

app = Flask(__name__)
SAVE_DIR = "downloads"
os.makedirs(SAVE_DIR, exist_ok=True)

class QuietLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(f"❌ {msg}")

def ydl_opts_common(filename):
    return {
        'outtmpl': os.path.join(SAVE_DIR, filename),
        'quiet': True,
        'no_warnings': True,
        'logger': QuietLogger(),
        'merge_output_format': 'mp4',
        'prefer_ffmpeg': True,
        'postprocessor_args': ['-loglevel', 'error'],
    }

@app.route("/info", methods=["POST"])
def info():
    url = request.json.get("url")
    if not url or not url.startswith("http"):
        return jsonify({"error": "Invalid URL"}), 400
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'logger': QuietLogger()}) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = [
            {"height": f.get("height"), "ext": f.get("ext")}
            for f in info.get("formats", [])
            if f.get("height") and f.get("vcodec") not in (None, "none")
        ]
        heights = sorted({f["height"] for f in formats if f["height"]}, reverse=True)
        return jsonify({"title": info.get("title"), "resolutions": heights})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/download", methods=["POST"])
def download():
    url = request.json.get("url")
    mode = request.json.get("mode", "quick")
    height = request.json.get("height")

    if not url or not url.startswith("http"):
        return jsonify({"error": "Invalid URL"}), 400

    unique_id = str(uuid.uuid4())
    base_path = os.path.join(SAVE_DIR, unique_id)
    filename = base_path + ".%(ext)s"
    opts = ydl_opts_common(filename)

    if mode == "quick":
        opts["format"] = "bestvideo[ext=mp4][vcodec*=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    elif mode == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif mode == "resolution" and height:
        opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        # Find downloaded file by unique_id
        filepath = next((os.path.join(SAVE_DIR, f) for f in os.listdir(SAVE_DIR) if f.startswith(unique_id)), None)
        if not filepath:
            return jsonify({"error": "Download failed"}), 500

        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)