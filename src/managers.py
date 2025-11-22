import os
from typing import Dict
from PIL import Image, ImageOps
import numpy as np


class AssetLoader:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.cache: Dict[str, Image.Image] = {}

        self.placeholder = None

    def load_image(self, filepath: str, method: str = "pil") -> Image.Image:
        # normalize path
        filepath = filepath.strip('"').replace("\\", os.sep)
        full_path = os.path.join(self.base_path, filepath)

        if filepath in self.cache:
            return self.cache[filepath]

        if not os.path.exists(full_path):
            print(f"Warning: Asset not found: {full_path}")
            self.cache[filepath] = self.placeholder
            return self.placeholder

        try:
            if method == "pil":
                img = Image.open(full_path).convert("RGBA")
                self.cache[filepath] = img
                return img
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            self.cache[filepath] = self.placeholder
            return self.placeholder
