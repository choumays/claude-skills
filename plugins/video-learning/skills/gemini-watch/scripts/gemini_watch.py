#!/usr/bin/env python3
"""Ask Gemini about a video. Gemini watches the actual video (pictures + audio),
and takes public YouTube URLs directly, with nothing downloaded locally.

Usage:
  gemini_watch.py <youtube-url | other-url | local-file> [--mode MODE | --prompt TEXT]
                  [--start 1:30] [--end 4:00] [--fps 1] [--model NAME] [--out FILE]

Modes:
  skill     (default) extract the skill being taught: steps, settings, tools, mistakes
  summary   what the video says and shows, with timestamps
  timeline  dense second-by-second log of what is on screen and said
  visual    only what is SEEN: on-screen text, UI, settings, gestures, edits
  transcript  verbatim transcript with timestamps

Needs GEMINI_API_KEY (free from https://aistudio.google.com/apikey).
Non-YouTube URLs (TikTok, Instagram...) are downloaded with yt-dlp and uploaded
through the Gemini Files API. Uses only the Python standard library.
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

PROMPTS = {
    "skill": """You are studying this video to learn the skill it teaches, so that the
knowledge can be written into an instruction manual for an AI agent.

Report, citing [mm:ss] timestamps throughout:
1. SKILL: one sentence naming the skill or outcome being taught.
2. PREREQUISITES: tools, software (with versions if shown), materials, accounts, prior knowledge.
3. PROCEDURE: numbered, concrete steps in order. Include every specific value that is
   shown or said: settings, numbers, menu paths, shortcuts, durations, quantities, prompts,
   code, wording. Note what is only SHOWN on screen and never said aloud.
4. PRINCIPLES: the reasoning and rules of thumb behind the steps (the "why").
5. MISTAKES: pitfalls, warnings, and what bad results look like.
6. QUALITY BAR: how the creator judges a good result.
7. CLAIMS TO VERIFY: anything promotional, unverified, or likely out of date.
Be specific and exhaustive; do not pad. If something is unclear, say so rather than guess.""",
    "summary": """Summarize this video. Give: the main point in two sentences; then the key
points as bullets with [mm:ss] timestamps; then anything shown on screen that matters
but is not said aloud (text, links, settings, code, products).""",
    "timeline": """Produce a dense timeline of this video. For each moment of change, one
line: [mm:ss] SAID: ... | SHOWN: ... . Capture on-screen text verbatim, UI elements,
cuts, transitions, gestures and demonstrations. Do not summarize; log.""",
    "visual": """Describe only what is visible in this video, not what is said. With
[mm:ss] timestamps, list: on-screen text and captions verbatim, software/UI and the exact
settings or menus used, physical actions and technique (hands, tools, posture), editing
techniques (cuts, zooms, B-roll, captions style, pacing), and any links or handles shown.""",
    "transcript": """Transcribe the speech in this video verbatim, with a [mm:ss] timestamp at
