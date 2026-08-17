<div align="center">
  <img src="static/banner.png" alt="Someli Banner" width="100%">
  
  # 🏨 Someli Room Check Report
  
  *Công cụ trích xuất và tổng hợp lịch dọn phòng tự động dành cho hệ thống Someli Property Management.*
</div>

---

## 📖 Giới thiệu
**Someli Room Check Report** là một ứng dụng Web nội bộ giúp bộ phận buồng phòng dễ dàng theo dõi lịch trả phòng (check-out) của khách hàng tại 16 cơ sở. Thay vì phải tra cứu thủ công qua hệ thống chính, công cụ này tự động kéo dữ liệu, gom nhóm lịch theo từng ca làm việc, và sắp xếp độ ưu tiên dọn phòng dựa trên lịch check-in tiếp theo của khách mới.

## ✨ Tính năng nổi bật
- **Giao diện Enterprise:** Thiết kế chuẩn doanh nghiệp, tối giản và trực quan với tông màu Dark Green sang trọng mang bản sắc của Someli.
- **Tự động phân ca (Shifts):** Tự động chia lịch dọn phòng thành 3 ca rành mạch: Ca Sáng (bao gồm cả phòng qua đêm), Ca Chiều, và Ca Tối.
- **Thuật toán sắp xếp đa tầng (Multi-level Sorting):** 
  - *Ưu tiên 1:* Sắp xếp theo giờ trả phòng từ sớm đến muộn.
  - *Ưu tiên 2:* Nếu cùng giờ trả, phòng có khách mới vào sớm hơn sẽ được đẩy lên trên để ưu tiên dọn trước.
  - *Ưu tiên 3:* Sắp xếp theo số thứ tự phòng (từ bé đến lớn) để dễ tìm kiếm.
- **Cảnh báo thông minh:** 
  - Tự động hiển thị ngoặc cảnh báo `(..h vào)` nếu khoảng cách thời gian giữa khách cũ và khách mới nhỏ hơn 12 tiếng.
  - Các phòng trả trong đêm sẽ tự động được ẩn giờ trả và thay bằng trạng thái `8h dọn`.
- **Bảo mật Token:** Mọi Token truy cập đều chỉ được lưu cục bộ trên trình duyệt (LocalStorage) của người dùng, đảm bảo an toàn tuyệt đối.

## 🛠️ Cài đặt & Sử dụng (Local)

Nếu bạn muốn chạy thử ứng dụng này trực tiếp trên máy tính cá nhân:

1. **Yêu cầu:** Máy tính cần cài sẵn [Python 3.8+](https://www.python.org/).
2. **Cài đặt thư viện:**
   Mở Terminal/CMD tại thư mục dự án và chạy:
   ```bash
   pip install -r requirements.txt
   ```
3. **Khởi chạy ứng dụng:**
   ```bash
   python app.py
   ```
4. **Sử dụng:** Mở trình duyệt web và truy cập vào địa chỉ `http://127.0.0.1:5000`

## 🚀 Hướng dẫn Triển khai Lên Mạng (Deploy)
Dự án đã được cấu hình sẵn để dễ dàng triển khai (Deploy) hoàn toàn miễn phí lên nền tảng **Render.com**. 

1. Đăng nhập vào Render bằng Github và chọn **New Web Service**.
2. Kết nối tới Repository chứa mã nguồn này.
3. Thiết lập môi trường chạy (Environment): `Python 3`
4. Cấu hình lệnh cài đặt (**Build Command**): 
   ```bash
   pip install -r requirements.txt
   ```
5. Cấu hình lệnh khởi chạy (**Start Command**): 
   ```bash
   gunicorn app:app
   ```
Mỗi khi bạn đẩy (Push) thay đổi mới lên Github, Render sẽ tự động cập nhật hệ thống của bạn ngay lập tức!

---
*Công cụ được phát triển đặc quyền dành cho đội ngũ vận hành của Someli Property Management.*
