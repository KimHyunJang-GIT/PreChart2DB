import tkinter as tk
import sys
import os

# 현재 스크립트(Main.py)의 디렉토리 (즉, src 디렉토리)를 Python 경로에 추가합니다.
# 이는 IDE에서 Main.py를 직접 실행할 때 모듈을 올바르게 찾기 위함입니다.
current_script_dir = os.path.dirname(os.path.abspath(__file__))
if current_script_dir not in sys.path:
    sys.path.insert(0, current_script_dir)

# 이제 'src' 디렉토리가 Python 경로에 있으므로, 'UI.tkinter_app'와 같이 절대 경로로 임포트할 수 있습니다.
from UI.tkinter_app import TkinterApp

if __name__ == "__main__":
    root = tk.Tk()
    app = TkinterApp(root)
    root.mainloop()
