import logging
import os
import sys
from typing import Dict, List, Any, Tuple, Optional

# プロジェクトルートを Python パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.database import get_db_connection

# ロガーの設定
logger = logging.getLogger(__name__)

def save_workout_data(workout_data: Dict[str, Any], data_points: List[Dict[str, Any]]) -> Optional[int]:
    """
    ワークアウトデータとデータポイントをデータベースに保存する
    
    Args:
        workout_data: ワークアウト情報を含む辞書
        data_points: データポイントのリスト
    
    Returns:
        Optional[int]: 保存に成功した場合はworkout_id、失敗した場合はNone
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ワークアウトデータの保存
        cursor.execute("""
            INSERT INTO workouts 
            (date, name, source, file_path, total_time, total_distance, 
             avg_power, avg_hr, tss, ftp, max_hr, work_kj)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workout_data.get('date'),
            workout_data.get('name'),
            workout_data.get('source'),
            workout_data.get('file_path'),
            workout_data.get('total_time'),
            workout_data.get('total_distance'),
            workout_data.get('avg_power'),
            workout_data.get('avg_hr'),
            workout_data.get('tss'),
            workout_data.get('ftp'),
            workout_data.get('max_hr'),
            workout_data.get('work_kj')
        ))
        
        # 挿入されたワークアウトのIDを取得
        workout_id = cursor.lastrowid
        
        # データポイントの保存
        if data_points and workout_id:
            for point in data_points:
                cursor.execute("""
                    INSERT INTO data_points 
                    (workout_id, timestamp, power, heart_rate, cadence)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    workout_id,
                    point.get('timestamp'),
                    point.get('power'),
                    point.get('heart_rate'),
                    point.get('cadence')
                ))
        
        conn.commit()
        logger.info(f"ワークアウトデータを保存しました。ID: {workout_id}")
        return workout_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"データ保存エラー: {str(e)}")
        return None
    
    finally:
        if conn:
            conn.close()

def check_workout_exists(file_path: str) -> bool:
    """
    同じファイルパスのワークアウトが既に存在するかチェック
    
    Args:
        file_path: ファイルパス
    
    Returns:
        bool: 存在する場合はTrue、そうでない場合はFalse
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM workouts WHERE file_path = ?", (file_path,))
        result = cursor.fetchone()
        
        return result is not None
    
    except Exception as e:
        logger.error(f"ワークアウト存在チェックエラー: {str(e)}")
        return False
    
    finally:
        if conn:
            conn.close()

def get_all_workouts() -> List[Dict[str, Any]]:
    """
    すべてのワークアウトデータを取得
    
    Returns:
        List[Dict[str, Any]]: ワークアウトのリスト
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, date, name, source, total_time, total_distance, 
                   avg_power, avg_hr, tss, ftp, max_hr, work_kj
            FROM workouts
            ORDER BY date DESC
        """)
        
        result = []
        for row in cursor.fetchall():
            workout = dict(row)
            result.append(workout)
        
        return result
    
    except Exception as e:
        logger.error(f"ワークアウト取得エラー: {str(e)}")
        return []
    
    finally:
        if conn:
            conn.close()

def delete_workout(workout_id: int) -> bool:
    """
    ワークアウトとそれに関連するデータを削除
    
    Args:
        workout_id: 削除するワークアウトのID
    
    Returns:
        bool: 削除成功の場合はTrue、失敗の場合はFalse
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 関連するデータポイントを削除
        cursor.execute("DELETE FROM data_points WHERE workout_id = ?", (workout_id,))
        
        # 関連するインターバルを削除
        cursor.execute("DELETE FROM intervals WHERE workout_id = ?", (workout_id,))
        
        # ワークアウトを削除
        cursor.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
        
        conn.commit()
        logger.info(f"ワークアウト（ID: {workout_id}）を削除しました")
        return True
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"ワークアウト削除エラー: {str(e)}")
        return False
    
    finally:
        if conn:
            conn.close()