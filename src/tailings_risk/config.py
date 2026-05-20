"""Typed configuration objects, loaded from configs/*.yaml.

A single place to declare every knob the experiments expose. Pydantic gives us
validation + clear error messages when an experiment config drifts from the
expected schema.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class CohortConfig(BaseModel):
    source: Literal["sigbm"] = "sigbm"
    start_month: str = "2015-01"
    end_month: str | None = None


class OutcomeConfig(BaseModel):
    database: Literal["wmtf", "wmtf+manual"] = "wmtf"
    severity_min: int = Field(4, ge=1, le=5)
    horizon_months: int = Field(12, ge=1)


class InsarConfig(BaseModel):
    enabled: bool = True
    insar_window_months: int = 12
    tracks: list[Literal["ascending", "descending"]] = ["ascending", "descending"]


class ClimateConfig(BaseModel):
    enabled: bool = True
    rainfall_windows_days: list[int] = [30, 90, 365]
    indices: list[Literal["spi3", "spi6", "api"]] = ["spi3", "spi6", "api"]


class OpsConfig(BaseModel):
    enabled: bool = True


class FeatureConfig(BaseModel):
    static: bool = True
    insar: InsarConfig = InsarConfig()
    climate: ClimateConfig = ClimateConfig()
    ops: OpsConfig = OpsConfig()


class CalibrationConfig(BaseModel):
    temperature_scaling: bool = True
    conformal: Literal["split", "mondrian", "none"] = "split"
    alpha: float = Field(0.1, gt=0, lt=1)


class ModelConfig(BaseModel):
    primary: Literal["tabpfn", "lightgbm", "weibull_aft"] = "tabpfn"
    baselines: list[str] = ["base_rate", "construction_rate", "anm_cri", "lightgbm"]
    multitask_by_construction: bool = True
    calibration: CalibrationConfig = CalibrationConfig()


class ValidationConfig(BaseModel):
    protocol: Literal["rolling_origin", "operator_out"] = "rolling_origin"
    step_months: int = 3
    held_out_failures: list[str] = ["fundao_2015", "b1_brumadinho_2019"]
    operator_out_cv: bool = True
    bootstrap_resamples: int = 1000


class PathsConfig(BaseModel):
    data_raw: Path = Path("data/raw")
    data_interim: Path = Path("data/interim")
    data_processed: Path = Path("data/processed")
    results: Path = Path("results")


class Config(BaseModel):
    seed: int = 0
    cohort: CohortConfig = CohortConfig()
    outcome: OutcomeConfig = OutcomeConfig()
    features: FeatureConfig = FeatureConfig()
    model: ModelConfig = ModelConfig()
    validation: ValidationConfig = ValidationConfig()
    paths: PathsConfig = PathsConfig()


def load(path: Path | str) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return Config(**raw)
