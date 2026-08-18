# Edit plan

The edit plan is the hand-off between the analysis tools and the LLM that writes the Resolve script. It is plain JSON: the LLM only translates it into Resolve API calls, it does not have to guess timings.

Status: **draft v0.1**.

- `build_edit_plan` (beat-sync server) drafts a plan from a song and clips, with cuts on the beat.
- `validate_plan` checks a plan before Resolve runs it: files exist, `in`/`out` fit inside each clip, no overlaps on a track, and clips start on a beat (within `beat_tolerance_frames`). Errors mean Resolve would fail or build the wrong edit. Warnings flag gaps and off-beat cuts.

## Shape

```json
{
  "version": "0.1",
  "project": { "name": "my_edit", "width": 1920, "height": 1080, "fps": 24 },
  "music": { "file": "input/song.mp3", "start": 0.0, "gain_db": 0 },
  "beat_grid": {
    "bpm": 128.0,
    "beats": [0.47, 0.94, 1.41],
    "downbeats": [0.47, 2.34],
    "sections": [{ "label": "drop", "start": 30.1, "end": 45.0 }]
  },
  "clips": [
    {
      "file": "input/a.mp4",
      "in": 12.0,
      "out": 13.5,
      "track": 1,
      "at": 30.1,
      "speed": 1.0,
      "transition_in": { "type": "Flash White", "frames": 12 },
      "effects": ["Screen Shake"]
    }
  ],
  "titles": [
    { "text": "FINALLY FREE", "at": 30.1, "duration": 2.0, "track": 2, "template": "Center Title" }
  ],
  "markers": [
    { "at": 30.1, "color": "Red", "name": "drop" }
  ]
}
```

## Fields

| Field | Meaning |
|---|---|
| `project` | Timeline size and frame rate |
| `music` | Soundtrack file; `start` = offset into the file |
| `beat_grid` | From `detect_beats`, `detect_downbeats`, `detect_sections`. Times in seconds |
| `clips[].file`, `in`, `out` | Source file and the range used from it (seconds) |
| `clips[].track`, `at` | Video track (1 = V1) and timeline position (seconds) |
| `clips[].speed` | 1.0 = normal; 0.5 = half speed |
| `clips[].transition_in` | Transition into this clip: a Resolve transition or one of the bundled Fusion transitions |
| `clips[].effects` | Fusion effect template names to apply |
| `clips[].section` | Optional: the music section label the clip sits in (written by `auto_amv_plan`) |
| `titles[]` | Text, timing, track and title template |
| `markers[]` | Timeline markers (Resolve colors: Blue, Red, Green, Yellow, ...) |

## Rules

- All times are seconds from timeline start (or from file start for `in`/`out`). The script converts to frames with `project.fps`.
- `out - in` divided by `speed` is the clip's length on the timeline.
- Clips on the same track must not overlap.
- Paths are relative to the repo root, or absolute.
- Unknown fields are ignored, so you can add notes for the LLM.

## Tools that read or write plans

- `build_edit_plan` (beat_sync): simple draft, clips in order on the beat.
- `auto_amv_plan` (beat_sync): full AMV draft with sections, motion-picked shots, and `Flash White` + `Screen Shake` on drop/chorus downbeats.
- `validate_plan` (beat_sync): check before rendering or running Resolve.
- `render_plan` (timeline_project): render to MP4 without Resolve. Uses track 1, `speed`, `music`, flash/shake markers and `titles`; `platform="tiktok"` makes a 9:16 version.
