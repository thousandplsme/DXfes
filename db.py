import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime
import os

# 接続状態を管理するフラグ
IS_CONNECTION_OK = False
db = None

# 1. 秘密鍵を探す
key_path = 'secret_key.json'

if os.path.exists(key_path):
    # A. 鍵がある場合（あなたのPC） -> 本当に接続する
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        IS_CONNECTION_OK = True
        print("✅ Firebase接続成功: リアルタイム通信モード")
    except Exception as e:
        print(f"⚠️ 接続エラー: {e}")
else:
    # B. 鍵がない場合（先輩のPC） -> 接続したフリをする
    print("ℹ️ secret_key.jsonが見つかりません: シミュレーションモードで動作します")
    IS_CONNECTION_OK = False

def send_concentration_data(user_name, score, mode):
    """
    データ送信関数
    鍵がない場合は、コンソールに表示するだけで何もしない
    """
    timestamp = datetime.datetime.now()
    
    # 鍵があって接続成功している場合
    if IS_CONNECTION_OK and db is not None:
        try:
            doc_ref = db.collection('contest_room').document(user_name)
            doc_ref.set({
                'score': score,
                'mode': mode,
                'last_updated': timestamp
            })
            # print(f"送信完了: {score}") # 動作確認用（うるさければコメントアウト）
        except Exception as e:
            print(f"送信失敗: {e}")
            
    # 鍵がない場合（先輩のPCなど）
    else:
        # 送信したつもりになってログだけ出す
        print(f"[Simulation] 送信データ: {user_name}, Score={score}, Mode={mode}")