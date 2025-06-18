FROM python:3.11-slim

# 作業ディレクトリを作成
WORKDIR /app

# 必要ファイルをコピー
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/functions.py ./functions.py

COPY app app
#COPY .env .env

# ポート指定
EXPOSE 8080

# 起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]
