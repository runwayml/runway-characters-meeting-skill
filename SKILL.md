---
name: runway-characters-meeting
description: |
  Send a Runway AI Character to any Zoom, Google Meet, or Microsoft Teams meeting.
  The character joins as a real participant — sees the room, hears everything, and
  responds live with lip-synced video, voice, and expressions. Use this skill whenever
  the user wants to send an AI character or avatar to a video call, clone themselves
  for a meeting, create a digital twin, or mentions a meeting link (meet.google.com,
  zoom.us, teams.microsoft.com) and wants an AI to join it. Also triggers for voice
  cloning for meetings, creating characters for calls, or getting post-call transcripts.
metadata:
  openclaw:
    emoji: "🎭"
    requires:
      env: ["RUNWAYML_API_SECRET"]
      bins: ["python3"]
    primaryEnv: "RUNWAYML_API_SECRET"
    source: "https://docs.dev.runwayml.com"
    repository: "https://github.com/runwayml/runway-characters-meeting-skill"
---

# Runway Characters Meeting

Script: `SKILL_DIR` refers to this skill's root directory.

All commands run through a single script: `$SKILL_DIR/scripts/runway_meeting.py`

## First-Time Setup

Run once when the skill is first loaded:

```bash
pip install -r $SKILL_DIR/requirements.txt
```

### 1. API Key

Check if `RUNWAYML_API_SECRET` is set. If not, stop and tell the user:

> You need a Runway API key. Get one free at https://dev.runwayml.com, then set:
> `export RUNWAYML_API_SECRET=key_...`

**Do not proceed without a valid API key.**

### 2. Character

Check if the user already has a character by running:

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character --list
```

**If a character exists with status `✓ READY`:** use its ID. Skip to Join Flow.

**If no characters exist:** guide the user through character creation. Ask:

> I need to set up a character for your meetings. You have three options:
> 1. **Clone yourself** — send me a selfie and a voice recording (10s–2min), and I'll create your digital twin
> 2. **Quick start** — I'll create a custom character with a bundled avatar and a preset voice
> 3. **Use a preset** — jump into a meeting instantly with a ready-made character (no setup needed):
>    `game-character` · `game-character-man` · `music-superstar` · `cat-character` · `influencer` · `tennis-coach` · `human-resource` · `fashion-designer` · `cooking-teacher`
>
> Which do you prefer? (or just send me a selfie to get started)

**Do not proceed until the user responds.** Do not auto-create.

**User chooses a preset:** skip character creation entirely. Use the preset ID directly in the join command:

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url  "<MEETING_URL>" \
  --avatar-type  "runway-preset" \
  --preset-id    "<preset-id>"
```

No personality, voice, or face setup needed. Skip to Join Flow.

**User chooses clone-yourself:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py clone-yourself \
  --name        "<user's name>" \
  --selfie      <path-to-selfie> \
  --voice-audio <path-to-recording> \
  --personality "<personality — see Personality Guidelines below>"
```

If the user only has a selfie but no voice recording, use `--voice "luna"` instead of `--voice-audio`.
If the user has no selfie, use `--face-description "<description>"` or omit for the bundled default.

**User chooses quick start:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name  "<name>" \
  --voice "luna" \
  --personality "<personality>"
```

This uses a bundled default face from `$SKILL_DIR/assets/`. Available bundled faces:
`monster.png` · `cat.png` · `warrior.png` · `boy.png`

To use a specific one: `--image "$SKILL_DIR/assets/cat.png"`

**Output:** the command prints a character ID and saves it to `~/.runway-characters.json`.
Store this ID — reuse it for every join. **Do NOT create a new character each time.**

### 3. Voice (optional, for advanced users)

If the user wants a custom voice separately (not through clone-yourself), use:

```bash
# Clone from audio recording:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --name "My Voice" --audio <path-to-recording>

# Or generate from text description:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --name "My Voice" \
  --description "A warm, professional voice with a calm tone"

# Preview before creating:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --description "A warm, professional voice" --preview
```

Voice cloning requires 10s–2min of clear speech, under 10MB. Text descriptions must be at least 20 characters.
Runway voices do not expire — once created, they're available forever.

