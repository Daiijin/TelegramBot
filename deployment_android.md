# Hướng Dẫn Chạy Bot Trên Điện Thoại Android (Self-Host)

Bạn có thể tận dụng chiếc điện thoại Android cũ để chạy bot 24/7 thay vì dùng laptop. Chúng ta sẽ sử dụng ứng dụng **Termux** (một môi trường dòng lệnh Linux trên Android).

## 1. Cài Đặt Termux
⚠️ **Lưu ý quan trọng**: Không tải Termux từ Google Play Store (phiên bản đó đã cũ và không còn được hỗ trợ).
1. Tải **F-Droid** (kho ứng dụng mã nguồn mở) hoặc tải trực tiếp APK Termux từ [Github của Termux](https://github.com/termux/termux-app/releases).
2. Cài đặt ứng dụng Termux.

## 2. Thiết Lập Môi Trường
Mở Termux và chạy lần lượt các lệnh sau (nhấn Enter sau mỗi dòng và chọn 'y' nếu được hỏi):

```bash
# Cập nhật hệ thống
pkg update && pkg upgrade -y

# Cài đặt Python và Git
pkg install python git -y

# Cài đặt các thư viện cần thiết cho biên dịch (nếu cần)
pkg install build-essential libffi libxml2 libxslt -y
```

## 3. Tải Mã Nguồn Bot
Bạn có 2 cách để đưa code vào điện thoại:

**Cách 1: Dùng Git (Khuyên dùng)**
Nếu bạn đã đẩy code lên Github:
```bash
git clone https://github.com/username/repo-name.git
cd repo-name
```

**Cách 2: Copy thủ công**
Copy thư mục code vào bộ nhớ trong điện thoại, sau đó trong Termux:
```bash
# Cấp quyền truy cập bộ nhớ
termux-setup-storage

# Di chuyển vào thư mục (ví dụ thư mục Download)
cd storage/downloads/TelegramBot
```

## 4. Cài Đặt Thư Viện Python
```bash
pip install -r requirements.txt
```
*Lưu ý: Nếu gặp lỗi khi cài đặt `google-generativeai` hoặc các thư viện khác, hãy thử nâng cấp pip: `pip install --upgrade pip`.*

## 5. Cấu Hình Biến Môi Trường
Tạo file `.env` trong thư mục dự án (nếu chưa có):
```bash
nano .env
```
Dán nội dung API Key vào (Ctrl+Shift+V để dán trong Termux):
```
TELEGRAM_TOKEN=your_telegram_token
GEMINI_API_KEY=your_gemini_api_key
```
Nhấn `Ctrl + X`, sau đó `y`, rồi `Enter` để lưu.

## 6. Chạy Bot
```bash
python src/main.py
```

## 7. Giữ Bot Chạy 24/7 (Quan Trọng)
Android rất tích cực tắt các ứng dụng chạy ngầm để tiết kiệm pin. Để bot không bị tắt:

1.  **Tắt Tối ưu hóa pin**: Vào Cài đặt -> Ứng dụng -> Termux -> Pin -> Chọn "Không hạn chế" (Unrestricted).
2.  **Khóa ứng dụng**: Mở trình đa nhiệm (Recent Apps), tìm Termux, nhấn giữ hoặc tìm biểu tượng ổ khóa để khóa nó lại.
3.  **Wakelock (Trong Termux)**: Vuốt thanh thông báo của Termux xuống, chọn "Acquire wakelock" để giữ CPU luôn chạy.

## 8. Hỏi Đáp Về Pin & Độ Ổn Định (Quan Trọng)

### 🔋 Có cần cắm sạc liên tục không?
**CÓ, nên cắm sạc.**
- Bot chạy 24/7 sẽ ngăn điện thoại rơi vào chế độ "Deep Sleep" (ngủ sâu), nên pin sẽ tụt nhanh hơn bình thường.
- **Lời khuyên**: Để bảo vệ pin (tránh bị phồng), bạn nên dùng một củ sạc công suất thấp (5W - 1A) hoặc cắm vào cổng USB của máy tính/router để sạc chậm. Vì đây là điện thoại không dùng đến nên việc chai pin có thể chấp nhận được.

### 📉 Độ ổn định thế nào?
- **Khá ổn cho nhu cầu cá nhân**, nhưng không bằng máy chủ chuyên nghiệp (VPS).
- **Rủi ro**:
    - **Mất Wifi**: Một số điện thoại tự ngắt Wifi khi tắt màn hình lâu. Hãy vào Cài đặt Wifi -> Giữ Wifi luôn bật khi ngủ.
    - **Bị hệ điều hành "giết"**: Các hãng như Xiaomi, Samsung, Oppo có cơ chế quản lý RAM rất gắt. Dù đã tắt tối ưu pin, đôi khi Termux vẫn bị tắt ngầm.
- **Khắc phục**:
    - Treo một thông báo (Notification) của Termux (Acquire Wakelock).
    - Kiểm tra bot mỗi sáng. Nếu thấy im lặng bất thường thì mở app lên lại.

### 💡 Giải pháp thay thế nếu cần ổn định tuyệt đối
Nếu bạn cần bot nhắc việc cực kỳ quan trọng và không muốn lo lắng về pin/wifi, hãy cân nhắc thuê **VPS (Máy chủ ảo)**.
- **Chi phí**: Khoảng 80k - 120k/tháng.
- **Ưu điểm**: Chạy 24/24, không bao giờ mất mạng, không tốn điện nhà.
- **Nhược điểm**: Tốn tiền hàng tháng.

## Ưu/Nhược Điểm Tổng Kết
✅ **Ưu điểm**: Miễn phí, tận dụng thiết bị cũ.
❌ **Nhược điểm**: Cần cắm sạc, phụ thuộc Wifi nhà, có rủi ro bị tắt ngầm.

