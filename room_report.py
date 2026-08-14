import json
import requests
from datetime import datetime, timedelta
import pytz
import os

import sys
sys.stdout.reconfigure(encoding='utf-8')

# Cấu hình Múi giờ Việt Nam
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
CONFIG_FILE = 'config.json'
REPORT_FILE = 'report.txt'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"Không tìm thấy file {CONFIG_FILE}. Vui lòng tạo file theo mẫu.")
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def fetch_data(config, target_date):
    """
    Gọi API để lấy dữ liệu.
    target_date là ngày Việt Nam cần lấy báo cáo (datetime.date)
    """
    # Tính startDate và endDate (UTC)
    # Ví dụ: lấy dữ liệu của ngày 15/08/2026 (VN)
    # Tức là từ 00:00:00 (VN) ngày 15/08 -> 23:59:59 (VN) ngày 15/08
    # Sang UTC sẽ là: 17:00:00 ngày 14/08 -> 16:59:59 ngày 15/08
    
    vn_start_dt = VN_TZ.localize(datetime.combine(target_date, datetime.min.time()))
    vn_end_dt = VN_TZ.localize(datetime.combine(target_date, datetime.max.time()))
    
    utc_start_dt = vn_start_dt.astimezone(pytz.UTC)
    utc_end_dt = vn_end_dt.astimezone(pytz.UTC)
    
    start_str = utc_start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = utc_end_dt.strftime("%Y-%m-%dT%H:%M:%S.999Z")
    
    url = f"{config['api_url']}?startDate={start_str}&endDate={end_str}"
    
    headers = {}
    if config['auth_type'] == 'Bearer':
        headers['Authorization'] = config['authorization']
    elif config['auth_type'] == 'Cookie':
        headers['Cookie'] = config['authorization']
    else:
        headers[config['auth_type']] = config['authorization']
        
    print(f"Đang gọi API: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        print(f"Lỗi gọi API: {response.status_code} - {response.text}")
        return []

def load_local_data(filepath):
    """Dùng để test với file schedule.json local"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f).get('data', [])

def process_data(data, target_date):
    """
    Xử lý dữ liệu và phân nhóm
    """
    checkouts = []
    checkins = {} # Lưu lại thời gian checkin của từng phòng để tìm lịch vào sớm

    for item in data:
        if 'roomId' not in item or not item['roomId']:
            continue
            
        room_id = item['roomId']['_id']
        room_code = item['roomId'].get('roomCode', 'Unknown')
        branch_name = item['branchId'].get('name', 'Unknown')
        
        # Parse thời gian (UTC -> VN)
        try:
            checkout_utc = datetime.strptime(item['checkoutAt'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            checkout_vn = checkout_utc.astimezone(VN_TZ)
            
            checkin_utc = datetime.strptime(item['checkinAt'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            checkin_vn = checkin_utc.astimezone(VN_TZ)
        except ValueError:
            # Bỏ qua nếu lỗi định dạng ngày
            continue
            
        # Lưu vào dict checkins để kiểm tra xem có khách vào sớm sau khi trả phòng không
        if room_id not in checkins:
            checkins[room_id] = []
        checkins[room_id].append(checkin_vn)
        
        # Lọc các phòng có lịch check-out vào đúng target_date
        if checkout_vn.date() == target_date:
            checkouts.append({
                'room_id': room_id,
                'room_code': room_code,
                'branch': branch_name,
                'checkout_time': checkout_vn
            })

    # Sắp xếp checkouts theo giờ trả phòng
    checkouts.sort(key=lambda x: x['checkout_time'])

    report = {}
    
    for co in checkouts:
        branch = co['branch']
        if branch not in report:
            report[branch] = {'Sáng': [], 'Chiều': [], 'Tối': []}
            
        co_time = co['checkout_time']
        hour = co_time.hour
        minute = co_time.minute
        
        # Tìm xem có khách nào checkin sau khi khách này checkout không (trong cùng ngày)
        next_checkin_str = ""
        room_id = co['room_id']
        for ci_time in sorted(checkins.get(room_id, [])):
            if ci_time >= co_time and ci_time.date() == co_time.date():
                gap_hours = (ci_time - co_time).total_seconds() / 3600
                if gap_hours >= 0:
                    time_ci_str = ci_time.strftime('%Hh%M').replace('h00', 'h')
                    next_checkin_str = f" ({time_ci_str} vào)"
                break # Chỉ lấy lượt checkin gần nhất
                
        time_co_str = co_time.strftime('%Hh%M').replace('h00', 'h')
        room_display = f"{co['room_code']} - {time_co_str} trả{next_checkin_str}"
        
        # Phân loại ca
        if hour < 12:
            report[branch]['Sáng'].append(room_display)
        elif 12 <= hour < 18:
            report[branch]['Chiều'].append(room_display)
        else:
            # Từ 18h trở đi là Tối, sau 21h30 là hôm sau dọn
            if hour >= 22 or (hour == 21 and minute > 30):
                room_display += " (hôm sau dọn)"
            report[branch]['Tối'].append(room_display)
            
    return report

def generate_report_text(report_data, target_date):
    date_str = target_date.strftime("Ngày %d/%m")
    
    if not report_data:
        return f"{date_str}\nKhông có phòng nào trả."
        
    lines = []
    
    for branch, shifts in report_data.items():
        lines.append(f"--- {branch} ---")
        lines.append(date_str)
        
        if shifts['Sáng']:
            lines.append(f"Sáng: {shifts['Sáng'][0]}")
            for room in shifts['Sáng'][1:]:
                lines.append(f"      {room}")
                
        if shifts['Chiều']:
            lines.append(f"Chiều: {shifts['Chiều'][0]}")
            for room in shifts['Chiều'][1:]:
                lines.append(f"       {room}")
                
        if shifts['Tối']:
            lines.append(f"Tối: {shifts['Tối'][0]}")
            for room in shifts['Tối'][1:]:
                lines.append(f"     {room}")
                
        lines.append("") # Dòng trống phân cách các cơ sở
        
    return "\n".join(lines).strip()

def main():
    print("=== Tool Tổng Hợp Lịch Phòng ===")
    config = load_config()
    
    # Mặc định: Nếu chạy sau 20h, lấy báo cáo ngày mai. Nếu chạy sớm hơn, lấy báo cáo hôm nay.
    now = datetime.now(VN_TZ)
    if now.hour >= 20:
        target_date = (now + timedelta(days=1)).date()
        print(f"Giờ chạy: {now.strftime('%H:%M')}. Đang lấy báo cáo cho NGÀY MAI ({target_date.strftime('%d/%m/%Y')})")
    else:
        target_date = now.date()
        print(f"Giờ chạy: {now.strftime('%H:%M')}. Đang lấy báo cáo cho HÔM NAY ({target_date.strftime('%d/%m/%Y')})")
        
    # Lấy từ API:
    data = fetch_data(config, target_date)
    
    if not data:
        print("Không có dữ liệu hoặc lỗi khi lấy dữ liệu.")
        return
        
    print(f"Đã lấy {len(data)} bản ghi. Đang xử lý...")
    report_data = process_data(data, target_date)
    
    report_text = generate_report_text(report_data, target_date)
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_text)
        
    print(f"\nĐã xuất báo cáo ra file '{REPORT_FILE}':\n")
    print(report_text)

if __name__ == "__main__":
    main()
