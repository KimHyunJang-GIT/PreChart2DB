import pymysql
from pymysql import Error
import pandas as pd
from .config import DB_CONFIG

class DatabaseManager:
    def __init__(self, db_config=None, status_callback=None):
        self.DB_CONFIG = db_config if db_config else DB_CONFIG
        self.status_callback = status_callback if status_callback else print

    def _update_status(self, message):
        self.status_callback(message)

    def _connect_to_db(self, create_db=False):
        conn = None
        try:
            db_config_no_db = self.DB_CONFIG.copy()
            if 'database' in db_config_no_db:
                del db_config_no_db['database']
            
            conn = pymysql.connect(**db_config_no_db)
            if create_db:
                with conn.cursor() as cursor:
                    self._update_status(f"데이터베이스 '{self.DB_CONFIG['database']}' 존재 여부 확인 및 생성...")
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.DB_CONFIG['database']}`")
                self._update_status(f"데이터베이스 '{self.DB_CONFIG['database']}' 확인 또는 생성 완료.")
            
            conn.select_db(self.DB_CONFIG['database'])
            self._update_status(f"데이터베이스 '{self.DB_CONFIG['database']}' 연결 성공.")
            return conn
        except Error as e:
            self._update_status(f"DB 연결 실패: {e}")
            if conn: conn.close()
            return None

    def _get_mysql_type(self, pandas_dtype):
        if 'int' in str(pandas_dtype): return 'BIGINT'
        if 'float' in str(pandas_dtype): return 'DOUBLE'
        if 'datetime' in str(pandas_dtype): return 'DATETIME'
        if 'bool' in str(pandas_dtype): return 'BOOLEAN'
        return 'VARCHAR(255)'

    def _create_table_from_dataframe(self, cursor, df, table_name):
        safe_table_name = ''.join(c for c in table_name if c.isalnum() or c == '_').replace(' ', '_')
        if not safe_table_name: safe_table_name = "untitled_table"

        columns_sql = ["`id` INT AUTO_INCREMENT PRIMARY KEY"]
        for col_name, dtype in df.dtypes.items():
            safe_col_name = ''.join(c for c in col_name if c.isalnum() or c == '_').replace(' ', '_')
            if not safe_col_name: continue
            mysql_type = self._get_mysql_type(dtype)
            columns_sql.append(f"`{safe_col_name}` {mysql_type}")

        if len(columns_sql) <= 1: raise ValueError("테이블을 생성할 컬럼 정보가 없습니다.")

        self._update_status(f"테이블 '{safe_table_name}'을(를) 재생성하여 스키마를 업데이트합니다.")
        cursor.execute(f"DROP TABLE IF EXISTS `{safe_table_name}`")
        create_table_query = f"CREATE TABLE `{safe_table_name}` ({', '.join(columns_sql)})"
        self._update_status(f"테이블 생성 쿼리 실행: {create_table_query}")
        cursor.execute(create_table_query)
        return safe_table_name

    def _insert_data_into_table(self, cursor, df, table_name, check_duplicates=True):
        safe_columns = [''.join(c for c in col if c.isalnum() or c == '_').replace(' ', '_') for col in df.columns]
        safe_columns = [col for col in safe_columns if col]
        if not safe_columns: raise ValueError("데이터를 삽입할 컬럼 정보가 없습니다.")

        columns_str = ", ".join([f"`{col}`" for col in safe_columns])
        data_to_insert = [tuple(None if pd.isna(x) else x for x in y) for y in df.to_numpy()]

        if check_duplicates:
            self._update_status(f"테이블 '{table_name}'에서 기존 데이터 조회 중... (중복 방지)")
            cursor.execute(f"SELECT {columns_str} FROM `{table_name}`")
            existing_data = {tuple(str(item) for item in row) for row in cursor.fetchall()}
            self._update_status(f"기존 데이터 {len(existing_data)}개 조회 완료.")
            
            df_tuples_str = [tuple(str(item) for item in row) for row in data_to_insert]
            new_data_indices = [i for i, row_tuple in enumerate(df_tuples_str) if row_tuple not in existing_data]
            data_to_insert = [data_to_insert[i] for i in new_data_indices]

        total_rows_in_file = len(df)
        inserted_rows_count = len(data_to_insert)
        skipped_rows_count = total_rows_in_file - inserted_rows_count

        if not data_to_insert:
            self._update_status(f"새로 추가할 데이터가 없습니다. ({skipped_rows_count}개 중복으로 건너뜀)")
            return True, f"파일의 모든 데이터({total_rows_in_file}개)가 이미 데이터베이스에 존재합니다."

        placeholders = ", ".join(["%s"] * len(safe_columns))
        insert_query = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
        self._update_status(f"{inserted_rows_count}개의 신규 데이터를 테이블 '{table_name}'에 삽입합니다. ({skipped_rows_count}개 중복으로 건너뜀)")
        cursor.executemany(insert_query, data_to_insert)
        return True, f"파일의 {total_rows_in_file}개 데이터 중, 신규 데이터 {inserted_rows_count}개가 삽입되었고, {skipped_rows_count}개는 건너뛰었습니다."

    def overwrite_table(self, df, table_name):
        conn = None
        try:
            conn = self._connect_to_db(create_db=True)
            if not conn: return False, "데이터베이스에 연결할 수 없습니다."
            with conn.cursor() as cursor:
                safe_table_name = self._create_table_from_dataframe(cursor, df, table_name)
                _, message = self._insert_data_into_table(cursor, df, safe_table_name, check_duplicates=False)
                conn.commit()
            return True, f"테이블 '{safe_table_name}'을(를) 성공적으로 덮어썼습니다. {message}"
        except Exception as e:
            if conn: conn.rollback()
            self._update_status(f"덮어쓰기 작업 실패: {e}")
            return False, f"덮어쓰기 작업 중 오류 발생: {e}"
        finally:
            if conn: conn.close()

    def append_new_data(self, df, table_name):
        conn = None
        try:
            conn = self._connect_to_db(create_db=False) # DB가 없으면 실패
            if not conn: return False, "데이터베이스에 연결할 수 없습니다. 먼저 DB를 생성해야 할 수 있습니다."
            with conn.cursor() as cursor:
                safe_table_name = ''.join(c for c in table_name if c.isalnum() or c == '_').replace(' ', '_')
                _, message = self._insert_data_into_table(cursor, df, safe_table_name, check_duplicates=True)
                conn.commit()
            return True, message
        except Error as e:
            if conn: conn.rollback()
            if e.args[0] == 1146: # Table doesn't exist
                return False, f"테이블 '{table_name}'이(가) 존재하지 않습니다. 먼저 '덮어쓰기'를 실행하여 테이블을 생성해주세요."
            self._update_status(f"추가 작업 실패: {e}")
            return False, f"데이터 추가 작업 중 오류 발생: {e}"
        except Exception as e:
            if conn: conn.rollback()
            self._update_status(f"추가 작업 실패: {e}")
            return False, f"데이터 추가 작업 중 오류 발생: {e}"
        finally:
            if conn: conn.close()