the start of each sentence or speaker turn. Label speakers if there are several.""",
}


def key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        sys.exit("GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
                 "and export GEMINI_API_KEY=...")
    return k


def request(url, data=None, headers=None, method=None, raw=False):
    h = {"x-goog-api-key": key()}
    h.update(headers or {})
    body = data if isinstance(data, (bytes, type(None))) else json.dumps(data).encode()
    if body is not None and "Content-Type" not in h and not raw:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.headers, r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        sys.exit(f"Gemini API error {e.code}: {detail[:2000]}")


def to_seconds(v):
    if v is None:
        return None
    s = 0.0
    for x in str(v).split(":"):
        s = s * 60 + float(x)
    return s


def is_youtube(u):
    return re.match(r"https?://(www\.|m\.)?(youtube\.com|youtu\.be)/", u) is not None


def upload(path):
    """Upload a local file with the Files API and wait until it is ACTIVE."""
    size = os.path.getsize(path)
    mime = mimetypes.guess_type(path)[0] or "video/mp4"
    hdrs, _ = request(f"{API}/upload/v1beta/files", {"file": {"display_name": os.path.basename(path)}}, {
        "X-Goog-Upload-Protocol": "resumable",
        "X-Goog-Upload-Command": "start",
        "X-Goog-Upload-Header-Content-Length": str(size),
        "X-Goog-Upload-Header-Content-Type": mime,
    })
    upload_url = hdrs.get("x-goog-upload-url")
    if not upload_url:
        sys.exit("Files API did not return an upload URL")
    with open(path, "rb") as f:
        data = f.read()
    _, body = request(upload_url, data, {
        "Content-Length": str(size),
        "X-Goog-Upload-Offset": "0",
        "X-Goog-Upload-Command": "upload, finalize",
    }, raw=True)
    info = json.loads(body)["file"]
    print(f"uploaded {path} -> {info['name']}, waiting for processing...", file=sys.stderr)
    for _ in range(120):
        if info.get("state") == "ACTIVE":
            return info
        if info.get("state") == "FAILED":
            sys.exit(f"Gemini could not process the file: {info}")
        time.sleep(5)
        _, body = request(f"{API}/v1beta/{info['name']}")
        info = json.loads(body)
    sys.exit("timed out waiting for the uploaded file to become ACTIVE")


def download(url, tmpdir):
    if not shutil.which("yt-dlp"):
        sys.exit("Gemini only reads YouTube links directly. Install yt-dlp (pip install yt-dlp) "
                 "to download other sites first, or pass a local file.")
    out = os.path.join(tmpdir, "video.%(ext)s")
    p = subprocess.run(["yt-dlp", "--no-playlist", "-f", "b[height<=720]/bv*[height<=720]+ba/b",
                        "--merge-output-format", "mp4", "-o", out, url], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"yt-dlp failed:\n{p.stderr[-2000:]}")
    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.startswith("video.")]
    return files[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--mode", choices=sorted(PROMPTS), default="skill")
    ap.add_argument("--prompt", help="custom question (overrides --mode)")
    ap.add_argument("--start", help="clip start, e.g. 1:30")
    ap.add_argument("--end", help="clip end, e.g. 4:00")
    ap.add_argument("--fps", type=float, help="frames per second Gemini samples (default 1; raise for fast action)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--out", help="also write the answer to this file")
    a = ap.parse_args()
    key()

    part = {}
    tmp = None
    if re.match(r"https?://", a.source) and is_youtube(a.source):
        part["fileData"] = {"fileUri": a.source}
    else:
        path = a.source
        if re.match(r"https?://", a.source):
            tmp = tempfile.mkdtemp(prefix="gemini-watch-")
            path = download(a.source, tmp)
        if not os.path.exists(path):
            sys.exit(f"no such file: {path}")
        if os.path.getsize(path) < 15 * 1024 * 1024:
            mime = mimetypes.guess_type(path)[0] or "video/mp4"
            part["inlineData"] = {"mimeType": mime,
                                  "data": base64.b64encode(open(path, "rb").read()).decode()}
        else:
            f = upload(path)
            part["fileData"] = {"fileUri": f["uri"], "mimeType": f.get("mimeType", "video/mp4")}

    vm = {}
    if a.start:
        vm["startOffset"] = f"{to_seconds(a.start):.0f}s"
    if a.end:
        vm["endOffset"] = f"{to_seconds(a.end):.0f}s"
    if a.fps:
        vm["fps"] = a.fps
    if vm:
        part["videoMetadata"] = vm

    prompt = a.prompt or PROMPTS[a.mode]
    body = {"contents": [{"parts": [part, {"text": prompt}]}]}
    _, resp = request(f"{API}/v1beta/models/{a.model}:generateContent", body)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)

    data = json.loads(resp)
    cands = data.get("candidates") or []
    if not cands:
        sys.exit(f"no answer from Gemini: {json.dumps(data)[:2000]}")
    text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
    if not text:
        sys.exit(f"empty answer (finishReason={cands[0].get('finishReason')})")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(f"<!-- source: {a.source} | model: {a.model} | mode: {a.prompt and 'custom' or a.mode} -->\n\n")
            f.write(text + "\n")
    print(text)
    usage = data.get("usageMetadata", {})
    if usage:
        print(f"\n[tokens: prompt={usage.get('promptTokenCount')} "
              f"output={usage.get('candidatesTokenCount')}]", file=sys.stderr)


if __name__ == "__main__":
    main()
