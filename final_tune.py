"""
import streamlit as st
import cv2
import numpy as np
import mediapipe as mp

# --- 1. ここにAIロジックを直接書く（キャッシュ回避のため） ---
class SimpleConcentrationDetector:
    def __init__(self):
        # MediaPipeの初期化
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # 基準値（スライダーで変更可能）
        self.EAR_THRESHOLD = 0.22
        # 「ここまでは減点しない」という許容範囲（セーフゾーン）
        self.SAFE_ANGLE = 20  
        # 画面外判定のマージン（0.0〜1.0）
        self.MARGIN = 0.01 

    def analyze_frame(self, frame):
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
            
            # --- 1. 画面外判定（Out of Frame Check） ---
            # 重要なパーツ（目・鼻・顎）が画面内にあるかチェック
            # 鼻(1), 左目外(33), 右目外(263), 顎(152)
            check_points = [1, 33, 263, 152]
            is_out_of_frame = False
            for idx in check_points:
                lm = landmarks[idx]
                # 座標が 0〜1 の範囲に収まっていないと画面外
                if lm.x < self.MARGIN or lm.x > (1.0 - self.MARGIN) or \
                   lm.y < self.MARGIN or lm.y > (1.0 - self.MARGIN):
                    is_out_of_frame = True
                    break
            
            if is_out_of_frame:
                return 0, "Out of Frame", {"ear":0, "yaw":0, "pitch":0}

            # --- 2. 各種計算 ---
            left_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144], img_w, img_h)
            right_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 373, 380], img_w, img_h)
            avg_ear = (left_ear + right_ear) / 2.0
            
            yaw, pitch = self._calculate_simple_pose(landmarks, img_w, img_h)
            debug_info = {"ear": avg_ear, "yaw": yaw, "pitch": pitch}

            # --- 3. スコア計算ロジック（減点方式） ---
            
            # A. 居眠り判定（これは即アウトで10点）
            if avg_ear < self.EAR_THRESHOLD:
                score = 10
                message = "Sleeping"
            
            else:
                # B. 姿勢による減点計算
                # 角度(Yaw/Pitch)の絶対値を取る
                abs_yaw = abs(yaw)
                abs_pitch = abs(pitch)
                
                # 減点数 = (現在の角度 - 許容範囲) * 係数
                # 許容範囲(SAFE_ANGLE)以内なら減点ゼロ
                yaw_penalty = max(0, abs_yaw - self.SAFE_ANGLE) * 2.5
                pitch_penalty = max(0, abs_pitch - self.SAFE_ANGLE) * 2.5
                
                # 100点から減点する
                raw_score = 100 - (yaw_penalty + pitch_penalty)
                
                # 0〜100の範囲に収める
                score = int(max(0, min(100, raw_score)))
                
                # メッセージの分岐
                if score > 80:
                    message = "Perfect"
                elif score > 60:
                    message = "Good"
                elif score > 40:
                    message = "Slightly Off"
                elif score > 20:
                    message = "Looking Away"
                else:
                    message = "Bad Posture"

        return score, message, debug_info

    # _calculate_ear と _calculate_simple_pose は変更なし（そのまま使ってください）
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

    def _calculate_simple_pose(self, landmarks, w, h):
        nose = np.array([landmarks[1].x * w, landmarks[1].y * h])
        left = np.array([landmarks[234].x * w, landmarks[234].y * h])
        right = np.array([landmarks[454].x * w, landmarks[454].y * h])
        top = np.array([landmarks[10].x * w, landmarks[10].y * h])
        bottom = np.array([landmarks[152].x * w, landmarks[152].y * h])

        face_width = np.linalg.norm(right - left)
        face_height = np.linalg.norm(bottom - top)

        if face_width == 0 or face_height == 0: return 0, 0

        center_x = (left[0] + right[0]) / 2.0
        center_y = (top[1] + bottom[1]) / 2.0

        diff_x = nose[0] - center_x
        diff_y = nose[1] - center_y

        # 係数300でスケーリング
        yaw_score = (diff_x / face_width) * 300
        pitch_score = (diff_y / face_height) * 300

        return yaw_score, pitch_score


# --- 2. ここから画面表示 (Streamlit) ---
st.title("🛠 最終調整モード (All-in-One)")

# スライダー
st.sidebar.header("基準値の調整")
ear_th = st.sidebar.slider("目の開き (EAR)", 0.15, 0.35, 0.22, 0.01)
yaw_th = st.sidebar.slider("横向き許容 (Yaw)", 10, 100, 40, 5) # 簡易計算なので数値大きめ推奨
pitch_th = st.sidebar.slider("縦向き許容 (Pitch)", 10, 100, 40, 5)

run = st.checkbox('カメラ起動', value=True)
FRAME_WINDOW = st.image([])

detector = SimpleConcentrationDetector()

if run:
    cap = cv2.VideoCapture(0)
    while run:
        ret, frame = cap.read()
        if not ret:
            st.error("カメラエラー")
            break
        
        # 値の更新
        detector.EAR_THRESHOLD = ear_th
        detector.YAW_THRESHOLD = yaw_th
        detector.PITCH_THRESHOLD = pitch_th
        
        # 解析
        score, msg, info = detector.analyze_frame(frame)
        
        # 描画
        color = (0, 255, 0) if score > 50 else (0, 0, 255)
        cv2.putText(frame, f"Status: {msg}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        cv2.putText(frame, f"Score: {score}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        
        if info:
            # 数値表示
            cv2.putText(frame, f"EAR: {info['ear']:.3f} (Lim:{ear_th})", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.putText(frame, f"Yaw: {info['yaw']:.1f} (Lim:{yaw_th})", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            cv2.putText(frame, f"Pitch: {info['pitch']:.1f} (Lim:{pitch_th})", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame)
    cap.release()
"""

