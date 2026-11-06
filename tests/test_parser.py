"""Parser robustness tests. Run: .venv/bin/python -m pytest -q tests  (or python tests/test_parser.py)

Each variant rewrites a real-format sample into another common screenplay style and checks the
parser recovers the same beats (type, speaker, emotion, text, start, end).
Uses a synthetic sample, not the confidential input pack.
"""
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from promo.parser import ScriptFormatError, parse_episode, parse_show  # noqa: E402

SAMPLE = """EPISODE NUMBER: Episode 7
EPISODE LOGLINE: A maid is accused of theft at a ball.
CONTINUITY NOTES: Follows Episode 6.

--- SCRIPT START ---

SCENE 01
Scene heading: INT. BALLROOM – NIGHT
Scene start: 00:00.00
Scene end: 00:20.00

Actions and dialogue:

**CAMERA:**
Start: (00:00.00) | End: (00:03.50)
Wide shot of the crowded ballroom as the music stops.

**LADY MARGARET (Furious, Loud):**
Start: (00:01.20) | End: (00:04.00)
"Thief! She stole my necklace!"

**ACTION:**
Start: (00:04.00) | End: (00:07.25)
The guests turn toward the trembling maid.

SCENE 02
Scene heading: EXT. GARDEN – NIGHT
Scene start: 00:20.00
Scene end: 01:05.00

**ANNA (O.S.) (Whispering):**
Start: (00:20.00) | End: (00:23.10)
"I never touched it."

**SOUND FX:**
Start: (01:02.00) | End: (01:05.00)
A door slams shut.
"""
EXPECTED = [("camera", None, None, 0.0, 3.5), ("dialogue", "LADY MARGARET", "Furious, Loud", 1.2, 4.0),
            ("action", None, None, 4.0, 7.25), ("dialogue", "ANNA", "Whispering", 20.0, 23.1),
            ("sfx", None, None, 62.0, 65.0)]
TEXTS = ["Wide shot of the crowded ballroom as the music stops.", "Thief! She stole my necklace!",
         "The guests turn toward the trembling maid.", "I never touched it.", "A door slams shut."]


def _ts(m, s):  # "01:02.00" -> (1, 2.0)
    return int(m), float(s)


def v_no_bold(t):        # 'CAMERA:' instead of '**CAMERA:**'
    return re.sub(r"\*\*(.+?):\*\*", r"\1:", t)


def v_inline_times(t):   # time on the label line, no parentheses
    return re.sub(r"\*\*(.+?):\*\*\nStart: \((\S+)\) \| End: \((\S+)\)", r"**\1:** Start: \2 | End: \3", t)


def v_brackets(t):       # [00:01.20 - 00:04.00] on its own line
    return re.sub(r"Start: \((\S+)\) \| End: \((\S+)\)", r"[\1 - \2]", t)


def v_srt(t):            # SRT-style arrows and comma decimals
    return re.sub(r"Start: \((\d+):(\d+)\.(\d+)\) \| End: \((\d+):(\d+)\.(\d+)\)", r"\1:\2,\3 --> \4:\5,\6", t)


def v_hours(t):          # h:mm:ss.ff
    return re.sub(r"\((\d\d:\d\d\.\d\d)\)", r"(0:\1)", t)


def v_no_header(t):      # no EPISODE NUMBER / LOGLINE lines: number must come from the file name
    return "\n".join(l for l in t.split("\n") if not l.startswith(("EPISODE", "CONTINUITY")))


def v_slugs_only(t):     # no SCENE markers, only INT./EXT. sluglines
    t = re.sub(r"SCENE 0\d\nScene heading: ", "", t)
    return re.sub(r"Scene (start|end): .*\n", "", t)


def v_crlf(t):
    return "\ufeff" + t.replace("\n", "\r\n")


VARIANTS = [lambda t: t, v_no_bold, v_inline_times, v_brackets, v_srt, v_hours, v_no_header, v_slugs_only, v_crlf,
            lambda t: v_no_bold(v_inline_times(t))]


def _check(ep, name):
    got = [(b.type, b.speaker, b.emotion, round(b.start, 2), round(b.end, 2)) for b in ep.beats]
    assert got == EXPECTED, f"{name}: {got}"
    assert [b.text for b in ep.beats] == TEXTS, f"{name}: {[b.text for b in ep.beats]}"
    assert ep.number == 7, name
    assert ep.duration == 65.0, name


def test_variants():
    for v in VARIANTS:
        name = getattr(v, "__name__", "variant")
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "episode-007.txt"
            f.write_text(v(SAMPLE), encoding="utf-8", newline="")
            _check(parse_episode(f), name)


def test_scenes():
    with tempfile.TemporaryDirectory() as d:
        for v in (lambda t: t, v_slugs_only):
            f = Path(d) / "episode-007.txt"
            f.write_text(v(SAMPLE), encoding="utf-8")
            ep = parse_episode(f)
            assert [b.scene for b in ep.beats] == [1, 1, 1, 2, 2], [b.scene for b in ep.beats]
            assert ep.beats[3].scene_heading.startswith("EXT. GARDEN"), ep.beats[3].scene_heading


def test_clear_errors():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "episode-001.txt"
        f.write_text("EPISODE NUMBER: Episode 1\nJust prose with no timestamps at all.\n")
        try:
            parse_episode(f)
            raise AssertionError("expected ScriptFormatError")
        except ScriptFormatError as e:
            assert "0 timed beats" in str(e)
        try:
            parse_show(Path(d) / "missing")
            raise AssertionError("expected ScriptFormatError")
        except ScriptFormatError as e:
            assert "no .txt" in str(e)


if __name__ == "__main__":
    test_variants()
    test_scenes()
    test_clear_errors()
    print(f"parser tests passed: {len(VARIANTS)} format variants, scene numbering, error messages")
