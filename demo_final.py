import streamlit as st
import cv2
import time
import numpy as np
import mediapipe as mp
from mediapipe import solutions
import firebase_admin
from firebase_admin import credentials, firestore
import os

# ==========================================
# 1. 内部設定 & Firebase初期化
# ==========================================
st.set_page_config(page_title="Final Demo", layout="wide")

# Firebase接続（エラーが出ても無視して進む設定）
try:
    key_path = 'secret_key.json'
    if not firebase_admin._apps:
        if os.path.exists(key_path):
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
    db_client = firestore.client()
    DB_ACTIVE = True
except Exception:
    DB_ACTIVE = False # 鍵がない、ネットがない場合はオフにする

# ==========================================
# 2. AIロジック（修正版をここに直接埋め込み）
# ==========================================
class AllInOneDetector:
    def __init__(self):
        self.face_mesh = solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        # 閾値設定（Sleepingになりにくいよう少し緩めに調整済み）
        self.EAR_THRESHOLD = 0.18 # 0.22だと厳しい場合があるので0.18に
        self.SAFE_YAW = 15
        self.SAFE_PITCH = 15
        self.SAFE_ROLL = 15

    def analyze(self, frame):
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            return 0, "No Face", {}

        landmarks = results.multi_face_landmarks[0].landmark
        
        # EAR計算
        left_ear = self._get_ear(landmarks, [33, 160, 158, 133, 153, 144], w, h)
        right_ear = self._get_ear(landmarks, [362, 385, 387, 263, 373, 380], w, h)
        avg_ear = (left_ear + right_ear) / 2.0
        
        # 姿勢計算
        yaw, pitch, roll = self._get_pose(landmarks, w, h)
        
        # 判定ロジック
        if avg_ear < self.EAR_THRESHOLD:
            score = 10
            msg = "Sleeping"
        else:
            # 減点方式
            p_yaw = max(0, abs(yaw) - self.SAFE_YAW) * 3.0
            p_pitch = max(0, abs(pitch) - self.SAFE_PITCH) * 2.5
            p_roll = max(0, abs(roll) - self.SAFE_ROLL) * 2.5
            
            penalty = p_yaw + p_pitch + p_roll
            score = int(max(0, min(100, 100 - penalty)))
            
            if score > 80: msg = "Perfect"
            elif score > 60: msg = "Good"
            elif score > 40: msg = "Slightly Off"
            elif score > 20: msg = "Looking Away"
            else: msg = "Bad Posture"
            
        return score, msg, {"ear": avg_ear, "yaw": yaw, "pitch": pitch, "roll": roll}

    def _get_ear(self, landmarks, indices, w, h):
        coords = [np.array([landmarks[i].x*w, landmarks[i].y*h]) for i in indices]
        v1 = np.linalg.norm(coords[1]-coords[5])
        v2 = np.linalg.norm(coords[2]-coords[4])
        h_d = np.linalg.norm(coords[0]-coords[3])
        return (v1+v2)/(2.0*h_d) if h_d != 0 else 0

    def _get_pose(self, lm, w, h):
        nose = np.array([lm[1].x*w, lm[1].y*h])
        leye = np.array([lm[33].x*w, lm[33].y*h])
        reye = np.array([lm[263].x*w, lm[263].y*h])
        chin = np.array([lm[152].x*w, lm[152].y*h])
        top = np.array([lm[10].x*w, lm[10].y*h])
        
        # Roll
        dx, dy = reye[0]-leye[0], reye[1]-leye[1]
        roll = np.degrees(np.arctan2(dy, dx))
        # Yaw
        dl, dr = np.linalg.norm(nose-leye), np.linalg.norm(nose-reye)
        yaw = ((dl - dr) / (dl + dr)) * 150 if (dl+dr) != 0 else 0
        # Pitch
        fh = np.linalg.norm(chin-top)
        cy = (top[1] + chin[1]) / 2.0
        pitch = ((nose[1] - cy) / fh) * 150 if fh != 0 else 0
        
        return yaw, pitch, roll

# ==========================================
# 3. メイン実行ループ
# ==========================================
st.title("🚀 Real-time AI Analysis (Independent Mode)")

col1, col2 = st.columns([2, 1])
with col1:
    view = st.image([])
with col2:
    mode = st.radio("Mode", ["Flower", "Book"])
    user = st.text_input("User", "Demo")
    data_view = st.empty()

# AI初期化
if 'ai' not in st.session_state:
    st.session_state.ai = AllInOneDetector()
detector = st.session_state.ai

cap = cv2.VideoCapture(0)
last_send = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.1)
        continue
    
    # 解析実行
    try:
        score, msg, info = detector.analyze(frame)
    except Exception as e:
        score, msg, info = 0, f"Err: {str(e)[:10]}", {} # エラー内容を画面に出す
    
    # 画面描画
    color = (0, 255, 0) if score > 50 else (0, 0, 255)
    cv2.putText(frame, f"SCORE: {score}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 4)
    cv2.putText(frame, f"{msg}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
    
    # 送信
    if DB_ACTIVE and (time.time() - last_send > 1.0):
        try:
            db_client.collection('contest_room').document(user).set({
                'score': score, 'mode': "Flower" if "花" in mode else "Book", 
                'last_updated': firestore.SERVER_TIMESTAMP
            })
            last_send = time.time()
        except: pass

    # 表示
    view.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
    
    if info:
        data_view.code(f"EAR: {info['ear']:.3f}\nYaw: {info['yaw']:.1f}\nPit: {info['pitch']:.1f}")