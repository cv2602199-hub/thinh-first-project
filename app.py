import json
import queue
import random
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MUSIC_EXTS = {".mp3", ".wav", ".m4a", ".aac"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi"}


@dataclass
class ProcessResult:
    """Kết quả xử lý của một video."""

    video: Path
    output: Path | None
    success: bool
    error: str | None = None


class MusicMergeApp:
    """Ứng dụng desktop ghép nhạc hàng loạt vào video."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Batch Video Music Merger")
        self.root.geometry("920x650")

        # Giá trị từ UI
        self.music_folder = tk.StringVar()
        self.keep_original_audio = tk.BooleanVar(value=True)
        self.music_volume = tk.DoubleVar(value=0.6)
        self.fade_seconds = tk.DoubleVar(value=1.0)
        self.assignment_mode = tk.StringVar(value="unique_random")

        # Trạng thái runtime
        self.video_files: list[Path] = []
        self.results: list[ProcessResult] = []
        self.worker_queue: queue.Queue = queue.Queue()
        self.processing = False

        self._build_ui()
        self._check_ffmpeg_available(show_popup=False)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="1) Chọn thư mục nhạc:").pack(anchor="w")
        music_row = ttk.Frame(frame)
        music_row.pack(fill="x", pady=6)
        ttk.Entry(music_row, textvariable=self.music_folder).pack(side="left", fill="x", expand=True)
        ttk.Button(music_row, text="Browse", command=self._pick_music_folder).pack(side="left", padx=6)

        ttk.Label(frame, text="2) Chọn nhiều video:").pack(anchor="w", pady=(8, 0))
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill="x", pady=6)
        ttk.Button(btn_row, text="Chọn video", command=self._pick_videos).pack(side="left")
        ttk.Button(btn_row, text="Xóa danh sách", command=self._clear_videos).pack(side="left", padx=6)

        self.video_listbox = tk.Listbox(frame, height=9)
        self.video_listbox.pack(fill="both", expand=False, pady=(0, 10))

        mode_group = ttk.LabelFrame(frame, text="3) Chế độ chọn nhạc")
        mode_group.pack(fill="x", pady=6)
        ttk.Radiobutton(
            mode_group,
            text="Random không trùng lặp đến khi hết danh sách",
            variable=self.assignment_mode,
            value="unique_random",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            mode_group,
            text="Random hoàn toàn",
            variable=self.assignment_mode,
            value="full_random",
        ).pack(anchor="w", pady=2)
        ttk.Radiobutton(
            mode_group,
            text="Ghép nhạc theo thứ tự danh sách",
            variable=self.assignment_mode,
            value="ordered",
        ).pack(anchor="w", pady=2)

        audio_group = ttk.LabelFrame(frame, text="4) Âm thanh")
        audio_group.pack(fill="x", pady=6)
        ttk.Checkbutton(audio_group, text="Giữ âm thanh gốc của video", variable=self.keep_original_audio).pack(anchor="w", pady=2)

        volume_row = ttk.Frame(audio_group)
        volume_row.pack(fill="x", pady=2)
        ttk.Label(volume_row, text="Âm lượng nhạc nền (0.0 - 2.0):").pack(side="left")
        ttk.Spinbox(volume_row, from_=0.0, to=2.0, increment=0.1, textvariable=self.music_volume, width=8).pack(side="left", padx=8)

        fade_row = ttk.Frame(audio_group)
        fade_row.pack(fill="x", pady=2)
        ttk.Label(fade_row, text="Fade in/out (giây):").pack(side="left")
        ttk.Spinbox(fade_row, from_=0.0, to=8.0, increment=0.2, textvariable=self.fade_seconds, width=8).pack(side="left", padx=8)

        action_row = ttk.Frame(frame)
        action_row.pack(fill="x", pady=(10, 6))
        ttk.Button(action_row, text="Kiểm tra FFmpeg", command=lambda: self._check_ffmpeg_available(show_popup=True)).pack(side="left")
        self.start_btn = ttk.Button(action_row, text="Bắt đầu ghép", command=self._start_processing)
        self.start_btn.pack(side="left", padx=8)

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(4, 8))

        self.status_label = ttk.Label(frame, text="Sẵn sàng")
        self.status_label.pack(anchor="w")

        ttk.Label(frame, text="Kết quả:").pack(anchor="w", pady=(8, 0))
        self.result_text = tk.Text(frame, height=12)
        self.result_text.pack(fill="both", expand=True)

    def _pick_music_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục nhạc")
        if folder:
            self.music_folder.set(folder)

    def _pick_videos(self):
        files = filedialog.askopenfilenames(
            title="Chọn video",
            filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi")],
        )
        for file in files:
            path = Path(file)
            if path.suffix.lower() in VIDEO_EXTS and path not in self.video_files:
                self.video_files.append(path)
                self.video_listbox.insert(tk.END, str(path))

    def _clear_videos(self):
        self.video_files.clear()
        self.video_listbox.delete(0, tk.END)

    def _check_ffmpeg_available(self, show_popup: bool = True) -> bool:
        has_ffmpeg = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
        if show_popup:
            if has_ffmpeg:
                messagebox.showinfo("FFmpeg", "Đã tìm thấy ffmpeg và ffprobe trong PATH.")
            else:
                messagebox.showerror(
                    "Thiếu FFmpeg",
                    "Không tìm thấy FFmpeg.\n\n"
                    "Cài FFmpeg:\n"
                    "- Windows: tải từ https://ffmpeg.org/download.html rồi thêm vào PATH.\n"
                    "- macOS: brew install ffmpeg\n"
                    "- Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg\n"
                    "Sau đó mở lại tool.",
                )
        return has_ffmpeg

    def _run_json_ffprobe(self, path: Path, entries: str) -> dict:
        """Gọi ffprobe và trả JSON đã parse."""
        cmd = ["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def _get_duration(self, media_path: Path) -> float:
        payload = self._run_json_ffprobe(media_path, "format=duration")
        return float(payload["format"]["duration"])

    def _video_has_audio_stream(self, media_path: Path) -> bool:
        payload = self._run_json_ffprobe(media_path, "stream=codec_type")
        streams = payload.get("streams", [])
        return any(stream.get("codec_type") == "audio" for stream in streams)

    def _collect_music_files(self) -> list[Path]:
        folder = Path(self.music_folder.get())
        if not folder.exists() or not folder.is_dir():
            return []
        return sorted([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in MUSIC_EXTS])

    def _build_output_path(self, video_path: Path) -> Path:
        candidate = video_path.with_name(f"{video_path.stem}_with_music.mp4")
        if not candidate.exists():
            return candidate
        index = 1
        while True:
            new_path = video_path.with_name(f"{video_path.stem}_with_music_{index}.mp4")
            if not new_path.exists():
                return new_path
            index += 1

    def _choose_music_for_videos(self, videos: list[Path], musics: list[Path]) -> list[Path]:
        mode = self.assignment_mode.get()
        if mode == "ordered":
            return [musics[i % len(musics)] for i in range(len(videos))]
        if mode == "full_random":
            return [random.choice(musics) for _ in videos]

        # unique_random: không trùng lặp cho đến khi hết danh sách.
        chosen: list[Path] = []
        pool: list[Path] = []
        for _ in videos:
            if not pool:
                pool = musics.copy()
                random.shuffle(pool)
            chosen.append(pool.pop())
        return chosen

    def _build_filter(self, video_duration: float) -> tuple[str, float, float]:
        """Chuẩn hóa giá trị người dùng nhập và tạo filter âm lượng/fade."""
        fade_sec = max(0.0, min(float(self.fade_seconds.get()), video_duration))
        volume = max(0.0, min(float(self.music_volume.get()), 2.0))
        fade_out_start = max(0.0, video_duration - fade_sec)
        music_filter = f"volume={volume},afade=t=in:st=0:d={fade_sec},afade=t=out:st={fade_out_start}:d={fade_sec}"
        return music_filter, fade_sec, volume

    def _process_one(self, video: Path, music: Path) -> ProcessResult:
        try:
            output = self._build_output_path(video)
            video_duration = self._get_duration(video)
            has_video_audio = self._video_has_audio_stream(video)
            music_filter, _, _ = self._build_filter(video_duration)

            # Nếu người dùng muốn giữ âm gốc nhưng video không có audio stream,
            # fallback sang chỉ dùng nhạc nền để tránh lỗi map/filter.
            use_original_audio = self.keep_original_audio.get() and has_video_audio

            if use_original_audio:
                filter_complex = f"[1:a]{music_filter}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[mix]"
                map_audio = "[mix]"
            else:
                filter_complex = f"[1:a]{music_filter}[mix]"
                map_audio = "[mix]"

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(video),
                "-stream_loop",
                "-1",
                "-i",
                str(music),
                "-filter_complex",
                filter_complex,
                "-map",
                "0:v:0",
                "-map",
                map_audio,
                "-t",
                f"{video_duration}",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-shortest",
                str(output),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return ProcessResult(video=video, output=output, success=True)
        except subprocess.CalledProcessError as exc:
            return ProcessResult(video=video, output=None, success=False, error=exc.stderr.strip()[:1000])
        except Exception as exc:  # noqa: BLE001
            return ProcessResult(video=video, output=None, success=False, error=str(exc))

    def _start_processing(self):
        if self.processing:
            return
        if not self._check_ffmpeg_available(show_popup=False):
            self._check_ffmpeg_available(show_popup=True)
            return
        if not self.video_files:
            messagebox.showwarning("Thiếu video", "Vui lòng chọn ít nhất một video.")
            return

        music_files = self._collect_music_files()
        if not music_files:
            messagebox.showwarning("Thiếu nhạc", "Không tìm thấy file nhạc hợp lệ trong thư mục đã chọn.")
            return

        self.results.clear()
        self.result_text.delete("1.0", tk.END)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.video_files)
        self.start_btn.config(state="disabled")
        self.processing = True

        assignments = self._choose_music_for_videos(self.video_files, music_files)

        thread = threading.Thread(target=self._worker, args=(self.video_files.copy(), assignments), daemon=True)
        thread.start()
        self.root.after(200, self._poll_queue)

    def _worker(self, videos: list[Path], musics: list[Path]):
        for index, (video, music) in enumerate(zip(videos, musics), start=1):
            self.worker_queue.put(("status", f"Đang xử lý {index}/{len(videos)}: {video.name} | Nhạc: {music.name}"))
            result = self._process_one(video, music)
            self.worker_queue.put(("result", result))
        self.worker_queue.put(("done", None))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.worker_queue.get_nowait()
                if kind == "status":
                    self.status_label.config(text=data)
                elif kind == "result":
                    self.results.append(data)
                    self.progress["value"] = len(self.results)
                elif kind == "done":
                    self._on_finished()
                    return
        except queue.Empty:
            pass

        if self.processing:
            self.root.after(200, self._poll_queue)

    def _on_finished(self):
        self.processing = False
        self.start_btn.config(state="normal")

        success = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]

        self.status_label.config(text=f"Hoàn tất. Thành công: {len(success)} | Lỗi: {len(failed)}")

        self.result_text.insert(tk.END, "=== VIDEO XUẤT THÀNH CÔNG ===\n")
        for item in success:
            self.result_text.insert(tk.END, f"✓ {item.video.name} -> {item.output}\n")

        self.result_text.insert(tk.END, "\n=== VIDEO LỖI ===\n")
        for item in failed:
            self.result_text.insert(tk.END, f"✗ {item.video.name}: {item.error}\n")


def main():
    root = tk.Tk()
    MusicMergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
