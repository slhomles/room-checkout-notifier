import json
import requests
from datetime import datetime
import pytz
import os

VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_url": "https://ad.someli.vn/api/bookings/calendar", "authorization": "", "auth_type": "Bearer"}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {"api_url": "https://ad.someli.vn/api/bookings/calendar", "authorization": "", "auth_type": "Bearer"}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def fetch_data(config, target_date_str):
    """
    Lấy dữ liệu từ target_date - 1 ngày đến target_date + 1 ngày để đảm bảo cover khung 22h đêm trước.
    """
    from datetime import timedelta
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    
    fetch_start_date = target_date - timedelta(days=1)
    fetch_end_date = target_date + timedelta(days=1)
    
    vn_start_dt = VN_TZ.localize(datetime.combine(fetch_start_date, datetime.min.time()))
    vn_end_dt = VN_TZ.localize(datetime.combine(fetch_end_date, datetime.max.time()))
    
    utc_start_dt = vn_start_dt.astimezone(pytz.UTC)
    utc_end_dt = vn_end_dt.astimezone(pytz.UTC)
    
    start_str = utc_start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = utc_end_dt.strftime("%Y-%m-%dT%H:%M:%S.999Z")
    
    url = f"{config['api_url']}?startDate={start_str}&endDate={end_str}"
    
    headers = {}
    if config['authorization']:
        if config['auth_type'] == 'Bearer' and not config['authorization'].startswith('Bearer '):
            headers['Authorization'] = f"Bearer {config['authorization']}"
        elif config['auth_type'] == 'Bearer':
            headers['Authorization'] = config['authorization']
        elif config['auth_type'] == 'Cookie':
            headers['Cookie'] = config['authorization']
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('data', [])
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")

def process_data(data, target_date_str):
    from datetime import timedelta
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    prev_date = target_date - timedelta(days=1)
    
    # Khung thời gian lấy báo cáo: 22h hôm trước đến 21h59:59 hôm nay
    start_time = VN_TZ.localize(datetime.combine(prev_date, datetime.strptime("22:00:00", "%H:%M:%S").time()))
    end_time = VN_TZ.localize(datetime.combine(target_date, datetime.strptime("22:00:00", "%H:%M:%S").time()))

    checkouts = []
    checkins = {}

    for item in data:
        if 'roomId' not in item or not item['roomId']:
            continue
            
        room_id = item['roomId']['_id']
        room_code = item['roomId'].get('roomCode', 'Unknown')
        branch_name = item['branchId'].get('name', 'Unknown')
        
        try:
            checkout_utc = datetime.strptime(item['checkoutAt'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            checkout_vn = checkout_utc.astimezone(VN_TZ)
            
            checkin_utc = datetime.strptime(item['checkinAt'], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.UTC)
            checkin_vn = checkin_utc.astimezone(VN_TZ)
        except ValueError:
            continue
            
        if room_id not in checkins:
            checkins[room_id] = []
        checkins[room_id].append(checkin_vn)
        
        # Chỉ lấy các phòng checkout nằm trong khung thời gian [start_time, end_time)
        if start_time <= checkout_vn < end_time:
            checkouts.append({
                'room_id': room_id,
                'room_code': room_code,
                'branch': branch_name,
                'checkout_time': checkout_vn
            })

    # Tính toán giờ check-in tiếp theo cho từng checkout để làm tiêu chí sắp xếp phụ
    for co in checkouts:
        co_time = co['checkout_time']
        room_id = co['room_id']
        next_checkin_time = None
        for ci_time in sorted(checkins.get(room_id, [])):
            if ci_time >= co_time:
                next_checkin_time = ci_time
                break
        co['next_checkin_time'] = next_checkin_time

    # Thuật toán sắp xếp đa tầng:
    # 1. Giờ trả (sớm đến muộn)
    # 2. Giờ khách vào (sớm đến muộn). Nếu không có khách vào, xếp xuống cuối cùng.
    max_datetime = VN_TZ.localize(datetime.combine(target_date + timedelta(days=365), datetime.max.time()))
    checkouts.sort(key=lambda x: (
        x['checkout_time'],
        x['next_checkin_time'] if x['next_checkin_time'] else max_datetime
    ))

    report = {}
    
    # Khởi tạo cố định 16 cơ sở
    ALL_BRANCHES = [
        "HN01 - 119 Đình Thôn",
        "HN02 - 475 Đội Cấn",
        "HN03 - 24 Thổ Quan, Khâm Thiên",
        "HN04 - 59A Yên Bình",
        "HN06 - 192 Lê Trọng Tấn",
        "HN07 - 67 Lê Thanh Nghị",
        "HN09 - Nguyễn Khả Trạc",
        "HN10 - 73 Mễ Trì Thượng",
        "HN11 - 225 Nguyễn Ngọc Vũ",
        "HN12 - 37 Phùng Khoang",
        "HN13 - 195 Tôn Đức Thắng",
        "SG01 - 688 Quang Trung",
        "SG02 - 127 Lê Văn Thọ",
        "SG03 - 549 Tân Sơn",
        "SG04 - 448 Nguyễn Văn Khối",
        "SG05 - 347 Lê Văn Thọ"
    ]
    
    for branch_name in ALL_BRANCHES:
        report[branch_name] = {'Sáng': [], 'Chiều': [], 'Tối': []}
    
    for co in checkouts:
        branch = co['branch']
        if branch not in report:
            report[branch] = {'Sáng': [], 'Chiều': [], 'Tối': []}
            
        co_time = co['checkout_time']
        hour = co_time.hour
        
        next_checkin_str = ""
        ci_time = co['next_checkin_time']
        if ci_time:
            gap_hours = (ci_time - co_time).total_seconds() / 3600
            # User request: nếu phòng được thuê cách lúc được checkout ít nhất 1h thì thêm ngoặc.
            # However, previously I used >= 0 and they were happy, but I'll stick to their latest confirmation.
            # "ưu tiên các phòng có lịch vào gần hơn"
            if 0 <= gap_hours <= 12:
                time_ci_str = ci_time.strftime('%Hh%M').replace('h00', 'h')
                next_checkin_str = f" ({time_ci_str} vào)"
                
        time_co_str = co_time.strftime('%Hh%M').replace('h00', 'h')
        room_display = f"{co['room_code']} - {time_co_str} trả{next_checkin_str}"
        
        # Thêm ghi chú dọn 8h sáng cho các phòng trả đêm
        is_night_cleaning = (hour >= 22 or hour < 8)
        if is_night_cleaning:
            room_display += " (8h sáng dọn)"
            
        # Gom ca Sáng, Chiều, Tối
        if hour >= 22 or hour < 12:
            report[branch]['Sáng'].append(room_display)
        elif 12 <= hour < 18:
            report[branch]['Chiều'].append(room_display)
        elif 18 <= hour < 22:
            report[branch]['Tối'].append(room_display)
            
    return report

def generate_branch_text(branch_name, shifts, target_date_str):
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    date_str = target_date.strftime("Ngày %d/%m")
    
    lines = []
    lines.append(f"--- {branch_name} ---")
    lines.append(date_str)
    
    if not shifts['Sáng'] and not shifts['Chiều'] and not shifts['Tối']:
        lines.append("Không có phòng nào trả.")
        return "\n".join(lines)
    
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
            
    return "\n".join(lines)
