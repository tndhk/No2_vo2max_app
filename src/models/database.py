import os
import sqlite3
from pathlib import Path

# データベースファイルのパス
DB_PATH = os.environ.get('DATABASE_PATH', 'data/vo2max.db')

def get_db_connection():
    """データベース接続を取得する"""
    # データディレクトリがなければ作成
    Path(os.path.dirname(DB_PATH)).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """データベースの初期化とテーブル作成"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # ワークアウトテーブル - 追加フィールド含む
    cur.execute('''
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        name TEXT,
        source TEXT,
        file_path TEXT,
        total_time INTEGER,
        total_distance REAL,
        avg_power INTEGER,
        avg_hr INTEGER,
        tss REAL,
        ftp INTEGER,           -- 追加: トレーニング時のFTP値
        max_hr INTEGER,        -- 追加: 最大心拍数（設定値）
        work_kj REAL,          -- 追加: 総仕事量（キロジュール）
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # インターバルテーブル - 変更なし
    cur.execute('''
    CREATE TABLE IF NOT EXISTS intervals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER,
        interval_type TEXT,
        start_time INTEGER,
        end_time INTEGER,
        duration INTEGER,
        distance REAL,
        avg_power INTEGER,
        max_power INTEGER, 
        avg_hr INTEGER,
        max_hr INTEGER,
        rpe REAL,
        vo2max_score REAL,
        FOREIGN KEY (workout_id) REFERENCES workouts (id)
    )
    ''')
    
    # データポイントテーブル - GPSと速度関連フィールド削除
    cur.execute('''
    CREATE TABLE IF NOT EXISTS data_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workout_id INTEGER,
        interval_id INTEGER,
        timestamp INTEGER,
        power INTEGER,
        heart_rate INTEGER,
        cadence INTEGER,
        FOREIGN KEY (workout_id) REFERENCES workouts (id),
        FOREIGN KEY (interval_id) REFERENCES intervals (id)
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()