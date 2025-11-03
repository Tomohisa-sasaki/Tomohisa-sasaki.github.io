# flask本体＋テンプレート描画＋リクエスト/リダイレクト/URL生成をインポート
from flask import Flask, render_template, request, redirect, url_for
from datetime import date
# 型ヒント
from typing import List,Dict

# Flaskアプリのインスタンス生成
app = Flask(__name__)
# 将来flash/CSRFに使う設定（ダミー）
app.config['SECRET_KEY'] = 'dev-secret'

# 例: {"date": date(2025,11,2),"name":"Bench","sets":5,"reps":5,"notes":"OK"}
WORKOUTS :List[Dict] = []

# ルートURL（トップページ）に対応するビュー関数を登録
@app.route('/')
def index():
    # テンプレートに渡す「文脈（コンテキスト）」を作る
    # Jinja側では {{ workouts }} やループで参照できる
    return render_template('index.html', workouts = WORKOUTS) # templates/index.html を描画しHTTPレスポンスにする

# 新規登録ページ。GET=フォーム表示, POST=送信処理
@app.route('/workouts/new', methods=['GET','POST'])
def new_workouts():
    if request.method == 'POST':
        # HTMLフォームのname属性で送られてきた値を取り出す
        raw_date = request.form.get('workout_date', "").strip()
        name = request.form.get('workout_date', )       



@app.route('/')
def home():
    return 'Hello Tomohisa'

if __name__ == '__main__':
    app.run(debug=True)