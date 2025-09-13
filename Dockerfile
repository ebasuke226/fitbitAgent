FROM python:3.11-slim
WORKDIR /app

# CIで作った dist/ を丸ごと持ち込む
COPY dist/ /tmp/dist/

# デバッグ用に中身を表示しつつ、pipを更新→wheelをインストール
RUN ls -l /tmp/dist && \
    python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir /tmp/dist/*.whl

CMD ["python", "-c", "import sample_pkg; print('container ok')"]
