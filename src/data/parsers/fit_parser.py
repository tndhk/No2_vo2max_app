import os
import datetime
import logging
from typing import Dict, List, Tuple, Optional, Any
from fitparse import FitFile

# ロガーの設定
logger = logging.getLogger(__name__)

class FitParser:
    """FITファイルを解析し、ワークアウトデータを抽出するクラス"""
    
    def __init__(self, file_path: str):
        """
        FITパーサーを初期化する
        
        Args:
            file_path: FITファイルのパス
        """
        self.file_path = file_path
        self.fit_file = None
        self.workout_data = {
            'date': None,
            'name': os.path.basename(file_path),
            'source': 'fit_file',
            'file_path': file_path,
            'total_time': None,
            'total_distance': None,
            'avg_power': None,
            'avg_hr': None,
            'tss': None,
            'ftp': None,
            'max_hr': None,
            'work_kj': None
        }
        self.data_points = []
    
    def parse(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        FITファイルを解析し、ワークアウトデータとデータポイントを返す
        
        Returns:
            Tuple[Dict, List[Dict]]: ワークアウト情報とデータポイントのリスト
        """
        try:
            self.fit_file = FitFile(self.file_path)
            self._extract_workout_info()
            self._extract_data_points()
            return self.workout_data, self.data_points
        except Exception as e:
            logger.error(f"FITファイル解析エラー: {str(e)}")
            raise ValueError(f"FITファイルの解析に失敗しました: {str(e)}")
    
    def _extract_workout_info(self):
        """セッション情報からワークアウトデータを抽出する"""
        for record in self.fit_file.get_messages('session'):
            # セッション開始時間を取得
            start_time = record.get_value('start_time')
            if start_time:
                self.workout_data['date'] = start_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 合計時間を取得（秒）
            total_time = record.get_value('total_elapsed_time')
            if total_time:
                self.workout_data['total_time'] = int(total_time)
            
            # 合計距離を取得（メートル）
            total_distance = record.get_value('total_distance')
            if total_distance:
                self.workout_data['total_distance'] = float(total_distance)
            
            # 平均パワーを取得
            avg_power = record.get_value('avg_power')
            if avg_power:
                self.workout_data['avg_power'] = int(avg_power)
            
            # 平均心拍を取得
            avg_hr = record.get_value('avg_heart_rate')
            if avg_hr:
                self.workout_data['avg_hr'] = int(avg_hr)
            
            # 総仕事量（キロジュール）を取得
            work = record.get_value('total_work')
            if work:
                self.workout_data['work_kj'] = float(work)
        
        # ファイル内にFTPや最大心拍の設定がある場合は抽出
        self._extract_user_profile()
    
    def _extract_user_profile(self):
        """ユーザープロファイルからFTPや最大心拍数を抽出する"""
        for record in self.fit_file.get_messages('user_profile'):
            max_hr = record.get_value('max_heart_rate')
            if max_hr:
                self.workout_data['max_hr'] = int(max_hr)
        
        # FTPは直接提供されていない場合があるため、関連フィールドから探す
        for record in self.fit_file.get_messages('zones_target'):
            ftp = record.get_value('functional_threshold_power')
            if ftp:
                self.workout_data['ftp'] = int(ftp)
    
    def _extract_data_points(self):
        """レコードメッセージからデータポイントを抽出する"""
        for record in self.fit_file.get_messages('record'):
            data_point = {}
            
            # タイムスタンプ（Unix時間）
            timestamp = record.get_value('timestamp')
            if timestamp:
                data_point['timestamp'] = int(timestamp.timestamp())
            else:
                continue  # タイムスタンプがなければスキップ
            
            # パワー値
            power = record.get_value('power')
            if power:
                data_point['power'] = int(power)
            
            # 心拍数
            heart_rate = record.get_value('heart_rate')
            if heart_rate:
                data_point['heart_rate'] = int(heart_rate)
            
            # ケイデンス
            cadence = record.get_value('cadence')
            if cadence:
                data_point['cadence'] = int(cadence)
            
            self.data_points.append(data_point)

def parse_fit_file(file_path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    FITファイルを解析するユーティリティ関数
    
    Args:
        file_path: FITファイルのパス
    
    Returns:
        Tuple[Dict, List[Dict]]: ワークアウト情報とデータポイントのリスト
    """
    parser = FitParser(file_path)
    return parser.parse()