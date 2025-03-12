import os
import logging
from typing import Tuple, Dict, Any, List, Optional
import tempfile

# ロガーの設定
logger = logging.getLogger(__name__)

# サポートされるファイル形式
SUPPORTED_EXTENSIONS = ['.fit']

class ValidationError(Exception):
    """データ検証エラー"""
    pass

def validate_file(uploaded_file) -> Tuple[str, str]:
    """
    アップロードされたファイルを検証する
    
    Args:
        uploaded_file: Streamlitのアップロードファイルオブジェクト
    
    Returns:
        Tuple[str, str]: 一時ファイルパスと元のファイル名
    
    Raises:
        ValidationError: ファイル形式が無効な場合
    """
    # ファイル名と拡張子を取得
    file_name = uploaded_file.name
    _, file_extension = os.path.splitext(file_name)
    file_extension = file_extension.lower()
    
    # サポートされている拡張子かチェック
    if file_extension not in SUPPORTED_EXTENSIONS:
        supported_ext_str = ', '.join(SUPPORTED_EXTENSIONS)
        raise ValidationError(f"サポートされていないファイル形式です。サポート形式: {supported_ext_str}")
    
    # 一時ファイルとして保存
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        temp_file_path = tmp_file.name
    
    return temp_file_path, file_name

def validate_workout_data(workout_data: Dict[str, Any]) -> Optional[str]:
    """
    ワークアウトデータが有効かどうかを検証する
    
    Args:
        workout_data: 検証するワークアウトデータ
    
    Returns:
        Optional[str]: エラーメッセージ（問題がなければNone）
    """
    # 必須フィールドの検証
    required_fields = ['date']
    for field in required_fields:
        if not workout_data.get(field):
            return f"必須フィールド '{field}' がありません。"
    
    # 日付が存在するか確認
    if not workout_data.get('date'):
        return "ワークアウト日時がありません。"
    
    # データポイントの最小数を確認（通常は何百もあるはず）
    # ここでは具体的な実装ではなく、一般的な考え方を示す
    min_data_points = 10  # この値は適宜調整
    
    return None

def validate_data_points(data_points: List[Dict[str, Any]]) -> Optional[str]:
    """
    データポイントが有効かどうかを検証する
    
    Args:
        data_points: 検証するデータポイントのリスト
    
    Returns:
        Optional[str]: エラーメッセージ（問題がなければNone）
    """
    # データポイントが空でないか確認
    if not data_points:
        return "データポイントがありません。"
    
    # データポイントの最小数を確認
    min_data_points = 10  # この値は適宜調整
    if len(data_points) < min_data_points:
        return f"データポイントが少なすぎます（{len(data_points)}）。最低 {min_data_points} 必要です。"
    
    # 各データポイントにタイムスタンプがあるか確認
    for i, point in enumerate(data_points):
        if 'timestamp' not in point:
            return f"データポイント #{i} にタイムスタンプがありません。"
    
    # パワーまたは心拍数のデータが存在するか確認
    has_power = any('power' in point for point in data_points)
    has_hr = any('heart_rate' in point for point in data_points)
    
    if not (has_power or has_hr):
        return "パワーデータまたは心拍数データのいずれかが必要です。"
    
    return None