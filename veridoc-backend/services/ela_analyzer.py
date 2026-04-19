import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import base64
import io

def perform_ela(image: Image.Image, quality: int = 90) -> tuple[str, int, float]:
    try:
        if image.mode != 'RGB': image = image.convert('RGB')
            
        resaved_buffer = io.BytesIO()
        image.save(resaved_buffer, 'JPEG', quality=quality)
        resaved_buffer.seek(0)
        resaved = Image.open(resaved_buffer)

        diff = ImageChops.difference(image, resaved)
        diff_gray = np.array(diff.convert('L'))
        
        max_diff = np.max(diff_gray)
        # THE FIX: Lowered from 25 to 8 to catch flat digital overrides in MS Paint
        if max_diff < 8:
            return generate_heatmap(diff, max_diff), 5, 1.0
        
        h, w = diff_gray.shape
        block_size = 32
        variances = []
        
        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = diff_gray[y:y+block_size, x:x+block_size]
                variances.append(np.var(block))
        
        if not variances:
            return "", 5, 0.0
            
        variances = np.array(variances)
        
        global_mean = np.mean(variances)
        top_blocks = np.percentile(variances, 99)
        
        if global_mean < 1.0:
            global_mean = 1.0
            
        spike_ratio = round(top_blocks / global_mean, 2)
        
        if global_mean < 5.0:
            if spike_ratio > 4.5 and max_diff > 35:
                score = (spike_ratio - 4.5) * 15
                forgery_probability = min(98, max(60, int(score)))
            else:
                forgery_probability = 5
        else:
            if spike_ratio > 6.5:
                score = (spike_ratio - 6.5) * 10
                forgery_probability = min(98, max(60, int(score)))
            else:
                forgery_probability = 5

        return generate_heatmap(diff, max_diff), forgery_probability, spike_ratio

    except Exception as e:
        print(f"ELA Error: {e}")
        return "", 5, 0.0

def generate_heatmap(diff, max_diff):
    scale = 255.0 / (max_diff if max_diff > 0 else 1)
    enhanced_diff = ImageEnhance.Brightness(diff).enhance(scale)
    diff_cv = cv2.cvtColor(np.array(enhanced_diff), cv2.COLOR_RGB2BGR)
    heatmap = cv2.applyColorMap(cv2.cvtColor(diff_cv, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_JET)
    _, buffer = cv2.imencode('.jpg', heatmap)
    return base64.b64encode(buffer).decode('utf-8')