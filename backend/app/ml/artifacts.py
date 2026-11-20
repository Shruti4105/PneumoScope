"""Versioned model artefact bundles.

A bundle directory ``artifacts/models/<version>/`` contains:

* ``config.json``           immutable model + decision-policy configuration
* ``model.pt``              full state dict (backbone + MC-Dropout head)
* ``evaluation.json``       evaluation report produced by the training pipeline
* ``reference_stats.json``  reference distributions for drift monitoring

The config hash is computed over canonical JSON and recorded in the model
registry; a bundle whose config or weights no longer match the registered
hashes is refused, so a deployed decision policy cannot change silently.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import torch

from app.ml.prediction import DecisionPolicy
from app.ml.resnet_model import PneumoniaResNet50

REQUIRED_CONFIG_KEYS = ("name", "version", "head", "mc_passes", "temperature", "refer_threshold",
                        "decision_threshold", "weights_file", "weights_sha256")


class ArtifactError(RuntimeError):
    pass


def canonical_hash(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_config(bundle_dir: Path) -> dict:
    cfg = read_json(bundle_dir / "config.json")
    if cfg is None:
        raise ArtifactError(f"config.json missing in {bundle_dir}")
    missing = [k for k in REQUIRED_CONFIG_KEYS if k not in cfg]
    if missing:
        raise ArtifactError(f"config.json missing keys: {', '.join(missing)}")
    return cfg


@dataclass
class ModelBundle:
    directory: Path
    config: dict
    config_hash: str
    model: PneumoniaResNet50
    policy: DecisionPolicy
    evaluation: dict | None = None
    reference_stats: dict | None = None
    extras: dict = field(default_factory=dict)

    @property
    def version(self) -> str:
        return self.config["version"]

    @property
    def temperature(self) -> float:
        return float(self.config["temperature"])

    @property
    def mc_passes(self) -> int:
        return int(self.config["mc_passes"])

    @property
    def calibration_status(self) -> str:
        return "temperature-scaled" if self.config.get("calibrated") else "uncalibrated"


def load_bundle(bundle_dir: Path, expected_config_hash: str | None = None,
                expected_weights_sha: str | None = None, verify_weights: bool = True) -> ModelBundle:
    bundle_dir = Path(bundle_dir)
    cfg = read_config(bundle_dir)
    chash = canonical_hash(cfg)
    if expected_config_hash and chash != expected_config_hash:
        raise ArtifactError("config.json hash does not match the registered configuration; refusing to load.")
    weights = bundle_dir / cfg["weights_file"]
    if not weights.exists():
        raise ArtifactError(f"weights file {weights.name} missing")
    if verify_weights:
        sha = file_sha256(weights)
        if sha != cfg["weights_sha256"] or (expected_weights_sha and sha != expected_weights_sha):
            raise ArtifactError("model weights checksum mismatch; refusing to load.")
    head = cfg["head"]
    model = PneumoniaResNet50(hidden=int(head["hidden"]), dropout=float(head["dropout"]), pretrained_backbone=False)
    state = torch.load(weights, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    policy = DecisionPolicy(refer_threshold=float(cfg["refer_threshold"]),
                            decision_threshold=float(cfg["decision_threshold"]),
                            refer_on_input_flags=bool(cfg.get("refer_on_input_flags", True)))
    return ModelBundle(directory=bundle_dir, config=cfg, config_hash=chash, model=model, policy=policy,
                       evaluation=read_json(bundle_dir / "evaluation.json"),
                       reference_stats=read_json(bundle_dir / "reference_stats.json"))
