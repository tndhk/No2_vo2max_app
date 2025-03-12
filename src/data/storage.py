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
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 保存前のデータをログに出力（デバッグ用）
        logger.debug(f"保存するワークアウトデータ: {workout_data}")
        
        # 数値フィールドを整数または浮動小数点に変換（Noneの場合はNoneのまま）
        total_time = workout_data.get('total_time')
        if total_time is not None:
            try:
                total_time = int(total_time)
            except (ValueError, TypeError):
                total_time = None
        
        total_distance = workout_data.get('total_distance')
        if total_distance is not None:
            try:
                total_distance = float(total_distance)
            except (ValueError, TypeError):
                total_distance = None
        
        avg_power = workout_data.get('avg_power')
        if avg_power is not None:
            try:
                avg_power = int(avg_power)
            except (ValueError, TypeError):
                avg_power = None
        
        avg_hr = workout_data.get('avg_hr')
        if avg_hr is not None:
            try:
                avg_hr = int(avg_hr)
            except (ValueError, TypeError):
                avg_hr = None
        
        tss = workout_data.get('tss')
        if tss is not None:
            try:
                tss = float(tss)
            except (ValueError, TypeError):
                tss = None
        
        ftp = workout_data.get('ftp')
        if ftp is not None:
            try:
                ftp = int(ftp)
            except (ValueError, TypeError):
                ftp = None
        
        max_hr = workout_data.get('max_hr')
        if max_hr is not None:
            try:
                max_hr = int(max_hr)
            except (ValueError, TypeError):
                max_hr = None
        
        work_kj = workout_data.get('work_kj')
        if work_kj is not None:
            try:
                work_kj = float(work_kj)
            except (ValueError, TypeError):
                work_kj = None
        
        strava_id = workout_data.get('strava_id')
        if strava_id is not None:
            try:
                strava_id = int(strava_id)
            except (ValueError, TypeError):
                strava_id = None
        
        # ワークアウトデータの保存
        cursor.execute("""
            INSERT INTO workouts 
            (date, name, source, file_path, total_time, total_distance, 
             avg_power, avg_hr, tss, ftp, max_hr, work_kj, strava_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workout_data.get('date'),
            workout_data.get('name'),
            workout_data.get('source'),
            workout_data.get('file_path'),
            total_time,
            total_distance,
            avg_power,
            avg_hr,
            tss,
            ftp,
            max_hr,
            work_kj,
            strava_id
        ))
        
        # 挿入されたワークアウトのIDを取得
        workout_id = cursor.lastrowid
        
        # データポイントの保存
        if data_points and workout_id:
            for i, point in enumerate(data_points):
                try:
                    # データポイントの各フィールドを適切な型に変換
                    timestamp = point.get('timestamp')
                    if timestamp is not None:
                        try:
                            timestamp = int(timestamp)
                        except (ValueError, TypeError):
                            timestamp = None
                    
                    power = point.get('power')
                    if power is not None:
                        try:
                            power = int(power)
                        except (ValueError, TypeError):
                            power = None
                    
                    heart_rate = point.get('heart_rate')
                    if heart_rate is not None:
                        try:
                            heart_rate = int(heart_rate)
                        except (ValueError, TypeError):
                            heart_rate = None
                    
                    cadence = point.get('cadence')
                    if cadence is not None:
                        try:
                            cadence = int(cadence)
                        except (ValueError, TypeError):
                            cadence = None
                    
                    # タイムスタンプが必須なのでチェック
                    if timestamp is None:
                        logger.warning(f"データポイント #{i} にタイムスタンプがないためスキップします")
                        continue
                    
                    cursor.execute("""
                        INSERT INTO data_points 
                        (workout_id, timestamp, power, heart_rate, cadence)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        workout_id,
                        timestamp,
                        power,
                        heart_rate,
                        cadence
                    ))
                except Exception as e:
                    logger.warning(f"データポイント #{i} の保存エラー: {str(e)}")
                    # 個別のデータポイントエラーは無視して続行
        
        conn.commit()
        logger.info(f"ワークアウトデータを保存しました。ID: {workout_id}, データポイント数: {len(data_points) if data_points else 0}")
        return workout_id
    
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"データ保存エラー: {str(e)}", exc_info=True)
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

def check_strava_activity_exists(strava_id: int) -> bool:
    """
    同じStravaアクティビティIDのワークアウトが既に存在するかチェック
    
    Args:
        strava_id: Stravaアクティビティ ID
    
    Returns:
        bool: 存在する場合はTrue、そうでない場合はFalse
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM workouts WHERE strava_id = ?", (strava_id,))
        result = cursor.fetchone()
        
        return result is not None
    
    except Exception as e:
        logger.error(f"Stravaアクティビティ存在チェックエラー: {str(e)}")
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
                   avg_power, avg_hr, tss, ftp, max_hr, work_kj, strava_id
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