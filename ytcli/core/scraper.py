"""yt-dlp wrapper — all yt-dlp interaction goes through here."""

import json
import subprocess


def _run_ytdlp(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run yt-dlp with given args. Returns CompletedProcess."""
    cmd = ["yt-dlp"] + args
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def get_video_metadata(url: str) -> dict:
    """Get video metadata JSON without downloading."""
    result = _run_ytdlp(["--dump-json", "--no-download", url])
    return json.loads(result.stdout)


def get_channel_videos(channel_url: str, limit: int = None) -> list[dict]:
    """Get metadata for all videos on a channel."""
    args = ["--dump-json", "--no-download", "--flat-playlist"]
    if limit:
        args.extend(["--playlist-items", f"1:{limit}"])
    args.append(channel_url)
    result = _run_ytdlp(args)
    videos = []
    for line in result.stdout.strip().split("\n"):
        if line:
            videos.append(json.loads(line))
    return videos


def download_video(url: str, output_dir: str, format: str = "mp4", quality: str = "1080") -> str:
    """Download video, return output path."""
    output_template = f"{output_dir}/%(title)s.%(ext)s"
    args = [
        "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
        "--merge-output-format", format,
        "-o", output_template,
        "--print", "after_move:filepath",
        url,
    ]
    result = _run_ytdlp(args)
    return result.stdout.strip().split("\n")[-1]


def download_audio(url: str, output_dir: str, format: str = "mp3", quality: str = "best") -> str:
    """Download audio only, return output path."""
    output_template = f"{output_dir}/%(title)s.%(ext)s"
    args = [
        "-x", "--audio-format", format,
        "-o", output_template,
        "--print", "after_move:filepath",
        url,
    ]
    if quality == "best":
        args.extend(["--audio-quality", "0"])
    result = _run_ytdlp(args)
    return result.stdout.strip().split("\n")[-1]


def download_thumbnail(url: str, output_dir: str) -> str:
    """Download thumbnail only, return output path."""
    output_template = f"{output_dir}/%(title)s.%(ext)s"
    args = [
        "--write-thumbnail", "--skip-download",
        "-o", output_template,
        url,
    ]
    result = _run_ytdlp(args)
    # yt-dlp doesn't print thumbnail path, construct it
    meta = get_video_metadata(url)
    import glob
    matches = glob.glob(f"{output_dir}/*.webp") + glob.glob(f"{output_dir}/*.jpg")
    return matches[-1] if matches else ""


def get_transcript(url: str, lang: str = "en") -> str:
    """Get subtitles/auto-captions as clean text."""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmp:
        output_template = f"{tmp}/sub"
        args = [
            "--write-auto-subs", "--sub-lang", lang,
            "--skip-download", "--convert-subs", "srt",
            "-o", output_template,
            url,
        ]
        _run_ytdlp(args, check=False)

        # Find the SRT file
        srt_files = [f for f in os.listdir(tmp) if f.endswith(".srt")]
        if not srt_files:
            # Try non-auto subs
            args[0] = "--write-subs"
            _run_ytdlp(args, check=False)
            srt_files = [f for f in os.listdir(tmp) if f.endswith(".srt")]

        if not srt_files:
            raise FileNotFoundError(f"No subtitles found for {url} in language {lang}")

        srt_path = os.path.join(tmp, srt_files[0])
        with open(srt_path) as f:
            lines = f.readlines()

        # Clean SRT to plain text (remove timestamps and numbers)
        text_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            if line not in text_lines[-1:]:  # basic dedup
                text_lines.append(line)

        return " ".join(text_lines)
