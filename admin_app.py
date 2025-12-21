import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import time
import os

# 1. Firebase初期化（db.pyと同じロジック）
key_path = 'secret_key.json'
if not firebase_admin._apps:
    if os.path.exists(key_path):
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

db = firestore.client()

# 2. 画面構築
st.set_page_config(page_title="管理者ダッシュボード", layout="wide")
st.title("🏫 リアルタイム集中状況モニター")

# 3. データ取得と表示のループ
placeholder = st.empty()

while True:
    # Firestoreからデータを取得
    docs = db.collection('contest_room').stream()
    data_list = []
    
    for doc in docs:
        d = doc.to_dict()
        d['user_name'] = doc.id # ドキュメントIDを名前にする
        data_list.append(d)
    
    with placeholder.container():
        if not data_list:
            st.info("データ待機中...")
        else:
            # カラムに分けてカード形式で表示
            cols = st.columns(4) # 4列で表示
            for i, student in enumerate(data_list):
                col = cols[i % 4]
                with col:
                    # スコアに応じて色を変える演出
                    score = student.get('score', 0)
                    mode = student.get('mode', 'Flower')
                    bg_color = "🟢" if score > 70 else "🟡" if score > 40 else "🔴"
                    
                    st.metric(
                        label=f"{bg_color} {student['user_name']}",
                        value=f"{score}点",
                        delta=mode
                    )
                    st.progress(score)
    
    time.sleep(2) # 2秒更新