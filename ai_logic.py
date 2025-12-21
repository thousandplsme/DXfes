import cv2
import numpy as np
import mediapipe as mp
from mediapipe import solutions

class SimpleConcentrationDetector:
    def __init__(self):
        self.mp_face_mesh = solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # 決定した閾値（調整済みの値を入れてください）
        self.EAR_THRESHOLD = 0.22
        self.SAFE_YAW = 15
        self.SAFE_PITCH = 15
        self.SAFE_ROLL = 15
        self.MARGIN = 0.01 

    def analyze_frame(self, frame):
        # AI処理（前回作成した高精度版ロジック）
        img_h, img_w, _ = frame.shape
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = self.face_mesh.process(image)
        image.flags.writeable = True
        
        score = 0
        message = "No Face"
        debug_info = {}

        if results.multi_face_landmarks:
            landmarks = results.multi_face_landmarks[0].landmark
            
            # 画面外判定
            check_points = [1, 33, 263, 152]
            is_out_of_frame = False
            for idx in check_points:
                lm = landmarks[idx]
                if lm.x < self.MARGIN or lm.x > (1.0 - self.MARGIN) or \
                   lm.y < self.MARGIN or lm.y > (1.0 - self.MARGIN):
                    is_out_of_frame = True
                    break
            
            if is_out_of_frame:
                return 0, "Out of Frame", {"ear":0, "yaw":0, "pitch":0, "roll":0}

            # 計算
            left_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144], img_w, img_h)
            right_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 373, 380], img_w, img_h)
            avg_ear = (left_ear + right_ear) / 2.0
            yaw, pitch, roll = self._calculate_precise_pose(landmarks, img_w, img_h)
            
            debug_info = {"ear": avg_ear, "yaw": yaw, "pitch": pitch, "roll": roll}

            # 判定
            if avg_ear < self.EAR_THRESHOLD:
                score = 10
                message = "Sleeping"
            else:
                p_yaw = max(0, abs(yaw) - self.SAFE_YAW) * 3.0
                p_pitch = max(0, abs_pitch - self.SAFE_PITCH) * 2.5
                p_roll = max(0, abs_roll - self.SAFE_ROLL) * 2.5
                
                total_penalty = p_yaw + p_pitch + p_roll
                raw_score = 100 - total_penalty
                score = int(max(0, min(100, raw_score)))
                
                if score > 80: message = "Perfect"
                elif score > 60: message = "Good"
                elif score > 40: message = "Slightly Off"
                elif score > 20: message = "Looking Away"
                else: message = "Bad Posture"

        return score, message, debug_info

    def _calculate_ear(self, landmarks, indices, w, h):
        coords = []
        for i in indices:
            lm = landmarks[i]
            coords.append(np.array([lm.x * w, lm.y * h]))
        v1 = np.linalg.norm(coords[1] - coords[5])
        v2 = np.linalg.norm(coords[2] - coords[4])
        h_dist = np.linalg.norm(coords[0] - coords[3])
        if h_dist == 0: return 0.0
        return (v1 + v2) / (2.0 * h_dist)

    def _calculate_precise_pose(self, landmarks, w, h):
        nose = np.array([landmarks[1].x * w, landmarks[1].y * h])
        left_eye = np.array([landmarks[33].x * w, landmarks[33].y * h])
        right_eye = np.array([landmarks[263].x * w, landmarks[263].y * h])
        chin = np.array([landmarks[152].x * w, landmarks[152].y * h])
        top = np.array([landmarks[10].x * w, landmarks[10].y * h])

        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        roll = np.degrees(np.arctan2(dy, dx))
        
        dist_l = np.linalg.norm(nose - left_eye)
        dist_r = np.linalg.norm(nose - right_eye)
        total = dist_l + dist_r
        if total == 0: return 0, 0, 0
        yaw = ((dist_l - dist_r) / total) * 150

        face_h = np.linalg.norm(chin - top)
        if face_h == 0: return 0, 0, 0
        center_y = (top[1] + chin[1]) / 2.0
        pitch = ((nose[1] - center_y) / face_h) * 150

        return yaw, pitch, roll