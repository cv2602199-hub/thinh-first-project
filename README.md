# Batch Video Music Playlist Merger

Tool desktop local bằng **Python + Tkinter + FFmpeg** để tạo video playlist dài (1h/2h/3h...) từ nhiều bài nhạc.

## Tính năng chính
- Chọn thư mục nhạc (`mp3`, `wav`, `m4a`, `aac`, `flac`) và chọn nhiều video (`mp4`, `mov`, `mkv`, `avi`).
- Chọn **số bài hát cho mỗi video** (ví dụ 30 bài).
- Thêm **Danh sách ưu tiên** để các bài yêu thích luôn được dùng trước khi random/chọn bài còn lại.
- 3 chế độ chọn nhạc:
  - Random không trùng lặp (hết danh sách sẽ tự vòng mới)
  - Random hoàn toàn
  - Theo thứ tự danh sách
- Tạo playlist audio bằng cách nối nhiều bài hát theo thứ tự đã chọn.
- Có thể nhập **thời lượng mục tiêu (giờ/phút)**:
  - Nếu chưa đủ thời lượng: tự lặp playlist cho đủ gần mục tiêu.
  - Nếu dài hơn mục tiêu: cắt đúng thời lượng mục tiêu.
- Tùy chọn **loop video** để khớp thời lượng playlist audio.
- Nếu video dài hơn playlist: tùy chọn cắt video theo playlist hoặc giữ nguyên.
- Tùy chọn giữ/tắt âm thanh gốc video, chỉnh volume nhạc nền, fade in/out.
- Tùy chọn chuẩn hóa audio về **44100 Hz, stereo**, xuất AAC cho MP4.
- Tùy chọn xuất file TXT playlist timestamp để dán mô tả YouTube. Các bài ưu tiên được đánh dấu `[PRIORITY]`.
- Không ghi đè file cũ: tự thêm `_1`, `_2`, ...

## Cài FFmpeg
- Windows: tải từ https://ffmpeg.org/download.html và thêm vào PATH.
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install ffmpeg`

Kiểm tra:
```bash
ffmpeg -version
ffprobe -version
```

## Cách chạy
```bash
python app.py
```
Hoặc:
```bash
python3 app.py
```

## Cách dùng nhanh
1. Chọn thư mục nhạc.
2. Chọn một hoặc nhiều video nền.
3. (Tùy chọn) Bấm **Thêm bài hát ưu tiên** để chọn các bài yêu thích, rồi bật **Ưu tiên danh sách yêu thích**.
4. Nhập **Số bài hát cho mỗi video** (ví dụ: 30).
5. (Tùy chọn) Nhập **Thời lượng mục tiêu** (ví dụ: 3 giờ 0 phút).
6. Bật **Loop video để khớp thời lượng playlist nhạc**.
7. Chọn các tùy chọn audio và bấm **Bắt đầu ghép playlist**.

## Ví dụ làm video dài
- **1 giờ**: đặt mục tiêu `1 giờ 0 phút`, số bài 15–20 (tùy độ dài bài), bật loop video.
- **2 giờ**: đặt mục tiêu `2 giờ 0 phút`, số bài 25–40, bật loop video.
- **3 giờ**: đặt mục tiêu `3 giờ 0 phút`, số bài 30+, bật loop video.

Tool sẽ tự lặp danh sách bài nếu chưa đủ thời lượng mục tiêu.

## File TXT playlist
Mỗi video xuất có thể đi kèm file:
- `ten-video-goc_playlist.txt`

Nội dung gồm:
- Tên video gốc
- Tên file video xuất
- Tổng thời lượng
- Timestamp từng bài theo thứ tự (dùng được cho mô tả YouTube), kèm `[PRIORITY]` nếu bài thuộc danh sách ưu tiên

Ví dụ:
```text
00:00 [PRIORITY] My Favorite Song.wav
04:25 Another Song.mp3
08:50 [PRIORITY] Jazz Night.flac
```
