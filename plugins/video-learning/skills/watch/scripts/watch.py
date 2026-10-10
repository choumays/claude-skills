#!/usr/bin/env python3
"""Turn a video (URL or local file) into things Claude can read: a timestamped
transcript and a set of still frames.

Usage:
  watch.py <url-or-file> [--out DIR] [--frames N | --every SECONDS | --scene]
           [--start HH:MM:SS] [--end HH:MM:SS] [--lang en] [--no-frames]

Writes into DIR (default ./watch/<video-id>):
  meta.json        title, channel, duration, url, description, chapters
  transcript.txt   "[mm:ss] text" lines, deduplicated
  frames/          frame_0001_t0012.jpg ... (t = seconds into the video)
  index.md         one file tying it together, the thing to read first

Needs yt-dlp for URLs (pip install yt-dlp) and ffmpeg for frames.
If no subtitles exist, falls back to local Whisper (openai-whisper or
faster-whisper) when installed; otherwise says so and continues.
"""
import argparse
import glob
import html
import json
import os
import re
import shutil
import subprocess
import sys


def run(cmd, check=True):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{p.stderr.strip()[-2000:]}")
    return p


def need(tool, hint):
    if not shutil.which(tool):
        sys.exit(f"missing dependency: {tool} ({hint})")


def hms_to_s(v):
    if v is None:
        return None
    parts = [float(x) for x in str(v).split(":")]
    s = 0.0
    for x in parts:
        s = s * 60 + x
    return s


def s_to_ts(s):
    s = int(s)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


# ---------- subtitles ----------

TS = re.compile(r"(\d+:)?\d{2}:\d{2}[.,]\d{3}\s*-->\s*((\d+:)?\d{2}:\d{2}[.,]\d{3})")


