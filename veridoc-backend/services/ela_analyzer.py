import base64
import io

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _block_size_for(height: int, width: int) -> int:
    shortest_edge = max(16, min(height, width))
    return int(_clamp(shortest_edge // 18, 16, 40))


def _score_ela_metrics(
    *,
    max_diff: float,
    p99: float,
    spike_ratio: float,
    mean_diff: float,
    hotspot_coverage: float,
    suspicious_block_fraction: float,
    low_texture_ratio: float,
    largest_component: float,
    component_count: int,
    peak_block_mean: float,
) -> int:
    score = 5.0

    if max_diff >= 10:
        score += min(12.0, (max_diff - 10.0) * 0.8)
    if p99 >= 10:
        score += min(14.0, (p99 - 10.0) * 0.7)
    if spike_ratio > 2.4:
        score += min(28.0, (spike_ratio - 2.4) * 7.5)

    if 0.001 <= hotspot_coverage <= 0.08:
        score += min(18.0, 7.0 + hotspot_coverage * 180.0)
    elif hotspot_coverage > 0.08:
        score += 6.0

    if suspicious_block_fraction > 0.01:
        score += min(14.0, suspicious_block_fraction * 160.0)

    if low_texture_ratio > 0.004:
        score += min(18.0, low_texture_ratio * 240.0)

    if peak_block_mean > 1.4:
        score += min(12.0, (peak_block_mean - 1.4) * 10.0)

    if 0.0002 <= largest_component <= 0.03:
        score += min(10.0, 4.0 + largest_component * 260.0)

    if component_count >= 3:
        score += min(8.0, float(component_count))

    # Widespread residual noise is usually recompression or scan texture, not tampering.
    if hotspot_coverage > 0.18 and mean_diff > 16 and spike_ratio < 4.0:
        score -= 12.0

    if mean_diff < 2.5 and spike_ratio < 2.0:
        score = min(score, 12.0)

    # Crisp-but-clean digital documents can create high variance ratios with almost no actual residual energy.
    if p99 < 4 and mean_diff < 0.15 and hotspot_coverage < 0.0005 and low_texture_ratio < 0.004 and peak_block_mean < 1.55:
        score = min(score, 14.0)

    return int(round(_clamp(score, 5.0, 98.0)))


def _build_anomalies(
    *,
    score: int,
    spike_ratio: float,
    hotspot_coverage: float,
    low_texture_ratio: float,
    component_count: int,
    largest_component: float,
) -> list[dict[str, str]]:
    anomalies: list[dict[str, str]] = []

    if score >= 52 and spike_ratio >= 3.2:
        anomalies.append(
            {
                "title": "Localized Pixel Splicing Signature",
                "description": (
                    f"Compression residuals form concentrated hotspots with a {spike_ratio}x variance spike, "
                    "which is consistent with pasted raster content or digital ink overlays."
                ),
                "severity": "Critical",
            }
        )

    if score >= 45 and low_texture_ratio >= 0.01:
        anomalies.append(
            {
                "title": "Low-Texture Residual Mismatch",
                "description": (
                    f"About {round(low_texture_ratio * 100, 2)}% of low-texture blocks show abnormal residual energy, "
                    "a common sign of edited text inside otherwise flat paper regions."
                ),
                "severity": "High",
            }
        )

    if score >= 42 and component_count >= 4 and 0.0004 <= largest_component <= 0.03:
        anomalies.append(
            {
                "title": "Clustered Compression Hotspots",
                "description": (
                    f"Residual hotspots cover {round(hotspot_coverage * 100, 2)}% of the page in {component_count} clusters, "
                    "suggesting localized edits instead of uniform camera or scanner noise."
                ),
                "severity": "High",
            }
        )

    return anomalies


def _analyze_residual_map(original_gray: np.ndarray, diff_gray: np.ndarray) -> dict[str, object]:
    max_diff = float(np.max(diff_gray))
    mean_diff = float(np.mean(diff_gray))
    p99 = float(np.percentile(diff_gray, 99))

    if max_diff < 6:
        return {
            "score": 5,
            "spike_ratio": 1.0,
            "anomalies": [],
            "evidence": {
                "max_diff": round(max_diff, 2),
                "mean_diff": round(mean_diff, 2),
                "p99_diff": round(p99, 2),
                "peak_block_mean": 0.0,
                "hotspot_coverage": 0.0,
                "low_texture_hotspot_ratio": 0.0,
                "largest_component_ratio": 0.0,
                "component_count": 0,
            },
            "max_diff": max_diff,
        }

    height, width = diff_gray.shape
    block_size = _block_size_for(height, width)
    block_variances = []
    original_variances = []
    block_means = []

    for y in range(0, height - block_size + 1, block_size):
        for x in range(0, width - block_size + 1, block_size):
            diff_block = diff_gray[y : y + block_size, x : x + block_size]
            original_block = original_gray[y : y + block_size, x : x + block_size]
            block_variances.append(float(np.var(diff_block)))
            original_variances.append(float(np.var(original_block)))
            block_means.append(float(np.mean(diff_block)))

    if not block_variances:
        return {
            "score": 5,
            "spike_ratio": 1.0,
            "anomalies": [],
            "evidence": {
                "max_diff": round(max_diff, 2),
                "mean_diff": round(mean_diff, 2),
                "p99_diff": round(p99, 2),
                "peak_block_mean": 0.0,
                "hotspot_coverage": 0.0,
                "low_texture_hotspot_ratio": 0.0,
                "largest_component_ratio": 0.0,
                "component_count": 0,
            },
            "max_diff": max_diff,
        }

    block_variances = np.asarray(block_variances, dtype=np.float32)
    original_variances = np.asarray(original_variances, dtype=np.float32)
    block_means = np.asarray(block_means, dtype=np.float32)

    median_variance = float(np.median(block_variances))
    top_variance = float(np.percentile(block_variances, 99))
    spike_ratio = round(top_variance / max(median_variance, 1.0), 2)
    peak_block_mean = float(np.max(block_means))
    std_diff = float(np.std(diff_gray))

    hotspot_threshold = max(18.0, p99 * 0.72, mean_diff + (std_diff * 2.2))
    hotspot_mask = (diff_gray >= hotspot_threshold).astype(np.uint8) * 255
    kernel = np.ones((3, 3), dtype=np.uint8)
    hotspot_mask = cv2.morphologyEx(hotspot_mask, cv2.MORPH_OPEN, kernel)
    hotspot_mask = cv2.morphologyEx(hotspot_mask, cv2.MORPH_CLOSE, kernel)

    hotspot_coverage = float(np.count_nonzero(hotspot_mask)) / float(hotspot_mask.size)

    component_count = 0
    largest_component = 0.0
    if np.count_nonzero(hotspot_mask) > 0:
        num_labels, _, stats, _ = cv2.connectedComponentsWithStats(hotspot_mask, 8)
        min_component_area = max(12, int((block_size * block_size) * 0.15))
        component_areas = [
            float(stats[i, cv2.CC_STAT_AREA]) / float(hotspot_mask.size)
            for i in range(1, num_labels)
            if stats[i, cv2.CC_STAT_AREA] >= min_component_area
        ]
        component_count = len(component_areas)
        largest_component = max(component_areas, default=0.0)

    suspicious_cutoff = max(float(np.percentile(block_variances, 96)), median_variance * 2.8)
    suspicious_blocks = block_variances >= suspicious_cutoff
    suspicious_block_fraction = float(np.mean(suspicious_blocks))

    low_texture_cutoff = float(np.percentile(original_variances, 45))
    low_texture_hotspots = np.logical_and(suspicious_blocks, original_variances <= low_texture_cutoff)
    low_texture_ratio = float(np.mean(low_texture_hotspots))

    score = _score_ela_metrics(
        max_diff=max_diff,
        p99=p99,
        spike_ratio=spike_ratio,
        mean_diff=mean_diff,
        hotspot_coverage=hotspot_coverage,
        suspicious_block_fraction=suspicious_block_fraction,
        low_texture_ratio=low_texture_ratio,
        largest_component=largest_component,
        component_count=component_count,
        peak_block_mean=peak_block_mean,
    )

    return {
        "score": score,
        "spike_ratio": spike_ratio,
        "anomalies": _build_anomalies(
            score=score,
            spike_ratio=spike_ratio,
            hotspot_coverage=hotspot_coverage,
            low_texture_ratio=low_texture_ratio,
            component_count=component_count,
            largest_component=largest_component,
        ),
        "evidence": {
            "max_diff": round(max_diff, 2),
            "mean_diff": round(mean_diff, 2),
            "p99_diff": round(p99, 2),
            "peak_block_mean": round(peak_block_mean, 2),
            "hotspot_coverage": round(hotspot_coverage, 4),
            "low_texture_hotspot_ratio": round(low_texture_ratio, 4),
            "largest_component_ratio": round(largest_component, 4),
            "component_count": component_count,
        },
        "max_diff": max_diff,
    }


def perform_ela(image: Image.Image, qualities: tuple[int, ...] = (95, 90, 85)) -> dict[str, object]:
    try:
        if image.mode != "RGB":
            image = image.convert("RGB")

        original_gray = np.array(image.convert("L"), dtype=np.float32)
        best_result: dict[str, object] | None = None

        for quality in qualities:
            resaved_buffer = io.BytesIO()
            image.save(resaved_buffer, "JPEG", quality=quality)
            resaved_buffer.seek(0)
            resaved = Image.open(resaved_buffer).convert("RGB")

            diff = ImageChops.difference(image, resaved)
            diff_gray = np.array(diff.convert("L"), dtype=np.float32)
            analysis = _analyze_residual_map(original_gray, diff_gray)
            analysis["quality"] = quality
            analysis["heatmap"] = generate_heatmap(diff, float(analysis["max_diff"]))

            if best_result is None or int(analysis["score"]) > int(best_result["score"]):
                best_result = analysis

        if best_result is None:
            raise ValueError("Unable to compute ELA metrics")

        return best_result

    except Exception as exc:
        print(f"ELA Error: {exc}")
        return {
            "heatmap": "",
            "score": 5,
            "spike_ratio": 1.0,
            "quality": 90,
            "anomalies": [],
            "evidence": {
                "max_diff": 0.0,
                "mean_diff": 0.0,
                "p99_diff": 0.0,
                "peak_block_mean": 0.0,
                "hotspot_coverage": 0.0,
                "low_texture_hotspot_ratio": 0.0,
                "largest_component_ratio": 0.0,
                "component_count": 0,
            },
            "max_diff": 0.0,
        }


def generate_heatmap(diff: Image.Image, max_diff: float) -> str:
    scale = 255.0 / (max_diff if max_diff > 0 else 1.0)
    enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)
    diff_cv = cv2.cvtColor(np.array(enhanced_diff), cv2.COLOR_RGB2BGR)
    heatmap = cv2.applyColorMap(cv2.cvtColor(diff_cv, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_JET)
    _, buffer = cv2.imencode(".jpg", heatmap)
    return base64.b64encode(buffer).decode("utf-8")
