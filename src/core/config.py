# --- Database Configuration ---
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '0000',
    'database': 'soloDB',
    'charset': 'utf8'
}

# --- App Information ---
APP_CONFIG = {
    "version": "1.0.0",
    "developer": "Gemini Assistant",
    "description": "이 앱은 CSV/Excel 파일을 데이터베이스에 적재하고 데이터를 분석하는 도구입니다."
}

# --- Streamlit UI Configuration ---
STREAMLIT_CONFIG = {
    "page_title": "PreChart2DB Streamlit App",
    "layout": "wide",
    "title": "데이터 전처리 및 DB 적재 웹 애플리케이션",
    "port": 8800
}

# --- Tkinter UI Configuration ---
TKINTER_CONFIG = {
    "title": "DB Table Setup",
    "geometry": "800x600"
}

# --- Data Visualization & Analysis Configuration ---
VISUALIZATION_CONFIG = {
    "top_n_categories": 20,  # For bar charts
    "dataframe_head_rows": 5,  # For df.head() previews
    "unique_values_display_limit": 50  # For displaying unique values list
}