def parse_subs(path):
    """Parse VTT or SRT into [(start_seconds, text)], removing the rolling
    duplication that YouTube auto-captions produce."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    cues = []
    for block in re.split(r"\n\s*\n", raw.replace("\r", "")):
        lines = block.strip().split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        start = hms_to_s(lines[idx].split("-->")[0].strip().replace(",", ".").split(" ")[0])
        text = " ".join(lines[idx + 1:])
        text = re.sub(r"<[^>]+>", "", text)  # inline timing / styling tags
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        if text:
            cues.append((start, text))

    out, prev = [], ""
    for start, text in cues:
        if text == prev:
            continue
        # auto-captions repeat the previous line then append new words
        if prev and text.startswith(prev):
            new = text[len(prev):].strip()
        else:
            new = text
            # or overlap at the word level
            pw, tw = prev.split(), text.split()
            for k in range(min(len(pw), len(tw)), 0, -1):
                if pw[-k:] == tw[:k]:
                    new = " ".join(tw[k:])
                    break
        prev = text
        if new:
            out.append((start, new))
    return out


def group_lines(cues, window=20.0):
    """Merge cues into ~window-second paragraphs so the transcript is readable."""
    lines, cur_t, buf = [], None, []
    for t, text in cues:
        if cur_t is None:
            cur_t = t
        if t - cur_t >= window and buf:
            lines.append((cur_t, " ".join(buf)))
            cur_t, buf = t, []
        buf.append(text)
    if buf:
        lines.append((cur_t, " ".join(buf)))
    return lines


def pick_sub_file(workdir, lang):
    files = glob.glob(os.path.join(workdir, "*.vtt")) + glob.glob(os.path.join(workdir, "*.srt"))
    if not files:
        return None
    # prefer manual subs in the requested language, then any in that language
    files.sort(key=lambda f: (f".{lang}" not in os.path.basename(f), "orig" not in f, len(f)))
    return files[0]


def whisper_transcribe(media):
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(os.environ.get("WHISPER_MODEL", "base"), compute_type="int8")
        segs, _ = model.transcribe(media)
        return [(s.start, s.text.strip()) for s in segs]
    except ImportError:
        pass
    try:
        import whisper  # type: ignore
        model = whisper.load_model(os.environ.get("WHISPER_MODEL", "base"))
        res = model.transcribe(media)
        return [(s["start"], s["text"].strip()) for s in res["segments"]]
    except ImportError:
        return None


# ---------- frames ----------

def extract_frames(media, outdir, duration, n=None, every=None, scene=False, start=None, end=None):
    need("ffmpeg", "apt install ffmpeg / brew install ffmpeg")
    os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(os.path.join(outdir, "*.jpg")):
        os.remove(f)
    s0 = start or 0.0
    s1 = end or duration or 0.0
    span = max(s1 - s0, 1.0)
    scale = "scale='min(1280,iw)':-2"

    if scene:
        # keep frames where the picture changes a lot (slides, cuts, new screens)
        tmp = os.path.join(outdir, "_scene")
        os.makedirs(tmp, exist_ok=True)
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "info", "-ss", str(s0)]
        if end:
            cmd += ["-to", str(end)]
        cmd += ["-i", media, "-vf", f"select='eq(n,0)+gt(scene,0.3)',showinfo,{scale}",
                "-vsync", "vfr", "-q:v", "3", os.path.join(tmp, "%04d.jpg")]
        p = run(cmd, check=False)
        times = [s0 + float(m) for m in re.findall(r"pts_time:([\d.]+)", p.stderr)]
        made = sorted(glob.glob(os.path.join(tmp, "*.jpg")))
        cap = n or 60
        if len(made) > cap:  # thin evenly
            keep = {round(i * (len(made) - 1) / (cap - 1)) for i in range(cap)}
        else:
            keep = set(range(len(made)))
        out = []
        for i, f in enumerate(made):
            if i in keep:
                t = times[i] if i < len(times) else s0
                dst = os.path.join(outdir, f"frame_{len(out)+1:04d}_t{int(t):04d}.jpg")
                os.replace(f, dst)
                out.append((t, dst))
        shutil.rmtree(tmp, ignore_errors=True)
        if out:
            return out
        n = n or 12  # static video: fall back to even sampling

    if every:
        stamps = [s0 + k * every for k in range(int(span // every) + 1)]
    else:
        n = n or min(max(int(span // 30), 8), 40)  # ~1 per 30s, 8..40
        stamps = [s0 + span * (i + 0.5) / n for i in range(n)]

    out = []
    for i, t in enumerate(stamps, 1):
        dst = os.path.join(outdir, f"frame_{i:04d}_t{int(t):04d}.jpg")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.2f}",
             "-i", media, "-frames:v", "1", "-vf", scale, "-q:v", "3", dst], check=False)
        if os.path.exists(dst):
            out.append((t, dst))
    return out


def probe_duration(media):
    if not shutil.which("ffprobe"):
        return None
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", media], check=False)
    try:
        return float(p.stdout.strip())
    except ValueError:
        return None


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="video URL (YouTube, TikTok, anything yt-dlp supports) or local file")
    ap.add_argument("--out", help="output directory")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--frames", type=int, help="number of evenly spaced frames")
    g.add_argument("--every", type=float, help="one frame every N seconds")
    ap.add_argument("--scene", action="store_true", help="frames on scene changes (best for slides/screens)")
    ap.add_argument("--no-frames", action="store_true", help="transcript only")
    ap.add_argument("--start", help="start time, e.g. 1:30")
    ap.add_argument("--end", help="end time, e.g. 4:00")
    ap.add_argument("--lang", default="en", help="subtitle language (default en)")
    ap.add_argument("--keep-video", action="store_true", help="keep the downloaded video file")
    a = ap.parse_args()

    start, end = hms_to_s(a.start), hms_to_s(a.end)
    is_url = re.match(r"https?://", a.source) is not None
    meta = {"source": a.source}

    if is_url:
        need("yt-dlp", "pip install yt-dlp")
        info = json.loads(run(["yt-dlp", "-J", "--no-playlist", a.source]).stdout)
        vid = re.sub(r"[^\w-]", "_", str(info.get("id", "video")))
        meta.update({k: info.get(k) for k in
                     ("id", "title", "channel", "uploader", "duration", "upload_date",
                      "webpage_url", "description", "chapters", "view_count")})
    else:
        if not os.path.exists(a.source):
            sys.exit(f"no such file: {a.source}")
        vid = re.sub(r"[^\w-]", "_", os.path.splitext(os.path.basename(a.source))[0])
        meta.update({"id": vid, "title": os.path.basename(a.source)})

    out = os.path.abspath(a.out or os.path.join("watch", vid))
    work = os.path.join(out, "_work")
    os.makedirs(work, exist_ok=True)

    # 1. transcript from subtitles
    cues = None
    sub_src = None
    if is_url:
        run(["yt-dlp", "--skip-download", "--no-playlist", "--write-subs", "--write-auto-subs",
             "--sub-langs", f"{a.lang}.*,{a.lang}", "--sub-format", "vtt/srt/best",
             "-o", os.path.join(work, "subs.%(ext)s"), a.source], check=False)
        sf = pick_sub_file(work, a.lang)
        if sf:
            cues, sub_src = parse_subs(sf), os.path.basename(sf)
    else:
        for ext in (".vtt", ".srt"):
            side = os.path.splitext(a.source)[0] + ext
            if os.path.exists(side):
                cues, sub_src = parse_subs(side), os.path.basename(side)
                break

    # 2. media (needed for frames, or for whisper)
    media = None
    want_media = not a.no_frames or cues is None
    if want_media:
        if is_url:
            fmt = "bv*[height<=720]+ba/b[height<=720]/b" if not a.no_frames else "ba/b"
            run(["yt-dlp", "--no-playlist", "-f", fmt, "--merge-output-format", "mp4",
                 "-o", os.path.join(work, "video.%(ext)s"), a.source])
            cands = [f for f in glob.glob(os.path.join(work, "video.*")) if not f.endswith(".part")]
            media = cands[0] if cands else None
        else:
            media = a.source

    if cues is None and media:
        cues = whisper_transcribe(media)
        sub_src = "whisper" if cues else None

    duration = meta.get("duration") or (probe_duration(media) if media else None)
    meta["duration"] = duration

    lines = []
    if cues:
        cues = [(t, x) for t, x in cues if (start is None or t >= start) and (end is None or t <= end)]
        lines = group_lines(cues)
    with open(os.path.join(out, "transcript.txt"), "w", encoding="utf-8") as f:
        for t, text in lines:
            f.write(f"[{s_to_ts(t)}] {text}\n")

    frames = []
    if not a.no_frames and media:
        frames = extract_frames(media, os.path.join(out, "frames"), duration,
                                n=a.frames, every=a.every, scene=a.scene, start=start, end=end)

    meta["transcript_source"] = sub_src or "none"
    meta["frame_count"] = len(frames)
    with open(os.path.join(out, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # 3. index.md: transcript with frames interleaved at their timestamps
    with open(os.path.join(out, "index.md"), "w", encoding="utf-8") as f:
        f.write(f"# {meta.get('title') or vid}\n\n")
        for k in ("channel", "webpage_url", "upload_date"):
            if meta.get(k):
                f.write(f"- {k}: {meta[k]}\n")
        if duration:
            f.write(f"- duration: {s_to_ts(duration)}\n")
        f.write(f"- transcript: {meta['transcript_source']}\n- frames: {len(frames)}\n\n")
        if meta.get("chapters"):
            f.write("## Chapters\n\n")
            for c in meta["chapters"]:
                f.write(f"- [{s_to_ts(c['start_time'])}] {c.get('title','')}\n")
            f.write("\n")
        if meta.get("description"):
            f.write("## Description\n\n" + meta["description"].strip()[:3000] + "\n\n")
        f.write("## Timeline\n\n")
        events = [(t, "T", x) for t, x in lines] + [(t, "F", p) for t, p in frames]
        events.sort(key=lambda e: (e[0], e[1]))
        for t, kind, x in events:
            if kind == "T":
                f.write(f"[{s_to_ts(t)}] {x}\n\n")
            else:
                f.write(f"![frame {s_to_ts(t)}](frames/{os.path.basename(x)})\n\n")
        if not lines:
            f.write("_No transcript available. Rely on the frames, or run gemini-watch for audio/visual analysis._\n")

    if not a.keep_video:
        shutil.rmtree(work, ignore_errors=True)
    elif media and media.startswith(work):
        shutil.move(media, os.path.join(out, os.path.basename(media)))
        shutil.rmtree(work, ignore_errors=True)

    print(json.dumps({"out": out, "title": meta.get("title"), "duration": duration,
                      "transcript_lines": len(lines), "transcript_source": meta["transcript_source"],
                      "frames": len(frames)}, indent=2))


if __name__ == "__main__":
    main()
