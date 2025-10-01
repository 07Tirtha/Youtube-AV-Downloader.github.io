import os
import sys
import yt_dlp
from tqdm import tqdm

# =========================
# Settings
# =========================
SAVE_DIR = os.getcwd()  # always save in the script folder

# =========================
# Quiet logger for yt-dlp
# =========================
class QuietLogger:
    def debug(self, msg):  # swallow everything
        pass
    def warning(self, msg):
        pass
    def error(self, msg):
        print(f"❌ {msg}")

# =========================
# TQDM progress hook
# =========================
class TqdmHook:
    def __init__(self, desc="Downloading"):
        self.pbar = None
        self.desc = desc

    def __call__(self, d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            if self.pbar is None:
                self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc=self.desc, leave=False)
            downloaded = d.get('downloaded_bytes', 0)
            # update only the delta
            if downloaded >= 0:
                self.pbar.n = downloaded
                self.pbar.refresh()
        elif d['status'] == 'finished':
            if self.pbar:
                self.pbar.close()
            print("✅ Download complete!\n")

# =========================
# Helpers
# =========================
def fetch_info(url):
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'logger': QuietLogger()}) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"❌ Failed to fetch video info: {e}")
        sys.exit(1)

def build_resolution_menu(info):
    """
    Return:
      res_list: list of int heights sorted desc (unique)
      prefer_mp4: True if we have mp4/avc1 choices; otherwise False (fallback to any codec/container)
    """
    fmts = info.get('formats', []) or []

    # Prefer reliable playback: MP4 container + H.264/avc1 video
    mp4_h264 = [
        f for f in fmts
        if f.get('height') and f.get('vcodec') not in (None, 'none')
        and f.get('ext') == 'mp4'
        and ('avc1' in (f.get('vcodec') or '') or 'h264' in (f.get('vcodec') or ''))
    ]
    any_video = [f for f in fmts if f.get('height') and f.get('vcodec') not in (None, 'none')]

    prefer_mp4 = True
    base = mp4_h264 if mp4_h264 else any_video
    if not mp4_h264:
        prefer_mp4 = False

    # Unique heights, highest first
    heights = sorted({f['height'] for f in base}, reverse=True)
    return heights, prefer_mp4

def ask_int(prompt, valid_range):
    while True:
        s = input(prompt).strip()
        if s.isdigit():
            n = int(s)
            if n in valid_range:
                return n
        print("❌ Invalid choice. Try again.")

# =========================
# Downloaders
# =========================
def ydl_opts_common(desc="Downloading"):
    return {
        'outtmpl': os.path.join(SAVE_DIR, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,  # hide yt-dlp’s bar
        'logger': QuietLogger(),
        'merge_output_format': 'mp4',
        'keepvideo': False,
        'progress_hooks': [TqdmHook(desc=desc)],
        # make it robust & smooth
        'retries': 10,
        'fragment_retries': 10,
        'continuedl': True,
        'concurrent_fragment_downloads': 4,
        # silence ffmpeg noise
        'postprocessor_args': ['-loglevel', 'error'],
        'prefer_ffmpeg': True,
    }

def quick_download(url):
    # Best reliable playback: prefer MP4/H.264 + m4a; fallback to best MP4; finally any best
    fmt = "bestvideo[ext=mp4][vcodec*=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    opts = ydl_opts_common("Quick download")
    opts['format'] = fmt
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def choose_resolution_and_download(url, info):
    heights, prefer_mp4 = build_resolution_menu(info)
    if not heights:
        print("❌ No video resolutions found.")
        sys.exit(1)

    print("\n📊 Available resolutions:")
    for idx, h in enumerate(heights, start=1):
        print(f"{idx}. {h}p")
    choice = ask_int("Select resolution number (1 = highest): ", range(1, len(heights) + 1))
    sel_height = heights[choice - 1]

    confirm = input(f"Download at {sel_height}p? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Download cancelled.")
        sys.exit(0)

    if prefer_mp4:
        # Clean H.264 path
        fmt = (
            f"bestvideo[ext=mp4][vcodec*=avc1][height<={sel_height}]"
            f"+bestaudio[ext=m4a]/best[ext=mp4]"
        )
    else:
        # Fallback to anything, then we still merge to mp4 container
        fmt = f"bestvideo[height<={sel_height}]+bestaudio/best"

    opts = ydl_opts_common(f"Downloading {sel_height}p")
    opts['format'] = fmt

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

def audio_only(url):
    # Show simple “best audio” (no size shown per your request)
    fmt = "bestaudio/best"
    opts = ydl_opts_common("Audio only")
    # Convert to mp3 at good quality
    opts['postprocessors'] = [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
    opts['format'] = fmt
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

# =========================
# Main
# =========================
def main():
    print("=== 🎬 YouTube Ultra Downloader (clean & fast) ===")
    url = input("🔗 Enter YouTube URL: ").strip()
    if not url.startswith("http"):
        print("❌ Invalid URL.")
        sys.exit(1)

    print("🔍 Fetching video info...")
    info = fetch_info(url)
    title = info.get('title') or "Unknown title"
    print(f"🎥 Title: {title}\n")

    print("Choose an option:")
    print("1. Quick download (best available, MP4)")
    print("2. Choose resolution manually")
    print("3. Audio only (MP3)")
    opt = ask_int("Enter 1/2/3: ", {1, 2, 3})

    if opt == 1:
        quick_download(url)
    elif opt == 2:
        choose_resolution_and_download(url, info)
    else:
        audio_only(url)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Cancelled by user.")