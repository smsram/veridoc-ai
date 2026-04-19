def combine_forensic_scores(
    *,
    ela_score: int,
    ocr_score: int,
    metadata_score: int,
    pdf_score: int,
    anomalies: list[dict[str, str]],
) -> int:
    weighted_score = (
        (ela_score * 0.46)
        + (ocr_score * 0.28)
        + (metadata_score * 0.14)
        + (pdf_score * 0.12)
    )

    strongest_signal = max(ela_score, ocr_score, metadata_score, pdf_score)
    critical_count = sum(1 for anomaly in anomalies if anomaly.get("severity") == "Critical")
    high_count = sum(1 for anomaly in anomalies if anomaly.get("severity") == "High")
    supporting_signals = sum(
        1
        for score in (ela_score, ocr_score, metadata_score, pdf_score)
        if score >= 35
    )

    synergy_bonus = 0.0
    if ela_score >= 45 and ocr_score >= 30:
        synergy_bonus += 12.0
    if metadata_score >= 80 and (ela_score >= 30 or ocr_score >= 25):
        synergy_bonus += 8.0
    if pdf_score >= 80:
        synergy_bonus += 14.0
    if supporting_signals >= 3:
        synergy_bonus += 8.0
    if critical_count >= 2:
        synergy_bonus += 6.0
    elif critical_count == 1 and high_count >= 1:
        synergy_bonus += 4.0

    fused_score = max(weighted_score + synergy_bonus, (strongest_signal * 0.72) + (weighted_score * 0.28))

    if supporting_signals == 0 and critical_count == 0 and high_count == 0:
        fused_score = min(fused_score, 14.0)

    if strongest_signal <= 15 and weighted_score <= 12 and not anomalies:
        return 5

    if strongest_signal < 30 and critical_count == 0 and high_count == 0:
        fused_score = min(fused_score, 24.0)

    return int(max(5, min(98, round(fused_score))))