Pass the voice ID to character creation: `--voice-id <VOICE_UUID>`

```bash
# List existing custom voices:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice --list
```

---

## Join Flow

### Step 1 — Validate before joining

Before every join, check these in order:

1. **API key:** `RUNWAYML_API_SECRET` must be set
2. **Character:** confirm the character ID is valid (check `~/.runway-characters.json` or run `create-character --list`)
3. **Meeting URL:** must be a valid Zoom, Google Meet, or Teams link

If any check fails, guide the user to fix it before proceeding.

### Step 2 — Gather context

Always gather fresh context before joining — do not reuse stale context from a previous session.

1. Read any available workspace files (MEMORY.md, daily logs, meeting notes, project docs)
2. If no workspace data is available, ask the user: `What's this meeting about? Any names, topics, or agenda items I should know?`
3. Synthesize a concise, meeting-specific personality override:

```
Synthesize the information below into a concise reference card for {name} to use
during a voice/video call. Use third-person throughout. Prioritize CONCRETE DETAILS.

PRIORITY ORDER:
1. SPECIFIC FACTS: names, places, dates, numbers, events
2. RECENT ACTIVITY: what happened today/this week — actions, not vibes
3. RELATIONSHIPS: who matters, specific interactions
4. PERSONALITY: 1-2 sentences MAX

CURATION RULES:
- KEEP: anything with a proper noun, a number, a date, or a concrete action
- DROP: vague descriptions, routine status updates, empty entries
- MERGE: if multiple entries say similar things, pick the most vivid one

OUTPUT FORMAT:

**{name}**: [1 sentence — tone/vibe]

**Known facts** (concrete only, max 10):
- [specific fact with names/dates/numbers]

**Recent activity**:
- [built X, fixed Y, went to Z]

**Right now**: [1 line — current activity]

**People**: [name — 1 specific detail each]

RULES:
- Concrete > abstract
- Actions > descriptions
- Do not invent facts
- If data is thin, keep it short — don't pad with filler
```

### Step 3 — Join the meeting

**Custom character (recommended):**

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url  "<MEETING_URL>" \
  --avatar-id    "<CHARACTER_UUID>" \
  --personality  "<context-aware personality from Step 2>"
```

**With a meeting password** (for password-protected Zoom rooms):

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url      "<MEETING_URL>" \
  --avatar-id        "<CHARACTER_UUID>" \
  --meeting-password "<password>"
```

