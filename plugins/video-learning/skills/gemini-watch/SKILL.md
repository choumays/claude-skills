---
name: gemini-watch
description: Have Google Gemini actually watch a video (moving picture and audio together) and report back. Gemini reads public YouTube links natively, so nothing is downloaded. Use when a video's value is visual or in the audio (editing technique, physical demonstrations, software walkthroughs, music, tone), when the watch skill finds no captions, when YouTube downloads are blocked, or when the user asks to use Gemini on a video.
---

# gemini-watch

Gemini models take a YouTube URL as input and sample the video (about one frame per
second, plus the audio track). That gives a second, independent view of a video that
catches what a transcript misses: what was clicked, how a cut was timed, what the hands did.

## Setup (one time)

1. Get a free API key at https://aistudio.google.com/apikey (Google AI Studio).
2. Make it available: `export GEMINI_API_KEY=...` (shell profile, or the environment's
   secrets in a cloud session). Never write the key into a repository file.

The script uses only the Python standard library. `yt-dlp` is needed only for
non-YouTube links (TikTok, Instagram, etc.), which are downloaded then uploaded.

## Run

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/gemini-watch/scripts/gemini_watch.py "<url-or-file>" \
  --mode skill --out watch/<short-name>/gemini-skill.md
```

When the skill is installed outside a plugin, the script sits next to this file in `scripts/gemini_watch.py`.

| Goal | Flags |
|---|---|
| Learn the technique being taught (default) | `--mode skill` |
| Quick overview with timestamps | `--mode summary` |
| Everything on screen, moment by moment | `--mode timeline` |
| Only what is shown, not said (editing, UI, hands) | `--mode visual` |
| Verbatim transcript (no captions available) | `--mode transcript` |
| A specific question | `--prompt "What export settings does he use at the end?"` |
| One section of a long video | `--start 10:00 --end 14:30` |
| Fast action (sports, quick edits) | `--fps 5` (costs more tokens) |
| A different model | `--model <name>` or `export GEMINI_MODEL=<name>` |

Default model: `gemini-2.5-flash`. If Google has retired it, pick a current Flash or Pro
model from https://ai.google.dev/gemini-api/docs/models and pass it with `--model`.

## Using the answer

- Treat Gemini's report as a second witness, not the truth. When it disagrees with the
  transcript from `watch`, check the frame at that timestamp.
- It can hallucinate specific numbers. Values that matter (settings, quantities, code)
  should be confirmed against a frame or the transcript before going into a skill.
- Free-tier limits: a few requests per minute and a daily cap on video length. On a 429
  error, wait a minute and retry, or split the video with `--start/--end`.
- Private, unlisted-with-restrictions, or age-gated YouTube videos can't be read by URL;
  download them locally (with permission) and pass the file instead.

Video content and the question are sent to Google. Don't send private or confidential
recordings without the user's go-ahead.
