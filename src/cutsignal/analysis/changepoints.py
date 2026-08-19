"""Deterministic, BIC-selected piecewise-linear change-point detection."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ChangePointEstimate:
    index: int
    before_slope_per_unit: float
    after_slope_per_unit: float
    bic_improvement: float


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    if x.size < 2 or np.allclose(x, x[0]):
        mean = float(np.mean(y)) if y.size else 0.0
        return 0.0, float(np.sum((y - mean) ** 2))
    centered_x = x - np.mean(x)
    slope = float(np.dot(centered_x, y - np.mean(y)) / np.dot(centered_x, centered_x))
    fitted = np.mean(y) + slope * centered_x
    sse = float(np.sum((y - fitted) ** 2))
    return slope, max(sse, 1e-12)


def detect_change_points(
    values: list[float] | np.ndarray,
    *,
    min_segment: int = 10,
    max_change_points: int = 3,
) -> list[ChangePointEstimate]:
    """Find globally selected piecewise-linear breaks with a BIC penalty.

    The function operates on equally spaced observations. It deliberately favors
    no break unless the reduction in residual error exceeds the complexity cost.
    """
    y = np.asarray(values, dtype=float)
    if y.ndim != 1:
        raise ValueError("values must be one-dimensional")
    if not np.all(np.isfinite(y)):
        raise ValueError("values must be finite")
    n = y.size
    if n < min_segment * 2 or max_change_points < 1:
        return []
    x = np.arange(n, dtype=float)
    max_segments = min(max_change_points + 1, n // min_segment)

    segment_cost = np.full((n + 1, n + 1), np.inf)
    segment_slope = np.zeros((n + 1, n + 1))
    for start in range(n):
        for end in range(start + min_segment, n + 1):
            slope, sse = _linear_fit(x[start:end], y[start:end])
            segment_cost[start, end] = sse
            segment_slope[start, end] = slope

    dp = np.full((max_segments + 1, n + 1), np.inf)
    previous = np.full((max_segments + 1, n + 1), -1, dtype=int)
    dp[1, min_segment:] = segment_cost[0, min_segment:]
    for segments in range(2, max_segments + 1):
        min_end = segments * min_segment
        for end in range(min_end, n + 1):
            starts = range((segments - 1) * min_segment, end - min_segment + 1)
            for start in starts:
                candidate = dp[segments - 1, start] + segment_cost[start, end]
                if candidate < dp[segments, end]:
                    dp[segments, end] = candidate
                    previous[segments, end] = start

    bics: list[float] = []
    for segments in range(1, max_segments + 1):
        sse = max(dp[segments, n], 1e-12)
        parameter_count = 2 * segments + (segments - 1)
        bics.append(n * np.log(sse / n) + parameter_count * np.log(n))
    best_segments = int(np.argmin(bics)) + 1
    if best_segments == 1:
        return []

    boundaries: list[int] = []
    end = n
    for segments in range(best_segments, 1, -1):
        start = int(previous[segments, end])
        if start < 0:
            return []
        boundaries.append(start)
        end = start
    boundaries.reverse()

    estimates: list[ChangePointEstimate] = []
    segment_edges = [0, *boundaries, n]
    baseline_bic = bics[0]
    for boundary_index, boundary in enumerate(boundaries, start=1):
        left = segment_edges[boundary_index - 1]
        right = segment_edges[boundary_index + 1]
        estimates.append(
            ChangePointEstimate(
                index=boundary,
                before_slope_per_unit=float(segment_slope[left, boundary]),
                after_slope_per_unit=float(segment_slope[boundary, right]),
                bic_improvement=float(max(baseline_bic - bics[best_segments - 1], 0.0)),
            )
        )
    return estimates
