---
name: video-to-skill
description: Turn videos into a reusable Claude skill or a specialist subagent (e.g. a video editor, social media manager, marketing specialist, or any expert role). Studies one or many YouTube/TikTok videos with the watch and gemini-watch skills, cross-checks what they teach, and writes a SKILL.md and/or agent file with the procedures, settings, principles and pitfalls. Use when the user says "learn this from the video", "teach Claude/my agent to do X", "build a skill/agent from these videos", "turn this tutorial into a skill", or shares a video and says "build this".
---

# video-to-skill

The pipeline: **find videos → watch each one twice (transcript+frames, then Gemini) →
merge into one knowledge base → write a skill and/or an agent → test it on a real task.**

Work in a folder such as `learn/<skill-name>/`; everything below lands there.

## 1. Pin down the target (ask only what you can't infer)

- **Role or skill**: "short-form video editor", "Facebook ads buyer", "bread baker".
- **Output**: a *skill* (instructions any session can load), an *agent* (a specialist
  persona with its own tools that loads those skills), or both. A role that bundles
  several skills ("social media manager") → both. One technique → a skill.
- **Where it lives**: project (`.claude/skills/`, `.claude/agents/`), personal
  (`~/.claude/skills/`, `~/.claude/agents/`), or this repo as a plugin.
- **Sources**: the user's links. If they gave none or only one for a broad skill, find
  3–8 strong ones (see step 2).

## 2. Collect sources

Prefer: practitioners showing their real work, recent uploads for fast-moving tools,
and videos with on-screen detail. Avoid: hype with no demonstration, reuploads.

```bash
# search YouTube without a browser (titles, channel, length, views, url)
yt-dlp "ytsearch15:<topic> tutorial" --flat-playlist \
  --print "%(title)s | %(channel)s | %(duration_string)s | %(view_count)s | %(url)s"
```

WebSearch also works. Keep a `sources.md` list with why each one was chosen.

## 3. Watch each video, two ways

For each source (run independent videos in parallel subagents when there are several):

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/watch/scripts/watch.py "<url>" --out learn/<skill>/videos/<id> --scene
python3 ${CLAUDE_PLUGIN_ROOT}/skills/gemini-watch/scripts/gemini_watch.py "<url>" --mode skill \
  --out learn/<skill>/videos/<id>/gemini-skill.md
```

(Outside a plugin, the scripts are in the sibling skill folders `../watch/scripts/` and `../gemini-watch/scripts/`.)

- Use the frame mode that fits the video (see the `watch` skill's table). For editing or
  other visual crafts, add `--mode visual` to Gemini too.
- If one route fails (no key, YouTube blocked, no captions) continue with the other and
  note the gap. If both fail, stop and tell the user what's needed.
- Then read `index.md`, open the frames that matter, and write
  `videos/<id>/notes.md` using the **video notes** template in
  `references/templates.md`. Every concrete value gets a timestamp.

## 4. Merge into one knowledge base

Write `learn/<skill>/knowledge.md`:

- **Consensus**: what several sources agree on → becomes the default procedure.
- **Variants**: where sources differ, record both with the conditions under which each
  wins ("A for talking heads, B for product demos").
- **Specifics**: exact settings, numbers, shortcuts, templates, prompts, checklists.
- **Judgment**: the principles behind the steps, and what "good" looks like.
- **Unverified**: single-source claims, promotional claims, things that may be outdated.
  Check software claims against current docs when you can.

Leave out filler, sponsor reads, and anything you can't tie to a source.

## 5. Write the skill

Follow the **SKILL.md** template in `references/templates.md`. Rules:

- `name`: lowercase-hyphenated. `description`: what it does AND when to trigger it,
  with the words a user would actually say. This line decides whether the skill fires.
- Body under ~300 lines, written as instructions to Claude ("Do X. Check Y."), not as a
  summary of videos. Procedure first, then decision rules, then pitfalls, then a
  quality checklist.
- Push long material (full setting tables, prompt libraries, per-platform specs) into
  `references/*.md` and say in the body when to read each one.
- Add `scripts/` only for steps that are deterministic and repeated (an ffmpeg export
  preset, a caption formatter). Test every script you add.
- End with a **Sources** section: video title, channel, URL, date studied.

## 6. Write the agent (if requested)

Follow the **agent** template in `references/templates.md`, saved to
`.claude/agents/<role>.md` (or `agents/<role>.md` inside a plugin). The agent file holds
the role, judgment and workflow; the skills hold the know-how. List the skills it should
use in the `skills:` field and restrict `tools:` to what the role needs. One agent can
draw on several video-built skills (a "social media manager" = scripting + editing +
posting-strategy skills).

## 7. Test, then tighten

1. Write 2–3 realistic tasks the user would actually give this skill/agent.
2. Run each with a fresh subagent that has only the new skill/agent (not your notes).
3. Compare the output against the videos' quality bar. Where it went wrong, the skill
   was vague or missing a step: fix the skill text, not the test.
4. Report to the user: what was learned, from which videos, where the files are, how
   to invoke it, what's unverified, and any setup it needs.

## Ethics and limits

- Distill technique in your own words with attribution; don't paste transcripts
  wholesale into a skill or republish a creator's paid material.
- A skill encodes what the videos show. Flag where real-world practice, a license,
  or safety training is needed (electrical, medical, financial, legal).
