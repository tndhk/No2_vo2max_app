import os
import sys
import logging
from pathlib import Path

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# プロジェクトルートを Python パスに追加
# この相対パスを修正 - current directory is in src/models, so we need to go up two levels
current_dir = os.path.dirname(os.path.abspath(__file__))  # models ディレクトリ
project_root = os.path.dirname(os.path.dirname(current_dir))  # プロジェクトルート
sys.path.insert(0, project_root)

# 正しいインポートパス
from src.models.database import get_db_connection

def update_database_schema():
    """既存のデータベースを更新して新しいフィールドを追加する"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # workoutsテーブルに strava_id カラムが存在するか確認
        cursor.execute("PRAGMA table_info(workouts)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # strava_id カラムが存在しない場合は追加
        if 'strava_id' not in columns:
            logger.info("workoutsテーブルに strava_id カラムを追加しています...")
            cursor.execute("ALTER TABLE workouts ADD COLUMN strava_id INTEGER")
            conn.commit()
            logger.info("データベースのスキーマを更新しました")
        else:
            logger.info("strava_id カラムは既に存在します")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"データベース更新エラー: {str(e)}", exc_info=True)
        if 'conn' in locals() and conn:
            conn.close()
        return False

if __name__ == "__main__":
    update_database_schema()