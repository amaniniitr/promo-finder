"""Deterministic screenplay parser: episode .txt -> structured beats.

No AI here. Every timestamp the tool runs/v1 comes from this parser, so the
LLM can only reference beat IDs and never invents times.

Tolerant to common format variants (tests: tests/test_parser.py):
  * episode number from 'EPISODE NUMBER: Episode 7', 'Episode 7', 'EP 7', or the file name;
  * logline / continuity notes optional;
  * scene markers 'SCENE 01', 'Scene 1:', '## SCENE 1 - INT. HALL', and INT./EXT. sluglines;
  * labels '**CAMERA:**', 'CAMERA:', '**NAME (Emotion):**', 'NAME (Emotion):', with the
    text on the same line or below;
  * times 'Start: (00:01.00) | End: (00:04.80)', 'Start: 00:01.00 | End: 00:04.80',
    '[00:01.00 - 00:04.80]', '00:01,00 --> 00:04,80', 'h:mm:ss' and seconds-only '1.0s - 4.8s';
    on the label line or the next line.
It raises ScriptFormatError (with the file name and what was missing) instead of
silently returning an episode with no beats.
"""
from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

_T = r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2}(?:[.,]\d+)?)"            # [h:]m:ss[.ff]
RE_TWO_TIMES = re.compile(rf"{_T}\)?\s*(?:\||-|–|—|-->|to|,)\s*(?:end\s*:?\s*)?\(?\s*{_T}", re.I)
RE_TWO_SECS = re.compile(r"(\d+(?:\.\d+)?)\s*s\s*(?:-|–|—|-->|to)\s*(\d+(?:\.\d+)?)\s*s\b", re.I)
RE_EP_NUM = [re.compile(r"^\W*EPISODE\s*(?:NUMBER|NO\.?|#)?\s*:?\s*(?:Episode|Ep\.?)?\s*(\d+)", re.I | re.M),
             re.compile(r"^\W*EP\.?\s*(\d+)\b", re.I | re.M)]
RE_LOGLINE = re.compile(r"^\W*(?:EPISODE\s+)?LOGLINE\s*:\s*(.+)$", re.I | re.M)
RE_CONT = re.compile(r"^\W*CONTINUITY(?:\s+NOTES)?\s*:\s*(.+)$", re.I | re.M)
RE_SCENE = re.compile(r"^[#*\s]*SCENE\s+(\d+)\b\s*[:.\-–—]?\s*(.*?)[*\s]*$", re.I)
RE_SLUG = re.compile(r"^[#*\s]*((?:INT|EXT|INT\./EXT|I/E)\.?\s.+?)[*\s]*$", re.I)
RE_HEADING = re.compile(r"^[#*\s]*Scene\s+heading\s*:\s*(.+?)[*\s]*$", re.I)
# Label: an UPPER-CASE name (optionally with parentheticals) followed by a colon, optionally in **bold**.
RE_LABEL = re.compile(r"^[#\s]*\**\s*([A-Z][A-Z0-9 .,'’&/\-]*?(?:\s*\([^)]*\))*)\s*:\s*\**\s*(.*)$")
NON_DIALOGUE = {"CAMERA": "camera", "ACTION": "action", "SOUND FX": "sfx", "SFX": "sfx", "SOUND": "sfx",
                "VISUAL": "camera", "SHOT": "camera", "MUSIC": "sfx"}
NOT_LABELS = {"SCENE HEADING", "SCENE START", "SCENE END", "ACTIONS AND DIALOGUE", "EPISODE NUMBER",
              "EPISODE LOGLINE", "LOGLINE", "CONTINUITY NOTES", "CONTINUITY", "START", "END", "EPISODE",
              "TITLE", "NOTE", "NOTES", "INT", "EXT"}


class ScriptFormatError(ValueError):
    pass


def to_sec(h, m, s) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + float(str(s).replace(",", "."))


def fmt(t: float) -> str:
    m, s = divmod(t, 60)
    return f"{int(m):02d}:{s:05.2f}"


def find_times(line: str) -> tuple[float, float] | None:
    m = RE_TWO_TIMES.search(line)
    if m:
        return to_sec(*m.group(1, 2, 3)), to_sec(*m.group(4, 5, 6))
    m = RE_TWO_SECS.search(line)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


class Beat(BaseModel):
    id: str            # e.g. "E01-B023"
    episode: int
    scene: int
    scene_heading: str
    idx: int           # index within episode
    type: str          # camera | action | sfx | dialogue
    speaker: str | None = None
    emotion: str | None = None
    text: str
    start: float
    end: float


class Episode(BaseModel):
    number: int
    logline: str
    continuity: str
    source_file: str
    duration: float
    beats: list[Beat]

    def render(self, types: tuple[str, ...] = ("action", "dialogue", "sfx", "camera")) -> str:
        """Compact text the LLM reads: one beat per line with its ID."""
        lines, scene = [], None
        for b in self.beats:
            if b.type not in types:
                continue
            if b.scene != scene:
                scene = b.scene
                lines.append(f"## SCENE {b.scene}: {b.scene_heading}")
            who = f"{b.speaker} ({b.emotion})" if b.speaker else b.type.upper()
            lines.append(f"[{b.id}] {fmt(b.start)}-{fmt(b.end)} {who}: {b.text}")
        return "\n".join(lines)


