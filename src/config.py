import yaml
import os
from pydantic import BaseModel, Field
from typing import Optional
from loguru import logger


class AppConfig(BaseModel):
    last_open_dir: str = "."


class RendererConfig(BaseModel):
    width: int = 1280
    height: int = 720
    fps: int = 60
    encoder_preset: str = "fast"
    crf: int = 20
    use_gpu: bool = True
    enable_audio: bool = True


class PathConfig(BaseModel):
    output_path: str = "./output.mp4"
    osu_path: str = "./example.osu"


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    renderer: RendererConfig = Field(default_factory=RendererConfig)
    path: PathConfig = Field(default_factory=PathConfig)

    @classmethod
    def from_yaml(cls, yamlpath: str) -> "Config":
        if not os.path.exists(yamlpath):
            raise FileNotFoundError(f"Config file '{yamlpath}' does not exist.")

        try:
            with open(yamlpath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return cls(**data)

        except Exception as e:
            logger.error(
                f"Failed to load config from '{yamlpath}': {e}, backing up to default config."
            )
            return cls()

    def to_yaml(self, yamlpath: str):
        with open(yamlpath, "w", encoding="utf-8") as f:
            yaml.dump(self.model_dump(), f, default_flow_style=False)
