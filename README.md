# claude-skills

Claude skills and agents.

## video-learning plugin

Teach Claude (and your agents) almost any skill from videos. Three parts that build on each other:

| Skill | What it does | Needs |
|---|---|---|
| `watch` | Turns a YouTube / TikTok / any yt-dlp URL or local file into a timestamped transcript plus still frames, on one timeline Claude can read | `yt-dlp`, `ffmpeg` (optional: `faster-whisper` for videos without captions) |
| `gemini-watch` | Has Gemini watch the actual video (picture + audio) and report the technique, a summary, a visual log, or answer a question. YouTube links go straight to Gemini, with nothing downloaded | `GEMINI_API_KEY` (free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)) |
| `video-to-skill` | The framework: finds videos, watches each one both ways, merges what they teach, and writes a new `SKILL.md` and/or a specialist subagent (video editor, social media manager, marketer...), then tests it | the two above |

### Install

**Claude Code (plugin):**

```
/plugin marketplace add choumays/claude-skills
/plugin install video-learning@choumays-skills
```

**Claude Code (plain skills):** copy `plugins/video-learning/skills/*` into `~/.claude/skills/`.

**Dependencies:**

```bash
pip install -U yt-dlp            # downloads + captions
brew install ffmpeg              # or: apt install ffmpeg
pip install faster-whisper       # optional, transcribes videos with no captions
export GEMINI_API_KEY=...        # optional but recommended, for gemini-watch
```

### Use

- "Watch this and give me the steps: <url>" → `watch`
- "Use Gemini on this video, what editing tricks does she use?" → `gemini-watch`
- "Build me a short-form video editor agent from these 5 videos: ..." → `video-to-skill`
- "Learn how to run Meta ads from the best YouTube tutorials and make it a skill" → `video-to-skill` (finds the videos itself)

Scripts can also be run directly:

```bash
python3 plugins/video-learning/skills/watch/scripts/watch.py "<url>" --scene
python3 plugins/video-learning/skills/gemini-watch/scripts/gemini_watch.py "<url>" --mode skill
```

Cloud sandboxes often block YouTube downloads. `gemini-watch` still works there because it
only calls Google's API; set `GEMINI_API_KEY` in the environment's secrets.
