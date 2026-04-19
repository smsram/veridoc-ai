from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pdf2image import convert_from_bytes
import io
import base64

# Import all services
from services.ela_analyzer import perform_ela
from services.forensic_scoring import combine_forensic_scores
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
        source_image = None

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
            source_image = Image.open(io.BytesIO(contents))
            base_image = source_image.convert('RGB')

        lang_map = {"en": "eng", "te": "tel", "hi": "hin"}
        tess_lang = f"eng+{lang_map.get(language, 'eng')}"
        gemini_lang = {"en": "English", "te": "Telugu", "hi": "Hindi"}.get(language, "English")

        # --- DETERMINISTIC MATH ---
        ela_results = perform_ela(base_image)
        ocr_results = extract_and_analyze_text(base_image, lang=tess_lang)
        file_meta_risk, file_meta_anomalies = extract_metadata_risk(image=source_image, image_bytes=contents if source_image else None)

        meta_anomalies.extend(file_meta_anomalies)
        meta_anomalies.extend(ela_results.get("anomalies", []))

        pdf_risk = 95 if recovered_pdf_b64 else 5
        combined_anomalies = meta_anomalies + ocr_results.get('anomalies', [])

        deterministic_score = combine_forensic_scores(
            ela_score=int(ela_results.get("score", 5)),
            ocr_score=int(ocr_results.get("signal_score", ocr_results.get("layout_penalty", 0))),
            metadata_score=file_meta_risk,
            pdf_score=pdf_risk,
            anomalies=combined_anomalies,
        )

        if deterministic_score <= 15 and not combined_anomalies:
            combined_anomalies.append(
                {
                    "title": "Clean Algorithmic Baseline",
                    "description": (
                        f"Document structure is native. Residual noise is uniform "
                        f"(Variance Spike: {ela_results.get('spike_ratio', 1.0)}x)."
                    ),
                    "severity": "Low",
                }
            )

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
            "heatmap_image": f"data:image/jpeg;base64,{ela_results.get('heatmap', '')}",
            "recovered_pdf": f"data:application/pdf;base64,{recovered_pdf_b64}" if recovered_pdf_b64 else None,
            "metadata": {
                "language_detected": language,
                "engine_version": "6.0-Adaptive-Ensemble",
                "revisions_detected": revisions_count,
                "ela_spike_ratio": ela_results.get("spike_ratio", 1.0),
                "ela_quality": ela_results.get("quality", 90),
                "ocr_confidence": ocr_results.get("avg_confidence", 0.0),
                "forensic_evidence": ela_results.get("evidence", {}),
            },
        }

    except Exception as e:
        print(f"Engine Failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Engine Error: {str(e)}")
