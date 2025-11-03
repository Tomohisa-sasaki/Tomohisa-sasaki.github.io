# flask本体＋テンプレート描画＋リクエスト/リダイレクト/URL生成をインポート
from flask import Flask, render_template, request, redirect, url_for
from datetime import date
# 型品と
from typing import List,Dict

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello Tomohisa'

if __name__ == '__main__':
    app.run(debug=True)