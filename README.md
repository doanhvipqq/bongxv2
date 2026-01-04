# Bot Telegram Golike Automation

Bot Telegram để tự động hóa các nhiệm vụ Golike cho Instagram, LinkedIn và Threads.

## 🚀 Cài đặt

### 1. Cài đặt Python
Yêu cầu Python 3.8 trở lên.

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình Bot Token

1. Tạo bot mới trên Telegram:
   - Mở [@BotFather](https://t.me/BotFather) trên Telegram
   - Gửi lệnh `/newbot`
   - Đặt tên và username cho bot
   - Sao chép Bot Token

2. Cập nhật file `bot_config.json`:
```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "users": {}
}
```

## 📱 Sử dụng

### Khởi động bot:
```bash
python main_bot.py
```

### Lệnh trên Telegram:

- `/start` - Bắt đầu sử dụng bot
- `/help` - Hướng dẫn chi tiết
- `/settings` - Cài đặt Golike token
- `/instagram` - Chạy tool Instagram
- `/linkedin` - Chạy tool LinkedIn
- `/threads` - Chạy tool Threads
- `/status` - Kiểm tra trạng thái
- `/stop` - Dừng tool đang chạy

## 🔑 Lấy Golike Authorization Token

1. Đăng nhập vào https://app.golike.net
2. Mở Developer Tools (F12)
3. Vào tab **Network**
4. Làm mới trang (F5)
5. Tìm request đến `api/users/me`
6. Copy giá trị trong header **"Authorization"**
7. Dán vào bot khi sử dụng `/settings`

## 📋 Tính năng

✅ Quản lý token cho 3 nền tảng (Instagram, LinkedIn, Threads)
✅ Chạy automation tools thông qua Telegram
✅ Kiểm tra trạng thái real-time
✅ Dừng/khởi động tools dễ dàng
✅ Lưu cấu hình tự động
✅ Giao diện tiếng Việt

## ⚠️ Lưu ý

- Chỉ chạy một tool tại một thời điểm
- Token cần được làm mới định kỳ khi hết hạn
- Giữ Bot Token bảo mật, không chia sẻ
- Đảm bảo kết nối internet ổn định

## 📁 Cấu trúc File

```
Xjcjfjfj/
├── main_bot.py          # Bot Telegram chính
├── Instagram.py         # Tool Golike Instagram
├── linkedin.py          # Tool Golike LinkedIn
├── thera.py            # Tool Golike Threads
├── bot_config.json     # Cấu hình bot
├── requirements.txt    # Dependencies
└── README.md          # File này
```

## 🛠️ Phát triển

Bot hiện đang ở giai đoạn phát triển. Các tính năng đang được tích hợp:
- ✅ Cấu trúc bot cơ bản
- ✅ Quản lý token
- 🔄 Tích hợp Instagram.py (đang phát triển)
- 🔄 Tích hợp linkedin.py (đang phát triển)  
- 🔄 Tích hợp thera.py (đang phát triển)

## 🤝 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra Bot Token đã đúng chưa
2. Đảm bảo đã cài đặt đủ dependencies
3. Kiểm tra Golike token còn hiệu lực không
4. Xem log trong terminal để tìm lỗi

## 📜 License

Dự án này dành cho mục đích học tập và nghiên cứu.
