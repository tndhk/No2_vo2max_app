import logging
import time
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timezone

# ロガーの設定
logger = logging.getLogger(__name__)

class StravaParser:
    """Stravaからのデータを解析するクラス"""
    
    def __init__(self, strava_service):
        """
        StravaParserを初期化する
        
        Args:
            strava_service: Strava APIとの通信を行うサービスインスタンス
        """
        self.strava_service = strava_service
    
    def parse_activity(self, activity_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """
        Stravaのアクティビティを解析し、ワークアウトデータとデータポイントを返す
        
        Args:
            activity_id: Stravaのアクティビティ ID
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]: 
                ワークアウトデータとデータポイントのタプル。エラー時はNoneを返す
        """
        try:
            # アクティビティの詳細情報を取得
            activity = self.strava_service.get_activity(activity_id)
            if not activity:
                logger.error(f"アクティビティ {activity_id} の詳細を取得できませんでした")
                return None, None
            
            # ストリームデータ（時系列データ）を取得
            streams = self.strava_service.get_activity_streams(
                activity_id, 
                ["time", "heartrate", "watts", "cadence"]
            )
            if not streams:
                logger.error(f"アクティビティ {activity_id} のストリームデータを取得できませんでした")
                return None, None
            
            # ワークアウトデータとデータポイントを抽出
            workout_data = self._extract_workout_data(activity)
            data_points = self._extract_data_points(streams)
            
            return workout_data, data_points
            
        except Exception as e:
            logger.error(f"アクティビティ解析エラー: {str(e)}")
            return None, None
    
    def _extract_workout_data(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """
        アクティビティ情報からワークアウトデータを抽出する
        
        Args:
            activity: Stravaのアクティビティデータ
            
        Returns:
            Dict[str, Any]: 内部形式のワークアウトデータ
        """
        # アクティビティの開始時間をISO形式からdatetime形式に変換
        start_date = activity.get('start_date')
        start_date_local = None
        if start_date:
            try:
                start_date_local = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%SZ").strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                logger.warning(f"日付の解析に失敗しました: {start_date}")
                start_date_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # アクティビティ名
        name = activity.get('name', f"Strava Activity {activity.get('id')}")
        
        # 合計時間（秒）
        moving_time = activity.get('moving_time', 0)
        elapsed_time = activity.get('elapsed_time', 0)
        total_time = elapsed_time
        
        # 合計距離（メートル）
        distance = activity.get('distance', 0.0)
        
        # 平均パワー
        avg_power = activity.get('average_watts')
        
        # 平均心拍数
        avg_hr = activity.get('average_heartrate')
        
        # 総仕事量（キロジュール）- Stravaでは直接提供されていないため計算
        work_kj = None
        if avg_power and moving_time:
            work_kj = (avg_power * moving_time) / 1000
        
        # キロジュール熱量 - Strava独自の指標
        kilojoules = activity.get('kilojoules')
        if kilojoules and not work_kj:
            work_kj = kilojoules
        
        # FTPとMax HRの設定 - アスリート情報から取得（あれば）
        ftp = None
        max_hr = None
        
        # アスリート情報を取得
        athlete = self.strava_service.get_athlete()
        if athlete:
            # FTPはStravaのAPIで直接提供されていないため、不明
            # 最大心拍数もAPIで直接提供されていないため、不明
            pass
        
        return {
            'date': start_date_local,
            'name': name,
            'source': 'strava',
            'file_path': f"strava_{activity.get('id')}",
            'total_time': total_time,
            'total_distance': distance,
            'avg_power': avg_power,
            'avg_hr': avg_hr,
            'tss': None,  # Training Stress Score - Strava APIでは直接提供されていない
            'ftp': ftp,
            'max_hr': max_hr,
            'work_kj': work_kj,
            'strava_id': activity.get('id')  # Stravaのアクティビティ ID
        }
    
    def _extract_data_points(self, streams: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ストリームデータからデータポイントを抽出する
        
        Args:
            streams: Stravaのストリームデータ
            
        Returns:
            List[Dict[str, Any]]: 内部形式のデータポイントのリスト
        """
        data_points = []
        
        # ストリームデータの構造をログに出力（デバッグ用）
        logger.debug(f"ストリームデータ構造: {list(streams.keys())}")
        
        # 各ストリームからデータを取得
        # ストリームデータはタイプによって構造が異なる場合があるため、より堅牢なアクセス方法を使用
        time_stream = []
        hr_stream = []
        power_stream = []
        cadence_stream = []
        
        # 時間ストリームの取得
        if 'time' in streams:
            try:
                time_data = streams['time']
                if isinstance(time_data, dict) and 'data' in time_data:
                    time_stream = time_data['data']
                elif isinstance(time_data, list):
                    time_stream = time_data
            except Exception as e:
                logger.warning(f"時間ストリームの解析エラー: {str(e)}")
        
        # 心拍数ストリームの取得
        if 'heartrate' in streams:
            try:
                hr_data = streams['heartrate']
                if isinstance(hr_data, dict) and 'data' in hr_data:
                    hr_stream = hr_data['data']
                elif isinstance(hr_data, list):
                    hr_stream = hr_data
            except Exception as e:
                logger.warning(f"心拍数ストリームの解析エラー: {str(e)}")
        
        # パワーストリームの取得
        if 'watts' in streams:
            try:
                power_data = streams['watts']
                if isinstance(power_data, dict) and 'data' in power_data:
                    power_stream = power_data['data']
                elif isinstance(power_data, list):
                    power_stream = power_data
            except Exception as e:
                logger.warning(f"パワーストリームの解析エラー: {str(e)}")
        
        # ケイデンスストリームの取得
        if 'cadence' in streams:
            try:
                cadence_data = streams['cadence']
                if isinstance(cadence_data, dict) and 'data' in cadence_data:
                    cadence_stream = cadence_data['data']
                elif isinstance(cadence_data, list):
                    cadence_stream = cadence_data
            except Exception as e:
                logger.warning(f"ケイデンスストリームの解析エラー: {str(e)}")
        
        # 時間ストリームがなければ空のリストを返す
        if not time_stream:
            logger.warning("時間ストリームが空のため、データポイントを生成できません")
            return []
        
        # 開始時間を取得（現在時刻をデフォルトとする）
        start_time = int(time.time())
        
        # 各ストリームの長さをチェック
        time_length = len(time_stream)
        hr_length = len(hr_stream)
        power_length = len(power_stream)
        cadence_length = len(cadence_stream)
        
        logger.info(f"データポイント生成: 時間={time_length}, 心拍={hr_length}, パワー={power_length}, ケイデンス={cadence_length}")
        
        # 各時点でのデータポイントを作成
        for i in range(time_length):
            data_point = {
                'timestamp': start_time + int(time_stream[i])  # 確実に整数に変換
            }
            
            # 心拍数があれば追加（整数に変換）
            if i < hr_length and hr_stream[i] is not None:
                try:
                    data_point['heart_rate'] = int(hr_stream[i])
                except (ValueError, TypeError):
                    # 変換できない場合はスキップ
                    pass
            
            # パワーがあれば追加（整数に変換）
            if i < power_length and power_stream[i] is not None:
                try:
                    data_point['power'] = int(power_stream[i])
                except (ValueError, TypeError):
                    # 変換できない場合はスキップ
                    pass
            
            # ケイデンスがあれば追加（整数に変換）
            if i < cadence_length and cadence_stream[i] is not None:
                try:
                    data_point['cadence'] = int(cadence_stream[i])
                except (ValueError, TypeError):
                    # 変換できない場合はスキップ
                    pass
            
            data_points.append(data_point)
        
        logger.info(f"生成されたデータポイント数: {len(data_points)}")
        if data_points:
            logger.debug(f"サンプルデータポイント: {data_points[0]}")
        
        return data_points

def parse_strava_activity(strava_service, activity_id: int) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
    """
    Stravaのアクティビティを解析するユーティリティ関数
    
    Args:
        strava_service: Strava APIとの通信を行うサービスインスタンス
        activity_id: Stravaのアクティビティ ID
        
    Returns:
        Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]]]: 
            ワークアウトデータとデータポイントのタプル
    """
    parser = StravaParser(strava_service)
    return parser.parse_activity(activity_id)