from PIL import Image, ExifTags

def extract_metadata_risk(image: Image.Image):
    """Checks hidden image metadata for editing software fingerprints."""
    risk_score = 5
    anomalies = []
    
    try:
        exif_data = image.getexif()
        if not exif_data:
            return risk_score, anomalies # Screenshots often have no EXIF

        for tag_id in exif_data:
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            data = str(exif_data.get(tag_id)).lower()

            # Flag known editing software
            flagged_software = ['adobe', 'photoshop', 'canva', 'gimp', 'pixelmator']
            if tag == 'Software' and any(sw in data for sw in flagged_software):
                risk_score = 95
                anomalies.append({
                    "title": "Editing Software Fingerprint",
                    "description": f"Metadata reveals the file was processed using {data.title()}.",
                    "severity": "Critical"
                })
    except Exception as e:
        print(f"EXIF Error: {e}")
        
    return risk_score, anomalies