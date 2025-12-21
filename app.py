import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from PIL import Image

st.set_page_config(page_title="Focus Garden", layout="wide")

# =====================
# ヘッダー
# =====================
header_left, header_right = st.columns([8, 1])

with header_left:
    st.title("Focus Garden")

with header_right:
    st.button("⚙ 設定")

st.divider()

# =====================
# メインビジュアルエリア
# =====================
st.subheader("メインビジュアルエリア")

try:
    main_image = Image.open("sample_image.jpg")
    st.image(main_image, use_container_width=True)
except:
    st.info("ここに現在のレベルに応じた画像が表示されます（例：花畑）")

st.divider()

# =====================
# 集中スコア
# =====================
score = 85
stars = "★★★★☆"
st.markdown(f"### 現在の集中スコア： {score}点　【 {stars} 】")

st.divider()

# =====================
# 下部エリア
# =====================
left, right = st.columns(2)

# メッセージエリア
with left:
    st.subheader("メッセージエリア")
    st.success("素晴らしい集中力です！\n\nこの調子で続けましょう 🌸")

# =====================
# ワイプエリア（常時カメラ）
# =====================
with right:
    st.subheader("ワイプエリア（自分のカメラ映像）")

    camera_on = st.checkbox("カメラを表示する", value=True)

    if camera_on:
        webrtc_streamer(
            key="wipe-camera",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            ),
            media_stream_constraints={
                "video": True,
                "audio": False,  # マイクは使わない
            },
        )
    else:
        st.info("カメラはオフになっています")