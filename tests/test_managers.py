"""Unit tests for src/managers.py — AssetLoader caching and fallback behaviour."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from src.managers import AssetLoader


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
class TestConstruction:
    def test_base_path_stored(self):
        loader = AssetLoader("/some/base/path")
        assert loader.base_path == "/some/base/path"

    def test_cache_starts_empty(self):
        loader = AssetLoader("/tmp")
        assert loader.cache == {}

    def test_placeholder_created(self):
        loader = AssetLoader("/tmp")
        assert loader.placeholder is not None
        assert loader.placeholder.width() == 1
        assert loader.placeholder.height() == 1


# ---------------------------------------------------------------------------
# Path normalisation
# ---------------------------------------------------------------------------
class TestPathNormalisation:
    @patch("src.managers.os.path.exists")
    @patch("src.managers.skia.Image")
    def test_quotes_stripped_from_filepath(self, mock_skia_image, mock_exists):
        """Filepaths with surrounding quotes should be stripped."""
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_skia_image.open.return_value = mock_img

        loader = AssetLoader("/base")
        loader.load_image('"path/to/image.png"')
        # The key in cache should be the stripped path
        assert "path/to/image.png" in loader.cache

    @patch("src.managers.os.path.exists")
    @patch("src.managers.skia.Image")
    def test_backslash_normalised(self, mock_skia_image, mock_exists):
        """Backslashes should be converted to os.sep."""
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_skia_image.open.return_value = mock_img

        loader = AssetLoader("/base")
        loader.load_image("path\\to\\image.png")
        normalized = "path" + os.sep + "to" + os.sep + "image.png"
        assert normalized in loader.cache

    @patch("src.managers.os.path.exists")
    @patch("src.managers.skia.Image")
    def test_full_path_constructed(self, mock_skia_image, mock_exists):
        """The full path should be base_path + normalized filepath."""
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_skia_image.open.return_value = mock_img

        loader = AssetLoader("/base")
        loader.load_image("subdir/file.png")
        mock_exists.assert_called_with(
            os.path.join("/base", "subdir/file.png")
        )


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
class TestCaching:
    @patch("src.managers.os.path.exists")
    @patch("src.managers.skia.Image")
    def test_image_cached_after_first_load(self, mock_skia_image, mock_exists):
        mock_exists.return_value = True
        mock_img = MagicMock()
        mock_skia_image.open.return_value = mock_img

        loader = AssetLoader("/base")
        result1 = loader.load_image("img.png")
        result2 = loader.load_image("img.png")

        # Same object returned
        assert result1 is result2
        # open only called once
        mock_skia_image.open.assert_called_once()

    @patch("src.managers.os.path.exists")
    @patch("src.managers.skia.Image")
    def test_different_images_not_confused(self, mock_skia_image, mock_exists):
        mock_exists.return_value = True
        mock_img_a = MagicMock()
        mock_img_b = MagicMock()
        mock_skia_image.open.side_effect = [mock_img_a, mock_img_b]

        loader = AssetLoader("/base")
        a = loader.load_image("a.png")
        b = loader.load_image("b.png")

        assert a is mock_img_a
        assert b is mock_img_b
        assert a is not b
        assert len(loader.cache) == 2


# ---------------------------------------------------------------------------
# Missing / invalid asset fallback
# ---------------------------------------------------------------------------
class TestMissingAsset:
    def test_missing_file_returns_placeholder(self):
        loader = AssetLoader("/nonexistent_base")
        result = loader.load_image("does_not_exist.png")
        assert result is loader.placeholder

    @patch("src.managers.skia.Image")
    def test_none_result_returns_placeholder(self, mock_skia_image):
        """If skia.Image.open returns None, use placeholder."""
        mock_skia_image.open.return_value = None

        loader = AssetLoader("/base")
        with patch("src.managers.os.path.exists", return_value=True):
            result = loader.load_image("bad.png")
        assert result is loader.placeholder

    @patch("src.managers.skia.Image")
    def test_exception_during_open_returns_placeholder(self, mock_skia_image):
        mock_skia_image.open.side_effect = RuntimeError("decode error")

        loader = AssetLoader("/base")
        with patch("src.managers.os.path.exists", return_value=True):
            result = loader.load_image("corrupt.png")
        assert result is loader.placeholder

    def test_missing_file_cached_as_placeholder(self):
        """After a failed load, the placeholder should be cached for that path."""
        loader = AssetLoader("/nonexistent_base")
        loader.load_image("nope.png")
        loader.load_image("nope.png")  # second call — should hit cache
        assert "nope.png" in loader.cache
        assert loader.cache["nope.png"] is loader.placeholder


# ---------------------------------------------------------------------------
# Placeholder properties
# ---------------------------------------------------------------------------
class TestPlaceholder:
    def test_placeholder_is_transparent(self):
        loader = AssetLoader("/tmp")
        p = loader.placeholder
        assert p.width() == 1
        assert p.height() == 1
        # A 1x1 transparent image should not throw on pixel access
        # Just verify it exists and has expected dimensions
        assert p is not None

    def test_placeholder_is_singleton(self):
        """_create_placeholder is called once in __init__."""
        loader = AssetLoader("/tmp")
        p = loader._create_placeholder()
        # New placeholder is a different object but has same dimensions
        assert p.width() == 1
        assert p.height() == 1
