import base64
import json
import io
import os
from openai import OpenAI
from PIL import Image


MEASUREMENT_NAMES = [
    "Chest", "Stomach", "Shoulder", "Sleeve Length",
    "Neck", "Round Sleeve", "Top Length",
    "Trouser Length", "Trouser-waist", "Hips", "Laps", "Knee", "Ankle"
]


def _get_api_key():
    val = os.getenv("OPENAI_API_KEY", "").strip()
    if not val:
        try:
            import streamlit as st
            val = str(st.secrets.get("OPENAI_API_KEY", "")).strip()
        except Exception:
            pass
    return val


SYSTEM_PROMPT = """You are an expert tailor and body measurement analyst. Given a front-facing photo of a person and their height, estimate their body measurements for tailoring.

Use your visual analysis of body proportions, not generic population averages. Look at the person's actual build — shoulder width relative to height, torso length, limb proportions, waist definition, etc.

For each measurement, consider:
- **Shoulder width**: straight distance between shoulder points
- **Chest circumference**: around the fullest part of the chest
- **Stomach/waist circumference**: around the narrowest part of the torso
- **Hips circumference**: around the widest part of the hips
- **Neck circumference**: around the base of the neck
- **Sleeve length**: from shoulder point to wrist bone
- **Round sleeve (bicep)**: circumference of the upper arm at its fullest
- **Top length**: from shoulder line to hip bone (vertical)
- **Trouser length**: from waist to ankle bone (vertical side)
- **Trouser-waist**: same as waist circumference
- **Laps (thigh)**: circumference of the upper thigh at its fullest
- **Knee circumference**: around the knee
- **Ankle circumference**: around the ankle

Return ONLY valid JSON with no markdown, no explanation:
{
  "Chest": number,
  "Stomach": number,
  "Shoulder": number,
  "Sleeve Length": number,
  "Neck": number,
  "Round Sleeve": number,
  "Top Length": number,
  "Trouser Length": number,
  "Trouser-waist": number,
  "Hips": number,
  "Laps": number,
  "Knee": number,
  "Ankle": number,
  "confidence": "high"|"medium"|"low",
  "notes": "brief explanation of what informed your estimates"
}"""


class OpenAIScanner:
    def __init__(self, model="gpt-4o"):
        self.model = model
        api_key = _get_api_key()
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or secrets.")
        self.client = OpenAI(api_key=api_key)

    def estimate_measurements(self, front_image: Image.Image, height_cm: float,
                              ref_chest=None, ref_shoulder=None,
                              ref_waist=None, ref_hip=None) -> dict:
        buffer = io.BytesIO()
        front_image.save(buffer, format="JPEG", quality=85)
        b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64}"

        refs = []
        if ref_chest:    refs.append(f"Chest={ref_chest}cm")
        if ref_shoulder: refs.append(f"Shoulder={ref_shoulder}cm")
        if ref_waist:    refs.append(f"Waist={ref_waist}cm")
        if ref_hip:      refs.append(f"Hips={ref_hip}cm")

        user_prompt = f"The person's height is {height_cm:.1f} cm."
        if refs:
            user_prompt += f" Known tape measurements for calibration: {', '.join(refs)}. Use these as ground truth anchors and adjust related measurements proportionally."
        user_prompt += " Estimate all 13 tailoring measurements in cm. Return JSON."

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url, "detail": "high"}}
                    ]}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000,
            )
        except Exception as e:
            return {"error": str(e)}

        raw = resp.choices[0].message.content.strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"error": f"Failed to parse API response: {raw[:200]}"}

        for name in MEASUREMENT_NAMES:
            if name in data:
                try:
                    data[name] = float(data[name])
                except (ValueError, TypeError):
                    data[name] = None

        data["_source"] = "openai"
        data["_model"] = self.model
        return data

    def annotate_image(self, image: Image.Image, measurements: dict) -> Image.Image:
        from PIL import ImageDraw, ImageFont
        ann = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", ann.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        fw, fh = ann.size
        lines = [f"GPT-4o Estimation", f"Height: {measurements.get('_height_cm', '?')} cm"]
        for name in MEASUREMENT_NAMES:
            v = measurements.get(name)
            if v is not None:
                lines.append(f"{name}: {v:.1f} cm")
        conf = measurements.get("confidence", "")
        if conf:
            lines.append(f"Confidence: {conf.upper()}")

        y = 20
        for line in lines:
            draw.text((20, y), line, fill=(255, 255, 255, 240), font=None)
            y += 22

        ann = Image.alpha_composite(ann, overlay)
        return ann.convert("RGB")
