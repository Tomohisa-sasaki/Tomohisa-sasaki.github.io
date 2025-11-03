# app.py
from flask import Flask, render_template, request, redirect, url_for  # ← Flask一式を読み込む
from datetime import date                                            # ← 日付型（フォームのdate入力と相性◎）
from typing import List, Dict                                        # ← 型ヒント（任意）

app = Flask(__name__)                                                # ← Flaskアプリのインスタンスを生成
app.config["SECRET_KEY"] = "dev-secret"                              # ← 後でCSRF/flash等に使うための設定（開発用）

WORKOUTS: List[Dict] = []                                            # ← インメモリの簡易“DB”（後でSQLiteに置換）

@app.route("/")                                                       # ← ルート（/）に対するハンドラを登録
def index():                                                          # ← エンドポイント関数名（url_forで参照される）
    return render_template("index.html", workouts=WORKOUTS)           # ← テンプレートにデータを渡して描画

@app.route("/workouts/new", methods=["GET", "POST"])                  # ← 新規登録画面：GET=表示, POST=保存
def new_workout():                                                    # ← エンドポイント名
    if request.method == "POST":                                      # ← HTTPメソッドで処理を分岐
        raw_date = request.form.get("workout_date", "").strip()       # ← フォーム値の取得（文字列）
        name = request.form.get("name", "").strip()                   # ← 種目名
        sets = request.form.get("sets", "0").strip()                  # ← セット数（文字列→後でint化）
        reps = request.form.get("reps", "0").strip()                  # ← 回数
        notes = request.form.get("notes", "").strip()                 # ← メモ（任意）

        if not raw_date or not name:                                  # ← 最小限のバリデーション
            return render_template("workouts_new.html", error="必須項目が未入力です。", form=request.form)

        try:
            y, m, d = [int(x) for x in raw_date.split("-")]           # ← 'YYYY-MM-DD' を数値に分解
            wdate = date(y, m, d)                                     # ← date型へ変換
            sets_i = int(sets) if sets else 0                         # ← 数値化
            reps_i = int(reps) if reps else 0
        except Exception:
            return render_template("workouts_new.html", error="入力形式が不正です。", form=request.form)

        WORKOUTS.append({                                             # ← “保存”（インメモリ；後でDB化）
            "date": wdate, "name": name, "sets": sets_i, "reps": reps_i, "notes": notes,
        })
        return redirect(url_for("index"))                             # ← PRG: POST→Redirect→GET

    return render_template("workouts_new.html")                        # ← GET: フォーム初期表示

if __name__ == "__main__":                                            # ← 直接実行されたときだけ開発サーバを立てる
    app.run(debug=True, port=5050)                                    # ← ★ ポートを5050に固定して起動