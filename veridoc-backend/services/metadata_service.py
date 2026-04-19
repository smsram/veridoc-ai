import io

from PIL import ExifTags, Image


FLAGGED_EDITORS = (
    "adobe",
    "photoshop",
    "canva",
    "gimp",
    "pixelmator",
    "pixlr",
    "lightroom",
    "snapseed",
    "affinity",
)


def _contains_editor_signature(value: object) -> str | None:
    lowered = str(value).strip().lower()
    for editor in FLAGGED_EDITORS:
        if editor in lowered:
            return editor
    return None


def extract_metadata_risk(image: Image.Image | None = None, image_bytes: bytes | None = None):
    """Checks raw image metadata for editing-software fingerprints."""
    risk_score = 5
    anomalies = []

    try:
        source_image = image
        if source_image is None and image_bytes is not None:
            source_image = Image.open(io.BytesIO(image_bytes))

        if source_image is None:
            return risk_score, anomalies

        exif_data = source_image.getexif()
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                editor = _contains_editor_signature(value)
                if editor and tag in {"Software", "ProcessingSoftware", "HostComputer", "Artist"}:
                    risk_score = 92
                    anomalies.append(
                        {
                            "title": "Editing Software Fingerprint",
                            "description": f"Metadata reveals the file was processed using {editor.title()}.",
                            "severity": "Critical",
                        }
                    )
                    break

        if risk_score < 90:
            for key, value in source_image.info.items():
                editor = _contains_editor_signature(value)
                if editor and key.lower() in {"software", "comment", "description", "creator"}:
                    risk_score = 88
                    anomalies.append(
                        {
                            "title": "Embedded Editor Metadata",
                            "description": f"File metadata contains an editor signature linked to {editor.title()}.",
                            "severity": "High",
                        }
                    )
                    break

    except Exception as exc:
        print(f"EXIF Error: {exc}")

    return risk_score, anomalies
