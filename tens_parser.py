"""Reader for the Bluehill .id_tens files supplied for this project.

The format is proprietary.  This reader identifies repeated binary records that
contain extension (mm), force (kN), and time (s), then validates each sequence.
It is intentionally conservative: unrecognised files raise a useful error.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class TensileCurve:
    specimen: str
    data: pd.DataFrame


def parse_id_tens(source: bytes | str | Path) -> list[TensileCurve]:
    """Extract tensile curves from a Bluehill ``.id_tens`` file.

    Returns records with extension in millimetres, force in kilonewtons, and
    time in seconds.  The known file layout stores each point as a 24-byte
    record headed by integer 2.  The validation below prevents incidental
    binary values from being interpreted as curves.
    """
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    else:
        raw = source

    points: list[tuple[int, float, float, float]] = []
    for offset in range(0, len(raw) - 24, 4):
        if struct.unpack_from("<I", raw, offset)[0] != 2:
            continue
        if raw[offset + 16 : offset + 24] != b"\x00" * 8:
            continue
        extension, force, time = struct.unpack_from("<fff", raw, offset + 4)
        if all(np.isfinite([extension, force, time])):
            points.append((offset, extension, force, time))

    runs: list[list[tuple[int, float, float, float]]] = []
    current: list[tuple[int, float, float, float]] = []
    previous_offset: int | None = None
    for point in points:
        if previous_offset is None or point[0] == previous_offset + 24:
            current.append(point)
        else:
            if _is_curve(current):
                runs.append(current)
            current = [point]
        previous_offset = point[0]
    if _is_curve(current):
        runs.append(current)

    curves: list[TensileCurve] = []
    for index, run in enumerate(runs, start=1):
        frame = pd.DataFrame(run, columns=["offset", "extension_mm", "force_kN", "time_s"])
        frame = frame.drop(columns="offset")
        curves.append(TensileCurve(f"Specimen {index}", frame))

    if not curves:
        raise ValueError(
            "No tensile curves were found. This .id_tens file may use a different Bluehill layout. "
            "Export raw data to CSV from Bluehill as a fallback."
        )
    return curves


def _is_curve(points: list[tuple[int, float, float, float]]) -> bool:
    if len(points) < 50:
        return False
    values = np.asarray([[point[1], point[2], point[3]] for point in points])
    extension, force, time = values.T
    return bool(
        np.all(np.diff(time) >= -1e-4)
        and np.nanmax(time) > 1
        and np.nanmax(extension) > 1
        and np.nanmax(force) > 0.001
        and np.nanmin(force) > -0.05
    )


def average_curve(curves: list[TensileCurve], points: int = 500) -> pd.DataFrame:
    """Interpolate included curves to a shared extension grid and average force.

    The mean stops at the shortest included curve so every displayed average
    point includes every specimen. Standard deviation uses sample standard
    deviation when two or more curves are selected.
    """
    if not curves:
        raise ValueError("Select at least one specimen.")

    prepared: list[pd.DataFrame] = []
    for curve in curves:
        frame = curve.data[["extension_mm", "force_kN"]].copy()
        frame = frame.sort_values("extension_mm").drop_duplicates("extension_mm")
        prepared.append(frame)

    start = max(float(frame.extension_mm.min()) for frame in prepared)
    end = min(float(frame.extension_mm.max()) for frame in prepared)
    if end <= start:
        raise ValueError("Selected curves do not have a shared extension range.")
    grid = np.linspace(start, end, points)
    forces = np.vstack(
        [np.interp(grid, frame.extension_mm.to_numpy(), frame.force_kN.to_numpy()) for frame in prepared]
    )
    return pd.DataFrame(
        {
            "extension_mm": grid,
            "mean_force_kN": forces.mean(axis=0),
            "std_force_kN": forces.std(axis=0, ddof=1) if len(prepared) > 1 else np.zeros_like(grid),
            "specimen_count": len(prepared),
        }
    )


def curve_summary(curves: list[TensileCurve]) -> pd.DataFrame:
    rows = []
    for curve in curves:
        peak_index = curve.data.force_kN.idxmax()
        peak = curve.data.loc[peak_index]
        rows.append(
            {
                "Specimen": curve.specimen,
                "Peak force (kN)": peak.force_kN,
                "Peak force (kgf)": peak.force_kN * 101.971621,
                "Extension at peak (mm)": peak.extension_mm,
                "End extension (mm)": curve.data.extension_mm.max(),
                "End time (s)": curve.data.time_s.max(),
            }
        )
    return pd.DataFrame(rows)
