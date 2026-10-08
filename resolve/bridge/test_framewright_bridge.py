"""Tests for framewright_bridge with a fake Resolve API. Run: python -m unittest resolve/bridge/test_framewright_bridge.py"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import framewright_bridge as fw  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


class Item:
    def __init__(self, path, fps=24.0, frames=2400):
        self.path, self.props = path, {"File Path": path, "FPS": str(fps), "Frames": str(frames)}

    def GetName(self):
        return os.path.basename(self.path)

    def GetClipProperty(self, key):
        return self.props.get(key)


class Folder:
    def __init__(self, name):
        self.name, self.clips, self.subs = name, [], []

    def GetName(self):
        return self.name

    def GetClipList(self):
        return self.clips

    def GetSubFolderList(self):
        return self.subs


class TimelineItem:
    def SetProperty(self, key, value):
        return False  # retime not scriptable, like many versions


class Timeline:
    def __init__(self, name):
        self.name, self.placed, self.markers, self.tracks = name, [], {}, 1

    def GetName(self):
        return self.name

    def GetStartFrame(self):
        return 86400

    def GetTrackCount(self, kind):
        return self.tracks

    def AddTrack(self, kind):
        self.tracks += 1
        return True

    def SetCurrentTimecode(self, tc):
        self.tc = tc
        return True

    def InsertFusionTitleIntoTimeline(self, name):
        return None

    def AddMarker(self, frame, color, name, note, duration):
        if frame in self.markers:
            return False
        self.markers[frame] = (color, name)
        return True


class MediaPool:
    def __init__(self, project):
        self.root, self.current, self.project = Folder("Master"), None, project

    def GetRootFolder(self):
        return self.root

    def SetCurrentFolder(self, f):
        self.current = f
        return True

    def AddSubFolder(self, parent, name):
        f = Folder(name)
        parent.subs.append(f)
        return f

    def ImportMedia(self, paths):
        items = [Item(p) for p in paths]
        (self.current or self.root).clips.extend(items)
        return items

    def CreateEmptyTimeline(self, name):
        t = Timeline(name)
        self.project.timelines.append(t)
        return t

    def AppendToTimeline(self, infos):
        self.project.current.placed.extend(infos)
        return [TimelineItem() for _ in infos]


class Project:
    def __init__(self):
        self.settings, self.timelines, self.current = {}, [], None
        self.mp = MediaPool(self)

    def SetSetting(self, k, v):
        self.settings[k] = v
        return True

    def GetMediaPool(self):
        return self.mp

    def GetTimelineCount(self):
        return len(self.timelines)

    def GetTimelineByIndex(self, i):
        return self.timelines[i - 1]

    def SetCurrentTimeline(self, t):
        self.current = t
        return True


class PM:
    def __init__(self):
        self.project = Project()

    def GetCurrentProject(self):
        return self.project


class Resolve:
    def __init__(self):
        self.pm = PM()

    def GetProjectManager(self):
        return self.pm


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plan = fw.load_plan(ROOT / "examples" / "edit_plan.example.json")
        for f in {c["file"] for c in self.plan["clips"]} | {self.plan["music"]["file"]}:
            p = Path(self.tmp.name, f)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"")

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_from_plan(self):
        r = Resolve()
        report = fw.build_from_plan(r, self.plan, base_dir=self.tmp.name, log=lambda *_: None)
        proj = r.pm.project
        self.assertEqual(report["clips_placed"], 5)
        self.assertEqual(report["skipped"], [])
        self.assertEqual(proj.settings["timelineFrameRate"], "24")
        tl = proj.current
        video = [p for p in tl.placed if p.get("mediaType") == 1]
        self.assertEqual([p["recordFrame"] - 86400 for p in video], [12, 60, 108, 132, 180])
        self.assertEqual((video[0]["startFrame"], video[0]["endFrame"]), (72, 119))
        self.assertTrue(any(p.get("mediaType") == 2 for p in tl.placed))
        names = [n for _, n in tl.markers.values()]
        self.assertIn("SPEED: 0.5x (placed at 1x)", names)
        self.assertIn("TITLE: THE DROP", names)
        self.assertIn("TRANSITION: Flash White 12f", names)
        self.assertEqual(len(tl.markers), report["markers"])
        # clips already in the pool are reused, and timeline names never collide
        fw.build_from_plan(r, self.plan, base_dir=self.tmp.name, log=lambda *_: None)
        self.assertEqual(sum(len(f.clips) for f in r.pm.project.mp.root.subs), 4)
        self.assertEqual(proj.current.GetName(), "beat_edit_example_2")

    def test_missing_file_is_skipped(self):
        self.plan["clips"][0]["file"] = "input/nope.mp4"
        report = fw.build_from_plan(Resolve(), self.plan, base_dir=self.tmp.name, log=lambda *_: None)
        self.assertEqual(report["clips_placed"], 4)
        self.assertTrue(report["skipped"][0].startswith("missing file"))

    def test_absolute_forward_slash_paths(self):
        # tools write paths like D:/x/a.mp4 on Windows; they must still match imported items
        for c in self.plan["clips"]:
            c["file"] = Path(self.tmp.name, c["file"]).as_posix()
        report = fw.build_from_plan(Resolve(), self.plan, base_dir="/elsewhere", log=lambda *_: None)
        self.assertEqual(report["clips_placed"], 5)

    def test_time_helpers(self):
        self.assertEqual(fw.to_srt_time(3661.5), "01:01:01,500")
        self.assertEqual(fw._timecode(86400 + 30, 24), "01:00:01:06")
        srt = fw.write_srt([{"start": 0, "end": 1.25, "text": " hi "}], Path(self.tmp.name, "a.srt"))
        self.assertEqual(srt.read_text(encoding="utf-8"), "1\n00:00:00,000 --> 00:00:01,250\nhi\n")


if __name__ == "__main__":
    unittest.main()
