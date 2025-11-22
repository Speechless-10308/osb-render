import os
from typing import Dict
from PIL import Image, ImageOps
import cv2
from cv2.typing import MatLike
import numpy as np


class AssetLoader:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.cache: Dict[str, MatLike] = {}

        self.placeholder = None

    def load_image(self, filepath: str, method: str = "cv2") -> MatLike | Image.Image:
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
            if method == "cv2":
                img_array = np.fromfile(full_path, dtype=np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_UNCHANGED)

                if img.shape[2] == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)

                self.cache[filepath] = img
                return img
            elif method == "pil":
                img = Image.open(full_path).convert("RGBA")
                self.cache[filepath] = img
                return img
        except Exception as e:
            print(f"Error loading image {full_path}: {e}")
            self.cache[filepath] = self.placeholder
            return self.placeholder
