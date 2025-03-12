import os
from pathlib import Path

# 基本パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = os.path.join(BASE_DIR, "data")

# 環境設定
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# データベース設定
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "vo2max.db"))

# Strava API設定
STRAVA_CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "")
STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "")

# 環境別設定
if ENVIRONMENT == "development":
    DEBUG = True
    # 開発用設定
else:
    DEBUG = False
    # 本番用設定

# アプリケーション設定
APP_NAME = "VO2max インターバル効果分析"
APP_VERSION = "0.1.0"