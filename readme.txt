コードを落としたら pip install -r requirements.txt を実行してください
→ライブラリが入ってなくて動かない！となるのを防ぐことができます

以下木村用メモ

python --version

streamlit run admin_app.py で起動しておきます。あなたが test_firebase.py でデータを書き込むと、この画面が勝手に更新される

streamlit run tune_ai.py

（環境作成）でエラーが出る場合
# WindowsのPythonランチャーを使って3.11指定で環境を作る
py -3.11 -m venv .venv

# ターミナルを一度ゴミ箱で消し、開き直す
# 開き直したときに (.venv) が出なければ以下を実行
.venv\Scripts\activate
これで確実にPython 3.11環境になり、MediaPipeのエラー（solutionsが見つからない問題）は消えます

もし上記でもエラーが出る場合「PowerShell」ではなく「コマンドプロンプト」を使えば、この制限を回避できます。

VSCodeのターミナルの右上にある「＋」の横の 「ｖ（下矢印）」 をクリック。

「Command Prompt (cmd)」 を選択。

新しい黒い画面が出たら、手動で以下を入力してEnter

.venv\Scripts\activate.bat

streamlit run final_tune.py