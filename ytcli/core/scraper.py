"""yt-dlp wrapper — all yt-dlp interaction goes through here."""

import json
import subprocess


def _run_ytdlp(args: list[str], check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run yt-dlp with given args. Returns CompletedProcess."""
    cmd = ["yt-dlp"] + args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"yt-dlp timed out after {timeout} seconds") from e


def get_video_metadata(url: str) -> dict:
    """Get video metadata JSON without downloading."""
    result = _run_ytdlp(["--dump-json", "--no-download", "--", url])
    return json.loads(result.stdout)


def get_channel_videos(channel_url: str, limit: int = None) -> list[dict]:
    """Get metadata for all videos on a channel."""
    args = ["--dump-json", "--no-download", "--flat-playlist"]
    if limit:
        args.extend(["--playlist-items", f"1:{limit}"])
    args.extend(["--", channel_url])
    result = _run_ytdlp(args)
    videos = []
    for line in result.stdout.strip().split("\n"):
        if line:
            try:
                videos.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # skip non-JSON lines (e.g. yt-dlp warnings)
    return videos


def download_video(url: str, output_dir: str, format: str = "mp4", quality: str = "1080") -> str:
    """Download video, return output path."""
    output_template = f"{output_dir}/%(title)s.%(ext)s"
    args = [
        "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
        "--merge-output-format", format,
        "-o", output_template,
        "--print", "after_move:filepath",
        "--", url,
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
        "--", url,
    ]
    if quality == "best":
        args.extend(["--audio-quality", "0"])
    result = _run_ytdlp(args)
    return result.stdout.strip().split("\n")[-1]


def download_thumbnail(url: str, output_dir: str) -> str | None:
    """Download thumbnail only, return output path or None on failure."""
    import os

    output_template = f"{output_dir}/%(title)s.%(ext)s"
    args = [
        "--write-thumbnail", "--skip-download",
        "--print", "after_move:filepath",
        "-o", output_template,
        "--", url,
    ]
    result = _run_ytdlp(args, check=False)
    if result.returncode != 0:
        return None
    # yt-dlp --print may output the thumbnail path on the last line
    lines = [l for l in result.stdout.strip().split("\n") if l.strip()]
    if lines:
        candidate = lines[-1].strip()
        if os.path.isfile(candidate):
            return candidate
    # Fallback: look for recently written thumbnail files in output_dir
    for ext in ("webp", "jpg", "png"):
        for f in sorted(os.listdir(output_dir), reverse=True):
            if f.endswith(f".{ext}"):
                return os.path.join(output_dir, f)
    return None


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
            "--", url,
        ]
        _run_ytdlp(args, check=False)

        # Find the SRT file
        srt_files = [f for f in os.listdir(tmp) if f.endswith(".srt")]
        if not srt_files:
            # Try non-auto subs with fresh args (don't mutate original)
            retry_args = [
                "--write-subs", "--sub-lang", lang,
                "--skip-download", "--convert-subs", "srt",
                "-o", output_template,
                "--", url,
            ]
            _run_ytdlp(retry_args, check=False)
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
