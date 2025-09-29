import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import datetime
import io
import pandas as pd

from core.config import DB_CONFIG, TKINTER_CONFIG, APP_CONFIG, VISUALIZATION_CONFIG
from core.database_manager import DatabaseManager
from core.data_importer import DataImporter

class TkinterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(TKINTER_CONFIG['title'])
        self.root.geometry(TKINTER_CONFIG['geometry'])

        # --- Style Configuration (Comprehensive Fix) ---
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

        default_bg = style.lookup("TFrame", "background")
        default_fg = style.lookup("TLabel", "foreground")

        style.configure("Treeview", background=default_bg, fieldbackground=default_bg, foreground=default_fg)
        style.map("Treeview",
                  background=[('selected', default_bg)],
                  foreground=[('selected', default_fg)])

        self.db_manager = DatabaseManager(db_config=DB_CONFIG, status_callback=self.update_status)
        self.data_importer = DataImporter(status_callback=self.update_status)
        self.current_df = None
        self.na_columns = []

        # --- UI Frames ---
        self.path_frame = tk.LabelFrame(root, text="파일 경로 설정")
        self.path_frame.pack(pady=10, padx=10, fill="x")
        self.path_label = tk.Label(self.path_frame, text="선택된 파일:")
        self.path_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.file_path_entry = tk.Entry(self.path_frame, width=50)
        self.file_path_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")
        # Removed Enter key binding from root
        self.browse_button = tk.Button(self.path_frame, text="파일 오픈", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.db_frame = tk.LabelFrame(root, text="데이터베이스 작업")
        self.db_frame.pack(pady=10, padx=10, fill="x")
        self.setup_db_button = tk.Button(self.db_frame, text="DB 테이블 셋팅 시작", command=self.start_db_setup)
        self.setup_db_button.pack(side=tk.LEFT, pady=10, padx=10)

        self.analysis_frame = tk.LabelFrame(root, text="데이터 분석 및 시각화")
        self.analysis_frame.pack(pady=10, padx=10, fill="x")

        self.column_label = tk.Label(self.analysis_frame, text="컬럼 선택:")
        self.column_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.column_selector = ttk.Combobox(self.analysis_frame, state="readonly", width=30)
        self.column_selector.pack(side=tk.LEFT, padx=5, pady=5)
        self.column_selector.bind("<<ComboboxSelected>>", self._on_column_selected)

        self.generate_chart_button = tk.Button(self.analysis_frame, text="컬럼 분석", command=self._generate_charts)
        self.generate_chart_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.edit_preview_frame = tk.LabelFrame(root, text="데이터 편집 및 미리보기")
        self.edit_preview_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.data_tree = ttk.Treeview(self.edit_preview_frame, show="headings")
        treescrolly = tk.Scrollbar(self.edit_preview_frame, orient="vertical", command=self.data_tree.yview)
        treescrollx = tk.Scrollbar(self.edit_preview_frame, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(xscrollcommand=treescrollx.set, yscrollcommand=treescrolly.set)
        treescrollx.pack(side="bottom", fill="x")
        treescrolly.pack(side="right", fill="y")
        self.data_tree.pack(side="left", fill="both", expand=True)
        self.data_tree.bind("<Double-1>", self._on_treeview_double_click)
        self.data_tree.bind("<<TreeviewSelect>>", self._clear_tree_selection)

        self.na_columns_frame = tk.LabelFrame(root, text="NA 값 포함 컬럼 (여기서만 수정 가능)")
        self.na_columns_frame.pack(pady=10, padx=10, fill="x")
        self.na_columns_text = tk.Text(self.na_columns_frame, wrap="word", state="disabled", height=4, takefocus=0)
        self.na_columns_text.config(selectbackground=default_bg, inactiveselectbackground=default_bg, selectforeground=self.na_columns_text.cget("foreground"))
        self.na_columns_text.bind("<Button-1>", lambda e: "break")
        self.na_columns_text.bind("<B1-Motion>", lambda e: "break")
        self.na_columns_text.pack(side="left", fill="both", expand=True)
        na_scrollbar = tk.Scrollbar(self.na_columns_frame, command=self.na_columns_text.yview)
        na_scrollbar.pack(side="right", fill="y")
        self.na_columns_text.config(yscrollcommand=na_scrollbar.set)

        self.status_label = tk.Label(root, text="상태: 대기 중...", fg="blue")
        self.status_label.pack(pady=5)

        self.log_frame = tk.LabelFrame(root, text="작업 상세 로그")
        self.log_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.log_text = tk.Text(self.log_frame, wrap="word", state="disabled", height=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        self.log_scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        self.log_scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=self.log_scrollbar.set)

        self.update_status("애플리케이션 시작됨.")

    def _clear_tree_selection(self, event):
        if self.data_tree.selection():
            self.data_tree.selection_remove(self.data_tree.selection())

    def _populate_data_preview(self, df):
        for i in self.data_tree.get_children():
            self.data_tree.delete(i)
        self.data_tree["columns"] = []
        if df is None: return

        self.data_tree["columns"] = df.columns.tolist()
        for col in df.columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=100, anchor='w')

        for index, row in df.iterrows():
            self.data_tree.insert("", "end", iid=index, values=[str(v) for v in row])

    def _on_treeview_double_click(self, event):
        region = self.data_tree.identify_region(event.x, event.y)
        if region != "cell": return

        column_id = self.data_tree.identify_column(event.x)
        column_name = self.data_tree.heading(column_id)['text']

        if column_name not in self.na_columns:
            self.update_status(f"'{column_name}' 컬럼은 NA값이 없어 편집할 수 없습니다.")
            return

        item_id = self.data_tree.identify_row(event.y)
        row_index = self.data_tree.index(item_id)
        column_index = int(column_id.replace('#', '')) - 1

        x, y, width, height = self.data_tree.bbox(item_id, column_id)
        entry_var = tk.StringVar(value=self.data_tree.item(item_id, "values")[column_index])
        entry = ttk.Entry(self.data_tree, textvariable=entry_var)
        entry.place(x=x, y=y, width=width, height=height)
        entry.focus_set()

        def save_edit(e):
            self._save_cell_value(e.widget, row_index, column_name, item_id)

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", lambda e: e.widget.destroy())

    def _save_cell_value(self, entry_widget, row_index, column_name, item_id):
        new_value_str = entry_widget.get()
        entry_widget.destroy()

        try:
            original_dtype = self.current_df[column_name].dtype
            if new_value_str == '' or new_value_str.upper() == 'NA' or new_value_str.upper() == 'NAN':
                new_value = pd.NA
            elif pd.api.types.is_numeric_dtype(original_dtype):
                new_value = pd.to_numeric(new_value_str)
            else:
                new_value = new_value_str

            self.current_df.loc[row_index, column_name] = new_value
            self.update_status(f"데이터 업데이트: 행 {row_index}, 열 '{column_name}' -> '{new_value}'")
            self._populate_data_preview(self.current_df)
            self._update_na_columns_display(self.current_df)

        except (ValueError, TypeError) as e:
            self.update_status(f"값 오류: '{new_value_str}'는 '{column_name}' 컬럼의 올바른 타입이 아닙니다. ({e})")
            self._populate_data_preview(self.current_df)

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_entry.delete(0, tk.END)
            self.file_path_entry.insert(0, file_path)
            self.update_status(f"파일 선택됨: {file_path}")
            self.current_df = None
            self.column_selector['values'] = []
            self.column_selector.set('')
            self._update_na_columns_display(None)
            self._populate_data_preview(None)
        else:
            self.update_status("파일 선택 취소됨.")

    def _update_column_selector(self, df):
        if df is not None:
            self.column_selector['values'] = df.columns.tolist()
            if not df.columns.empty: self.column_selector.set(df.columns[0])
        else:
            self.column_selector['values'] = []
            self.column_selector.set('')

    def _update_na_columns_display(self, df):
        self.na_columns_text.config(state="normal")
        self.na_columns_text.delete(1.0, tk.END)
        if df is not None:
            self.na_columns = df.columns[df.isna().any()].tolist()
            if self.na_columns:
                self.na_columns_text.insert(tk.END, "\n".join(self.na_columns))
            else:
                self.na_columns_text.insert(tk.END, "결측치(NA)를 포함하는 컬럼이 없습니다.")
        else:
            self.na_columns = []
        self.na_columns_text.config(state="disabled")

    def _on_column_selected(self, event):
        self.update_status(f"컬럼 '{self.column_selector.get()}' 선택됨.")

    def _display_dataframe_head(self, df):
        self.update_status(f"\n--- 데이터프레임 미리보기 (상위 {VISUALIZATION_CONFIG['dataframe_head_rows']}행) ---\n{df.head(VISUALIZATION_CONFIG['dataframe_head_rows']).to_string()}")

    def _display_dataframe_description(self, df):
        buffer = io.StringIO()
        df.info(buf=buffer)
        self.update_status(f"\n--- 데이터프레임 정보 (df.info()) ---\n{buffer.getvalue()}")
        self.update_status(f"\n--- 데이터프레임 기술 통계 (df.describe()) ---\n{df.describe().to_string()}")

    def _generate_charts(self):
        if self.current_df is None: return messagebox.showwarning("경고", "먼저 파일을 로드해주세요.")
        selected_column = self.column_selector.get()
        if not selected_column: return messagebox.showwarning("경고", "분석할 컬럼을 선택해주세요.")

        df_column = self.current_df[selected_column]
        self.update_status(f"\n--- 컬럼 '{selected_column}' 분석 시작 ---")
        self.update_status(f"결측치(NA) 개수: {df_column.isnull().sum()}개")
        self.update_status(f"\n--- 값 빈도수 ---\n{df_column.value_counts(dropna=False).to_string()}")
        self.update_status(f"\n--- 기술 통계 ---\n")
        try: self.update_status(df_column.describe(include='all').to_string())
        except Exception as e: self.update_status(f"기술 통계 생성 중 오류: {e}")
        self.update_status(f"\n--- 고유 값 목록 (상위 {VISUALIZATION_CONFIG['unique_values_display_limit']}개) ---")
        unique_values = df_column.unique()
        display_limit = VISUALIZATION_CONFIG['unique_values_display_limit']
        self.update_status(f"고유 값 개수: {len(unique_values)}")
        self.update_status(f"고유 값: {unique_values[:display_limit].tolist()}")
        self.update_status(f"--- 컬럼 '{selected_column}' 분석 완료 ---\n")

    def start_db_setup(self, event=None):
        file_path = self.file_path_entry.get()
        if not file_path:
            messagebox.showwarning("경고", "먼저 파일을 선택해주세요.")
            return

        self.update_status(f"DB 셋팅 시작: {file_path}")
        try:
            self.update_status("데이터 로딩을 시작합니다...")
            df = self.data_importer.load_data(file_path)

            if df is None:
                messagebox.showerror("오류", "파일을 읽는 데 실패했습니다. 작업 상세 로그를 확인해주세요.")
                return

            self.update_status("데이터 로딩 성공. 데이터프레임이 생성되었습니다.")
            self.current_df = df
            self._update_column_selector(df)
            self._update_na_columns_display(df)
            self._populate_data_preview(df)
            self._display_dataframe_head(df)
            self._display_dataframe_description(df)

            file_name_without_ext = os.path.splitext(os.path.basename(file_path))[0]

            self.update_status("데이터베이스 연결 및 테이블 덮어쓰기 시도 중...")
            success, message = self.db_manager.overwrite_table(df, file_name_without_ext)
            self.update_status(f"DB Manager 응답: Success={success}, Message={message}")

            if success:
                self.update_status(f"DB 작업 완료: {message}")
                messagebox.showinfo("작업 완료", message)
            else:
                self.update_status(f"DB 작업 실패: {message}")
                messagebox.showerror("오류", message)

        except Exception as e:
            self.update_status(f"CRITICAL: start_db_setup에서 예상치 못한 예외 발생: {e}")
            messagebox.showerror("심각한 오류", f"처리 중 예상치 못한 오류가 발생했습니다:\n{e}")

    def update_status(self, message):
        log_entry = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n"
        self.status_label.config(text=f"상태: {message.splitlines()[0]}")
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        print(log_entry.strip())