import streamlit as st
import cv2
import numpy as np
import mediapipe as mp
from mediapipe import solutions

# --- 1. 高精度AIロジッククラス ---
class SimpleConcentrationDetector:
    def __init__(self):
        self.mp_face_mesh = solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # --- 基準値 (スライダーで調整される初期値) ---
        self.EAR_THRESHOLD = 0.18
        
        # 許容範囲（セーフゾーン）
        self.SAFE_YAW = 40    # ひねり
        self.SAFE_PITCH = 20  # うつむき
        self.SAFE_ROLL = 15   # 傾き

        # 画面外判定のマージン
        self.MARGIN = 0.01 

    def analyze_frame(self, frame):
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
            
            # 1. 画面外判定
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

            # 2. EAR計算
            left_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144], img_w, img_h)
            right_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 373, 380], img_w, img_h)
            avg_ear = (left_ear + right_ear) / 2.0
            
            # 3. 姿勢計算（高精度版）
            yaw, pitch, roll = self._calculate_precise_pose(landmarks, img_w, img_h)
            
            debug_info = {"ear": avg_ear, "yaw": yaw, "pitch": pitch, "roll": roll}

            # --- スコア計算 ---
            if avg_ear < self.EAR_THRESHOLD:
                score = 10
                message = "Sleeping"
            else:
                # 減点計算
                abs_yaw = abs(yaw)
                abs_pitch = abs(pitch)
                abs_roll = abs(roll)
                
                # 係数（厳しさ）の調整
                p_yaw = max(0, abs_yaw - self.SAFE_YAW) * 3.0
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

        # Roll
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        roll = np.degrees(np.arctan2(dy, dx))
        
        # Yaw (目と鼻の距離差)
        dist_l = np.linalg.norm(nose - left_eye)
        dist_r = np.linalg.norm(nose - right_eye)
        total = dist_l + dist_r
        if total == 0: return 0, 0, 0
        yaw = ((dist_l - dist_r) / total) * 150

        # Pitch
        face_h = np.linalg.norm(chin - top)
        if face_h == 0: return 0, 0, 0
        center_y = (top[1] + chin[1]) / 2.0
        pitch = ((nose[1] - center_y) / face_h) * 150

        return yaw, pitch, roll

# --- 2. ここから画面表示 (Streamlit) ---
st.title("🛠 カメラ判定モード")
st.markdown("Yaw(ひねり)とRoll(傾き)にも対応。")

st.sidebar.header("許容範囲の設定 (Safe Zone)")
ear_th = st.sidebar.slider("目閉じ判定 (EAR Threshold)", 0.15, 0.35, 0.22, 0.01)
yaw_safe = st.sidebar.slider("ひねり許容 (Safe Yaw)", 0, 50, 15, 1)
pitch_safe = st.sidebar.slider("うつむき許容 (Safe Pitch)", 0, 50, 20, 1)
roll_safe = st.sidebar.slider("傾き許容 (Safe Roll)", 0, 50, 15, 1) # 新規追加

run = st.checkbox('カメラ起動', value=True)
FRAME_WINDOW = st.image([])

detector = SimpleConcentrationDetector()

if run:
    cap = cv2.VideoCapture(0)
    while run:
        ret, frame = cap.read()
        if not ret:
            st.error("カメラ映像が取得できません")
            break
        
        # スライダー値を反映
        detector.EAR_THRESHOLD = ear_th
        detector.SAFE_YAW = yaw_safe
        detector.SAFE_PITCH = pitch_safe
        detector.SAFE_ROLL = roll_safe
        
        # 解析
        score, msg, info = detector.analyze_frame(frame)
        
        # 描画
        # 色: 100~80=緑, 80~40=黄色, 40以下=赤
        if score > 80: color = (0, 255, 0)
        elif score > 40: color = (255, 255, 0)
        else: color = (255, 0, 0) # BGRなので (青, 緑, 赤) → 赤は(0,0,255)だがOpenCVのputTextはRGB指定ではないため注意
        # StreamlitはRGBで表示するため、ここでの書き込みはBGRで行う
        # OpenCVのデフォルトはBGR。赤=(0,0,255), 黄=(0,255,255), 緑=(0,255,0)
        if score > 80: cv_color = (0, 255, 0)
        elif score > 40: cv_color = (0, 255, 255)
        else: cv_color = (0, 0, 255)

        cv2.putText(frame, f"Status: {msg}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, cv_color, 3)
        cv2.putText(frame, f"Score: {score}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, cv_color, 3)
        
        if info:
            # 白文字で数値表示
            font_s = 0.6
            cv2.putText(frame, f"EAR: {info['ear']:.3f} (Th:{ear_th})", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, font_s, (255,255,255), 2)
            
            # 各数値がSafeゾーンを超えたら赤くする演出
            c_yaw = (0,0,255) if abs(info['yaw']) > yaw_safe else (255,255,255)
            c_pit = (0,0,255) if abs(info['pitch']) > pitch_safe else (255,255,255)
            c_rol = (0,0,255) if abs(info['roll']) > roll_safe else (255,255,255)

            cv2.putText(frame, f"Yaw: {info['yaw']:.1f} (Safe:{yaw_safe})", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, font_s, c_yaw, 2)
            cv2.putText(frame, f"Pitch: {info['pitch']:.1f} (Safe:{pitch_safe})", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, font_s, c_pit, 2)
            cv2.putText(frame, f"Roll: {info['roll']:.1f} (Safe:{roll_safe})", (30, 230), cv2.FONT_HERSHEY_SIMPLEX, font_s, c_rol, 2)

        # 最後にRGB変換して表示
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame)
    cap.release()