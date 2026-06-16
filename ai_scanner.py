import math
import numpy as np
from PIL import Image, ImageDraw
from typing import Optional

from mediapipe.tasks import python  # type: ignore
from mediapipe.tasks.python import vision  # type: ignore
import mediapipe as mp


LEFT_SHOULDER  = 11
RIGHT_SHOULDER = 12
LEFT_HIP       = 23
RIGHT_HIP      = 24
LEFT_KNEE      = 25
RIGHT_KNEE     = 26
LEFT_ANKLE     = 27
RIGHT_ANKLE    = 28
LEFT_EAR       = 7
RIGHT_EAR      = 8
LEFT_ELBOW     = 13
RIGHT_ELBOW    = 14
LEFT_WRIST     = 15
RIGHT_WRIST    = 16
NOSE           = 0

POSE_CONNECTIONS = frozenset([
    (0, 1), (1, 2), (2, 3), (3, 7),
    (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15),
    (12, 14), (14, 16),
    (11, 23), (12, 24), (23, 24),
    (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32),
    (27, 31), (28, 32),
])

class PoseScanner:
    def __init__(self, model_path: str = "pose_landmarker.task"):
        self.model_path = model_path
        self._detector = None

    def _get_detector(self):
        if self._detector is None:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = vision.PoseLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
            )
            self._detector = vision.PoseLandmarker.create_from_options(options)
        return self._detector

    def detect(self, image: Image.Image):
        detector = self._get_detector()
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(image))
        result = detector.detect(mp_image)
        if not result.pose_landmarks:
            return None
        lm = result.pose_landmarks[0]
        coords = np.zeros((33, 3))
        for i in range(33):
            coords[i] = [lm[i].x, lm[i].y, lm[i].visibility]
        return coords

    @staticmethod
    def _dist(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    @staticmethod
    def _circ_from_width(width_ratio, depth_factor=1.15):
        return width_ratio * math.pi / 2 * (1 + depth_factor)

    def estimate_measurements(
        self,
        front_image: Image.Image,
        height_cm: float,
        back_image: Optional[Image.Image] = None,
        ref_chest: Optional[float] = None,
        ref_shoulder: Optional[float] = None,
        ref_waist: Optional[float] = None,
        ref_hip: Optional[float] = None,
    ) -> Optional[dict]:
        landmarks = self.detect(front_image)
        if landmarks is None:
            return None

        fw, fh = front_image.size
        lm = landmarks.copy()
        lm[:, 0] *= fw
        lm[:, 1] *= fh

        def px(a, b):
            return math.sqrt((lm[a][0] - lm[b][0]) ** 2 + (lm[a][1] - lm[b][1]) ** 2)

        def vis(idx):
            return lm[idx][2] > 0.5

        enough = sum(vis(i) for i in [LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE])
        if enough < 4:
            return None

        shoulder_px = px(LEFT_SHOULDER, RIGHT_SHOULDER)
        hip_px = px(LEFT_HIP, RIGHT_HIP)
        torso_px = (lm[11][1] + lm[12][1]) / 2 - (lm[23][1] + lm[24][1]) / 2
        leg_left_px = lm[LEFT_HIP][1] - lm[LEFT_ANKLE][1] if vis(LEFT_ANKLE) else 0
        leg_right_px = lm[RIGHT_HIP][1] - lm[RIGHT_ANKLE][1] if vis(RIGHT_ANKLE) else 0
        leg_px = max(leg_left_px, leg_right_px)

        head_top_y = min(lm[NOSE][1] - (lm[LEFT_EAR][1] - lm[NOSE][1]) * 1.2 if vis(LEFT_EAR) else
                          lm[NOSE][1] - torso_px * 0.12, lm[NOSE][1])
        ankle_y = max(lm[LEFT_ANKLE][1] if vis(LEFT_ANKLE) else 0,
                      lm[RIGHT_ANKLE][1] if vis(RIGHT_ANKLE) else 0)
        person_px = max(ankle_y - head_top_y, torso_px + leg_px, 1)
        scale = height_cm / person_px

        def cm(dist_px):
            return dist_px * scale

        def circ_from_width_px(width_px, adjust=1.15):
            w = cm(width_px)
            return w * math.pi / 2 * (1 + adjust)

        shoulder = cm(shoulder_px)
        chest_width_px = shoulder_px * 0.95 if vis(LEFT_SHOULDER) else hip_px
        chest_width = cm(chest_width_px)
        chest = circ_from_width_px(chest_width_px, 1.2)

        waist_y = (lm[LEFT_HIP][1] + lm[RIGHT_HIP][1]) / 2 - (torso_px * 0.15)
        waist_width_px = None
        if 0 <= waist_y < fh:
            left_hip_x = lm[LEFT_HIP][0]
            right_hip_x = lm[RIGHT_HIP][0]
            waist_width_px = right_hip_x - left_hip_x
            if waist_width_px <= 0:
                waist_width_px = hip_px * 0.85
        else:
            waist_width_px = hip_px * 0.85
        stomach = circ_from_width_px(waist_width_px, 1.1)

        hip_width_px = hip_px if hip_px > 0 else shoulder_px * 0.9
        hips = circ_from_width_px(hip_width_px, 1.2)

        neck_width_px = px(LEFT_SHOULDER, RIGHT_SHOULDER) * 0.3
        neck = circ_from_width_px(neck_width_px, 1.0)
        if neck < 25:
            neck = height_cm * 0.196

        sleeve_left = cm(px(LEFT_SHOULDER, LEFT_WRIST)) if vis(LEFT_WRIST) else None
        sleeve_right = cm(px(RIGHT_SHOULDER, RIGHT_WRIST)) if vis(RIGHT_WRIST) else None
        sleeve = sleeve_left or sleeve_right or (height_cm * 0.352)

        bicep_left = circ_from_width_px(px(LEFT_ELBOW, LEFT_SHOULDER) * 0.2, 1.0) if vis(LEFT_ELBOW) else None
        bicep_right = circ_from_width_px(px(RIGHT_ELBOW, RIGHT_SHOULDER) * 0.2, 1.0) if vis(RIGHT_ELBOW) else None
        round_sleeve = bicep_left or bicep_right or (height_cm * 0.168)

        top_len = cm(torso_px) if torso_px > 0 else height_cm * 0.300

        trouser_len = cm(leg_px) if leg_px > 0 else height_cm * 0.472
        trouser_waist = stomach

        lap_width_px = px(LEFT_HIP, LEFT_KNEE) * 0.25 if vis(LEFT_KNEE) else hip_px * 0.35
        laps = circ_from_width_px(lap_width_px, 1.0)
        if laps < 30:
            laps = hips * 0.62

        knee_width_px = px(LEFT_KNEE, RIGHT_KNEE) if (vis(LEFT_KNEE) and vis(RIGHT_KNEE)) else hip_px * 0.35
        knee = circ_from_width_px(knee_width_px, 1.0)
        if knee < 20:
            knee = hips * 0.42

        ankle_width_px = px(LEFT_ANKLE, RIGHT_ANKLE) if (vis(LEFT_ANKLE) and vis(RIGHT_ANKLE)) else trouser_len * 0.06
        ankle = circ_from_width_px(ankle_width_px, 0.9)
        if ankle < 15:
            ankle = hips * 0.24

        cf = ref_chest / chest if ref_chest and chest > 0 else 1.0
        sf = ref_shoulder / shoulder if ref_shoulder and shoulder > 0 else 1.0
        wf = ref_waist / stomach if ref_waist and stomach > 0 else 1.0
        hf = ref_hip / hips if ref_hip and hips > 0 else 1.0

        blend = (cf + sf + wf + hf) / 4
        if ref_chest or ref_shoulder or ref_waist or ref_hip:
            pass
        else:
            blend = 1.0

        n_refs = sum(x is not None for x in [ref_chest, ref_shoulder, ref_waist, ref_hip])
        if n_refs >= 3:
            conf = "high"
            note = f"Calibrated with {n_refs} tape measurements. Landmark-based estimation."
        elif n_refs >= 1:
            conf = "medium"
            note = f"Partially calibrated ({n_refs} tape reference). Add more for higher accuracy."
        else:
            conf = "medium"
            note = "Estimated from pose landmarks and height. Provide tape measurements for better accuracy."

        adjust = blend if abs(blend - 1.0) > 0.05 else 1.0

        result = {
            "Chest":          chest * adjust,
            "Stomach":        stomach * adjust,
            "Shoulder":       shoulder * adjust,
            "Sleeve Length":  sleeve * adjust,
            "Neck":           neck * adjust,
            "Round Sleeve":   round_sleeve * adjust,
            "Top Length":     top_len * adjust,
            "Trouser Length": trouser_len * adjust,
            "Trouser-waist":  trouser_waist * adjust,
            "Hips":           hips * adjust,
            "Laps":           laps * adjust,
            "Knee":           knee * adjust,
            "Ankle":          ankle * adjust,
            "_confidence":    conf,
            "_notes":         note,
            "_scale":         scale,
            "_landmarks":     landmarks,
        }
        return result

    def annotate_image(self, image: Image.Image, landmarks: np.ndarray) -> Image.Image:
        ann = image.copy().convert("RGBA")
        overlay = Image.new("RGBA", ann.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        fw, fh = image.size
        lm_abs = landmarks.copy()
        lm_abs[:, 0] *= fw
        lm_abs[:, 1] *= fh

        for i, (a, b) in enumerate(POSE_CONNECTIONS):
            if landmarks[a][2] < 0.3 or landmarks[b][2] < 0.3:
                continue
            ax, ay = lm_abs[a][0], lm_abs[a][1]
            bx, by = lm_abs[b][0], lm_abs[b][1]
            draw.line([(ax, ay), (bx, by)], fill=(37, 99, 235, 200), width=3)

        colors = [
            (255, 50, 50), (255, 255, 50), (50, 255, 50),
            (50, 200, 255), (255, 100, 200), (200, 150, 255),
        ]
        for i in range(33):
            if landmarks[i][2] < 0.3:
                continue
            x, y = lm_abs[i][0], lm_abs[i][1]
            col = colors[i % len(colors)]
            r = 5
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=col + (220,))
            draw.text((x + 7, y - 5), str(i), fill=(255, 255, 255, 220))

        ann = Image.alpha_composite(ann, overlay)
        return ann.convert("RGB")
