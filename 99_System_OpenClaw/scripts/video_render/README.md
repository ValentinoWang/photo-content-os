# Local video renderer

These entrypoints only consume local files and write local candidates. They do not
call TTS, ASR or models, overlay teaching clips, export editor projects, or upload
anything. The caller supplies already generated PCM WAV narration and HTML.

```json
{
  "width": 1920,
  "height": 1080,
  "fps": 30,
  "assets_dir": "assets",
  "fonts": [{"path": "assets/approved-font.ttf"}],
  "timeout_seconds": 120,
  "narration_wav": "narration.wav",
  "shots": [
    {"id": "intro", "html": "intro.html", "frames": 60, "start_frame": 0},
    {"id": "explain", "html": "explain.html", "frames": 90, "start_frame": 60,
     "animation_requirement": "Approved animation requirement",
     "spoken_text": "The corresponding spoken sentence"}
  ]
}
```

This is a private renderer input, not a new cloud task or receipt protocol. Paths
for `assets_dir`, fonts and WAVs resolve against the manifest directory; HTML paths
resolve against `assets_dir`. Resource URLs resolve relative to the HTML, within
`assets_dir`. Symlink escapes and remote requests fail. Width and height must be
even. FPS and frame counts are positive integers. `start_frame` may be omitted;
when present it must match the contiguous schedule. No time interpolation occurs.
Instead of a global WAV, every shot may declare its own `narration_wav`; mixing
the two modes fails. Narration must match its schedule within one frame. The final
audio is trimmed/padded only within that tolerance. Teaching clips require no WAV.

Each HTML must define `window.seekFrame(frame, fps)`, which may return a Promise.
The hook must set the entire visual state for that frame, including any canvas.
For canvas text, use the pinned family `PCPinned0` and draw inside the hook.
Wall-clock timers and requestAnimationFrame do not drive shots. CSS/Web Animations
are paused and seeked to `frame * 1000 / fps`. Images must finish decoding before
capture. Audio/video elements are rejected; pre-extract them to local still frames.
Browser time, timezone, locale, device scale, RNG seed and DOM font are fixed.
The optional per-shot `seed` is a uint32 (default 1).

Use one pinned Playwright installation and browser build for repeatability. Set
`VIDEO_RENDER_PLAYWRIGHT_MODULE` to its absolute module entrypoint if Playwright
is not installed in this repository. `browser_executable` is optional; omission
uses that Playwright installation's Chromium. No dependency is installed by these
scripts. Missing Node, Playwright, browser, fonts, FFmpeg or FFprobe fails explicitly.
Cache keys include runtime identity, renderer source, HTML, fonts and frame settings;
actual consumed resources and every PNG are hash-checked. Changing only narration
does not rerender frames. Repairing a failed shot reuses the other verified shots.

```bash
99_System_OpenClaw/.venv-content-os/bin/python \
  99_System_OpenClaw/scripts/video_render/multi_shot.py \
  --manifest /local/job/manifest.json --output /local/job/frames-run

99_System_OpenClaw/.venv-content-os/bin/python \
  99_System_OpenClaw/scripts/video_render/compose.py \
  --manifest /local/job/manifest.json --output /local/job/direct-run

99_System_OpenClaw/.venv-content-os/bin/python \
  99_System_OpenClaw/scripts/video_render/teaching_clips.py \
  --manifest /local/job/manifest.json --output /local/job/teaching-run --transparent
```

`compose.py` produces `candidate.mp4` (H.264/AAC) after frame-count, duration,
track, input-hash and full-decode checks. Its status is in `compose-status.json`.
`multi_shot.py` writes `shot-status.json` with per-shot `completed` / `failed`,
failure code/reason, frame progress, attempts and `cached`. Frame progress is also
flushed as JSON lines on stdout while rendering. Status codes are machine values;
the frontend must map them using its approved copy contract. Local file paths and
diagnostics must stay local. Only a successful current receipt authorizes use of
the candidate; an earlier candidate can remain after a later failed run.

`teaching_clips.py` exports independent silent H.264 MP4 clips by default, or ProRes
4444 MOV with alpha for `--transparent`, plus `teaching-clips.json`. Its metadata
preserves `animation_requirement` and `spoken_text` for the editing handoff. The
editing software owns placement/overlay. Transparency requires transparent HTML
backgrounds. No automatic fallback changes the requested format.

Use separate output directories for direct composition and teaching export. Each
export takes an exclusive lock and refuses unowned or source-overlapping output
directories. Failed outputs are not reported as candidates. After abnormal process
termination, inspect the recorded lock owner before manually removing a stale lock.
Only subprocess groups created for the current shot are terminated on completion
or timeout. Raw inputs and historical editor projects are never edited.

Tests: `tests/test_video_render.py` runs with unittest or pytest. Configure
`VIDEO_RENDER_PLAYWRIGHT_MODULE` to enable the real-browser tests; without it they
are explicitly skipped. Optional `VIDEO_RENDER_TEST_FONT` and
`VIDEO_RENDER_TEST_BROWSER` select the pinned local test runtime. Fixtures use
temporary directories and FFmpeg sine narration, with no paid calls.
