import os
from typing import Dict
import numpy as np
import skia
from loguru import logger


class AssetLoader:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.cache: Dict[str, skia.Image] = {}

        self.placeholder = self._create_placeholder()

    def _create_placeholder(self) -> skia.Image:
        surface = skia.Surface(1, 1)
        canvas = surface.getCanvas()
        canvas.clear(skia.Color(0, 0, 0, 0))
        return surface.makeImageSnapshot()

    def load_image(self, filepath: str, method: str = "pil") -> skia.Image:
        # normalize path
        filepath = filepath.strip('"').replace("\\", os.sep)
        full_path = os.path.join(self.base_path, filepath)

        if filepath in self.cache:
            return self.cache[filepath]

        if not os.path.exists(full_path):
            logger.warning(f"Asset not found: {full_path}")
            self.cache[filepath] = self.placeholder
            return self.placeholder

        try:
            if method == "pil":
                image = skia.Image.open(full_path)

            if image is None:
                logger.warning(f"Warning: Failed to load image: {full_path}")
                self.cache[filepath] = self.placeholder
                return self.placeholder

            self.cache[filepath] = image
            return image

        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            self.cache[filepath] = self.placeholder
            return self.placeholder
