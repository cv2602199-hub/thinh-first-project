# Batch Video Music Merger (Local Tool)

Tool desktop bằng **Python + Tkinter + FFmpeg** để ghép nhạc nền vào nhiều video hàng loạt.

## Tính năng

- Chọn thư mục nhạc, hỗ trợ: `mp3`, `wav`, `m4a`, `aac`.
- Chọn nhiều video cùng lúc, hỗ trợ: `mp4`, `mov`, `mkv`, `avi`.
- Tự động ghép 1 bài nhạc vào mỗi video theo 3 chế độ:
  - Random không trùng lặp cho đến khi hết danh sách.
  - Random hoàn toàn.
  - Ghép theo thứ tự danh sách.
- Tự ép thời lượng nhạc theo video:
  - Nhạc dài hơn video: tự cắt vừa bằng video.
  - Nhạc ngắn hơn video: tự lặp cho đủ thời lượng video.
- Tùy chọn âm thanh:
  - Giữ hoặc tắt âm thanh gốc của video.
  - Điều chỉnh âm lượng nhạc nền.
  - Fade in / fade out nhẹ.
- Lưu file mới ngay cạnh video gốc.
- Tên xuất: `ten-video-goc_with_music.mp4`.
- Không ghi đè: tự tăng số `_1`, `_2`, ... nếu trùng tên.
- Có thanh tiến trình và danh sách kết quả thành công/lỗi.

---

## Yêu cầu

- Python 3.10+
- FFmpeg (có cả `ffmpeg` và `ffprobe` trong `PATH`)

## Cài FFmpeg

### Windows
1. Tải bản build tại: https://ffmpeg.org/download.html
2. Giải nén.
3. Thêm thư mục `bin` (chứa `ffmpeg.exe`) vào biến môi trường `PATH`.
4. Mở lại terminal / app.

### macOS
```bash
brew install ffmpeg
```

### Ubuntu / Debian
```bash
sudo apt update && sudo apt install ffmpeg
```

Kiểm tra:
```bash
ffmpeg -version
ffprobe -version
```

---

## Cách chạy tool

Trong thư mục dự án:

```bash
python app.py
```

(Nếu máy dùng `python3`):

```bash
python3 app.py
```

---

## Hướng dẫn sử dụng

1. Bấm **Browse** để chọn thư mục nhạc.
2. Bấm **Chọn video** để chọn nhiều video.
3. Chọn chế độ gán nhạc.
4. Cấu hình âm thanh:
   - Giữ/tắt âm thanh gốc video.
   - Âm lượng nhạc nền.
   - Thời lượng fade in/out.
5. Bấm **Bắt đầu ghép**.
6. Theo dõi thanh tiến trình và danh sách kết quả.

## Ghi chú

- Tool xử lý tuần tự từng video để dễ theo dõi trạng thái.
- Video đầu ra luôn mã âm thanh AAC để tương thích tốt.
- Nếu video không có audio gốc mà chọn "Giữ âm thanh gốc", FFmpeg vẫn có thể trộn nhạc bình thường trong đa số trường hợp.
