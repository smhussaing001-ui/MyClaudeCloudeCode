# Paste this to your Windows Claude Code as the first message

You are automating a DaVinci Resolve Studio listicle edit. **Read `PLAYBOOK.md`
in this folder in full before doing anything** — it is the verified, correct-only
method (a human already disproved every dead-end for you; they're listed, don't
retry them).

Ground rules for this session:
- **Verify every step by reading the timeline back through the API.** Do not use
  screenshots to check your work — they waste tokens. Read clip starts/ends/names.
- Import and use the provided modules `resolve_env.py` and `audio_duck.py`; don't
  rewrite them.
- Secrets come from environment variables, never hard-coded:
  `ELEVENLABS_API_KEY` (voiceover). If it isn't set, stop and ask me to set it.
- After each write step, print a one-line read-back confirmation (counts, frames).
- Do NOT reorder/rebuild anything or delete clips unless I explicitly ask.

Do this now, in order:
1. Run the connection self-test:
   `python check_env.py`
   Report what it prints. If it fails, walk me through the fix from the
   `resolve_env.py` header (env vars / Local scripting / 64-bit Python). Stop
   until it passes.
2. Confirm prerequisites with me: (a) which Media Pool bin holds the branded
   **Fusion Composition** title, (b) the ElevenLabs **voice ID** to use, (c)
   whether markers are already placed. Also confirm ffmpeg is on PATH
   (`ffmpeg -version`).
3. Once confirmed, run the per-video LOOP from `PLAYBOOK.md` §2, pausing at the
   two human-judgement steps: after step 3 show me the cropped caption strips so
   I confirm each NAME/LINK, and after step 7 show me the rewritten scripts for
   approval before generating voiceover.

Start with step 1.
