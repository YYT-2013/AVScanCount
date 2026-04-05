import os
import queue
import shutil
import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from core.comparer import CompareResult, compare_snapshots
from core.extractor import prepare_target
from core.hasher import HashAlgo
from core.scanner import build_snapshot
from report.csv_export import export_compare_records_csv
from report.image_report import generate_png_report


I18N = {
    "zh": {
        "title": "杀毒软件查杀统计工具 (Tk)",
        "sample_path": "样本路径",
        "browse": "浏览",
        "extract_root": "解压根目录(可选)",
        "password": "解压密码",
        "av_name": "杀毒软件名称",
        "hash": "Hash算法",
        "lang": "界面语言",
        "icon_path": "报告图标(可选)",
        "delete_after": "检测完成后删除解压目录(仅压缩包)",
        "start": "开始检测",
        "finish": "检测完成",
        "csv": "导出CSV",
        "report": "生成图片报告",
        "logs": "日志输出",
        "choose_icon": "选择图标",
        "choose_extract_root": "选择解压目录",
        "warn_path": "请先选择样本路径。",
        "warn_missing": "路径不存在，请重新选择。",
        "done": "完成",
        "done_msg": "差分检测完成，可导出 CSV 或生成图片报告。",
        "stats_title": "=== 统计结果 ===",
        "stats_total": "样本总数",
        "stats_removed": "查杀数量",
        "stats_remaining": "剩余数量",
        "stats_rate": "查杀率",
        "hint_scan": "请手动运行杀毒软件扫描，完成后点击【检测完成】。",
    },
    "en": {
        "title": "AV Scan Compare Tool (Tk)",
        "sample_path": "Sample Path",
        "browse": "Browse",
        "extract_root": "Extract Root (Optional)",
        "password": "Archive Password",
        "av_name": "Antivirus Name",
        "hash": "Hash Algorithm",
        "lang": "Language",
        "icon_path": "Report Icon (Optional)",
        "delete_after": "Delete extracted folder after finish (archive only)",
        "start": "Start",
        "finish": "Finish",
        "csv": "Export CSV",
        "report": "Generate Report",
        "logs": "Logs",
        "choose_icon": "Choose Icon",
        "choose_extract_root": "Choose Extract Folder",
        "warn_path": "Please choose sample path first.",
        "warn_missing": "Path not found, please choose again.",
        "done": "Done",
        "done_msg": "Compare completed. You can export CSV or report image now.",
        "stats_title": "=== Statistics ===",
        "stats_total": "Sample Total",
        "stats_removed": "Removed",
        "stats_remaining": "Remaining",
        "stats_rate": "Removed Rate",
        "hint_scan": "Run antivirus scan manually, then click [Finish].",
    },
}


