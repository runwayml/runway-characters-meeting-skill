# Runway Characters Meeting Skill

> Send a Runway AI Character to any Zoom, Google Meet, or Microsoft Teams meeting.
> Works with Claude Code, OpenAI agents, OpenClaw, or any agent that supports skills.

The character joins as a real participant tile — sees the room, hears everything, and
responds live with lip-synced video, voice, and expressions.

---

## Quick Start

All you need is a Runway API key and a meeting link. Everything runs through a single script.

```bash
# 1. Get your key at https://dev.runwayml.com
export RUNWAYML_API_SECRET=key_...

# 2. Install dependencies
pip install -r requirements.txt

# 3. Clone yourself (one-time — selfie + voice in one command)
python scripts/runway_meeting.py clone-yourself \
  --name        "Yining" \
  --selfie      /path/to/selfie.jpg \
  --voice-audio /path/to/voice-clip.m4a \
  --personality "You are Yining, a PM at Runway."

# 4. Send it to a meeting
python scripts/runway_meeting.py join \
  --meeting-url "https://meet.google.com/your-meeting-id" \
  --avatar-id   "<id from step 3>"

# 5. After the meeting — save transcript + memory
python scripts/runway_meeting.py transcript \
  --session-id "<id>" --save-memory --avatar-id "<id>"
```

No selfie? No voice recording? Use `--voice "luna"` for a preset voice, or
skip `clone-yourself` entirely and use a preset avatar with `--avatar-type runway-preset --preset-id game-character`.

No server to run — the hosted deployment handles all the orchestration.
Works with any face: human selfies, animal photos, cartoon characters, abstract art.

---

## Subcommands

Everything runs through `scripts/runway_meeting.py`:

| Subcommand | Description |
|------------|-------------|
| `clone-yourself` | **Fastest path.** Selfie + voice recording → character in one command. |
| `create-character` | Create a character step-by-step (face, voice, personality separately). |
| `clone-voice` | Clone your voice from audio or generate one from a description. |
| `join` | Send a character to a meeting. Auto-injects past meeting memory. |
| `leave` | Remove a character from a meeting. |
| `status` | Check if a session is still active. |
| `transcript` | Get the conversation transcript. Save to memory for future meetings. |
| `list` | List your characters and available presets. |

### Examples

```bash
# Create a character step-by-step
python scripts/runway_meeting.py create-character \
  --name "Aria" --voice luna \
  --personality "You are Aria..."

# Clone your voice
python scripts/runway_meeting.py clone-voice \
  --name "My Voice" --audio /path/to/recording.m4a

# Join with a preset (no setup needed)
python scripts/runway_meeting.py join \
  --meeting-url "https://zoom.us/j/123456789" \
  --avatar-type "runway-preset" \
  --preset-id   "game-character"

# List existing characters
python scripts/runway_meeting.py create-character --list

# List existing voices
python scripts/runway_meeting.py clone-voice --list
```

Exit codes: `0` joined · `1` error · `2` insufficient credits · `3` bad meeting URL

---

## Bundled Face Images

The `assets/` folder includes default character faces ready to use:

| File | Look |
|------|------|
| `assets/monster.png` | White furry monster |
| `assets/cat.png` | Orange cat |
| `assets/warrior.png` | Sci-fi warrior woman |
| `assets/boy.png` | 3D animated boy |

Pass any of these as `--image assets/monster.png` when creating a character.

## Preset Avatars (No Character Setup)

Use these as `--preset-id` with `--avatar-type runway-preset` for instant testing:

`game-character` · `game-character-man` · `music-superstar` · `cat-character`
`influencer` · `tennis-coach` · `human-resource` · `fashion-designer` · `cooking-teacher`

---

## Supported Platforms

| Platform | Status |
|----------|--------|
| Google Meet | ✅ |
| Zoom | ✅ |
| Microsoft Teams | ✅ |

---

## Agent Integration

1. Point your agent at this skill: https://github.com/runwayml/runway-characters-meeting-skill
2. Set `RUNWAYML_API_SECRET` in your environment
3. The agent reads `SKILL.md` and activates automatically when you share a meeting link

**Works with:** Claude Code · OpenAI agents · OpenClaw · any agent runtime that supports skills

**Example conversation:**
```
You:   Hey, can you join this standup?
       https://meet.google.com/abc-defg-hij

Agent: I'll send your character to the meeting. One moment...
       ✓ Aria has joined your Google Meet.
       Say "leave the meeting" when you want them to hang up.
```

---

## License

Apache 2.0
