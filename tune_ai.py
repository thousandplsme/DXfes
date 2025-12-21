import streamlit as st
import cv2
import numpy as np
from ai_logic import ConcentrationDetector

st.title("🛠 AI精度調整モード")
st.markdown("数値を見ながら、**「Looking Away」にならないギリギリのライン**を探ってください。")

st.sidebar.header("判定基準の調整")

# 1. EAR (目の開き)
ear_threshold = st.sidebar.slider(
    "目の開閉判定 (EAR)", 
    0.10, 0.40, 0.22, 0.01,
    help="これより低いと「Sleeping」になります。"
)

# 2. Yaw (横向き)
yaw_threshold = st.sidebar.slider(
    "横向き許容範囲 (Yaw)", 
    10, 90, 30, 5,
    help="これより横を向くと「Looking Away」になります。"
)

# 3. Pitch (縦向き・うつむき) ★追加！
pitch_threshold = st.sidebar.slider(
    "縦向き許容範囲 (Pitch)", 
    10, 90, 30, 5, # ノートPCなら30〜40くらい必要なことが多いです
    help="これより下/上を向くと「Looking Away」になります。"
)

run = st.checkbox('カメラ起動', value=True)
FRAME_WINDOW = st.image([])

detector = ConcentrationDetector()

if run:
    cap = cv2.VideoCapture(0)
    
    while run:
        ret, frame = cap.read()
        if not ret:
            st.error("カメラ映像が取得できません")
            break
        
        # スライダーの値をAIに反映
        detector.EAR_THRESHOLD = ear_threshold
        detector.YAW_THRESHOLD = yaw_threshold
        detector.PITCH_THRESHOLD = pitch_threshold # ★ここも反映
        
        # AI解析
        score, message, debug_info = detector.analyze_frame(frame)
        
        # --- 描画処理 ---
        # 色修正: 赤は (0, 0, 255)
        color = (0, 255, 0) if score > 50 else (0, 0, 255)
        
        # 文字表示
        cv2.putText(frame, f"Status: {message}", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)
        cv2.putText(frame, f"Score: {score}", (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 3)

        if debug_info:
            ear_val = debug_info['ear']
            yaw_val = debug_info['yaw']
            pitch_val = debug_info['pitch']
            
            # デバッグ数値の表示
            # 数値が基準を超えていたら、そこだけ赤文字にする演出
            c_ear = (0, 255, 255) if ear_val < ear_threshold else (255, 255, 255)
            c_yaw = (0, 0, 255) if abs(yaw_val) > yaw_threshold else (255, 255, 255)
            c_pit = (0, 0, 255) if abs(pitch_val) > pitch_threshold else (255, 255, 255)

            cv2.putText(frame, f"EAR: {ear_val:.3f} (Limit: {ear_threshold})", (30, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_ear, 2)
            cv2.putText(frame, f"Yaw: {yaw_val:.1f} (Limit: {yaw_threshold})", (30, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_yaw, 2)
            cv2.putText(frame, f"Pitch: {pitch_val:.1f} (Limit: {pitch_threshold})", (30, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, c_pit, 2)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame)

    cap.release()