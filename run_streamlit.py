import subprocess
import sys
import os

# src 디렉토리를 Python 경로에 추가하여 core 모듈을 찾을 수 있도록 합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 이제 src가 경로에 있으므로 core.config를 임포트할 수 있습니다.
from core.config import STREAMLIT_CONFIG

# Streamlit 앱 파일의 절대 경로
streamlit_app_path = os.path.join(src_dir, "UI", "streamlit_app.py")

def main():
    port = STREAMLIT_CONFIG['port']
    print(f"Streamlit 앱 실행 중: {streamlit_app_path} (포트: {port})")
    try:
        # 'streamlit' 명령어를 실행하고 --server.port 인자를 추가합니다.
        subprocess.run([
            sys.executable, 
            "-m", 
            "streamlit", 
            "run", 
            streamlit_app_path, 
            "--server.port", 
            str(port)
        ], check=True)
    except FileNotFoundError:
        print("오류: 'streamlit' 명령어를 찾을 수 없습니다. Streamlit이 설치되어 있고 PATH에 추가되었는지 확인하세요.")
        print("설치: pip install streamlit")
    except subprocess.CalledProcessError as e:
        print(f"Streamlit 앱 실행 중 오류 발생: {e}")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")

if __name__ == "__main__":
    main()
