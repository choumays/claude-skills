# Templates

## Video notes (`videos/<id>/notes.md`)

```markdown
# <video title>
- Channel / creator:
- URL:
- Length / upload date:
- Why it's a source: <real practitioner? shows the work? recent?>
- Routes used: watch (transcript: captions|whisper|none, frames: N) / gemini (mode)

## What it teaches
<one or two sentences>

## Procedure
1. <step> — <exact values> [mm:ss]
2. ...

## Settings, numbers, shortcuts, templates
| What | Value | Where seen |
|---|---|---|
| <export bitrate> | <12 Mbps> | frame [03:41] |

## Principles (the why)
- <rule of thumb> [mm:ss]

## Mistakes and warnings
- <pitfall> [mm:ss]

## Quality bar
- <how the creator judges a good result>

## Disagreements between transcript, frames and Gemini
- <Gemini said X at [02:10], frame shows Y> → resolved as ...

## Unverified / promotional / possibly outdated
- ...
```

## SKILL.md

```markdown
---
name: <skill-name>
description: <What it does in one sentence.> Use when <the situations and the words a
  user would say: "...", "...", or when ...>.
---

# <Skill title>

<Two or three sentences: the outcome, and the approach in a nutshell.>

## Before starting
- Inputs to ask for or find: <footage, brand guide, account access, ...>
- Tools required: <software + version, CLI, API key> and how to check for them.

## Procedure
1. <Imperative step with exact values.>
   - If <condition>: <variant>.
2. ...

## Decision rules
- <When X, do A; when Y, do B.> (from source 2 vs source 4)

## Pitfalls
- <Mistake> → <what to do instead>.

## Quality checklist (run before delivering)
- [ ] <observable check>
- [ ] ...

## Reference files
- `references/<topic>.md`: read when <situation>.

## Sources
- "<title>", <channel>, <url> (studied <date>)
```

## Agent (`.claude/agents/<role>.md`)

```markdown
---
name: <role-name>
description: <Role> specialist. Use proactively when <the tasks it should be handed:
  "...", "...">.
tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch
skills: <skill-a>, <skill-b>
model: inherit
---

You are a <role> with the working habits of the practitioners in your skills' sources.

## How you work
1. Clarify the brief: <the 2–4 things this role always needs to know>.
2. Load the relevant skill and follow its procedure; don't improvise past it when it
   covers the case.
3. <Role-specific workflow: draft → self-review against the skill's quality checklist →
   deliver.>

## Standards
- <Non-negotiables taken from the videos' quality bars.>

## Hand back
- The deliverable, where it is, what you checked, and anything you were unsure of.
```

Notes:
- `skills:` preloads the listed skills into the agent's context. Keep `tools:` to what
  the role needs; omit the field to inherit every tool.
- A role agent should stay short (under ~80 lines). Detail belongs in skills.
