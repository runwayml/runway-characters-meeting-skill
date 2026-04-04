# Runway Characters Meeting

Send a Runway AI Character to any Zoom, Google Meet, or Microsoft Teams meeting.
The character joins as a real participant tile — sees the room, hears everything,
and responds live with lip-synced video, voice, and expressions.

**Latency:** ~1.5 seconds — feels like a real video call, not a voicemail.
**Languages:** Characters speak any language — just prompt them in that language.
**Cost:** ~$0.20/min of active session (1 credit = 3 seconds, 1 credit = $0.01), billed to your Runway account.

---

## When to Activate This Skill

Activate when the user shares a meeting link and wants an AI character to join:

- "Can you join this meeting?" + meeting URL
- "Send a character to my standup" + Zoom / Meet / Teams link
- "I want an AI in this call" + link
- Pastes a meet.google.com, zoom.us, or teams.microsoft.com URL
- "Join my meeting as [name]"
- "Create my doppelganger" / "make an AI version of me"
- "Clone my voice for meetings"

Do NOT activate for general questions about the product, or for Runway video calls
(those use the video-call-agent skill, not this one).

---

## Setup

Only one thing is required:

```
RUNWAYML_API_SECRET    # get yours at https://dev.runwayml.com — starts with key_
```

If it's missing, stop and tell the user:
> You need a Runway API key. Get one free at https://dev.runwayml.com, then set:
> `export RUNWAYML_API_SECRET=your_key`

Install dependencies once (first run only):

```bash
pip install -r $SKILL_DIR/requirements.txt
```

Everything runs through a single script: `$SKILL_DIR/scripts/runway_meeting.py`

---

## Quick Path: Clone Yourself

The fastest way to get started — one command creates your face, clones your voice,
and builds the character. **Do this once. Reuse forever.**

```bash
python $SKILL_DIR/scripts/runway_meeting.py clone-yourself \
  --name        "Yining" \
  --selfie      /path/to/selfie.jpg \
  --voice-audio /path/to/voice-recording.m4a \
  --personality "You are Yining, a PM at Runway. Be concise and professional. Wait to be addressed in group calls."
```

Works with any face — human selfies, animal photos, cartoon characters, abstract art.
The voice recording should be at least 10 seconds of clear speech.

**No selfie? No recording? No problem:**

```bash
# Selfie only + preset voice:
python $SKILL_DIR/scripts/runway_meeting.py clone-yourself \
  --name "Yining" --selfie /path/to/selfie.jpg --voice "luna" \
  --personality "You are Yining..."

# All AI-generated (no uploads needed):
python $SKILL_DIR/scripts/runway_meeting.py clone-yourself \
  --name "Aria" \
  --face-description "Friendly 3D animated woman, warm smile, soft studio lighting" \
  --voice-description "A warm, friendly voice with a slight British accent" \
  --personality "You are Aria, a helpful meeting assistant."
```

The command prints a character ID. **Skip straight to the Meeting Join Workflow below.**

---

## Advanced: Create a Character Step-by-Step

For more control over each piece (face, voice, personality separately), use the
subcommands below. Otherwise, `clone-yourself` above is easier.

### Step 0 (Optional): Clone your voice

Skip this step to use one of the 30 built-in preset voices. Do this step if the user
wants the character to sound like *them*, or wants a specific custom voice.

**Clone from an audio recording** (min 10s, max 5min, under 10MB):

```bash
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --name "My Voice" \
  --audio /path/to/recording.m4a
```

**Generate a voice from a text description** (no recording needed):

```bash
# Preview first (no voice created, just a sample URL):
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --description "A warm, professional British accent, calm and articulate" \
  --preview

# Then create once satisfied:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice \
  --name "British Assistant" \
  --description "A warm, professional British accent, calm and articulate"
```

**Output:** prints a `voice ID`. Pass it to `create-character` with `--voice-id`.

```bash
# List existing custom voices:
python $SKILL_DIR/scripts/runway_meeting.py clone-voice --list
```

---

### Step 1: Check if you already have a character

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character --list
```

If a character is listed with status `✓ READY`, copy its `id` and skip to
**Meeting Join Workflow**.

### Step 2: Create a character

The skill includes default face images in `$SKILL_DIR/assets/`. Just pick a name,
voice, and personality — the face is handled automatically.

**Simplest — uses a bundled default face + preset voice:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice       "luna" \
  --personality "You are Aria, a concise and friendly AI assistant. Keep responses to 1-3 sentences. Wait to be addressed before speaking in group calls."
```