def _split_label(label: str) -> tuple[str, str | None, str | None]:
    """'LADY JULIANA (Confused, Breathless)' -> (dialogue, 'LADY JULIANA', 'Confused, Breathless')."""
    up = re.sub(r"\s*\([^)]*\)", "", label).strip().upper()
    if up in NON_DIALOGUE:
        return NON_DIALOGUE[up], None, None
    parens = re.findall(r"\(([^)]*)\)", label)
    name = re.sub(r"\s*\([^)]*\)", "", label).strip()
    emo = [p for p in parens if p.upper().replace(" ", "") not in {"O.S.", "V.O.", "CONT'D", "OS", "VO"}]
    return "dialogue", name, ", ".join(emo) or None


def _label(line: str):
    m = RE_LABEL.match(line)
    if not m:
        return None
    name = re.sub(r"\s*\([^)]*\)", "", m.group(1)).strip().upper()
    if not name or name in NOT_LABELS or name.startswith("SCENE") or re.fullmatch(r"[\d .:]+", name):
        return None
    return m.group(1).strip(), m.group(2).strip()


def _episode_number(raw: str, path: Path) -> int:
    for rx in RE_EP_NUM:
        if m := rx.search(raw):
            return int(m.group(1))
    if m := re.search(r"(?:episode|ep)[\s_-]*0*(\d+)", path.stem, re.I) or re.search(r"(\d+)", path.stem):
        return int(m.group(1))
    raise ScriptFormatError(f"{path.name}: no episode number in the text or the file name")


def parse_episode(path: str | Path) -> Episode:
    path = Path(path)
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    num = _episode_number(raw, path)
    logline = (m.group(1).strip() if (m := RE_LOGLINE.search(raw)) else "")
    cont = (m.group(1).strip() if (m := RE_CONT.search(raw)) else "")

    lines = raw.split("\n")
    beats: list[Beat] = []
    scene, heading, untimed = 0, "", 0
    fresh_marker = False          # a SCENE marker was seen and no beat has used it yet
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if m := RE_SCENE.match(line):
            scene, fresh_marker = int(m.group(1)), True
            if m.group(2) and not re.match(r"(?i)heading|start|end", m.group(2)):
                heading = m.group(2).strip(" -–—:")
        elif m := RE_HEADING.match(line):
            heading = m.group(1).strip()
        elif (m := RE_SLUG.match(line)) and not _label(line):
            heading = m.group(1).strip()
            if not fresh_marker:  # sluglines without SCENE markers start a new scene
                scene += 1
            fresh_marker = False
        elif lab := _label(line):
            label, rest = lab
            times = find_times(rest)
            j = i + 1
            if times:
                rest = (RE_TWO_TIMES.sub("", rest) if RE_TWO_TIMES.search(rest) else RE_TWO_SECS.sub("", rest))
                rest = re.sub(r"(?i)\bstart\s*:?|\bend\s*:?|[\[\]()|]", " ", rest).strip(" -–—:")
            else:
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and (times := find_times(lines[j])) and not _label(lines[j].strip()):
                    j += 1
            if not times:
                untimed += 1
                i += 1
                continue
            text = [rest] if rest else []
            while j < len(lines) and lines[j].strip() and not _label(lines[j].strip()) \
                    and not RE_SCENE.match(lines[j].strip()):
                text.append(lines[j].strip())
                j += 1
            btype, speaker, emotion = _split_label(label)
            body = " ".join(text).strip()
            if btype == "dialogue":
                body = body.strip('"“”')
            idx = len(beats)
            fresh_marker = False
            beats.append(Beat(
                id=f"E{num:02d}-B{idx:03d}", episode=num, scene=max(scene, 1), scene_heading=heading,
                idx=idx, type=btype, speaker=speaker, emotion=emotion, text=body,
                start=times[0], end=max(times[0], times[1]),
            ))
            i = j
            continue
        i += 1

    if not beats:
        raise ScriptFormatError(
            f"{path.name}: found 0 timed beats ({untimed} labels without timestamps). Expected blocks like "
            "'**ACTION:**' or 'NAME (Emotion):' followed by 'Start: (mm:ss.ff) | End: (mm:ss.ff)'.")
    duration = max(b.end for b in beats)
    return Episode(number=num, logline=logline, continuity=cont, source_file=path.name,
                   duration=duration, beats=beats)


def parse_show(folder: str | Path) -> list[Episode]:
    folder = Path(folder)
    files = sorted(p for p in folder.glob("*") if p.suffix.lower() in (".txt", ".md", ".fountain"))
    if not files:
        raise ScriptFormatError(f"{folder}: no .txt/.md/.fountain episode files")
    eps = [parse_episode(p) for p in files]
    nums = [e.number for e in eps]
    if len(set(nums)) != len(nums):
        raise ScriptFormatError(f"{folder}: duplicate episode numbers {sorted(n for n in set(nums) if nums.count(n) > 1)}")
    return sorted(eps, key=lambda e: e.number)
