# flask本体＋テンプレート描画＋リクエスト/リダイレクト/URL生成をインポート
from flask import Flask, render_template, request, redirect, url_for
from datetime import date
# 型ヒント
from typing import List,Dict

# Flaskアプリのインスタンス生成
app = Flask(__name__)
# 将来flas

@app.route('/')
def home():
    return 'Hello Tomohisa'

if __name__ == '__main__':
    app.run(debug=True)