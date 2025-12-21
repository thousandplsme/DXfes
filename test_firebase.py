import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import datetime

# 1. 初期化
# secret_key.json が同じフォルダにあることを確認してください
cred = credentials.Certificate('secret_key.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

print("🔥 Firebase接続成功！データを書き込みます...")

# 2. データの書き込みテスト
# 'contest_room' というコレクションの中に、自分の名前のドキュメントを作る
doc_ref = db.collection('contest_room').document('Leader_User')
doc_ref.set({
    'name': 'リーダー',
    'score': 100,
    'mode': 'Flower',
    'timestamp': datetime.datetime.now()
})

print("✅ 書き込み完了！Firebaseコンソールを見てください。")

# 3. データの読み取りテスト
print("🔍 今書き込んだデータを読み取ります...")
docs = db.collection('contest_room').stream()

for doc in docs:
    print(f"ID: {doc.id} => Data: {doc.to_dict()}")