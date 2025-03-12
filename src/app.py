import streamlit as st
import os
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import datetime
import sys

# プロジェクトルートを Python パスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# アプリケーションのインポート
from data.validators import validate_file, ValidationError
from data.parsers.fit_parser import parse_fit_file
from data.storage import save_workout_data, check_workout_exists, get_all_workouts, delete_workout
from config import APP_NAME, APP_VERSION

# ロガーの設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # アプリケーションのタイトルとサイドバーの設定
    st.title(f"{APP_NAME} v{APP_VERSION}")
    
    # サイドバーでセクションを選択
    section = st.sidebar.radio(
        "セクション",
        ["ワークアウトアップロード", "ワークアウト一覧", "分析", "設定"]
    )
    
    # 選択されたセクションに基づいて表示を切り替え
    if section == "ワークアウトアップロード":
        show_upload_section()
    elif section == "ワークアウト一覧":
        show_workouts_list()
    elif section == "分析":
        show_analysis_section()
    elif section == "設定":
        show_settings_section()

def show_upload_section():
    """ワークアウトファイルのアップロードセクション"""
    st.header("ワークアウトファイルのアップロード")
    
    # ファイルアップローダー
    uploaded_file = st.file_uploader(
        "FITファイルをアップロード",
        type=["fit"],
        help="Garmin、Wahoo、その他のデバイスからエクスポートしたFITファイルをアップロードしてください。"
    )
    
    # FTPと最大心拍数の入力フィールド
    col1, col2 = st.columns(2)
    with col1:
        ftp_value = st.number_input("FTP値（省略可）", min_value=0, value=0, help="ワークアウト時のFTP値")
    with col2:
        max_hr_value = st.number_input("最大心拍数（省略可）", min_value=0, value=0, help="最大心拍数")
    
    if uploaded_file is not None:
        try:
            with st.spinner("ファイルを処理中..."):
                # ファイルの検証
                temp_file_path, original_filename = validate_file(uploaded_file)
                
                # 既に同じファイル名のワークアウトが存在するかチェック
                if check_workout_exists(original_filename):
                    st.warning(f"同名のファイル '{original_filename}' は既にアップロードされています。")
                    return
                
                # FITファイルの解析
                workout_data, data_points = parse_fit_file(temp_file_path)
                
                # 手動入力したFTPと最大心拍数を追加（存在しない場合のみ）
                if ftp_value > 0 and not workout_data.get('ftp'):
                    workout_data['ftp'] = ftp_value
                if max_hr_value > 0 and not workout_data.get('max_hr'):
                    workout_data['max_hr'] = max_hr_value
                
                # 元のファイル名を保存
                workout_data['name'] = original_filename
                workout_data['file_path'] = original_filename
                
                # 解析データを表示
                st.subheader("解析結果")
                
                # 基本情報
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("日付", workout_data.get('date', '不明')[:10])
                with col2:
                    total_time_min = workout_data.get('total_time', 0) / 60 if workout_data.get('total_time') else 0
                    st.metric("時間", f"{total_time_min:.1f} 分")
                with col3:
                    st.metric("距離", f"{workout_data.get('total_distance', 0) / 1000:.2f} km" if workout_data.get('total_distance') else "不明")
                
                # パワーと心拍数
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("平均パワー", f"{workout_data.get('avg_power', 0)} W" if workout_data.get('avg_power') else "不明")
                with col2:
                    st.metric("平均心拍数", f"{workout_data.get('avg_hr', 0)} bpm" if workout_data.get('avg_hr') else "不明")
                with col3:
                    st.metric("総仕事量", f"{workout_data.get('work_kj', 0):.1f} kJ" if workout_data.get('work_kj') else "不明")
                
                # データポイントのサンプルを表示
                if data_points:
                    st.subheader("データポイントサンプル")
                    sample_size = min(5, len(data_points))
                    sample_df = pd.DataFrame(data_points[:sample_size])
                    
                    # タイムスタンプを人間が読める形式に変換
                    if 'timestamp' in sample_df.columns:
                        sample_df['human_time'] = sample_df['timestamp'].apply(
                            lambda x: datetime.datetime.fromtimestamp(x).strftime('%H:%M:%S')
                        )
                    
                    st.dataframe(sample_df)
                    st.text(f"データポイント数: {len(data_points)}")
                
                # 保存ボタン
                if st.button("データを保存", key="save_workout"):
                    workout_id = save_workout_data(workout_data, data_points)
                    if workout_id:
                        st.success(f"ワークアウトデータを保存しました（ID: {workout_id}）")
                        
                        # 一時ファイルを削除
                        try:
                            os.remove(temp_file_path)
                        except Exception as e:
                            logger.error(f"一時ファイル削除エラー: {str(e)}")
                    else:
                        st.error("データの保存に失敗しました。")
        
        except ValidationError as e:
            st.error(f"検証エラー: {str(e)}")
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            logger.exception("ファイル処理中にエラーが発生")

def show_workouts_list():
    """ワークアウト一覧セクション"""
    st.header("ワークアウト一覧")
    
    # 保存されたワークアウトを取得
    workouts = get_all_workouts()
    
    if not workouts:
        st.info("保存されたワークアウトがありません。「ワークアウトアップロード」セクションからファイルをアップロードしてください。")
        return
    
    # ワークアウトデータをDataFrameに変換
    df = pd.DataFrame(workouts)
    
    # 日付を読みやすい形式に変換
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
    
    # 時間を分に変換
    if 'total_time' in df.columns:
        df['duration_min'] = df['total_time'].apply(lambda x: f"{x/60:.1f} 分" if x else "")
    
    # 距離をkmに変換
    if 'total_distance' in df.columns:
        df['distance_km'] = df['total_distance'].apply(lambda x: f"{x/1000:.2f} km" if x else "")
    
    # 表示用のカラムを選択
    display_columns = ['id', 'date', 'name', 'duration_min', 'distance_km', 'avg_power', 'avg_hr', 'ftp']
    display_df = df[display_columns].rename(columns={
        'id': 'ID',
        'date': '日付',
        'name': '名前',
        'duration_min': '時間',
        'distance_km': '距離',
        'avg_power': '平均パワー',
        'avg_hr': '平均心拍数',
        'ftp': 'FTP'
    })
    
    st.dataframe(display_df, use_container_width=True)
    
    # ワークアウト削除機能
    with st.expander("ワークアウトの削除"):
        workout_id = st.number_input("削除するワークアウトID", min_value=1, step=1)
        
        if st.button("削除", key="delete_workout"):
            if delete_workout(workout_id):
                st.success(f"ワークアウト（ID: {workout_id}）を削除しました。")
                st.rerun()  # 画面を更新
            else:
                st.error("ワークアウトの削除に失敗しました。")

def show_analysis_section():
    """データ分析セクション（未実装）"""
    st.header("VO2maxインターバル分析")
    st.info("このセクションは開発中です...")

def show_settings_section():
    """設定セクション（未実装）"""
    st.header("設定")
    st.info("このセクションは開発中です...")

if __name__ == "__main__":
    main()