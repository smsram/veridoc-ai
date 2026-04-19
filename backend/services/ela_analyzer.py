import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import io
import base64

def perform_ela(image_path: str, quality: int = 90) -> tuple[str, int]:
    """
    Performs Error Level Analysis to detect pixel manipulation.
    Returns a tuple: (base64_heatmap_string, forgery_score_percentage)
    """
    try:
        original = Image.open(image_path).convert('RGB')
        
        # Save image at a lower quality to a buffer
        resaved_buffer = io.BytesIO()
        original.save(resaved_buffer, 'JPEG', quality=quality)
        resaved_buffer.seek(0)
        resaved = Image.open(resaved_buffer)

        # Calculate the absolute difference between original and resaved
        diff = ImageChops.difference(original, resaved)
        
        # Get the maximum pixel difference
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        if max_diff == 0:
            max_diff = 1 # Prevent division by zero
            
        # Enhance the difference to make the heatmap visible
        scale = 255.0 / max_diff
        enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)
        
        # Convert to OpenCV format to apply a colormap (Heatmap effect)
        diff_cv = cv2.cvtColor(np.array(enhanced_diff), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(diff_cv, cv2.COLOR_BGR2GRAY)
        
        # Apply Jet colormap: Red = High error (tampered), Blue = Low error (original)
        heatmap = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
        
        # Calculate a rough "forgery score" based on the variance of the errors
        # High variance usually means isolated tampering
        variance = np.var(gray)
        base_score = min(100, int((variance / 1000) * 100))
        # Ensure it's between 5% (baseline noise) and 98%
        forgery_score = max(5, min(98, base_score))

        # Convert heatmap back to Base64 to send to React
        _, buffer = cv2.imencode('.jpg', heatmap)
        heatmap_base64 = base64.b64encode(buffer).decode('utf-8')

        return heatmap_base64, forgery_score

    except Exception as e:
        print(f"ELA Analysis Error: {e}")
        # Return a safe fallback if analysis fails
        return "", 0