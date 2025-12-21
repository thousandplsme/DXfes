import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import time
import os

st.set_page_config(page_title="管理者ダッシュボード", layout="wide")

# Firebase初期化 (db.pyと同様)
key_path = 'secret_key.json'
if not firebase_admin._apps:
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

db = firestore.client()

st.title("🏫 Focus Garden - リアルタイム見守りシステム")
st.markdown("クラス全員の集中状況を可視化しています（画像は保存されていません）")

# 自動更新のコンテナ
placeholder = st.empty()

while True:
    try:
        # Firestoreから全データ取得
        docs = db.collection('contest_room').stream()
        data_list = []
        for doc in docs:
            d = doc.to_dict()
            d['user_name'] = doc.id
            data_list.append(d)
        
        with placeholder.container():
            if not data_list:
                st.warning("現在、接続している生徒はいません。")
            else:
                # 3列でカード表示
                cols = st.columns(3)
                for i, student in enumerate(data_list):
                    col = cols[i % 3]
                    with col:
                        score = student.get('score', 0)
                        mode = student.get('mode', 'Unknown')
                        
                        # スコアに応じた装飾
                        if score > 80:
                            status_icon = "🌸" if mode == "Flower" else "🏰"
                            color = "green"
                        elif score > 40:
                            status_icon = "🌿" if mode == "Flower" else "📚"
                            color = "orange"
                        else:
                            status_icon = "🥀" if mode == "Flower" else "💤"
                            color = "red"

                        # カード風の表示
                        st.markdown(f"""
                        <div style="border: 2px solid {color}; padding: 10px; border-radius: 10px; margin-bottom: 10px;">
                            <h3>{status_icon} {student['user_name']}</h3>
                            <p>Mode: <b>{mode}</b></p>
                            <h2 style="color: {color};">{score}点</h2>
                        </div>
                        """, unsafe_allow_html=True)
                        st.progress(score)
                        
        time.sleep(2) # 2秒ごとに更新
        
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        time.sleep(5)