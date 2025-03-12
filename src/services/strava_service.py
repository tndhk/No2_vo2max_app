import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

# プロジェクトルートをPythonパスに追加するためのインポート
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config import STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET

# ロガーの設定
logger = logging.getLogger(__name__)

class StravaService:
    """StravaのAPIと通信するためのサービスクラス"""
    
    # トークン情報を保存するファイルパス
    TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../data/strava_token.json')
    
    # Strava APIのベースURL
    API_BASE_URL = "https://www.strava.com/api/v3"
    
    def __init__(self):
        """StravaServiceの初期化"""
        self.client_id = STRAVA_CLIENT_ID
        self.client_secret = STRAVA_CLIENT_SECRET
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        
        # 保存されたトークンがあれば読み込む
        self._load_token()
    
    def _load_token(self) -> bool:
        """
        保存されたトークン情報を読み込む
        
        Returns:
            bool: トークンの読み込みに成功した場合はTrue
        """
        try:
            if os.path.exists(self.TOKEN_FILE):
                with open(self.TOKEN_FILE, 'r') as f:
                    token_data = json.load(f)
                    
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires_at = token_data.get('expires_at', 0)
                
                return True
            return False
        except Exception as e:
            logger.error(f"トークン読み込みエラー: {str(e)}")
            return False
    
    def _save_token(self) -> bool:
        """
        トークン情報をファイルに保存する
        
        Returns:
            bool: 保存に成功した場合はTrue
        """
        try:
            # 保存先ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)
            
            token_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'expires_at': self.token_expires_at
            }
            
            with open(self.TOKEN_FILE, 'w') as f:
                json.dump(token_data, f)
            
            return True
        except Exception as e:
            logger.error(f"トークン保存エラー: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """
        認証済みかつトークンが有効かどうかを確認
        
        Returns:
            bool: 認証済みかつトークンが有効な場合はTrue
        """
        current_time = time.time()
        
        # トークンが存在しない場合はFalse
        if not self.access_token or not self.refresh_token:
            return False
        
        # トークンの有効期限が切れている場合は更新を試みる
        if self.token_expires_at <= current_time:
            return self.refresh_access_token()
        
        return True
    
    def get_authorization_url(self, redirect_uri: str) -> str:
        """
        認証用のURLを生成
        
        Args:
            redirect_uri: 認証後のリダイレクト先URL
            
        Returns:
            str: 認証用URL
        """
        if not self.client_id:
            raise ValueError("STRAVA_CLIENT_IDが設定されていません")
        
        scope = "read,activity:read"
        
        auth_url = (
            f"https://www.strava.com/oauth/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&approval_prompt=force"
            f"&scope={scope}"
        )
        
        return auth_url
    
    def exchange_token(self, code: str) -> bool:
        """
        認証コードをアクセストークンに交換
        
        Args:
            code: 認証コード
            
        Returns:
            bool: トークン交換に成功した場合はTrue
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("STRAVA_CLIENT_IDまたはSTRAVA_CLIENT_SECRETが設定されていません")
        
        try:
            response = requests.post(
                "https://www.strava.com/oauth/token",
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'code': code,
                    'grant_type': 'authorization_code'
                }
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            self.token_expires_at = token_data.get('expires_at', 0)
            
            # トークン情報をファイルに保存
            self._save_token()
            
            return True
        
        except Exception as e:
            logger.error(f"トークン交換エラー: {str(e)}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        アクセストークンを更新
        
        Returns:
            bool: トークン更新に成功した場合はTrue
        """
        if not self.client_id or not self.client_secret or not self.refresh_token:
            return False
        
        try:
            response = requests.post(
                "https://www.strava.com/oauth/token",
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret,
                    'refresh_token': self.refresh_token,
                    'grant_type': 'refresh_token'
                }
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            self.access_token = token_data.get('access_token')
            self.refresh_token = token_data.get('refresh_token')
            self.token_expires_at = token_data.get('expires_at', 0)
            
            # 更新したトークン情報をファイルに保存
            self._save_token()
            
            return True
        
        except Exception as e:
            logger.error(f"トークン更新エラー: {str(e)}")
            return False
    
    def get_athlete(self) -> Optional[Dict[str, Any]]:
        """
        現在認証されているアスリート（ユーザー）情報を取得
        
        Returns:
            Optional[Dict[str, Any]]: アスリート情報
        """
        if not self.is_authenticated():
            return None
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/athlete",
                headers={'Authorization': f'Bearer {self.access_token}'}
            )
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"アスリート情報取得エラー: {str(e)}")
            return None
    
    def get_activities(self, per_page: int = 30, page: int = 1) -> Optional[List[Dict[str, Any]]]:
        """
        ユーザーのアクティビティリストを取得
        
        Args:
            per_page: 1ページあたりのアクティビティ数
            page: ページ番号
            
        Returns:
            Optional[List[Dict[str, Any]]]: アクティビティリスト
        """
        if not self.is_authenticated():
            return None
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/athlete/activities",
                headers={'Authorization': f'Bearer {self.access_token}'},
                params={'per_page': per_page, 'page': page}
            )
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"アクティビティリスト取得エラー: {str(e)}")
            return None
    
    def get_activity(self, activity_id: int) -> Optional[Dict[str, Any]]:
        """
        特定のアクティビティの詳細を取得
        
        Args:
            activity_id: アクティビティID
            
        Returns:
            Optional[Dict[str, Any]]: アクティビティ詳細情報
        """
        if not self.is_authenticated():
            return None
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/activities/{activity_id}",
                headers={'Authorization': f'Bearer {self.access_token}'},
                params={'include_all_efforts': True}
            )
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"アクティビティ詳細取得エラー: {str(e)}")
            return None
    
    def get_activity_streams(self, activity_id: int, stream_types: List[str]) -> Optional[Dict[str, Any]]:
        """
        アクティビティのストリームデータ（時系列データ）を取得
        
        Args:
            activity_id: アクティビティID
            stream_types: 取得するストリームの種類のリスト
                          (time, distance, latlng, altitude, velocity_smooth, 
                           heartrate, cadence, watts, temp, moving, grade_smooth)
            
        Returns:
            Optional[Dict[str, Any]]: ストリームデータ
        """
        if not self.is_authenticated():
            return None
        
        # リスト内の項目をカンマ区切りの文字列に変換
        keys_str = ','.join(stream_types)
        
        try:
            response = requests.get(
                f"{self.API_BASE_URL}/activities/{activity_id}/streams",
                headers={'Authorization': f'Bearer {self.access_token}'},
                params={
                    'keys': keys_str,
                    'key_by_type': True
                }
            )
            
            response.raise_for_status()
            return response.json()
        
        except Exception as e:
            logger.error(f"ストリームデータ取得エラー: {str(e)}")
            return None