**With a custom/cloned voice** (use the ID from `clone-voice`):

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice-id    "<VOICE_UUID>" \
  --personality "You are Aria..."
```

**Specific bundled face** (pick from `$SKILL_DIR/assets/`):

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice       "luna" \
  --personality "You are Aria..." \
  --image       "$SKILL_DIR/assets/monster.png"
```

Available bundled faces: `monster.png` · `cat.png` · `warrior.png` · `boy.png`

**User's own image** (local file — auto-uploaded to Runway):

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice       "luna" \
  --personality "You are Aria..." \
  --image       "/path/to/face.jpg"
```

**HTTPS image URL:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice       "luna" \
  --personality "You are Aria..." \
  --image       "https://example.com/face.png"
```

**Generate a face from a text description** (when the user wants a custom look):

```bash
python $SKILL_DIR/scripts/runway_meeting.py create-character \
  --name        "Aria" \
  --voice       "luna" \
  --personality "You are Aria..." \
  --description "A friendly 3D animated woman, warm smile, facing camera, head and shoulders, soft studio lighting"
```

Good description patterns by personality type:
- **Warm / friendly** → soft 3D animation, Pixar-style, watercolor
- **Sharp / professional** → clean illustration, stylized portrait, low-poly
- **Playful / chaotic** → candy texture, claymation, pop art
- **Cute / wholesome** → chibi, plush toy, animal character, kawaii

**Optional: add an opening line** the character says when joining:
Add `--start-line "Hey everyone, I'm here for the standup."` to any command above.

**Output:** The command prints the character `id` and saves it to `~/.runway-characters.json`.
Store this ID — pass it to every join command. **Do NOT create a new character each time.**

---

### Available voices

| Voice | Gender | Style |
|-------|--------|-------|
| `luna` | F | Warm |
| `maya` | F | Upbeat |
| `clara` | F | Soft |
| `skye` | F | Bright |
| `victoria` | F | Firm |
| `nina` | F | Smooth |
| `emma` | F | Clear |
| `mia` | F | Youthful |
| `summer` | F | Breezy |
| `ruby` | F | Easy-going |
| `aurora` | F | Bright |
| `georgia` | F | Mature |
| `petra` | F | Forward |
| `violet` | F | Gentle |
| `adrian` | M | Smooth |
| `adam` | M | Friendly |
| `leo` | M | Easy-going |
| `felix` | M | Excitable |
| `max` | M | Upbeat |
| `zach` | M | Casual |
| `morgan` | M | Informative |
| `vincent` | M | Knowledgeable |
| `marcus` | M | Firm |
| `jasper` | M | Clear |
| `david` | M | Informative |
| `blake` | M | Gravelly |
| `drew` | M | Breathy |
| `nathan` | M | Firm |
| `roman` | M | Lively |
| `sam` | M | Even |

---

### Preset avatars (no character setup needed)

If you don't want to create a character, presets work immediately with no setup.
They have fixed appearances and no custom personality — use only as a fallback.

Available preset IDs:
`game-character` · `game-character-man` · `music-superstar` · `cat-character`
`influencer` · `tennis-coach` · `human-resource` · `fashion-designer` · `cooking-teacher`

---

## Meeting Join Workflow

### Step 0: Gather context before joining

Before joining, the agent should build context for the character.
Read any available information to create a focused, meeting-specific personality:

1. Check for a `MEMORY.md` or meeting notes file in the user's workspace
2. Ask the user for: meeting name, participants, agenda, topics, or goals
3. Read any relevant documents the user has mentioned
4. Build a concise personality override that includes this concrete context

Write the personality to a temp variable or pass it directly via `--personality`.
**Concrete details beat abstract instructions** — include real names, real topics,
real agenda items. The character will use this context during the call.

### Step 1: Join the meeting

**Custom character (recommended):**

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url  "<MEETING_URL>" \
  --avatar-id    "<CHARACTER_UUID>" \
  --personality  "<context-aware personality for this specific meeting>"
```

**With a meeting password** (for password-protected Zoom rooms):

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url      "<MEETING_URL>" \
  --avatar-id        "<CHARACTER_UUID>" \
  --meeting-password "<password>"
```

**Preset avatar (fallback — no character creation needed):**

```bash
python $SKILL_DIR/scripts/runway_meeting.py join \
  --meeting-url  "<MEETING_URL>" \
  --avatar-type  "runway-preset" \
  --preset-id    "game-character"
```

Expected output (JSON on stdout):

```json
{ "sessionId": "uuid", "status": "active" }
```

**Exit codes:**

