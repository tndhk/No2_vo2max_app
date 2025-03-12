FROM python:3.9-slim

WORKDIR /app

# 必要な依存パッケージのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY . .

# データディレクトリの作成
RUN mkdir -p /app/data

# Streamlitのポート公開
EXPOSE 8501

# 環境変数の設定
ENV PYTHONPATH=/app

# コマンドを直接実行
CMD bash -c "echo '=== データベース初期化を実行中...' && \
             python -m src.models.database && \
             echo '=== データベーススキーマの更新を実行中...' && \
             python -m src.models.update_db && \
             echo '=== Streamlitアプリケーションを起動中...' && \
             streamlit run src/app.py"