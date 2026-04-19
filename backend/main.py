from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pdf2image import convert_from_bytes
import io
import os

from services.ela_analyzer import perform_ela
from services.metadata_service import extract_metadata_risk
from services.ocr_service import extract_and_analyze_text
from services.xai_reporter import generate_vision_forensic_report

app = FastAPI(title="VeriDoc Code-First Forensic Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "VeriDoc Code-First Engine Online"}

@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    language: str = Form("en") 
):
    try:
        # 1. Read File & Convert to Image
        contents = await file.read()
        filename = file.filename.lower()

        if filename.endswith('.pdf'):
            images = convert_from_bytes(contents)
            if not images:
                raise ValueError("Empty PDF")
            base_image = images[0].convert('RGB')
        else:
            base_image = Image.open(io.BytesIO(contents)).convert('RGB')

        # 2. Map Language
        lang_map = {"en": "eng", "te": "tel", "hi": "hin"}
        tess_lang = f"eng+{lang_map.get(language, 'eng')}"
        gemini_lang = {"en": "English", "te": "Telugu", "hi": "Hindi"}.get(language, "English")

        # ---------------------------------------------------------
        # 3. CODE-FIRST DETERMINISTIC ENGINES (NO AI YET)
        # ---------------------------------------------------------
        heatmap_b64, ela_score = perform_ela(base_image)
        ocr_results = extract_and_analyze_text(base_image, lang=tess_lang)
        meta_risk, meta_anomalies = extract_metadata_risk(base_image)

        # 4. Calculate Hard Math Risk Score
        # If OCR finds a weird text overlay, it spikes to 85. Otherwise, use max of ELA/Meta.
        ocr_risk = 85 if len(ocr_results.get('anomalies', [])) > 0 else 5
        deterministic_score = max(ela_score, meta_risk, ocr_risk)

        # Combine all code-level anomalies into a single list
        combined_anomalies = meta_anomalies + ocr_results.get('anomalies', [])
        
        # If the pixel math detected a drawing or paste, add it to the list
        if ela_score > 60:
            combined_anomalies.append({
                "title": "Digital Ink or Pixel Splicing (ELA)",
                "description": "Algorithmic Error Level Analysis detected severe pixel mismatches, indicating drawn ink, digital white-out, or pasted images.",
                "severity": "Critical"
            })

        # ---------------------------------------------------------
        # 5. AI REPORTER (Formats the final data)
        # ---------------------------------------------------------
        # THIS IS WHAT WAS CRASHING. It now correctly passes the 2 missing arguments!
        xai_report = generate_vision_forensic_report(
            image=base_image, 
            deterministic_score=deterministic_score,       # <-- Argument 1
            deterministic_anomalies=combined_anomalies,    # <-- Argument 2
            target_language=gemini_lang
        )

        # 6. Return Payload
        return {
            "status": "success",
            "file_analyzed": file.filename,
            "xai_report": xai_report,
            "heatmap_image": f"data:image/jpeg;base64,{heatmap_b64}",
            "metadata": {
                "language_detected": language,
                "engine_version": "3.0-Deterministic"
            }
        }

    except Exception as e:
        print(f"Engine Failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")