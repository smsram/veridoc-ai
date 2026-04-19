import numpy as np
import pytesseract
from PIL import Image


def _safe_float(value: object) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return -1.0


def _median_absolute_deviation(values: list[float], median_value: float) -> float:
    values_array = np.asarray(values, dtype=np.float32)
    return float(np.median(np.abs(values_array - median_value)))


def _dedupe_anomalies(anomalies: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []

    for anomaly in anomalies:
        key = f"{anomaly['title']}::{anomaly['description']}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(anomaly)

    return unique


def extract_and_analyze_text(image: Image.Image, lang: str = "eng+tel+hin"):
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        anomalies: list[dict[str, str]] = []
        lines: dict[str, list[dict[str, float | str]]] = {}
        confidences: list[float] = []
        raw_tokens: list[str] = []

        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            conf = _safe_float(data["conf"][i])

            if text:
                raw_tokens.append(text)
            if conf > 0:
                confidences.append(conf)

            if conf < 0 or len(text) < 2 or not any(char.isalnum() for char in text):
                continue

            line_id = f"{data['block_num'][i]}_{data['par_num'][i]}_{data['line_num'][i]}"
            lines.setdefault(line_id, []).append(
                {
                    "text": text,
                    "conf": conf,
                    "x": float(data["left"][i]),
                    "w": float(data["width"][i]),
                    "y": float(data["top"][i]),
                    "h": float(data["height"][i]),
                    "baseline": float(data["top"][i]) + float(data["height"][i]),
                }
            )

        for words in lines.values():
            if len(words) < 3:
                continue

            heights = [float(word["h"]) for word in words]
            baselines = [float(word["baseline"]) for word in words]
            word_confidences = [float(word["conf"]) for word in words]

            median_height = float(np.median(heights))
            median_baseline = float(np.median(baselines))
            median_conf = float(np.median(word_confidences))

            if median_height < 10:
                continue

            height_mad = max(1.0, _median_absolute_deviation(heights, median_height))
            baseline_mad = max(1.0, _median_absolute_deviation(baselines, median_baseline))

            spaces = []
            for index in range(1, len(words)):
                prev_word = words[index - 1]
                curr_word = words[index]
                gap = float(curr_word["x"]) - (float(prev_word["x"]) + float(prev_word["w"]))
                if gap > 0:
                    spaces.append(gap)

            median_space = float(np.median(spaces)) if spaces else 5.0
            space_mad = max(1.0, _median_absolute_deviation(spaces, median_space)) if spaces else 1.0

            relative_height_spread = float(np.std(heights)) / max(median_height, 1.0)
            if len(words) >= 4 and relative_height_spread > 0.32:
                anomalies.append(
                    {
                        "title": "Mixed Typography Geometry",
                        "description": (
                            f"This text line shows unusually mixed word heights ({round(relative_height_spread * 100, 1)}% spread), "
                            "which is consistent with pasted replacement text."
                        ),
                        "severity": "High",
                    }
                )

            for index, word in enumerate(words):
                word_text = str(word["text"])
                word_height = float(word["h"])
                word_conf = float(word["conf"])
                baseline_offset = abs(float(word["baseline"]) - median_baseline)
                height_offset = abs(word_height - median_height)

                height_threshold = max(4.0, median_height * 0.28, height_mad * 3.0)
                if height_offset > height_threshold:
                    anomalies.append(
                        {
                            "title": "Font Inconsistency Detected",
                            "description": (
                                f"The word '{word_text}' is {int(round(word_height))}px tall while its line median is "
                                f"{int(round(median_height))}px, suggesting mismatched font rendering."
                            ),
                            "severity": "High",
                        }
                    )

                baseline_threshold = max(3.0, baseline_mad * 3.5, median_height * 0.18)
                if baseline_offset > baseline_threshold:
                    anomalies.append(
                        {
                            "title": "Layout Misalignment Spotting",
                            "description": (
                                f"The word '{word_text}' shifts vertically by {int(round(baseline_offset))}px from the line baseline, "
                                "which often appears after pasted text-box edits."
                            ),
                            "severity": "Critical",
                        }
                    )

                if index > 0:
                    prev_word = words[index - 1]
                    actual_space = float(word["x"]) - (float(prev_word["x"]) + float(prev_word["w"]))
                    spacing_threshold = max(12.0, median_space + max(8.0, space_mad * 4.0), median_space * 2.2)
                    if actual_space > spacing_threshold:
                        anomalies.append(
                            {
                                "title": "Abnormal Kerning / Spacing",
                                "description": (
                                    f"The gap before '{word_text}' is {int(round(actual_space))}px while the line norm is "
                                    f"{int(round(median_space))}px, indicating likely erase-and-replace editing."
                                ),
                                "severity": "Critical",
                            }
                        )

                confidence_drop = median_conf - word_conf
                if median_conf >= 75 and word_conf > 0 and confidence_drop > 30 and len(word_text) >= 3:
                    anomalies.append(
                        {
                            "title": "Rendering Confidence Drop",
                            "description": (
                                f"OCR confidence for '{word_text}' drops to {int(round(word_conf))}% while nearby text is "
                                f"near {int(round(median_conf))}%, which can signal inconsistent rendering or pasted glyphs."
                            ),
                            "severity": "Medium",
                        }
                    )

        unique_anomalies = _dedupe_anomalies(anomalies)[:6]
        average_confidence = round(float(np.mean(confidences)), 2) if confidences else 0.0

        severity_weights = {"Critical": 20, "High": 12, "Medium": 6}
        penalty = min(78, sum(severity_weights.get(anomaly["severity"], 6) for anomaly in unique_anomalies))

        if average_confidence and average_confidence < 55 and unique_anomalies:
            penalty = min(85, penalty + 6)

        return {
            "text": " ".join(raw_tokens),
            "anomalies": unique_anomalies,
            "avg_confidence": average_confidence,
            "layout_penalty": penalty,
            "signal_score": penalty,
        }
    except Exception as exc:
        print(f"OCR/Layout Error: {exc}")
        return {
            "text": "",
            "anomalies": [],
            "avg_confidence": 0.0,
            "layout_penalty": 0,
            "signal_score": 0,
        }
