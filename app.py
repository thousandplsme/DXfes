import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from PIL import Image
import os

# =====================
# ページ設定
# =====================
st.set_page_config(
    page_title="AttenCheck",
    layout="wide"
)

# =====================
# セッション状態初期化
# =====================
if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

if "mode" not in st.session_state:
    st.session_state.mode = "花モード"

if "score" not in st.session_state:
    st.session_state.score = 85

# =====================
# CSS（レスポンシブ対応）
# =====================
st.markdown(
    """
    <style>
    img {
        max-width: 100%;
        height: auto;
        animation: fadeIn 0.6s ease-in-out;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================
# ヘッダー
# =====================
header_left, header_right = st.columns([8, 1])

with header_left:
    st.title("AttenCheck")

with header_right:
    if st.button("⚙ 設定"):
        st.session_state.show_settings = not st.session_state.show_settings

# =====================
# 設定パネル（画面内）
# =====================
if st.session_state.show_settings:
    st.markdown("### ⚙ 設定")

    col1, col2 = st.columns(2)

    with col1:
        st.radio(
            "画像テーマ",
            ("花モード", "本モード"),
            key="mode"
        )

    with col2:
        st.slider(
            "集中スコア",
            0, 100,
            key="score"
        )

st.divider()

# =====================
# モード → フォルダ
# =====================
def get_base_folder(mode):
    if "花" in mode:
        return "images/flower"
    else:
        return "images/book"

def get_image_by_score(score, base_folder):
    if score < 20:
        return f"{base_folder}/20.png"
    elif score < 40:
        return f"{base_folder}/40.png"
    elif score < 60:
        return f"{base_folder}/60.png"
    elif score < 80:
        return f"{base_folder}/80.png"
    else:
        return f"{base_folder}/100.png"

mode = st.session_state.mode
score = st.session_state.score

base_folder = get_base_folder(mode)
image_path = get_image_by_score(score, base_folder)

# =====================
# 画像処理
# =====================
def load_image_no_alpha(path, bg_color=(255, 255, 255)):
    img = Image.open(path)

    # 透過PNGの場合
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, bg_color)
        background.paste(img, mask=img.split()[-1])  # alphaをマスクに使う
        return background
    else:
        return img

# =====================
# メインビジュアル
# =====================
if os.path.exists(image_path):
    image = load_image_no_alpha(image_path)
    st.image(image, use_container_width=True)
else:
    st.error("画像ファイルが見つかりません")

st.divider()

# =====================
# スコア表示
# =====================
star_count = score // 20
stars = "★" * star_count + "☆" * (5 - star_count)

st.markdown(
    f"### 現在の集中スコア： {score}点　【 {stars} 】"
)

st.divider()

# =====================
# 下部エリア
# =====================
left, right = st.columns(2)

# メッセージエリア
with left:
    st.subheader("メッセージ")

    if score < 20:
        st.warning("画面から少し意識が離れているかもしれません。背筋を伸ばして、授業に目を向けてみましょう。")
    elif score < 40:
        st.info("授業には参加できています。ノートや画面に意識を戻してみましょう。")
    elif score < 60:
        st.info("安定して授業に集中できています。この調子で先生の話を聞いていきましょう。")
    elif score < 80:
        st.success("とても良い集中状態です！今の理解を大切に、内容をつかんでいきましょう。")
    else:
        st.success("授業にしっかり集中できています！このまま最後まで取り組めそうです。")

# =====================
# ワイプ（常時カメラ）
# =====================
with right:
    
    webrtc_streamer(
        key="wipe-camera",
        mode=WebRtcMode.SENDRECV,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={
            "video": True,
            "audio": False,
        },
    )
