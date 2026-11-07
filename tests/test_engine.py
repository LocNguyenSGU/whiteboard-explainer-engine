"""Smoke tests for the storyboard engine: the checks that block a render, and the demo storyboard itself."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from khuon.kiem_tra import kiem_nhip, kiem_text  # noqa: E402


def words(until):
    return [{"w": f"w{i}", "start": float(i), "end": float(i) + 0.8} for i in range(int(until))]


def test_gap_longer_than_4s_without_new_visual_is_an_error():
    tl = {"scenes": [{"elements": [{"id": "s1.a", "enterAt": 0.0}, {"id": "s1.b", "enterAt": 10.0}]}]}
    errors = kiem_nhip(tl, words(11), {})
    assert len(errors) == 1 and "10.0s" in errors[0]


def test_visuals_every_3s_pass():
    tl = {"scenes": [{"elements": [{"id": f"s1.e{i}", "enterAt": float(i * 3)} for i in range(5)]}]}
    assert kiem_nhip(tl, words(13), {}) == []


def test_source_lines_and_frames_do_not_count_as_new_visuals():
    tl = {"scenes": [{"elements": [{"id": "s1.a", "enterAt": 0.0}, {"id": "s1.nguon", "enterAt": 3.0},
                                   {"id": "s1.anh-fr", "enterAt": 6.0}, {"id": "s1.b", "enterAt": 9.0}]}]}
    assert len(kiem_nhip(tl, words(10), {})) == 1


def test_unquoted_color_tag_is_flagged_because_yaml_would_drop_it():
    assert kiem_text("    - code: {tieu_de: x, dong: [\"a @ b #do\"]}")
    assert not kiem_text('    nhan: {o: trai, items: ["a @ b #do"]}')


def test_demo_storyboard_builds_with_zero_errors():
    out = subprocess.run(["bash", os.path.join(ROOT, "scripts", "demo.sh"), "--check"], capture_output=True, text=True,
                         env=dict(os.environ, PYTHON=sys.executable))
    assert out.returncode == 0, out.stdout + out.stderr
    assert " 0 lỗi" in out.stdout
