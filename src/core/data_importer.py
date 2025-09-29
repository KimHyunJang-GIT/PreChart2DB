import pandas as pd
import os

class DataImporter:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback if status_callback else print

    def _update_status(self, message):
        self.status_callback(message)

    def load_data(self, file_input, csv_delimiter=',', csv_encoding='utf-8', excel_sheet_name=None):
        # This function now accepts either a file path (string) or a file-like object.
        if file_input is None:
            self._update_status("오류: 파일 경로 또는 객체가 제공되지 않았습니다.")
            return None

        file_name = ""
        file_object = None

        if isinstance(file_input, str): # It's a file path
            file_name = os.path.basename(file_input)
            file_object = file_input
        elif hasattr(file_input, 'name'): # It's a file-like object (e.g., from Streamlit)
            file_name = file_input.name
            file_object = file_input
        else:
            self._update_status("오류: 잘못된 파일 입력 타입입니다.")
            return None

        file_extension = os.path.splitext(file_name)[1].lower()
        df = None

        try:
            if file_extension == '.csv':
                # Load all data as strings to prevent type inference errors
                df = pd.read_csv(file_object, sep=csv_delimiter, encoding=csv_encoding, dtype=str)
                self._update_status(f"CSV 파일 로드 성공: {file_name}")
            elif file_extension in ('.xlsx', '.xls'):
                # Load all data as strings
                if excel_sheet_name:
                    df = pd.read_excel(file_object, sheet_name=excel_sheet_name, dtype=str)
                else:
                    df = pd.read_excel(file_object, dtype=str) # 첫 번째 시트 로드
                self._update_status(f"Excel 파일 로드 성공: {file_name}")
            else:
                self._update_status(f"지원하지 않는 파일 형식: {file_extension}")
                return None

            # Convert columns to numeric where possible, ignoring errors for mixed-type columns
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='ignore')

            self._update_status(f"파일 읽기 및 타입 변환 성공. 총 {len(df)} 행, 컬럼: {', '.join(df.columns)}")
            return df

        except FileNotFoundError:
            self._update_status(f"파일을 찾을 수 없습니다: {file_name}")
            return None
        except Exception as e:
            self._update_status(f"파일 로드 중 오류 발생 ({file_name}): {e}")
            return None
