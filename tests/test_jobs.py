import src.jobs as jobs

from src.config import Config
from src.jobs import RenderJob
from src.models import Layer, Origin, SBObject, Storyboard, Vector2


def _make_job(tmp_path, *, enable_audio=True):
    osu_path = tmp_path / "test.osu"
    osu_path.write_text("AudioFilename: audio.mp3\n", encoding="utf-8")
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"not a real audio file")

    config = Config(
        path={"osu_path": str(osu_path), "output_path": str(tmp_path / "out.mp4")},
        renderer={"enable_audio": enable_audio},
    )
    return RenderJob(config)


def test_audio_duration_extends_storyboard_duration(tmp_path, monkeypatch):
    job = _make_job(tmp_path)
    storyboard = Storyboard()
    storyboard.background_layer.append(
        SBObject(
            layer=Layer.Background,
            origin=Origin.Centre,
            filepath="sprite.png",
            position=Vector2(320, 240),
            life_end=55_000,
        )
    )
    monkeypatch.setattr(job, "_get_audio_duration", lambda: 60_000)

    assert job._get_video_duration(storyboard) == 60_000


def test_audio_duration_does_not_extend_when_audio_is_disabled(tmp_path):
    job = _make_job(tmp_path, enable_audio=False)
    storyboard = Storyboard()
    storyboard.background_layer.append(
        SBObject(
            layer=Layer.Background,
            origin=Origin.Centre,
            filepath="sprite.png",
            position=Vector2(320, 240),
            life_end=55_000,
        )
    )
    assert job._get_video_duration(storyboard) == 55_000


def test_audio_duration_is_probed_from_the_declared_audio_file(tmp_path, monkeypatch):
    job = _make_job(tmp_path)
    calls = []

    def fake_probe(path, ffmpeg_path):
        calls.append((path, ffmpeg_path))
        return 60_000

    monkeypatch.setattr(jobs, "probe_media_duration", fake_probe)

    assert job._get_audio_duration() == 60_000
    assert calls == [(job.audio_path, jobs.get_ffmpeg_path())]
