import streamlit as st
import cv2
import time
import numpy as np
from ai_logic import SimpleConcentrationDetector
import db 

st.set_page_config(page_title="AI Analysis Core", layout="wide")

# --- 緊急用スイッチ ---
# 会場ネットが遅い場合、ここをFalseにすれば通信なしで動きます
ENABLE_DB = True 

st.title("💻 Core AI Engine (Real-time Analysis)")

# サイドバー設定
st.sidebar.title("Controller")
user_name = st.sidebar.text_input("User ID", value="DemoUser")
mode = st.sidebar.radio("Mode", ["Flower", "Book"])
run = st.sidebar.checkbox('System Active', value=True)

# デバッグ表示（どこで止まっているか可視化）
status_text = st.empty()

# 画面分割
col1, col2 = st.columns([2, 1])
with col1:
    frame_window = st.image([])
with col2:
    score_metric = st.empty()
    st.divider()
    debug_area = st.empty()

# AI初期化
try:
    if 'detector' not in st.session_state:
        st.session_state['detector'] = SimpleConcentrationDetector()
    detector = st.session_state['detector']
except Exception as e:
    st.error(f"AI初期化エラー: {e}")

if run:
    status_text.text("カメラを起動中...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("⚠️ カメラが見つかりません。他のアプリが使っている可能性があります。")
        st.stop()
        
    last_send_time = time.time()
    
    status_text.text("システム稼働中")
    
    while run:
        ret, frame = cap.read()
        
        # ★カメラが取れない時の安全策（真っ白画面回避）
        if not ret:
            # 映像が来なくても、黒い画面を作って動かし続ける
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, "CAMERA ERROR - SIMULATION MODE", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
        
        # 1. AI解析
        try:
            score, msg, info = detector.analyze_frame(frame)
        except Exception as e:
            # エラーが出ても止まらないようにする
            score = 0
            msg = "Error"
            info = {}
            print(e)

        # 2. 通信（エラーが出たらスキップして進む）
        if ENABLE_DB:
            try:
                current_time = time.time()
                if current_time - last_send_time > 1.0:
                    mode_en = "Flower" if "花" in mode else "Book"
                    db.send_concentration_data(user_name, score, mode_en)
                    last_send_time = current_time
            except:
                pass # 通信エラーは無視

        # 3. 画面描画
        if score > 80: color = (0, 255, 0)
        elif score > 40: color = (0, 255, 255)
        else: color = (0, 0, 255)

        # 情報を映像に書き込み
        cv2.putText(frame, f"SCORE: {score}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
        cv2.putText(frame, f"STATUS: {msg}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
        # Streamlit表示
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_window.image(frame_rgb, use_container_width=True)
        
        # 数値パネル更新
        score_metric.metric("Score", f"{score}", delta=msg)
        
        # パラメータ表示
        if info:
            debug_area.code(f"""
Yaw   : {info.get('yaw', 0):.1f}
Pitch : {info.get('pitch', 0):.1f}
Roll  : {info.get('roll', 0):.1f}
            """)
            
    cap.release()