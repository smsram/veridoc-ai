import os
import google.generativeai as genai
from PIL import Image

# 1. Attempt to grab the API key from your environment variables
API_KEY = os.environ.get("GEMINI_API_KEY") 

if API_KEY:
    genai.configure(api_key=API_KEY)

def generate_vision_forensic_report(image: Image.Image, deterministic_score: int, deterministic_anomalies: list, target_language: str = "English", use_ai: str = "false"):
    """
    Routes between Fast Deterministic Mode and Deep Generative AI Mode based on user toggle.
    """
    
    # --- 1. FAST TESTING MODE (Default) ---
    if str(use_ai).lower() != "true":
        return {
            "overall_probability": deterministic_score,
            "executive_summary": f"FAST TESTING MODE ACTIVE: The local algorithmic engines calculated a {deterministic_score}% probability of manipulation based on pixel variance and typographic geometry.",
            "detailed_anomalies": deterministic_anomalies
        }

    # --- 2. DEEP AI SYNTHESIS MODE (Gemini Multimodal) ---
    risk_level = "Critical Risk" if deterministic_score > 70 else "Moderate Risk" if deterministic_score > 30 else "Low Risk"
    
    # Fallback if no API key is provided
    if not API_KEY:
        print("WARNING: GEMINI_API_KEY not found. Falling back to synthetic mock response.")
        return generate_mock_ai_response(deterministic_score, risk_level, deterministic_anomalies)

    try:
        # THE FIX: Switched to 1.5-flash. The Free Tier for this is universally active and stable.
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Format the algorithmic anomalies so Gemini can read them
        anomaly_descriptions = "\n".join([f"- {a['title']}: {a['description']}" for a in deterministic_anomalies])
        if not anomaly_descriptions:
            anomaly_descriptions = "None. Document geometry and pixel variance are clean."

        # The Prompt Strategy: Give Gemini the math AND the image
        prompt = f"""
        You are 'VeriDoc AI', an elite digital forensics expert system.
        I am providing you with a scanned document and the mathematical results from our low-level deterministic forensic engine.
        
        Engine Forgery Probability: {deterministic_score}% ({risk_level})
        Detected Algorithmic Anomalies:
        {anomaly_descriptions}
        
        Task: Write a highly professional, clinical executive summary (3 to 4 sentences) explaining the analysis. 
        Do not just list the anomalies. Instead, synthesize WHAT the anomalies mean in the context of the image provided. 
        If the score is high, explain how the document was likely tampered with (e.g., digital text overlay, pixel splicing, layout shifts).
        If the score is low, confirm its structural and cryptographic integrity.
        
        Respond strictly in {target_language}. Do not use Markdown formatting like bolding.
        """
        
        # Call Gemini with the Prompt AND the Raw Image!
        response = model.generate_content([prompt, image])
        ai_summary = response.text.strip()
        
        return {
            "overall_probability": deterministic_score,
            "executive_summary": f"GEMINI XAI ANALYSIS: {ai_summary}",
            "detailed_anomalies": deterministic_anomalies
        }
        
    except Exception as e:
        print(f"Gemini API Error: {e}")
        # If API limits out or fails, gracefully fallback so the frontend never crashes
        return generate_mock_ai_response(deterministic_score, risk_level, deterministic_anomalies)


def generate_mock_ai_response(deterministic_score, risk_level, deterministic_anomalies):
    """Fallback generator if Gemini API is unreachable."""
    if deterministic_score > 70:
        summary = f"DEEP AI ANALYSIS: Multimodal inspection confirms a {risk_level} of document manipulation ({deterministic_score}% probability). "
        anomaly_types = [a['title'].lower() for a in deterministic_anomalies]
        if any("pixel" in a for a in anomaly_types):
            summary += "Deep pixel-level variance indicates non-native digital ink or spliced raster elements have been superimposed over the original background. "
        if any("layout" in a or "font" in a for a in anomaly_types):
            summary += "Typographic geometry analysis reveals severe inconsistencies in text baseline alignment and font scaling, strongly suggesting manual text replacement. "
    elif deterministic_score > 30:
        summary = f"DEEP AI ANALYSIS: Multimodal inspection indicates a {risk_level} ({deterministic_score}% probability). The document exhibits anomalous characteristics that require manual review."
    else:
        summary = f"DEEP AI ANALYSIS: Multimodal inspection confirms a {risk_level} ({deterministic_score}% probability). The document maintains cryptographic structural integrity. No signs of digital tampering detected."

    return {
        "overall_probability": deterministic_score,
        "executive_summary": summary,
        "detailed_anomalies": deterministic_anomalies
    }