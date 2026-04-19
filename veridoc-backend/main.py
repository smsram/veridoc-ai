from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pdf2image import convert_from_bytes
import io
import os
import base64

# Import all services
from services.ela_analyzer import perform_ela
from services.metadata_service import extract_metadata_risk
from services.ocr_service import extract_and_analyze_text
from services.xai_reporter import generate_vision_forensic_report
from services.pdf_recovery import analyze_and_recover_pdf

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
    language: str = Form("en"),
    use_ai: str = Form("false") # Catches the toggle from the frontend
):
    try:
        contents = await file.read()
        filename = file.filename.lower()
        
        meta_anomalies = []
        recovered_pdf_b64 = None
        revisions_count = 0

        # --- PDF RECOVERY ENGINE ---
        if filename.endswith('.pdf'):
            recovery_results = analyze_and_recover_pdf(contents)
            revisions_count = recovery_results["revision_count"]
            
            if recovery_results["is_modified"]:
                meta_anomalies.extend(recovery_results["risk_indicators"])
                recovered_pdf_b64 = base64.b64encode(recovery_results["recovered_bytes"]).decode('utf-8')

            images = convert_from_bytes(contents)
            if not images:
                raise ValueError("Empty PDF")
            base_image = images[0].convert('RGB')
        else:
            base_image = Image.open(io.BytesIO(contents)).convert('RGB')

        lang_map = {"en": "eng", "te": "tel", "hi": "hin"}
        tess_lang = f"eng+{lang_map.get(language, 'eng')}"
        gemini_lang = {"en": "English", "te": "Telugu", "hi": "Hindi"}.get(language, "English")

        # --- DETERMINISTIC MATH ---
        heatmap_b64, ela_score, spike_ratio = perform_ela(base_image)
        ocr_results = extract_and_analyze_text(base_image, lang=tess_lang)
        file_meta_risk, file_meta_anomalies = extract_metadata_risk(base_image)
        
        meta_anomalies.extend(file_meta_anomalies)

        # 1. Base Score calculation
        pdf_risk = 95 if recovered_pdf_b64 else 5
        base_score = max(ela_score, file_meta_risk, pdf_risk)

        # 2. Add the Layout & Font Geometry Penalty
        layout_penalty = ocr_results.get("layout_penalty", 0)
        if layout_penalty > 0:
            deterministic_score = min(98, max(75, base_score + layout_penalty))
        else:
            deterministic_score = base_score
        
        combined_anomalies = meta_anomalies + ocr_results.get('anomalies', [])
        
        if ela_score > 40:
            combined_anomalies.append({
                "title": "Pixel Splicing / Digital Ink Detected",
                "description": f"Engine detected an unnatural pixel variance spike (Ratio: {spike_ratio}x the baseline noise).",
                "severity": "Critical"
            })
            
        if deterministic_score <= 15 and not combined_anomalies:
            combined_anomalies.append({
                "title": "Clean Algorithmic Baseline",
                "description": f"Document structure is native. Noise is uniform (Variance Spike: {spike_ratio}x).",
                "severity": "Low"
            })

        # --- REPORTER ---
        xai_report = generate_vision_forensic_report(
            image=base_image, 
            deterministic_score=deterministic_score,
            deterministic_anomalies=combined_anomalies,
            target_language=gemini_lang,
            use_ai=use_ai 
        )

        return {
            "status": "success",
            "file_analyzed": file.filename,
            "xai_report": xai_report,
            "heatmap_image": f"data:image/jpeg;base64,{heatmap_b64}",
            "recovered_pdf": f"data:application/pdf;base64,{recovered_pdf_b64}" if recovered_pdf_b64 else None,
            "metadata": {
                "language_detected": language,
                "engine_version": "5.0-PDF-Recovery",
                "revisions_detected": revisions_count
            }
        }

    except Exception as e:
        print(f"Engine Failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")