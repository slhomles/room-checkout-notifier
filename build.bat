@echo off
echo Đang đóng gói ứng dụng...
call .\venv\Scripts\activate
pyinstaller --name RoomCheckApp --onefile --noconsole --add-data "templates;templates" app.py
echo Đóng gói hoàn tất. File nằm trong thư mục dist.
pause
