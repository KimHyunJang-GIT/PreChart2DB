import streamlit as st
import pandas as pd
import os
import io
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import platform

# --- 한글 폰트 설정 ---
if platform.system() == 'Windows':
    plt.rc('font', family='Malgun Gothic')
elif platform.system() == 'Darwin':
    plt.rc('font', family='AppleGothic')
else:
    plt.rc('font', family='NanumGothic')
plt.rcParams['axes.unicode_minus'] = False
# --- 한글 폰트 설정 끝 ---

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, '..'))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from core.config import DB_CONFIG, APP_CONFIG, STREAMLIT_CONFIG, VISUALIZATION_CONFIG
from core.database_manager import DatabaseManager
from core.data_importer import DataImporter

def run_streamlit_app():
    st.set_page_config(page_title=STREAMLIT_CONFIG['page_title'], layout=STREAMLIT_CONFIG['layout'])
    st.title(f"📊 {STREAMLIT_CONFIG['title']}")

    # --- Sidebar ---
    st.sidebar.header("⚙️ 설정 및 정보")

    st.sidebar.subheader("데이터베이스 설정")
    db_host = st.sidebar.text_input("DB 호스트", value=DB_CONFIG['host'])
    db_user = st.sidebar.text_input("DB 사용자", value=DB_CONFIG['user'])
    db_password = st.sidebar.text_input("DB 비밀번호", type="password", value=DB_CONFIG['password'])
    db_name = st.sidebar.text_input("DB 이름", value=DB_CONFIG['database'])

    updated_db_config = {
        'host': db_host,
        'user': db_user,
        'password': db_password,
        'database': db_name,
        'charset': DB_CONFIG['charset']
    }
    db_manager = DatabaseManager(db_config=updated_db_config, status_callback=lambda msg: st.info(msg))

    st.sidebar.subheader("파일 로드 옵션")
    csv_delimiter = st.sidebar.selectbox("CSV 구분자", (",", ";", "\t"), index=0)
    csv_encoding = st.sidebar.selectbox("CSV 인코딩", ("utf-8", "euc-kr", "cp949"), index=0)
    excel_sheet_name = st.sidebar.text_input("Excel 시트 이름 (비워두면 첫 번째 시트)", value="")

    data_importer = DataImporter(status_callback=lambda msg: st.info(msg))

    st.sidebar.subheader("앱 정보")
    with st.sidebar.expander("자세히 보기"):
        st.write(f"**버전:** {APP_CONFIG['version']}")
        st.write(f"**개발자:** {APP_CONFIG['developer']}")
        st.markdown(f"*{APP_CONFIG['description']}*")
    # --- Sidebar End ---

    st.header("1. 파일 업로드")
    uploaded_file = st.file_uploader("CSV 또는 Excel 파일을 선택하세요", type=["csv", "xlsx", "xls"])

    # --- 데이터 로딩 및 상태 관리 로직 ---
    if 'current_df' not in st.session_state:
        st.session_state.current_df = None
    if 'last_uploaded_filename' not in st.session_state:
        st.session_state.last_uploaded_filename = None
    # Initialize session state for overwrite confirmation
    if 'confirm_overwrite_db' not in st.session_state:
        st.session_state.confirm_overwrite_db = False

    if uploaded_file is None and st.session_state.last_uploaded_filename is not None:
        st.session_state.current_df = None
        st.session_state.last_uploaded_filename = None
        st.session_state.confirm_overwrite_db = False # Reset confirmation
        st.rerun()

    elif uploaded_file is not None and uploaded_file.name != st.session_state.last_uploaded_filename:
        st.session_state.current_df = None
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.confirm_overwrite_db = False # Reset confirmation

        with st.spinner(f"'{uploaded_file.name}' 파일을 로딩하고 분석하는 중입니다... 잠시만 기다려 주세요."):
            try:
                sheet = excel_sheet_name if excel_sheet_name else 0
                df = data_importer.load_data(
                    uploaded_file,
                    csv_delimiter=csv_delimiter,
                    csv_encoding=csv_encoding,
                    excel_sheet_name=sheet
                )
                if df is not None:
                    st.session_state.current_df = df
                    st.session_state.file_name_without_ext = os.path.splitext(uploaded_file.name)[0]
                    st.success(f"파일 로드 성공: {uploaded_file.name} (총 {len(df)} 행)")
                else:
                    st.error("파일 로드에 실패했습니다. 파일 형식이나 옵션을 확인해 주세요.")
                    st.session_state.last_uploaded_filename = None
            except Exception as e:
                st.error(f"파일 처리 중 오류 발생: {e}")
                st.session_state.current_df = None
                st.session_state.last_uploaded_filename = None
        st.rerun()

    # --- 분석 UI 표시 ---
    if st.session_state.current_df is not None:
        df = st.session_state.current_df
        file_name_without_ext = st.session_state.get('file_name_without_ext', '')

        tab1, tab2, tab3 = st.tabs(["📊 데이터 탐색 및 편집", "📈 컬럼 상세 분석", "💾 데이터베이스 연동"])

        with tab1:
            st.subheader("데이터 요약")
            col1, col2, col3 = st.columns(3)
            col1.metric("총 행 수", f"{df.shape[0]:,} 개")
            col2.metric("총 컬럼 수", f"{df.shape[1]:,} 개")
            total_missing = df.isnull().sum().sum()
            col3.metric("총 결측치 수", f"{total_missing:,} 개")

            with st.container(border=True):
                st.subheader("📝 데이터 편집 및 미리보기")
                st.info("💡 여기에서 데이터를 직접 수정할 수 있습니다. 수정된 내용은 즉시 앱 전체에 반영됩니다.")
                edited_df = st.data_editor(df, width='stretch', num_rows="dynamic")
                
                # 사용자에 의해 데이터가 수정되었는지 확인하고, 수정되었다면 상태를 업데이트한 후 즉시 새로고침합니다.
                if not df.equals(edited_df):
                    st.session_state.current_df = edited_df
                    st.rerun()

            with st.container(border=True):
                st.subheader("📈 데이터 기술 통계")
                st.dataframe(df.describe(include='all').astype(str))

            with st.container(border=True):
                st.subheader("ℹ️ 데이터 타입 및 결측치 정보")
                info_df = pd.DataFrame({
                    "Non-Null Count": df.notna().sum(),
                    "Dtype": df.dtypes
                }).reset_index().rename(columns={"index": "Column"})
                st.dataframe(info_df.astype(str), width='stretch')

        with tab2:
            st.subheader("분석할 컬럼 선택")
            selected_column = st.selectbox("분석할 컬럼을 선택하세요", df.columns, label_visibility="collapsed")

            if selected_column:
                df_column = df[selected_column]
                na_count = df_column.isnull().sum()
                st.metric(f"'{selected_column}' 컬럼의 결측치(NA) 개수", f"{na_count:,} 개")

                with st.container(border=True):
                    st.subheader("🎨 데이터 분포 시각화")
                    if pd.api.types.is_numeric_dtype(df_column):
                        fig, axes = plt.subplots(1, 2, figsize=(15, 5))
                        fig.suptitle(f"'{selected_column}' 컬럼 분포", fontsize=16)
                        sns.histplot(df_column.dropna(), kde=True, ax=axes[0])
                        axes[0].set_title("히스토그램 (Histogram)")
                        sns.boxplot(x=df_column, ax=axes[1])
                        axes[1].set_title("상자 그림 (Box Plot)")
                        st.pyplot(fig)
                        plt.clf()
                    else:
                        top_n = VISUALIZATION_CONFIG['top_n_categories']
                        value_counts = df_column.value_counts().nlargest(top_n)
                        fig, ax = plt.subplots(figsize=(10, 6))
                        sns.barplot(x=value_counts.index.astype(str), y=value_counts.values, ax=ax)
                        ax.set_title(f"'{selected_column}' 값 빈도수 (상위 {top_n}개)")
                        ax.set_ylabel("빈도수")
                        plt.xticks(rotation=45, ha='right')
                        plt.tight_layout()
                        st.pyplot(fig)
                        plt.clf()

                with st.container(border=True):
                    st.subheader("📋 데이터 요약")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**값 빈도수 (Value Counts)**")
                        st.dataframe(df_column.value_counts(dropna=False).to_frame().astype(str))
                    with col2:
                        st.write("**기술 통계 (Descriptive Statistics)**")
                        st.dataframe(df_column.describe(include='all').to_frame().astype(str))

        with tab3:
            st.subheader("데이터베이스 작업 옵션")
            st.write("원하는 데이터베이스 작업 유형을 선택하세요.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 전체 덮어쓰기 (기존 데이터 삭제)", width='stretch', key="initiate_overwrite"):
                    st.session_state.confirm_overwrite_db = True
                    st.rerun()
                
                if st.session_state.confirm_overwrite_db:
                    st.warning(f"**경고:** 테이블 '{file_name_without_ext}'의 모든 데이터가 삭제되고 현재 파일의 데이터로 대체됩니다. 계속하시겠습니까?")
                    if st.button("삭제 및 덮어쓰기 진행", type="primary", key="confirm_overwrite"):
                        st.info(f"DB: overwrite_table 호출 시도. DataFrame shape: {df.shape}, Table name: {file_name_without_ext}")
                        success, message = db_manager.overwrite_table(df, file_name_without_ext)
                        st.info(f"DB: overwrite_table 응답: Success={success}, Message={message}")
                        if success:
                            st.success(f"✅ {message}")
                        else:
                            st.error(f"❌ {message}")
                        st.session_state.confirm_overwrite_db = False # Reset confirmation after action
                        st.rerun()

            with col2:
                if st.button("➕ 변경된 내용만 추가", width='stretch', key="append_data"):
                    st.info(f"DB: append_new_data 호출 시도. DataFrame shape: {df.shape}, Table name: {file_name_without_ext}")
                    success, message = db_manager.append_new_data(df, file_name_without_ext)
                    st.info(f"DB: append_new_data 응답: Success={success}, Message={message}")
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")
                    st.rerun()

if __name__ == "__main__":
    run_streamlit_app()
