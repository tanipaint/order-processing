# ベースイメージ
FROM python:3.10-slim

# 環境変数設定
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 作業ディレクトリ作成
WORKDIR /app

# Python依存関係
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ソースをコピー
COPY src/ /app/src/

# デフォルトコマンド
CMD ["python", "-m", "src.main"]