class App:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.geometry("980x760")

        self.lang_var = StringVar(value="zh")
        self.path_var = StringVar()
        self.extract_root_var = StringVar()
        self.password_var = StringVar(value="infected")
        self.av_name_var = StringVar()
        self.hash_var = StringVar(value="md5")
        self.icon_var = StringVar()
        self.delete_after_var = BooleanVar(value=False)

        self.before_snapshot: dict[str, dict[str, str]] = {}
        self.compare_result: CompareResult | None = None
        self.target_dir: Path | None = None
        self.extracted_dir: Path | None = None

        self.work_queue: queue.Queue[tuple] = queue.Queue()
        self.busy = False

        self._build_ui()
        self._apply_language()
        self.root.after(80, self._process_queue)

    def t(self, key: str) -> str:
        return I18N[self.lang_var.get()][key]

    def _build_ui(self) -> None:
        self.main = ttk.Frame(self.root, padding=10)
        self.main.pack(fill="both", expand=True)

        for i in range(3):
            self.main.columnconfigure(i, weight=1 if i == 1 else 0)

        row = 0
        self.lbl_sample = ttk.Label(self.main)
        self.lbl_sample.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.main, textvariable=self.path_var).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        ttk.Button(self.main, text="", command=self._choose_source).grid(row=row, column=2, sticky="ew", padx=4, pady=4)

        row += 1
        self.lbl_extract = ttk.Label(self.main)
        self.lbl_extract.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.main, textvariable=self.extract_root_var).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.btn_extract = ttk.Button(self.main, command=self._choose_extract_root)
        self.btn_extract.grid(row=row, column=2, sticky="ew", padx=4, pady=4)

        row += 1
        self.lbl_pwd = ttk.Label(self.main)
        self.lbl_pwd.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.main, textvariable=self.password_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=4)

        row += 1
        self.lbl_av = ttk.Label(self.main)
        self.lbl_av.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.main, textvariable=self.av_name_var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=4)

        row += 1
        self.lbl_hash = ttk.Label(self.main)
        self.lbl_hash.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Combobox(self.main, textvariable=self.hash_var, values=["md5", "sha1", "sha256"], state="readonly").grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=4, pady=4
        )

        row += 1
        self.lbl_lang = ttk.Label(self.main)
        self.lbl_lang.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        lang_cb = ttk.Combobox(self.main, textvariable=self.lang_var, values=["zh", "en"], state="readonly")
        lang_cb.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        lang_cb.bind("<<ComboboxSelected>>", lambda _: self._apply_language())

        row += 1
        self.lbl_icon = ttk.Label(self.main)
        self.lbl_icon.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ttk.Entry(self.main, textvariable=self.icon_var).grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        self.btn_icon = ttk.Button(self.main, command=self._choose_icon)
        self.btn_icon.grid(row=row, column=2, sticky="ew", padx=4, pady=4)

        row += 1
        self.chk_delete = ttk.Checkbutton(self.main, variable=self.delete_after_var)
        self.chk_delete.grid(row=row, column=0, columnspan=3, sticky="w", padx=4, pady=4)

        row += 1
        self.progress = ttk.Progressbar(self.main, maximum=100, mode="determinate")
        self.progress.grid(row=row, column=0, columnspan=3, sticky="ew", padx=4, pady=8)

        row += 1
        btn_row = ttk.Frame(self.main)
        btn_row.grid(row=row, column=0, columnspan=3, sticky="ew")
        btn_row.columnconfigure((0, 1, 2, 3), weight=1)

        self.btn_start = ttk.Button(btn_row, command=self.start_detection)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        self.btn_finish = ttk.Button(btn_row, command=self.finish_detection, state="disabled")
        self.btn_finish.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self.btn_csv = ttk.Button(btn_row, command=self.export_csv, state="disabled")
        self.btn_csv.grid(row=0, column=2, sticky="ew", padx=4, pady=4)
        self.btn_report = ttk.Button(btn_row, command=self.export_report, state="disabled")
        self.btn_report.grid(row=0, column=3, sticky="ew", padx=4, pady=4)

        row += 1
        self.lbl_logs = ttk.Label(self.main)
        self.lbl_logs.grid(row=row, column=0, columnspan=3, sticky="w", padx=4, pady=(8, 4))

        row += 1
        self.log_box = ScrolledText(self.main, height=18)
        self.log_box.grid(row=row, column=0, columnspan=3, sticky="nsew", padx=4, pady=4)
        self.main.rowconfigure(row, weight=1)

    def _apply_language(self) -> None:
        self.root.title(self.t("title"))
        self.lbl_sample.configure(text=self.t("sample_path"))
        self.lbl_extract.configure(text=self.t("extract_root"))
        self.lbl_pwd.configure(text=self.t("password"))
        self.lbl_av.configure(text=self.t("av_name"))
        self.lbl_hash.configure(text=self.t("hash"))
        self.lbl_lang.configure(text=self.t("lang"))
        self.lbl_icon.configure(text=self.t("icon_path"))
        self.chk_delete.configure(text=self.t("delete_after"))
        self.lbl_logs.configure(text=self.t("logs"))
        self.btn_extract.configure(text=self.t("choose_extract_root"))
        self.btn_icon.configure(text=self.t("choose_icon"))
        self.btn_start.configure(text=self.t("start"))
        self.btn_finish.configure(text=self.t("finish"))
        self.btn_csv.configure(text=self.t("csv"))
        self.btn_report.configure(text=self.t("report"))

        # first browse button is the third widget in row 0, col 2
        browse_button = self.main.grid_slaves(row=0, column=2)[0]
        browse_button.configure(text=self.t("browse"))

    def _log(self, text: str) -> None:
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")

    def _set_progress(self, current: int, total: int, prefix: str) -> None:
        pct = 0 if total <= 0 else int(current * 100 / total)
        self.progress["value"] = pct
        self._log(f"{prefix} [{current}/{total}] {pct}%")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.btn_start.configure(state="disabled" if busy else "normal")
        self.btn_finish.configure(state="disabled" if busy or self.target_dir is None else "normal")

    def _choose_source(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Archive Files", "*.zip *.rar *.7z"), ("All Files", "*.*")]
        )
        if file_path:
            self.path_var.set(file_path)
            return
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.path_var.set(folder_path)

    def _choose_extract_root(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.extract_root_var.set(path)

    def _choose_icon(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.ico"), ("All", "*.*")])
        if path:
            self.icon_var.set(path)

    def start_detection(self) -> None:
        if self.busy:
            return
        source_text = self.path_var.get().strip()
        if not source_text:
            messagebox.showwarning("Warning", self.t("warn_path"))
            return
        source_path = Path(source_text)
        if not source_path.exists():
            messagebox.showwarning("Warning", self.t("warn_missing"))
            return

        self.before_snapshot.clear()
        self.compare_result = None
        self.target_dir = None
        self.extracted_dir = None
        self.progress["value"] = 0
        self.btn_csv.configure(state="disabled")
        self.btn_report.configure(state="disabled")
        self.btn_finish.configure(state="disabled")
        self._set_busy(True)

        password = self.password_var.get().strip() or None
        av_name = self.av_name_var.get().strip()
        hash_algo: HashAlgo = self.hash_var.get()  # type: ignore
        extract_root = Path(self.extract_root_var.get().strip()) if self.extract_root_var.get().strip() else None

        def worker():
            try:
                self.work_queue.put(("log", "准备样本路径..." if self.lang_var.get() == "zh" else "Preparing target..."))
                target_dir, extracted_dir = prepare_target(
                    source_path=source_path,
                    password=password,
                    antivirus_name=av_name,
                    extract_root=extract_root,
                    progress_callback=lambda c, t, n: self.work_queue.put(("progress", c, t, f"解压中: {n}" if self.lang_var.get() == "zh" else f"Extracting: {n}")),
                )
                before_snapshot = build_snapshot(
                    root_dir=target_dir,
                    algorithm=hash_algo,
                    progress_callback=lambda c, t, r: self.work_queue.put(("progress", c, t, f"Hash计算: {r}" if self.lang_var.get() == "zh" else f"Hashing: {r}")),
                )
                self.work_queue.put(("start_done", before_snapshot, target_dir, extracted_dir))
            except Exception as e:
                self.work_queue.put(("error", f"开始检测失败：{e}" if self.lang_var.get() == "zh" else f"Start failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def finish_detection(self) -> None:
        if self.busy or not self.target_dir:
            return
        self._set_busy(True)
        self.progress["value"] = 0
        hash_algo: HashAlgo = self.hash_var.get()  # type: ignore

        def worker():
            try:
                after_snapshot = build_snapshot(
                    root_dir=self.target_dir,
                    algorithm=hash_algo,
                    progress_callback=lambda c, t, r: self.work_queue.put(("progress", c, t, f"扫描后Hash: {r}" if self.lang_var.get() == "zh" else f"Post-scan hash: {r}")),
                )
                result = compare_snapshots(self.before_snapshot, after_snapshot)
                self.work_queue.put(("finish_done", result))
            except Exception as e:
                self.work_queue.put(("error", f"检测完成失败：{e}" if self.lang_var.get() == "zh" else f"Finish failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def export_csv(self) -> None:
        if not self.compare_result:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        export_compare_records_csv(Path(path), self.av_name_var.get().strip(), self.compare_result.records)
        self._log(f"CSV -> {path}")

    def export_report(self) -> None:
        if not self.compare_result:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        report_path = generate_png_report(
            output_path=Path(path),
            antivirus_name=self.av_name_var.get().strip(),
            total=self.compare_result.total,
            removed=self.compare_result.removed,
            remaining=self.compare_result.remaining,
            removed_rate=self.compare_result.removed_rate,
            language=self.lang_var.get(),
            icon_path=Path(self.icon_var.get()) if self.icon_var.get().strip() else None,
        )
        self._log(f"Report -> {report_path}")
        try:
            os.startfile(str(report_path))  # type: ignore[attr-defined]
        except Exception:
            pass

    def _process_queue(self) -> None:
        try:
            while True:
                item = self.work_queue.get_nowait()
                kind = item[0]
                if kind == "log":
                    self._log(item[1])
                elif kind == "progress":
                    _, cur, total, msg = item
                    self._set_progress(cur, total, msg)
                elif kind == "start_done":
                    _, before_snapshot, target_dir, extracted_dir = item
                    self.before_snapshot = before_snapshot
                    self.target_dir = target_dir
                    self.extracted_dir = extracted_dir
                    self.progress["value"] = 100
                    self.btn_finish.configure(state="normal")
                    self._log(self.t("hint_scan"))
                    self._set_busy(False)
                elif kind == "finish_done":
                    self.compare_result = item[1]
                    r = self.compare_result
                    self._log(self.t("stats_title"))
                    self._log(f"{self.t('stats_total')}: {r.total}")
                    self._log(f"{self.t('stats_removed')}: {r.removed}")
                    self._log(f"{self.t('stats_remaining')}: {r.remaining}")
                    self._log(f"{self.t('stats_rate')}: {r.removed_rate:.2f}%")

                    if self.delete_after_var.get() and self.extracted_dir and self.extracted_dir.exists():
                        shutil.rmtree(self.extracted_dir, ignore_errors=True)
                        self._log(f"Deleted extracted folder: {self.extracted_dir}")
                        self.extracted_dir = None

                    self.btn_csv.configure(state="normal")
                    self.btn_report.configure(state="normal")
                    self._set_busy(False)
                    messagebox.showinfo(self.t("done"), self.t("done_msg"))
                elif kind == "error":
                    messagebox.showerror("Error", item[1])
                    self._set_busy(False)
        except queue.Empty:
            pass
        self.root.after(80, self._process_queue)


def run() -> None:
    app = App()
    app.root.mainloop()
