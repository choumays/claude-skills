---
name: watch
description: Watch a video the way Claude can, by turning it into a timestamped transcript plus still frames. Works with YouTube, TikTok, Instagram, Vimeo, X and any other site yt-dlp supports, or a local video file. Use whenever the user shares a video link or file, asks "watch this", "what does this video say/show", wants notes, steps, a summary or quotes from a video, or wants to learn a technique from a tutorial.
---

# watch

Claude can't play video, but it can read text and look at images. This skill cuts a
video into both: the captions (or a Whisper transcript) and a set of frames, laid out
on one timeline in `index.md`.

## Requirements

- `yt-dlp` for URLs: `pip install -U yt-dlp`
- `ffmpeg` / `ffprobe` for frames: `apt install ffmpeg` or `brew install ffmpeg`
- Optional, for videos with no captions: `pip install faster-whisper` (or `openai-whisper`)

Check them before the first run: `yt-dlp --version && ffmpeg -version | head -1`.
If one is missing, install it or tell the user what to install.

## Run

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/watch.py "<url-or-file>" --out watch/<short-name>
```

When the skill is installed outside a plugin, the script sits next to this file in `scripts/watch.py`.

Pick the frame mode based on the video:

| Video type | Flags |
|---|---|
| Talking head, podcast, lecture with no visuals | `--no-frames` (transcript only, fastest) |
| Tutorial, screen recording, slides, software demo | `--scene` (one frame per visual change, max 60) |
| Physical skill: cooking, editing, a sport, a craft | `--every 5` for close detail, or `--frames 40` |
| Long video, only one part matters | `--start 12:00 --end 18:30` |
| Short (TikTok/Reels/Shorts) | defaults are fine (8+ frames) |

Other flags: `--lang fr` for subtitles in another language; `--keep-video` keeps the mp4.

## Read the output

1. Read `index.md` first. It holds the metadata, chapters, description and a timeline
   where transcript paragraphs and frame links are interleaved by timestamp.
2. Open frames with the Read tool when the transcript points at something visual
   ("click here", "like this", "see the settings", on-screen text, diagrams, code).
   Don't open every frame for a talking-head video; do open most of them for a screen
   tutorial or a physical demonstration.
3. Cite timestamps (`[04:12]`) in what you tell the user so they can jump to the moment.

## When it fails

- **No transcript and no Whisper**: the frames still work. For audio content, use the
  `gemini-watch` skill, which hears the audio itself.
- **Sign-in / age / region / bot check errors from yt-dlp**: update it
  (`pip install -U yt-dlp`), then retry with `--cookies-from-browser chrome` added to the
  yt-dlp calls, or fall back to `gemini-watch` for public YouTube videos.
- **Network blocked** (cloud sandboxes often block YouTube): say so plainly and suggest
  running locally, or `gemini-watch`, which only needs to reach Google's API.

## Going further

To turn several videos into a reusable skill or agent, use the `video-to-skill` skill.
It calls this one for each video.
