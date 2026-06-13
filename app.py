import json
import math
import queue
import random
import shutil
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

MUSIC_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi"}


@dataclass
class ProcessResult:
    video: Path
    output: Path | None
    success: bool
    playlist_txt: Path | None = None
    error: str | None = None


class MusicMergeApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Batch Video Music Playlist Merger")
        self.root.geometry("980x760")

        self.music_folder = tk.StringVar()
        self.keep_original_audio = tk.BooleanVar(value=True)
        self.music_volume = tk.DoubleVar(value=0.6)
        self.fade_seconds = tk.DoubleVar(value=1.0)
        self.assignment_mode = tk.StringVar(value="unique_random")

        self.songs_per_video = tk.IntVar(value=30)
        self.target_hours = tk.IntVar(value=0)
        self.target_minutes = tk.IntVar(value=0)
        self.loop_video_to_playlist = tk.BooleanVar(value=True)
        self.cut_video_if_longer = tk.BooleanVar(value=True)
        self.export_playlist_txt = tk.BooleanVar(value=True)
        self.normalize_audio_44k = tk.BooleanVar(value=True)
        self.use_priority_list = tk.BooleanVar(value=True)
        self.priority_song_count = tk.IntVar(value=30)
        self.priority_mode = tk.StringVar(value="unique_random")
        self.priority_total_label = tk.StringVar(value="Tổng số bài ưu tiên: 0")

        self.video_files: list[Path] = []
        self.priority_files: list[Path] = []
        self.results: list[ProcessResult] = []
        self.worker_queue: queue.Queue = queue.Queue()
        self.processing = False

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="1) Chọn thư mục nhạc:").pack(anchor="w")
        row = ttk.Frame(frame); row.pack(fill="x", pady=4)
        ttk.Entry(row, textvariable=self.music_folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Browse", command=self._pick_music_folder).pack(side="left", padx=6)

        ttk.Label(frame, text="2) Chọn nhiều video:").pack(anchor="w", pady=(6, 0))
        row = ttk.Frame(frame); row.pack(fill="x", pady=4)
        ttk.Button(row, text="Chọn video", command=self._pick_videos).pack(side="left")
        ttk.Button(row, text="Xóa danh sách", command=self._clear_videos).pack(side="left", padx=6)
        self.video_listbox = tk.Listbox(frame, height=7)
        self.video_listbox.pack(fill="both", pady=(0, 8))

        mode_group = ttk.LabelFrame(frame, text="3) Chế độ chọn nhạc")
        mode_group.pack(fill="x", pady=6)
        ttk.Radiobutton(mode_group, text="Random không trùng lặp", variable=self.assignment_mode, value="unique_random").pack(anchor="w")
        ttk.Radiobutton(mode_group, text="Random hoàn toàn", variable=self.assignment_mode, value="full_random").pack(anchor="w")
        ttk.Radiobutton(mode_group, text="Theo thứ tự danh sách", variable=self.assignment_mode, value="ordered").pack(anchor="w")

        priority_group = ttk.LabelFrame(frame, text="4) Danh sách ưu tiên")
        priority_group.pack(fill="x", pady=6)
        ttk.Checkbutton(priority_group, text="Ưu tiên danh sách yêu thích", variable=self.use_priority_list).pack(anchor="w")

        priority_count_row = ttk.Frame(priority_group); priority_count_row.pack(fill="x", pady=2)
        ttk.Label(priority_count_row, text="Số bài lấy từ danh sách ưu tiên:").pack(side="left")
        ttk.Spinbox(priority_count_row, from_=0, to=9999, textvariable=self.priority_song_count, width=8).pack(side="left", padx=8)
        ttk.Label(priority_count_row, textvariable=self.priority_total_label).pack(side="left", padx=8)

        priority_mode_row = ttk.Frame(priority_group); priority_mode_row.pack(fill="x", pady=2)
        ttk.Label(priority_mode_row, text="Chế độ ưu tiên:").pack(side="left")
        ttk.Radiobutton(priority_mode_row, text="Random không trùng", variable=self.priority_mode, value="unique_random").pack(side="left", padx=4)
        ttk.Radiobutton(priority_mode_row, text="Random hoàn toàn", variable=self.priority_mode, value="full_random").pack(side="left", padx=4)
        ttk.Radiobutton(priority_mode_row, text="Theo thứ tự", variable=self.priority_mode, value="ordered").pack(side="left", padx=4)

        priority_buttons = ttk.Frame(priority_group); priority_buttons.pack(fill="x", pady=2)
        ttk.Button(priority_buttons, text="Thêm bài hát ưu tiên", command=self._add_priority_songs).pack(side="left")
        ttk.Button(priority_buttons, text="Xóa khỏi danh sách ưu tiên", command=self._remove_priority_songs).pack(side="left", padx=6)
        ttk.Button(priority_buttons, text="Random danh sách ưu tiên", command=self._shuffle_priority_songs).pack(side="left")
        self.priority_listbox = tk.Listbox(priority_group, height=4, selectmode=tk.EXTENDED)
        self.priority_listbox.pack(fill="x", pady=(2, 0))

        cfg = ttk.LabelFrame(frame, text="5) Cấu hình playlist/video")
        cfg.pack(fill="x", pady=6)

        row = ttk.Frame(cfg); row.pack(fill="x", pady=2)
        ttk.Label(row, text="Số bài hát cho mỗi video:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=9999, textvariable=self.songs_per_video, width=8).pack(side="left", padx=8)

        row = ttk.Frame(cfg); row.pack(fill="x", pady=2)
        ttk.Label(row, text="Thời lượng mục tiêu: Giờ").pack(side="left")
        ttk.Spinbox(row, from_=0, to=24, textvariable=self.target_hours, width=5).pack(side="left", padx=4)
        ttk.Label(row, text="Phút").pack(side="left")
        ttk.Spinbox(row, from_=0, to=59, textvariable=self.target_minutes, width=5).pack(side="left", padx=4)

        ttk.Checkbutton(cfg, text="Loop video để khớp thời lượng playlist nhạc", variable=self.loop_video_to_playlist).pack(anchor="w")
        ttk.Checkbutton(cfg, text="Nếu video dài hơn playlist thì cắt video theo playlist", variable=self.cut_video_if_longer).pack(anchor="w")
        ttk.Checkbutton(cfg, text="Xuất file TXT playlist", variable=self.export_playlist_txt).pack(anchor="w")
        ttk.Checkbutton(cfg, text="Chuẩn hóa audio về 44100 Hz (stereo)", variable=self.normalize_audio_44k).pack(anchor="w")

        audio = ttk.LabelFrame(frame, text="6) Âm thanh")
        audio.pack(fill="x", pady=6)
        ttk.Checkbutton(audio, text="Giữ âm thanh gốc của video", variable=self.keep_original_audio).pack(anchor="w")
        row = ttk.Frame(audio); row.pack(fill="x", pady=2)
        ttk.Label(row, text="Âm lượng nhạc nền (0.0 - 2.0):").pack(side="left")
        ttk.Spinbox(row, from_=0.0, to=2.0, increment=0.1, textvariable=self.music_volume, width=8).pack(side="left", padx=8)
        row = ttk.Frame(audio); row.pack(fill="x", pady=2)
        ttk.Label(row, text="Fade in/out (giây):").pack(side="left")
        ttk.Spinbox(row, from_=0.0, to=8.0, increment=0.2, textvariable=self.fade_seconds, width=8).pack(side="left", padx=8)

        row = ttk.Frame(frame); row.pack(fill="x", pady=6)
        ttk.Button(row, text="Kiểm tra FFmpeg", command=lambda: self._check_ffmpeg_available(True)).pack(side="left")
        self.start_btn = ttk.Button(row, text="Bắt đầu ghép playlist", command=self._start_processing)
        self.start_btn.pack(side="left", padx=8)

        self.progress = ttk.Progressbar(frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(4, 8))
        self.status_label = ttk.Label(frame, text="Sẵn sàng")
        self.status_label.pack(anchor="w")

        ttk.Label(frame, text="Log / Kết quả:").pack(anchor="w", pady=(6, 0))
        self.result_text = tk.Text(frame, height=12)
        self.result_text.pack(fill="both", expand=True)

    def _append_log(self, text: str):
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)

    def _pick_music_folder(self):
        folder = filedialog.askdirectory(title="Chọn thư mục nhạc")
        if folder:
            self.music_folder.set(folder)

    def _pick_videos(self):
        files = filedialog.askopenfilenames(title="Chọn video", filetypes=[("Video files", "*.mp4 *.mov *.mkv *.avi")])
        for file in files:
            path = Path(file)
            if path.suffix.lower() in VIDEO_EXTS and path not in self.video_files:
                self.video_files.append(path)
                self.video_listbox.insert(tk.END, str(path))

    def _clear_videos(self):
        self.video_files.clear()
        self.video_listbox.delete(0, tk.END)

    def _add_priority_songs(self):
        files = filedialog.askopenfilenames(
            title="Thêm bài hát ưu tiên",
            initialdir=self.music_folder.get() or None,
            filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.aac *.flac")],
        )
        for file in files:
            path = Path(file)
            if path.suffix.lower() in MUSIC_EXTS and path not in self.priority_files:
                self.priority_files.append(path)
        self._refresh_priority_listbox()

    def _remove_priority_songs(self):
        selected = list(self.priority_listbox.curselection())
        for index in reversed(selected):
            self.priority_listbox.delete(index)
            del self.priority_files[index]
        self._refresh_priority_listbox()

    def _shuffle_priority_songs(self):
        random.shuffle(self.priority_files)
        self._refresh_priority_listbox()

    def _refresh_priority_listbox(self):
        self.priority_listbox.delete(0, tk.END)
        for path in self.priority_files:
            self.priority_listbox.insert(tk.END, path.name)
        self.priority_total_label.set(f"Tổng số bài ưu tiên: {len(self.priority_files)}")

    def _check_ffmpeg_available(self, show_popup=True) -> bool:
        ok = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
        if show_popup and not ok:
            messagebox.showerror("Thiếu FFmpeg", "Không tìm thấy FFmpeg.\nWindows: tải từ ffmpeg.org và thêm PATH\nmacOS: brew install ffmpeg\nUbuntu: sudo apt install ffmpeg")
        if show_popup and ok:
            messagebox.showinfo("FFmpeg", "Đã tìm thấy ffmpeg và ffprobe trong PATH.")
        return ok

    def _run_json_ffprobe(self, path: Path, entries: str) -> dict:
        cmd = ["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)]
        r = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(r.stdout)

    def _get_duration(self, path: Path) -> float:
        return float(self._run_json_ffprobe(path, "format=duration")["format"]["duration"])

    def _video_has_audio_stream(self, path: Path) -> bool:
        streams = self._run_json_ffprobe(path, "stream=codec_type").get("streams", [])
        return any(s.get("codec_type") == "audio" for s in streams)

    def _collect_music_files(self) -> list[Path]:
        folder = Path(self.music_folder.get())
        if not folder.exists() or not folder.is_dir():
            return []
        return sorted([f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in MUSIC_EXTS])

    def _build_output_path(self, video_path: Path) -> Path:
        base = video_path.with_name(f"{video_path.stem}_with_music.mp4")
        if not base.exists():
            return base
        i = 1
        while True:
            p = video_path.with_name(f"{video_path.stem}_with_music_{i}.mp4")
            if not p.exists():
                return p
            i += 1

    def _build_playlist_txt_path(self, video_path: Path) -> Path:
        base = video_path.with_name(f"{video_path.stem}_playlist.txt")
        if not base.exists():
            return base
        i = 1
        while True:
            p = video_path.with_name(f"{video_path.stem}_playlist_{i}.txt")
            if not p.exists():
                return p
            i += 1

    def _select_regular_songs(self, musics: list[Path], count: int) -> list[Path]:
        mode = self.assignment_mode.get()
        if count <= 0:
            return []
        if mode == "ordered":
            return [musics[i % len(musics)] for i in range(count)]
        if mode == "full_random":
            return [random.choice(musics) for _ in range(count)]

        # Random không trùng lặp: dùng hết pool rồi tự vòng mới, không bị lỗi khi count lớn.
        selected: list[Path] = []
        pool: list[Path] = []
        for _ in range(count):
            if not pool:
                pool = musics.copy()
                random.shuffle(pool)
            selected.append(pool.pop())
        return selected

    def _select_priority_songs(self, priority_files: list[Path], count: int) -> list[Path]:
        mode = self.priority_mode.get()
        if count <= 0 or not priority_files:
            return []
        if mode == "ordered":
            return [priority_files[i % len(priority_files)] for i in range(count)]
        if mode == "full_random":
            return [random.choice(priority_files) for _ in range(count)]

        # Random không trùng: dùng hết danh sách rồi bắt đầu vòng mới nếu N quá lớn.
        selected: list[Path] = []
        pool: list[Path] = []
        for _ in range(count):
            if not pool:
                pool = priority_files.copy()
                random.shuffle(pool)
            selected.append(pool.pop())
        return selected

    def _select_songs(self, musics: list[Path], count: int) -> tuple[list[Path], list[bool], list[Path], list[Path]]:
        """Chọn bài hát ưu tiên trước, sau đó chọn nhạc thường để đủ tổng số bài."""
        if not self.use_priority_list.get() or not self.priority_files:
            regular = self._select_regular_songs(musics, count)
            return regular, [False] * len(regular), [], regular

        valid_priority = [p for p in self.priority_files if p.exists() and p.suffix.lower() in MUSIC_EXTS]
        if not valid_priority:
            regular = self._select_regular_songs(musics, count)
            return regular, [False] * len(regular), [], regular

        priority_count = max(0, min(self.priority_song_count.get(), count))
        selected_priority = self._select_priority_songs(valid_priority, priority_count)
        priority_keys = {p.resolve() for p in valid_priority}
        regular_library = [m for m in musics if m.resolve() not in priority_keys]
        if not regular_library:
            regular_library = musics
        regular = self._select_regular_songs(regular_library, count - len(selected_priority))
        songs = selected_priority + regular
        is_priority = [True] * len(selected_priority) + [False] * len(regular)
        return songs, is_priority, selected_priority, regular

    @staticmethod
    def _ts(seconds: float) -> str:
        s = int(seconds)
        h, r = divmod(s, 3600)
        m, sec = divmod(r, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

    def _target_seconds(self) -> int:
        return max(0, self.target_hours.get()) * 3600 + max(0, self.target_minutes.get()) * 60

    def _expand_to_target(self, songs: list[Path], durations: list[float], is_priority: list[bool], target_seconds: int) -> tuple[list[Path], list[float], list[bool]]:
        if target_seconds <= 0:
            return songs, durations, is_priority
        base_songs = songs.copy()
        base_durations = durations.copy()
        base_is_priority = is_priority.copy()
        total = sum(durations)
        while total < target_seconds:
            songs.extend(base_songs)
            durations.extend(base_durations)
            is_priority.extend(base_is_priority)
            total = sum(durations)
        return songs, durations, is_priority

    def _build_concat_file(self, songs: list[Path], txt_path: Path):
        # File concat chỉ trỏ tới các WAV tạm có cùng codec/sample-rate/channel,
        # vì vậy có thể nối an toàn dù thư mục gốc trộn MP3/WAV/M4A/AAC/FLAC.
        with txt_path.open("w", encoding="utf-8") as f:
            f.write("ffconcat version 1.0\n")
            for s in songs:
                escaped = str(s).replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

    def _create_playlist_audio(self, songs: list[Path], temp_dir: Path) -> Path:
        """Chuyển từng bài sang WAV 44100Hz stereo rồi nối thành 1 audio playlist."""
        segment_paths: list[Path] = []
        for index, song in enumerate(songs):
            segment = temp_dir / f"segment_{index:05d}.wav"
            convert_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(song),
                "-vn",
                "-ac",
                "2",
                "-ar",
                "44100",
                str(segment),
            ]
            subprocess.run(convert_cmd, capture_output=True, text=True, check=True)
            segment_paths.append(segment)

        concat_list = temp_dir / "concat_list.txt"
        playlist_wav = temp_dir / "playlist.wav"
        self._build_concat_file(segment_paths, concat_list)
        concat_cmd = ["ffmpeg", "-y", "-safe", "0", "-f", "concat", "-i", str(concat_list), "-vn", "-ac", "2", "-ar", "44100", str(playlist_wav)]
        subprocess.run(concat_cmd, capture_output=True, text=True, check=True)
        return playlist_wav

    def _write_playlist_txt(self, txt_path: Path, src_video: Path, out_video: Path, songs: list[Path], durations: list[float], is_priority: list[bool], export_duration: float):
        lines = [
            f"Tên video gốc: {src_video.name}",
            f"Video xuất: {out_video.name}",
            f"Tổng thời lượng: {self._ts(export_duration)}",
            "",
            "Danh sách bài hát:",
        ]
        current_seconds = 0.0
        for song, dur, priority in zip(songs, durations, is_priority):
            # TXT chỉ ghi những bài thực sự bắt đầu trước khi video xuất kết thúc.
            # Nếu bài cuối bị cắt giữa chừng, timestamp bắt đầu vẫn được giữ lại.
            if current_seconds >= export_duration:
                break
            prefix = "[PRIORITY] " if priority else ""
            lines.append(f"{self._ts(current_seconds)} {prefix}{song.name}")
            current_seconds += dur
        txt_path.write_text("\n".join(lines), encoding="utf-8")

    def _process_one(self, video: Path, music_files: list[Path]) -> ProcessResult:
        temp_files: list[Path] = []
        try:
            songs, is_priority, used_priority, used_regular = self._select_songs(music_files, max(1, self.songs_per_video.get()))
            durations = [self._get_duration(s) for s in songs]
            songs, durations, is_priority = self._expand_to_target(songs, durations, is_priority, self._target_seconds())

            playlist_duration = sum(durations)
            target_seconds = self._target_seconds()
            output_duration = target_seconds if target_seconds > 0 else playlist_duration

            out_video = self._build_output_path(video)
            playlist_txt = self._build_playlist_txt_path(video) if self.export_playlist_txt.get() else None

            self.worker_queue.put(("log", f"- Chọn {len(songs)} bài cho {video.name}"))
            self.worker_queue.put(("log", f"- Danh sách ưu tiên: {len(self.priority_files)} bài."))
            self.worker_queue.put(("log", "- Đã sử dụng ưu tiên: " + (", ".join([s.name for s in used_priority]) if used_priority else "Không có")))
            self.worker_queue.put(("log", "- Đã random: " + (", ".join([s.name for s in used_regular[:10]]) + (" ..." if len(used_regular) > 10 else "") if used_regular else "Không có")))
            self.worker_queue.put(("log", f"- Tổng thời lượng playlist: {self._ts(output_duration)}"))
            self.worker_queue.put(("log", "- Danh sách bài: " + ", ".join([s.name for s in songs[:10]]) + (" ..." if len(songs) > 10 else "")))

            with tempfile.TemporaryDirectory(prefix="music_merge_") as td:
                temp_dir = Path(td)
                playlist_wav = self._create_playlist_audio(songs, temp_dir)

                video_duration = self._get_duration(video)
                has_audio = self._video_has_audio_stream(video)
                volume = max(0.0, min(float(self.music_volume.get()), 2.0))
                fade = max(0.0, min(float(self.fade_seconds.get()), output_duration))
                fade_out_start = max(0.0, output_duration - fade)
                music_filter = f"volume={volume},afade=t=in:st=0:d={fade},afade=t=out:st={fade_out_start}:d={fade}"
                if self.normalize_audio_44k.get():
                    music_filter = music_filter + ",aformat=sample_rates=44100:channel_layouts=stereo"

                loop_needed = self.loop_video_to_playlist.get() and output_duration > video_duration
                stream_loop_value = str(max(0, math.ceil(output_duration / video_duration) - 1)) if loop_needed else "0"
                if (not loop_needed) and video_duration > output_duration and not self.cut_video_if_longer.get():
                    export_duration = video_duration
                else:
                    export_duration = output_duration
                self.worker_queue.put(("log", f"- Đang loop video: {'Có' if loop_needed else 'Không'}"))
                self.worker_queue.put(("log", f"- Thời lượng video xuất: {self._ts(export_duration)}"))

                use_mix = self.keep_original_audio.get() and has_audio
                if use_mix:
                    filter_complex = f"[1:a]{music_filter}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[mix]"
                    map_audio = "[mix]"
                else:
                    filter_complex = f"[1:a]{music_filter}[mix]"
                    map_audio = "[mix]"

                cmd = ["ffmpeg", "-y"]
                if loop_needed:
                    cmd += ["-stream_loop", stream_loop_value]
                cmd += ["-i", str(video), "-i", str(playlist_wav), "-filter_complex", filter_complex, "-map", "0:v:0", "-map", map_audio]

                cmd += ["-t", f"{export_duration}"]

                cmd += ["-c:v", "copy", "-c:a", "aac"]
                if self.normalize_audio_44k.get():
                    cmd += ["-ac", "2", "-ar", "44100"]
                cmd += [str(out_video)]
                subprocess.run(cmd, capture_output=True, text=True, check=True)

            if self.export_playlist_txt.get() and playlist_txt is not None:
                self._write_playlist_txt(playlist_txt, video, out_video, songs, durations, is_priority, export_duration)
                self.worker_queue.put(("log", f"- TXT playlist: {playlist_txt}"))

            self.worker_queue.put(("log", f"- Video xuất: {out_video}"))
            return ProcessResult(video=video, output=out_video, success=True, playlist_txt=playlist_txt)
        except subprocess.CalledProcessError as exc:
            return ProcessResult(video=video, output=None, success=False, error=exc.stderr.strip()[:1200])
        except Exception as exc:
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
            messagebox.showwarning("Thiếu nhạc", "Không tìm thấy file nhạc hợp lệ.")
            return
        total_songs = max(1, self.songs_per_video.get())
        if self.use_priority_list.get() and self.priority_song_count.get() > total_songs:
            self.priority_song_count.set(total_songs)
            messagebox.showwarning(
                "Điều chỉnh số bài ưu tiên",
                "Số bài ưu tiên lớn hơn tổng số bài/video nên đã tự giảm bằng tổng số bài/video.",
            )

        self.results.clear()
        self.result_text.delete("1.0", tk.END)
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.video_files)
        self.start_btn.config(state="disabled")
        self.processing = True

        t = threading.Thread(target=self._worker, args=(self.video_files.copy(), music_files), daemon=True)
        t.start()
        self.root.after(150, self._poll_queue)

    def _worker(self, videos: list[Path], music_files: list[Path]):
        for i, video in enumerate(videos, start=1):
            self.worker_queue.put(("status", f"Đang xử lý {i}/{len(videos)}: {video.name}"))
            result = self._process_one(video, music_files)
            self.worker_queue.put(("result", result))
        self.worker_queue.put(("done", None))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.worker_queue.get_nowait()
                if kind == "status":
                    self.status_label.config(text=data)
                    self._append_log(data)
                elif kind == "log":
                    self._append_log(data)
                elif kind == "result":
                    self.results.append(data)
                    self.progress["value"] = len(self.results)
                elif kind == "done":
                    self._on_finished(); return
        except queue.Empty:
            pass
        if self.processing:
            self.root.after(150, self._poll_queue)

    def _on_finished(self):
        self.processing = False
        self.start_btn.config(state="normal")
        success = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        self.status_label.config(text=f"Hoàn tất. Thành công: {len(success)} | Lỗi: {len(failed)}")
        self._append_log("\n=== THÀNH CÔNG ===")
        for item in success:
            self._append_log(f"✓ {item.video.name} -> {item.output}")
            if item.playlist_txt:
                self._append_log(f"  Playlist TXT: {item.playlist_txt}")
        self._append_log("\n=== LỖI ===")
        for item in failed:
            self._append_log(f"✗ {item.video.name}: {item.error}")


def main():
    root = tk.Tk()
    MusicMergeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
