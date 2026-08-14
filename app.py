from flask import Flask, request, jsonify, render_template
import webbrowser
import threading
import os
from datetime import datetime
import pytz

import core

app = Flask(__name__)

# Cấu hình thư mục templates tĩnh (để Pyinstaller vẫn tìm thấy file)
import sys
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch', methods=['POST'])
def fetch_report():
    data = request.json
    target_date = data.get('date') # Format YYYY-MM-DD
    token = data.get('token')
    
    if not target_date:
        return jsonify({"error": "Vui lòng chọn ngày"}), 400
        
    if not token:
        return jsonify({"error": "Vui lòng nhập Token xác thực"}), 400
        
    auth_type = "Cookie" if "session_id=" in token else "Bearer"
    config = {
        "api_url": "https://ad.someli.vn/api/bookings/calendar",
        "authorization": token,
        "auth_type": auth_type
    }
        
    try:
        api_data = core.fetch_data(config, target_date)
        report_data = core.process_data(api_data, target_date)
        
        # Format the result to return to frontend
        branches = list(report_data.keys())
        branches.sort()
        
        # Lưu trữ lại report_text cho mỗi cơ sở
        formatted_reports = {}
        for branch in branches:
            formatted_reports[branch] = core.generate_branch_text(branch, report_data[branch], target_date)
            
        return jsonify({
            "status": "success",
            "branches": branches,
            "reports": formatted_reports
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
