"""Unit tests for src/config.py — Config model and YAML persistence."""

import os
import tempfile
import pytest
from src.config import Config, AppConfig, RendererConfig, PathConfig


# ---------------------------------------------------------------------------
# AppConfig
# ---------------------------------------------------------------------------
class TestAppConfig:
    def test_defaults(self):
        cfg = AppConfig()
        assert cfg.last_open_dir == "."
        assert cfg.theme == "dark"
        assert cfg.config_dir == ""

    def test_custom_values(self):
        cfg = AppConfig(last_open_dir="/tmp", theme="light", config_dir="/etc")
        assert cfg.last_open_dir == "/tmp"
        assert cfg.theme == "light"


# ---------------------------------------------------------------------------
# RendererConfig
# ---------------------------------------------------------------------------
class TestRendererConfig:
    def test_defaults(self):
        cfg = RendererConfig()
        assert cfg.width == 1280
        assert cfg.height == 720
        assert cfg.fps == 60
        assert cfg.encoder_preset == "fast"
        assert cfg.crf == 20
        assert cfg.use_gpu is True
        assert cfg.sample_method == "linear"
        assert cfg.enable_audio is True
        assert cfg.pixel_format == "yuv420p"
        assert cfg.gop_size == 12
        assert cfg.b_frames == 2
        assert cfg.preset_tuning == "default"
        assert cfg.audio_bitrate == "192k"
        assert cfg.audio_codec == "aac"

    def test_custom_resolution(self):
        cfg = RendererConfig(width=1920, height=1080, fps=30)
        assert cfg.width == 1920
        assert cfg.height == 1080
        assert cfg.fps == 30

    def test_cpu_mode(self):
        cfg = RendererConfig(use_gpu=False)
        assert cfg.use_gpu is False

    def test_encoder_settings(self):
        cfg = RendererConfig(crf=23, encoder_preset="medium", pixel_format="yuv420p10le")
        assert cfg.crf == 23
        assert cfg.encoder_preset == "medium"
        assert cfg.pixel_format == "yuv420p10le"


# ---------------------------------------------------------------------------
# PathConfig
# ---------------------------------------------------------------------------
class TestPathConfig:
    def test_defaults(self):
        cfg = PathConfig()
        assert cfg.output_path == "./output.mp4"
        assert cfg.osu_path == "./example.osu"

    def test_custom(self):
        cfg = PathConfig(output_path="/out/video.mp4", osu_path="/maps/beatmap.osu")
        assert cfg.osu_path == "/maps/beatmap.osu"


# ---------------------------------------------------------------------------
# Config (top-level)
# ---------------------------------------------------------------------------
class TestConfig:
    def test_default_construction(self):
        cfg = Config()
        assert cfg.app.theme == "dark"
        assert cfg.renderer.width == 1280
        assert cfg.path.osu_path == "./example.osu"

    def test_nested_override(self):
        cfg = Config(
            app=AppConfig(theme="light"),
            renderer=RendererConfig(width=640, height=480),
        )
        assert cfg.app.theme == "light"
        assert cfg.renderer.width == 640
        # Path is default
        assert cfg.path.output_path == "./output.mp4"

    def test_from_yaml_valid_file(self):
        yaml_content = """
app:
  last_open_dir: /home/user/maps
  theme: light
path:
  osu_path: /maps/test.osu
  output_path: /out/test.mp4
renderer:
  width: 1920
  height: 1080
  fps: 30
  use_gpu: false
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8",
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            cfg = Config.from_yaml(tmp_path)
            assert cfg.app.last_open_dir == "/home/user/maps"
            assert cfg.app.theme == "light"
            assert cfg.path.osu_path == "/maps/test.osu"
            assert cfg.renderer.width == 1920
            assert cfg.renderer.height == 1080
            assert cfg.renderer.fps == 30
            assert cfg.renderer.use_gpu is False
        finally:
            os.unlink(tmp_path)

    def test_from_yaml_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            Config.from_yaml("/nonexistent/path/config.yaml")

    def test_from_yaml_partial_data(self):
        """YAML with only some keys should use defaults for the rest."""
        yaml_content = """
app:
  theme: light
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8",
        ) as f:
            f.write(yaml_content)
            tmp_path = f.name

        try:
            cfg = Config.from_yaml(tmp_path)
            assert cfg.app.theme == "light"
            # Defaults for missing fields
            assert cfg.renderer.width == 1280
            assert cfg.path.osu_path == "./example.osu"
        finally:
            os.unlink(tmp_path)

    def test_to_yaml_round_trip(self):
        """Write config to YAML and read it back."""
        cfg = Config(
            app=AppConfig(theme="light", last_open_dir="/test"),
            renderer=RendererConfig(width=800, height=600),
            path=PathConfig(osu_path="/t.osu"),
        )

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False, encoding="utf-8",
        ) as f:
            tmp_path = f.name

        try:
            cfg.to_yaml(tmp_path)
            loaded = Config.from_yaml(tmp_path)
            assert loaded.app.theme == "light"
            assert loaded.app.last_open_dir == "/test"
            assert loaded.renderer.width == 800
            assert loaded.renderer.height == 600
            assert loaded.path.osu_path == "/t.osu"
        finally:
            os.unlink(tmp_path)

    def test_to_yaml_creates_parent_dirs(self):
        """to_yaml should create parent directories if they don't exist."""
        tmp_dir = tempfile.mkdtemp()
        nested_path = os.path.join(tmp_dir, "subdir", "config.yaml")
        try:
            cfg = Config()
            cfg.to_yaml(nested_path)
            assert os.path.isfile(nested_path)
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_model_dump_is_serializable(self):
        cfg = Config()
        data = cfg.model_dump()
        assert "app" in data
        assert "renderer" in data
        assert "path" in data
        assert data["app"]["theme"] == "dark"
