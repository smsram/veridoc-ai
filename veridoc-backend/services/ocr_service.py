import pytesseract
from PIL import Image
import numpy as np

def extract_and_analyze_text(image: Image.Image, lang: str = 'eng+tel+hin'):
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        anomalies = []
        
        lines = {}
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            text = data['text'][i].strip()
            conf = int(data['conf'][i])
            
            if conf < 0 or not text or len(text) < 2:
                continue
                
            line_id = f"{data['block_num'][i]}_{data['par_num'][i]}_{data['line_num'][i]}"
            if line_id not in lines:
                lines[line_id] = []
                
            lines[line_id].append({
                'text': text,
                'conf': conf,
                'x': data['left'][i],       # NEW: X coordinate (Horizontal start)
                'w': data['width'][i],      # NEW: Width of word
                'y': data['top'][i],
                'h': data['height'][i],
                'baseline': data['top'][i] + data['height'][i]
            })

        for line_id, words in lines.items():
            if len(words) < 3:
                continue 
            
            clean_words = [w for w in words if not any(c in w['text'] for c in ['/', '(', ')', '[', ']', '|'])]
            if not clean_words:
                clean_words = words

            heights = [w['h'] for w in clean_words]
            baselines = [w['baseline'] for w in clean_words]
            tops = [w['y'] for w in clean_words]
            
            median_h = np.median(heights)
            median_baseline = np.median(baselines)
            median_top = np.median(tops)

            # NEW: Calculate normal horizontal spacing between words
            spaces = []
            for i in range(1, len(words)):
                prev = words[i-1]
                curr = words[i]
                space = curr['x'] - (prev['x'] + prev['w'])
                if space > 0:
                    spaces.append(space)
            median_space = np.median(spaces) if spaces else 5
            
            for i, word in enumerate(words):
                if median_h < 10:
                    continue
                
                # 1. Abnormal Spacing / Kerning Check (Catches MS Paint Erase & Replace)
                if i > 0:
                    prev = words[i-1]
                    actual_space = word['x'] - (prev['x'] + prev['w'])
                    # If the gap is 2.5x larger than normal, it's a pasted textbox
                    if actual_space > (median_space * 2.5) and actual_space > 12:
                        anomalies.append({
                            "title": "Abnormal Kerning / Spacing",
                            "description": f"The spacing before '{word['text']}' is {actual_space}px (Line normal is {int(median_space)}px). Highly indicative of erased and replaced digital text.",
                            "severity": "Critical"
                        })

                # 2. Font Inconsistency Check
                has_tall_punct = any(c in word['text'] for c in ['/', '(', ')', '[', ']', '|'])
                height_diff = abs(word['h'] - median_h)
                
                # If it has brackets, we don't ignore it, we just give it a wider 60% tolerance. Otherwise 30%.
                threshold = 0.60 if has_tall_punct else 0.30
                if height_diff > (median_h * threshold) and height_diff > 4:
                    anomalies.append({
                        "title": "Font Inconsistency Detected",
                        "description": f"The word '{word['text']}' (Height: {word['h']}px) radically mismatches the line median ({int(median_h)}px).",
                        "severity": "High"
                    })
                    
                # 3. Layout Misalignment Spotting
                has_descender = any(c in word['text'] for c in ['p', 'q', 'g', 'y', 'j', ',', ';'])
                
                # If it has a descender ('g'), we check the TOP alignment. If not, we check the BOTTOM baseline.
                alignment_diff = abs(word['y'] - median_top) if has_descender else abs(word['baseline'] - median_baseline)
                
                if alignment_diff > 4:
                    anomalies.append({
                        "title": "Layout Misalignment Spotting",
                        "description": f"The word '{word['text']}' shifts vertically by {int(alignment_diff)}px from the line's natural axis. Highly indicative of pasted text boxes.",
                        "severity": "Critical"
                    })

        unique_anomalies = list({a['title'] + a['description']: a for a in anomalies}.values())[:4]
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_conf = np.mean(confidences) if confidences else 0
        
        penalty = sum([20 for a in unique_anomalies if a['severity'] == 'Critical']) + \
                  sum([10 for a in unique_anomalies if a['severity'] == 'High'])

        return {
            "text": " ".join([w for w in data['text'] if w.strip()]),
            "anomalies": unique_anomalies,
            "avg_confidence": avg_conf,
            "layout_penalty": penalty
        }
    except Exception as e:
        print(f"OCR/Layout Error: {e}")
        return {"text": "", "anomalies": [], "layout_penalty": 0}