**Custom display name** (defaults to the character's name):

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url "<MEETING_URL>" \
  --avatar-id   "<CHARACTER_UUID>" \
  --bot-name    "Yining's AI"
```

**Preset avatar (fallback — no character creation needed):**

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url  "<MEETING_URL>" \
  --avatar-type  "runway-preset" \
  --preset-id    "game-character"
```

Available preset IDs:
`game-character` · `game-character-man` · `music-superstar` · `cat-character`
`influencer` · `tennis-coach` · `human-resource` · `fashion-designer` · `cooking-teacher`

**Exit codes:**

| Code | Meaning | What to tell the user |
|------|---------|----------------------|
| `0` | Joined successfully | "✓ [Name] has joined your meeting." |
| `1` | General error | Show the error message |
| `2` | Insufficient credits | "You're out of Runway credits. Add more at https://dev.runwayml.com/billing" |
| `3` | Bad meeting URL | "That meeting link may have expired. Can you send a fresh one?" |

Store the returned `sessionId` internally — **never expose session IDs to the user.**

### Step 4 — Confirm and offer controls

Tell the user:

> ✓ [Character name] has joined your [Zoom / Google Meet / Teams] call.
> Say "leave the meeting" when you want them to hang up.

---

## Leave Flow

When the user says "leave", "end the call", "hang up", "remove", or similar:

```bash
python $SKILL_DIR/scripts/runway_meeting.py leave --session-id "<SESSION_ID>"
```

Tell the user: "✓ [Name] has left the meeting."

**Always run transcript + save-memory immediately after leaving:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --session-id  "<SESSION_ID>" \
  --save-memory \
  --avatar-id   "<CHARACTER_UUID>"
```

This saves the conversation to the character's persistent memory so it remembers past meetings automatically on the next join. The last 5 meeting summaries are injected into context on every future join.

Also leave automatically if the conversation is ending and a session is still active.

---

## Checking Session Status

```bash
python $SKILL_DIR/scripts/runway_meeting.py status --session-id "<SESSION_ID>"
```

---

## Getting the Transcript

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --avatar-id  "<CHARACTER_UUID>" \
  --session-id "<SESSION_ID>"
```

Returns the full conversation transcript after the call ends.

**Save with a custom summary** (instead of auto-building from transcript):

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --session-id "<SESSION_ID>" \
  --save-memory \
  --avatar-id  "<CHARACTER_UUID>" \
  --summary    "Discussed Q3 roadmap with Alex and Sam. Key decision: launch in October."
```

---

## Personality Guidelines

When building the `--personality` for a meeting, follow these principles:

- **Concrete details beat abstract instructions** — include real names, real topics, real agenda items
- Include the character's role in this specific meeting
- Keep responses short: 1–3 sentences unless asked for more
- Wait to be addressed before speaking in group calls
- Characters speak any language — just instruct them in the personality (e.g., "Respond in Spanish at all times")

Example:

```
You are Aria, a helpful AI assistant joining a product review meeting.
Context: the team is reviewing the Q3 roadmap. Participants: Alex (PM), Sam (Eng).
Be concise and speak only when addressed. Keep answers under 2 sentences.
```

---

## Available Voices

30 built-in preset voices (no setup needed):

| Voice | Gender | Style | | Voice | Gender | Style |
|-------|--------|-------|-|-------|--------|-------|
| `luna` | F | Warm | | `adrian` | M | Smooth |
| `maya` | F | Upbeat | | `adam` | M | Friendly |
| `clara` | F | Soft | | `leo` | M | Easy-going |
| `skye` | F | Bright | | `felix` | M | Excitable |
| `victoria` | F | Firm | | `max` | M | Upbeat |
| `nina` | F | Smooth | | `zach` | M | Casual |
| `emma` | F | Clear | | `morgan` | M | Informative |
| `mia` | F | Youthful | | `vincent` | M | Knowledgeable |
| `summer` | F | Breezy | | `marcus` | M | Firm |
| `ruby` | F | Easy-going | | `jasper` | M | Clear |
| `aurora` | F | Bright | | `david` | M | Informative |
| `georgia` | F | Mature | | `blake` | M | Gravelly |
| `petra` | F | Forward | | `drew` | M | Breathy |
| `violet` | F | Gentle | | `nathan` | M | Firm |
| | | | | `roman` | M | Lively |
| | | | | `sam` | M | Even |

Or clone your own voice — see First-Time Setup above.

---

## Persistent Memory

The character remembers past meetings and uses that context in future calls.

How it works:
1. After a meeting ends, run `transcript --save-memory` to save the summary
2. On the next `join`, the last 5 meeting summaries are automatically injected into context
3. The character can then reference past topics, decisions, and participants

Memory is stored locally in `~/.runway-characters.json`. Each character keeps up to 10 summaries (oldest are dropped automatically).

---

## Billing & Credits

- **Cost:** ~$0.20/min of active session (1 credit = 3 seconds, 1 credit = $0.01)
- Character creation is free — only active sessions cost credits
- Always leave the session when the meeting ends to stop billing
- If join fails with exit code `2`, tell the user to add credits at https://dev.runwayml.com/billing

---

## Error Recovery

| Error | Action |
|-------|--------|
| Invalid or expired meeting URL (exit 3) | Ask user for a fresh invite link |
| Credits exhausted (exit 2) | Direct to https://dev.runwayml.com/billing |
| Character not found | Run `create-character --list` and pick a valid ID |
| Server error | Retry once after 5 seconds |
| Character status PROCESSING | Wait 10–30s for READY, then retry |

---

## Notes

- Supports Zoom, Google Meet, and Microsoft Teams
- Custom characters must have status `READY` before joining — presets are always available
- `--personality` on `join` overrides the character's stored personality for that session only
- Works with any face: human selfies, animal photos, cartoon characters, abstract art
- Latency: ~1.5 seconds — feels like a real video call
- Never expose session IDs, API keys, or internal details in messages to the user