| Code | Meaning | Action |
|------|---------|--------|
| `0` | Joined successfully | Tell user: "✓ [Character] has joined your [platform] meeting." |
| `1` | General error | Show the error message |
| `2` | Insufficient credits | Show the user: "You're out of Runway credits. Add credits at https://dev.runwayml.com/billing" — the error JSON includes a `checkoutUrl` field. |
| `3` | Bad meeting URL | Ask user for a fresh link (links expire quickly) |

Store the returned `sessionId` — you'll need it to leave or get the transcript.

### Step 2: Confirm and offer controls

> "[Character name] has joined your [Zoom / Google Meet / Teams] call.
> Say 'leave the meeting' when you want them to hang up."

---

## Leaving a Meeting

When the user says "leave", "end the call", "hang up", "remove", or similar:

```bash
python $SKILL_DIR/scripts/runway_meeting.py leave --session-id "<SESSION_ID>"
```

Confirm: "✓ [Character] has left the meeting."

**Always run transcript + save-memory after leaving:**

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --session-id  "<SESSION_ID>" \
  --save-memory \
  --avatar-id   "<CHARACTER_UUID>"
```

This saves the conversation to the character's memory so it remembers
past meetings automatically on the next join.

Also leave automatically if the conversation is ending and a session is still active.

---

## Checking Session Status

```bash
python $SKILL_DIR/scripts/runway_meeting.py status --session-id "<SESSION_ID>"
```

---

## Getting the Transcript After the Meeting

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --avatar-id  "<CHARACTER_UUID>" \
  --session-id "<SESSION_ID>"
```

Returns the full conversation transcript — what the character and participants said
during the call — captured in real-time. Call after leaving.

**Save transcript to character memory** (used automatically on next join):

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --session-id "<SESSION_ID>" \
  --save-memory \
  --avatar-id  "<CHARACTER_UUID>"
```

Or provide a custom summary instead of auto-building from the transcript:

```bash
python $SKILL_DIR/scripts/runway_meeting.py transcript \
  --session-id "<SESSION_ID>" \
  --save-memory \
  --avatar-id  "<CHARACTER_UUID>" \
  --summary    "Discussed Q3 roadmap with Alex and Sam. Key decision: launch in October."
```

The character will recall this context automatically the next time it joins a meeting.

---

## Persistent Memory

The character remembers past meetings and uses that context in future calls.

How it works:
1. After a meeting ends, run `transcript --save-memory` to save the summary
2. On the next `join`, the last 5 meeting summaries are automatically injected
   into the character's personality as context
3. The character can then reference past topics, decisions, and participants

Memory is stored locally in `~/.runway-characters.json`. Each character keeps
up to 10 past meeting summaries (oldest are dropped automatically).

---

## Languages

Characters speak any language — just instruct them in the personality:

```
You are Aria. Respond in Spanish at all times.
```

Or switch languages mid-meeting by telling the character directly in the call.
Runway characters support all major languages with full lip-sync accuracy.

---

## Personality Guidelines

When setting `--personality` for a meeting:

- Include the character's role in this specific meeting
- Add any context the user provides (names, agenda, topics)
- Keep responses short — 1–3 sentences unless asked for more
- Wait to be addressed before speaking in group calls

Example:

```
You are Aria, a helpful AI assistant joining a product review meeting.
Context: the team is reviewing the Q3 roadmap. Participants: Alex (PM), Sam (Eng).
Be concise and speak only when addressed. Keep answers under 2 sentences.
```

---

## Billing & Credits

- Cost is ~$0.20/min of active session time (1 credit = 3 seconds, 1 credit = $0.01), charged to the user's Runway account.
- If join fails with exit code `2`, the user is out of credits:
  > "You don't have enough Runway credits. Add credits at https://dev.runwayml.com → Billing."
- Always leave the session when the meeting ends to stop billing.
- Character creation is free — only active sessions cost credits.

---

## Error Recovery

| Error | Action |
|-------|--------|
| Invalid or expired meeting URL (exit 3) | Ask user for a fresh invite link |
| Credits exhausted (exit 2) | Direct to https://dev.runwayml.com → Billing |
| Character not found | Run `create --list` and pick a valid character ID |
| Server error | Retry once after 5 seconds |
| Character status PROCESSING | Wait 10–30s for READY, then retry |

---

## Notes

- Supports Zoom, Google Meet, and Microsoft Teams
- Custom characters must have status `READY` before joining — presets are always available
- `--personality` on `join` overrides the character's stored personality for that session (custom characters only)
- Never expose session IDs or API keys in messages to the user
