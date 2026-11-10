# File: miniapp_html.py

MINIAPP_HTML = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>FAST IVAS</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

        :root {
            --bg: #0B1120; --surface: rgba(30, 41, 59, 0.7); --surface-hover: rgba(51, 65, 85, 0.8);
            --primary: #3b82f6; --primary-gradient: linear-gradient(135deg, #3b82f6, #8b5cf6);
            --success: #10b981; --danger: #ef4444; --warning: #f59e0b;
            --text: #f8fafc; --text-muted: #94a3b8; --border: rgba(255, 255, 255, 0.1);
            --radius: 16px; --shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); --glass-blur: blur(12px);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Outfit', sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background-color: var(--bg); background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 20%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 20%); color: var(--text); padding-bottom: 90px; overflow-x: hidden; min-height: 100vh; }
        button { cursor: pointer; font-family: inherit; border: none; outline: none; }

        #custom-modal { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.7); backdrop-filter: blur(5px); z-index: 9999; display: none; justify-content: center; align-items: center; padding: 20px; }
        #custom-modal.open { display: flex; }
        .modal-content { background: var(--bg); border: 1px solid var(--border); border-radius: 20px; padding: 24px; width: 100%; max-width: 340px; text-align: center; box-shadow: var(--shadow); animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275); }
        @keyframes popIn { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .modal-title { font-size: 20px; font-weight: 700; margin-bottom: 10px; color: var(--text); }
        .modal-msg { font-size: 15px; color: var(--text-muted); margin-bottom: 24px; line-height: 1.5; white-space: pre-wrap;}
        .modal-actions { display: flex; gap: 12px; }
        .modal-actions button { flex: 1; padding: 14px; border-radius: 12px; font-weight: 600; font-size: 15px; }

        .sidebar { position: fixed; top: 0; left: -300px; width: 300px; height: 100vh; background: rgba(15, 23, 42, 0.95); backdrop-filter: var(--glass-blur); z-index: 1000; transition: 0.4s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 4px 0 24px rgba(0,0,0,0.5); display: flex; flex-direction: column; border-right: 1px solid var(--border); }
        .sidebar.open { left: 0; }
        .overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); backdrop-filter: blur(4px); z-index: 999; display: none; opacity: 0; transition: opacity 0.3s; }
        .overlay.open { display: block; opacity: 1; }
        .sidebar-header { padding: 30px 20px; border-bottom: 1px solid var(--border); text-align: center; }
        .sidebar-header h2 { background: var(--primary-gradient); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 24px; font-weight: 700; }
        .sidebar-user { font-size: 13px; color: var(--text-muted); margin-top: 5px; }
        .sidebar-menu { flex: 1; padding: 20px 10px; overflow-y: auto; }
        .menu-item { display: flex; align-items: center; padding: 15px 20px; color: var(--text-muted); text-decoration: none; transition: 0.2s; font-weight: 500; font-size: 16px; border-radius: 12px; margin-bottom: 5px; }
        .menu-item:hover, .menu-item.active { background: var(--surface-hover); color: var(--text); }
        .menu-item .icon { margin-right: 15px; font-size: 22px; }
        .menu-admin { border-top: 1px solid var(--border); margin-top: 10px; padding-top: 10px; color: var(--danger); }

        .top-bar { display: flex; align-items: center; padding: 15px 20px; background: rgba(15, 23, 42, 0.8); backdrop-filter: var(--glass-blur); position: sticky; top: 0; z-index: 100; border-bottom: 1px solid var(--border); }
        .menu-btn { background: var(--surface); border: 1px solid var(--border); font-size: 20px; color: var(--text); margin-right: 15px; width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; transition: 0.2s; }
        .menu-btn:active { transform: scale(0.9); }
        .page-title { font-size: 20px; font-weight: 700; color: var(--text); flex: 1; text-align: center; padding-right: 55px;}

        .container { padding: 20px; animation: fadeIn 0.4s ease; }
        .view { display: none; }
        .view.active { display: block; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }

        .card { background: var(--surface); backdrop-filter: var(--glass-blur); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; box-shadow: var(--shadow); border: 1px solid var(--border); }
        .balance-card { background: var(--primary-gradient); border: none; position: relative; overflow: hidden; }
        .balance-card::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 60%); opacity: 0.5; }
        .balance-title { font-size: 15px; color: rgba(255,255,255,0.8); font-weight: 500; }
        .balance-amount { font-size: 36px; font-weight: 700; color: #fff; margin-top: 5px; text-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        
        .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .stat-box { background: var(--surface); padding: 15px; border-radius: var(--radius); text-align: center; border: 1px solid var(--border); }
        .stat-box .value { font-size: 22px; font-weight: 700; color: var(--text); margin-top: 5px; }
        .stat-box .label { font-size: 13px; color: var(--text-muted); font-weight: 500; }

        .form-group { margin-bottom: 15px; }
        .form-label { display: block; font-size: 14px; color: var(--text-muted); margin-bottom: 8px; font-weight: 500; }
        .form-control { width: 100%; padding: 14px 16px; border-radius: 12px; background: rgba(15, 23, 42, 0.6); color: var(--text); border: 1px solid var(--border); font-size: 16px; transition: 0.2s; outline: none; }
        .form-control:focus { border-color: var(--primary); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
        
        .btn { width: 100%; padding: 15px; border-radius: 12px; font-size: 16px; font-weight: 600; display: flex; justify-content: center; align-items: center; gap: 8px; transition: 0.2s; margin-top: 10px; color: #fff; }
        .btn:active { transform: scale(0.97); }
        .btn-primary { background: var(--primary-gradient); box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3); }
        .btn-success { background: var(--success); box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); }
        .btn-danger { background: var(--danger); box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3); }
        .btn-outline { background: transparent; border: 1px solid var(--border); }
        
        .order-card { background: var(--surface); border-radius: var(--radius); padding: 16px; margin-bottom: 15px; border: 1px solid var(--border); position: relative; overflow: hidden; transition: 0.3s; }
        .order-card.pending { border-left: 4px solid var(--warning); }
        .order-card.completed { border-left: 4px solid var(--success); background: rgba(16, 185, 129, 0.05); }
        .order-card.expired { border-left: 4px solid var(--danger); opacity: 0.6; }
        .order-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .order-phone { font-size: 18px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; }
        .order-badge { font-size: 12px; padding: 4px 10px; border-radius: 20px; font-weight: 600; background: rgba(255,255,255,0.1); display: flex; align-items: center; gap: 5px; }
        .order-info { display: flex; gap: 15px; font-size: 13px; color: var(--text-muted); margin-bottom: 12px; flex-wrap: wrap;}
        .order-info span { display: flex; align-items: center; gap: 5px; }
        
        .format-toggles { display: flex; gap: 15px; margin-bottom: 12px; font-size: 13px; background: rgba(15,23,42,0.5); padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); }
        .format-toggles label { display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--text-muted); }
        .format-toggles input[type="checkbox"] { accent-color: var(--primary); width: 15px; height: 15px; }

        .otp-box { background: rgba(16, 185, 129, 0.1); padding: 12px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border: 1px solid var(--success); }
        .otp-code { font-size: 22px; font-weight: 700; color: var(--success); letter-spacing: 3px; font-family: monospace;}
        
        .action-row { display: flex; gap: 10px; margin-top: 10px; }
        .btn-small { flex: 1; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600; display: flex; justify-content: center; align-items: center; gap: 5px; color: #fff; }
        .btn-small.copy { background: rgba(255,255,255,0.1); }
        .btn-small.cancel { background: rgba(239, 68, 68, 0.2); color: var(--danger); }
        
        .list-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .list-btn { background: var(--surface); border: 1px solid var(--border); padding: 14px; border-radius: 12px; text-align: left; color: var(--text); font-size: 14px; display: flex; flex-direction: column; gap: 6px; transition: 0.2s; }
        .list-btn:hover { background: var(--surface-hover); border-color: var(--primary); }
        .list-btn .name { font-weight: 600; display: flex; align-items: center; gap: 8px; font-size: 15px;}
        .list-btn .count { font-size: 12px; color: var(--text-muted); text-align: right; }

        .pagination { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; background: var(--surface); padding: 10px; border-radius: 12px; border: 1px solid var(--border); }
        .pagination button { flex: 1; padding: 10px; border-radius: 8px; background: rgba(255,255,255,0.1); color: var(--text); font-weight: 600; border: none; font-size: 14px; }
        .pagination button:disabled { opacity: 0.3; cursor: not-allowed; }
        .pagination span { flex: 1; text-align: center; font-size: 14px; color: var(--text-muted); font-weight: 500; }

        .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; height: 75px; background: rgba(15, 23, 42, 0.95); backdrop-filter: var(--glass-blur); display: flex; justify-content: space-around; align-items: center; border-top: 1px solid var(--border); z-index: 100; overflow-x: auto; }
        .nav-item { display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 10px; gap: 3px; background: none; transition: 0.2s; min-width: 16%; font-weight: 500; white-space: nowrap; }
        .nav-item .icon { font-size: 20px; transition: 0.2s; }
        .nav-item.active { color: var(--primary); }
        .nav-item.active .icon { transform: translateY(-3px); }

        .loading { text-align: center; padding: 30px; color: var(--text-muted); }
        .spinner { border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--primary); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        #toast { position: fixed; bottom: 95px; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--surface); backdrop-filter: var(--glass-blur); color: white; padding: 12px 24px; border-radius: 30px; font-weight: 500; border: 1px solid var(--border); box-shadow: var(--shadow); opacity: 0; transition: 0.3s; z-index: 2000; pointer-events: none; }
        #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

        .admin-tabs { display: flex; overflow-x: auto; gap: 8px; margin-bottom: 15px; padding-bottom: 5px; }
        .admin-tab { padding: 8px 16px; border-radius: 20px; background: var(--surface); color: var(--text-muted); white-space: nowrap; font-size: 14px; }
        .admin-tab.active { background: var(--primary); color: white; }
        
        .maint-toggle { display: flex; gap: 10px; margin-bottom: 20px; }
        .maint-btn { flex: 1; padding: 15px; border-radius: 12px; font-weight: 700; font-size: 16px; background: var(--surface); color: var(--text-muted); border: 2px solid transparent; }
        .maint-btn.on { background: rgba(16, 185, 129, 0.2); border-color: var(--success); color: var(--success); }
        .maint-btn.off { background: rgba(239, 68, 68, 0.2); border-color: var(--danger); color: var(--danger); }

        #maintenance-screen {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: var(--bg); z-index: 99999; display: none;
            flex-direction: column; align-items: center; justify-content: center;
            padding: 30px; text-align: center;
        }
        #maintenance-screen img { max-width: 100%; max-height: 40vh; border-radius: 16px; margin-bottom: 20px; box-shadow: var(--shadow); }
        #maintenance-screen h1 { color: var(--danger); margin-bottom: 15px; font-size: 28px; }
        #maintenance-screen p { color: var(--text); font-size: 18px; line-height: 1.6; white-space: pre-wrap; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div id="maintenance-screen">
        <img id="maint-img" src="" style="display: none;">
        <h1 data-i18n="maint_title">🛠 BẢO TRÌ HỆ THỐNG</h1>
        <p id="maint-text">Hệ thống đang được bảo trì. Vui lòng quay lại sau!</p>
    </div>

    <div id="toast">Copied!</div>

    <div id="custom-modal">
        <div class="modal-content">
            <div class="modal-title" id="modal-title">Xác nhận</div>
            <div class="modal-msg" id="modal-msg">Bạn có chắc chắn muốn thực hiện hành động này?</div>
            <div class="modal-actions">
                <button class="btn-outline" id="modal-btn-cancel">Hủy bỏ</button>
                <button class="btn-primary" id="modal-btn-confirm">Đồng ý</button>
            </div>
        </div>
    </div>

    <div class="overlay" id="overlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>FAST IVAS</h2>
            <div class="sidebar-user" id="side-user-info">Loading...</div>
        </div>
        <div class="sidebar-menu">
            <a href="#" class="menu-item active" onclick="navTo('home')"><span class="icon">🏠</span> <span data-i18n="home">Trang chủ</span></a>
            <a href="#" class="menu-item" onclick="navTo('buy')"><span class="icon">🛒</span> <span data-i18n="buy">Mua Số OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('tempmail')"><span class="icon">📧</span> <span>Tạo Temp Mail</span></a>
            <a href="#" class="menu-item" onclick="navTo('radar')"><span class="icon">📡</span> <span data-i18n="radar_title">Radar OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('history')"><span class="icon">📜</span> <span data-i18n="history">Lịch sử</span></a>
            <a href="#" class="menu-item" onclick="navTo('wallet')"><span class="icon">💵</span> <span data-i18n="wallet">Ví & Rút Tiền</span></a>
            <a href="#" class="menu-item" onclick="navTo('stats')"><span class="icon">📊</span> <span data-i18n="stats">Thống Kê</span></a>
            <a href="#" class="menu-item" onclick="navTo('leaderboard')"><span class="icon">🏆</span> <span data-i18n="leaderboard">Bảng Xếp Hạng</span></a>
            <a href="#" class="menu-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')"><span class="icon">📢</span> <span data-i18n="otp_group">OTP Group</span></a>
            <a href="#" class="menu-item" onclick="navTo('profile')"><span class="icon">👤</span> <span data-i18n="profile">Hồ Sơ</span></a>
            
            <a href="#" class="menu-item menu-admin" id="menu-admin" onclick="navTo('admin')" style="display: none;">
                <span class="icon">🛡</span> <span data-i18n="admin">ADMIN PANEL</span>
            </a>
        </div>
    </div>

    <div class="top-bar" id="main-top-bar">
        <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        <div class="page-title" id="top-title" data-i18n="home">Trang chủ</div>
    </div>

    <div class="container" id="main-container">
        <!-- HOME -->
        <div id="view-home" class="view active">
            <div class="card balance-card">
                <div class="balance-title" data-i18n="balance">Số dư khả dụng</div>
                <div class="balance-amount" id="home-balance">$0.000</div>
            </div>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label" data-i18n="today_otp">OTP Hôm Nay</div>
                    <div class="value" id="home-today-otps">0</div>
                </div>
                <div class="stat-box">
                    <div class="label" data-i18n="total_orders">Tổng Đơn</div>
                    <div class="value" id="home-total-orders">0</div>
                </div>
            </div>

            <h3 style="margin-bottom: 15px; font-size: 18px; font-weight: 600;" data-i18n="active_orders">⏳ Đơn Đang Chờ</h3>
            <div id="active-orders-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
        </div>

        <!-- BUY -->
        <div id="view-buy" class="view">
            <div class="card">
                <div class="form-group">
                    <label class="form-label" data-i18n="select_source">Chọn Nguồn Số</label>
                    <select class="form-control" id="provider-select" onchange="renderBuyOptions()">
                        <option value="MK">🎱 Numbers 1 (MK)</option>
                        <option value="NP">📱 Numbers 2 (NP)</option>
                        <option value="BASHA">🔢 Numbers BS (Basha)</option>
                        <option value="SLVN">🌐 Numbers 4 (SLVN)</option>
                    </select>
                </div>
            </div>
            <div id="buy-list-container" class="list-grid"></div>
        </div>

        <!-- TEMP MAIL -->
        <div id="view-tempmail" class="view">
            <div class="card" style="border: 1px solid rgba(249,115,22,0.3); background: rgba(30,41,59,0.8);">
                <div style="background: rgba(249,115,22,0.15); color: #fb923c; padding: 10px 14px; border-radius: 10px; font-size: 13px; margin-bottom: 15px; line-height: 1.5; border: 1px solid rgba(249,115,22,0.3);">
                    ⚠️ All users please note earn per otp is in beta version, testing,... it is not scheduled for now... It will start soon ...Thank You......
                </div>
                
                <div class="form-label" style="font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 15px;">Generate Temp Email</div>
                
                <div class="form-group">
                    <label class="form-label">Username (Optional)</label>
                    <input type="text" class="form-control" id="mail-username" placeholder="Prefix / username">
                </div>
                
                <div class="form-group">
                    <label class="form-label">Domain</label>
                    <select class="form-control" id="mail-domain-select">
                        <option value="">Auto-select random domain</option>
                    </select>
                </div>
                
                <button class="btn" style="background: linear-gradient(135deg, #f97316, #ea580c); box-shadow: 0 4px 15px rgba(249,115,22,0.4);" onclick="generateTempMail()">Generate Mail ...</button>
            </div>

            <div class="card" id="mail-active-box" style="display: none;">
                <div class="form-label" style="font-size: 16px; font-weight: bold; color: var(--success); margin-bottom: 10px;">📬 Live Inbox:</div>
                <div style="background: rgba(16,185,129,0.1); padding: 12px; border-radius: 10px; border: 1px solid var(--success); display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div id="current-mail-address" style="font-weight: 700; font-size: 15px; color: var(--text); word-break: break-all;"></div>
                    <button class="btn-small copy" style="background: var(--success); width: 85px;" onclick="copyText(document.getElementById('current-mail-address').innerText)">📋 Copy</button>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: 600; font-size: 15px;">📥 Messages:</span>
                    <button class="btn-small copy" style="width: auto; padding: 6px 12px;" onclick="loadMailMessages()">🔄 Refresh</button>
                </div>
                <div id="mail-messages-list">
                    <div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 15px;">No messages yet.</div>
                </div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">Recoverable Mails</div>
                <div id="mail-history-list">
                    <div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 10px;">No saved history yet.</div>
                </div>
            </div>
        </div>

        <!-- RADAR OTP -->
        <div id="view-radar" class="view">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div style="font-size: 16px; font-weight: 700; color: var(--text);">📡 Unified Radar Feed</div>
                <div style="font-size: 12px; color: var(--success); background: rgba(16,185,129,0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.3);" id="radar-records-count">0 records</div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span>📊 Platform Activity</span>
                    <span style="font-size: 12px; color: var(--text-muted);">Last 30 mins</span>
                </div>
                <div id="radar-platforms-chart" style="display: flex; flex-direction: column; gap: 10px;"></div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span>🌍 Country & Operator</span>
                    <span style="font-size: 12px; color: var(--text-muted);">Last 30 mins</span>
                </div>
                <div id="radar-countries-chart" style="display: flex; flex-direction: column; gap: 10px;"></div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                    <span>⚡ Live OTP Feed (Real-time)</span>
                    <span style="font-size: 11px; color: var(--primary);">● Live Updates</span>
                </div>
                <div id="radar-feed-list"><div class="loading"><div class="spinner"></div>Đang tải radar...</div></div>
            </div>
        </div>

        <!-- HISTORY -->
        <div id="view-history" class="view">
            <div style="margin-bottom: 15px; display: flex; justify-content: flex-end;">
                <button class="btn btn-danger" style="width: auto; padding: 10px 18px; font-size: 14px;" onclick="clearHistory()">🗑️ Clear History (Xóa Lịch Sử)</button>
            </div>
            <div id="history-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
            <div class="pagination" id="history-pagination" style="display: none;">
                <button id="btn-prev" onclick="changeHistoryPage(-1)" data-i18n="prev_page">← Trang trước</button>
                <span id="page-info">Trang 1 / 1</span>
                <button id="btn-next" onclick="changeHistoryPage(1)" data-i18n="next_page">Trang sau →</button>
            </div>
        </div>

        <!-- WALLET -->
        <div id="view-wallet" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="ton_wallet">💵 Ví TON</div>
                <div class="form-group">
                    <input type="text" class="form-control" id="ton-address" placeholder="UQ... hoặc EQ...">
                </div>
                <button class="btn btn-primary" onclick="saveWallet()" data-i18n="save_address">Lưu Địa Chỉ</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="withdraw">💰 Rút Tiền</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px;">
                    <button class="btn-small copy" onclick="setWithdrawAmount(1)">$1</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(2)">$2</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(5)">$5</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(8)">$8</button>
                </div>
                <button class="btn-small copy" style="width: 100%; margin-bottom: 15px; background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.4); color: #93c5fd;" onclick="setWithdrawAmount('max')" data-i18n="withdraw_all">
                    ⚡ Rút Toàn Bộ (Phí $0.1)
                </button>
                <div class="form-group">
                    <input type="number" class="form-control" id="withdraw-amount" placeholder="Nhập số tiền ($)" step="0.1">
                </div>
                <button class="btn btn-success" onclick="requestWithdraw()" data-i18n="send_request">Gửi Yêu Cầu</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="invite_friends">💌 Mời Bạn Bè</div>
                <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 8px; word-break: break-all; font-size: 13px; margin-bottom: 10px; border: 1px solid var(--border);" id="ref-link"></div>
                <button class="btn btn-outline" onclick="copyRef()" data-i18n="copy_link">📋 Sao Chép Link</button>
            </div>
        </div>

        <!-- STATS -->
        <div id="view-stats" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="stats_today">📊 THỐNG KÊ HÔM NAY <span style="font-size: 12px; color: var(--success);" id="stats-realtime-indicator">● Real-time</span></div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="label" data-i18n="total_otp">Tổng OTP</div>
                        <div class="value" id="stats-total-otps" style="color: var(--primary);">0</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="stats_country">🌍 OTP THEO QUỐC GIA</div>
                <div id="stats-countries-list"></div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="stats_platform">📱 OTP THEO NỀN TẢNG</div>
                <div id="stats-platforms-list"></div>
            </div>
        </div>

        <!-- LEADERBOARD -->
        <div id="view-leaderboard" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="top_10">🏆 TOP 10 CAO THỦ</div>
                <div id="leaderboard-list">
                    <div class="loading"><div class="spinner"></div>Đang tải...</div>
                </div>
            </div>
        </div>

        <!-- PROFILE -->
        <div id="view-profile" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="your_profile">👤 HỒ SƠ CỦA BẠN</div>
                <div id="profile-info" style="font-size: 15px; line-height: 2;"></div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="language">🌐 Ngôn Ngữ (Language)</div>
                <select class="form-control" id="lang-select" onchange="changeLanguage(this.value)">
                    <option value="vi">🇻🇳 Tiếng Việt</option>
                    <option value="en">🇬🇧 English</option>
                </select>
            </div>
        </div>

        <!-- ADMIN -->
        <div id="view-admin" class="view">
            <div class="admin-tabs">
                <button class="admin-tab active" onclick="switchAdminTab('overview')">Tổng quan</button>
                <button class="admin-tab" onclick="switchAdminTab('users')">Users</button>
                <button class="admin-tab" onclick="switchAdminTab('broadcast')">📡 Radar TB</button>
                <button class="admin-tab" onclick="switchAdminTab('withdraw')">Rút tiền</button>
                <button class="admin-tab" onclick="switchAdminTab('bs')">Số BS</button>
                <button class="admin-tab" onclick="switchAdminTab('cmds')">Commands</button>
                <button class="admin-tab" onclick="switchAdminTab('maint')">Bảo trì</button>
            </div>

            <div id="admin-tab-overview" class="admin-tab-content">
                <div class="stats-grid">
                    <div class="stat-box"><div class="label">Users</div><div class="value" id="admin-total-users">0</div></div>
                    <div class="stat-box"><div class="label">Orders</div><div class="value" id="admin-total-orders">0</div></div>
                </div>
                <div class="card" style="text-align: center; font-size: 18px; font-weight: bold;">
                    Trạng thái Bot: <span id="admin-bot-status" style="color: var(--success);">🟢 Đang hoạt động</span>
                </div>
                <div class="card">
                    <div class="form-label">Chi tiết kho số</div>
                    <div id="admin-stock-info"></div>
                </div>
            </div>

            <div id="admin-tab-users" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div id="admin-user-list" class="loading">Đang tải...</div>
                </div>
            </div>

            <!-- ADMIN BROADCAST TAB TÍCH HỢP THANH TRƯỢT % (10% - 100%) NHƯ BRO YÊU CẦU -->
            <div id="admin-tab-broadcast" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label" style="font-size:16px; font-weight:bold; margin-bottom:10px;">📡 Gửi Thông Báo Radar Nền Tảng</div>
                    <div style="font-size:13px; color:var(--text-muted); margin-bottom:12px;">Chọn nhanh nền tảng quốc tế / mạng xã hội đang có tỷ lệ nhận OTP cao:</div>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 15px;">
                        <button class="btn-small copy" onclick="selectRadarPlatform('Instagram')">📸 Instagram</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Facebook')">📘 Facebook</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('TikTok')">🎬 TikTok</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Threads')">🧵 Threads</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Twitter / X')">🐦 Twitter / X</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('imo')">📱 imo</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('1xbet')">⚽ 1xbet</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Telegram')">✈️ Telegram</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('WhatsApp')">💬 WhatsApp</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Zalo')">🇻🇳 Zalo</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Google')">🇬 Google</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('YouTube')">▶️ YouTube</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Discord')">🎮 Discord</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Steam')">🎮 Steam</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Netflix')">🍿 Netflix</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Spotify')">🎧 Spotify</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Shopee')">🛍️ Shopee</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Lazada')">🟠 Lazada</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Amazon')">📦 Amazon</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Binance/Crypto')">🪙 Binance/Crypto</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('PayPal')">🅿️ PayPal</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Tinder / Dating')">❤️ Tinder / Dating</button>
                        <button class="btn-small copy" style="grid-column: span 2;" onclick="selectRadarPlatform('Tất cả mạng xã hội & Dịch vụ quốc tế khác')">🌐 Tất cả mạng xã hội quốc tế khác</button>
                    </div>

                    <div class="form-group">
                        <label class="form-label">Nền tảng đã chọn:</label>
                        <input type="text" class="form-control" id="broadcast-platform" value="Instagram">
                    </div>

                    <!-- THANH TRƯỢT % TỶ LỆ NHẬN OTP (10% ĐẾN 100%) -->
                    <div class="form-group">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <label class="form-label" style="margin-bottom:0;">⚡ Tỷ lệ nhận OTP (%):</label>
                            <span id="slider-percent-val" style="font-weight: 700; color: var(--success); font-size: 16px;">100% (Mức 10)</span>
                        </div>
                        <input type="range" id="broadcast-rate-slider" min="1" max="10" value="10" class="form-control" style="padding: 0; height: 8px; accent-color: var(--success); cursor: pointer;" oninput="updateRateSlider(this.value)">
                    </div>

                    <div class="form-group">
                        <label class="form-label">Nội dung thông báo (Tự động cập nhật tỷ lệ %):</label>
                        <textarea class="form-control" id="broadcast-msg" rows="4" placeholder="Nhập nội dung thông báo thủ công..."></textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Ảnh đính kèm (Tùy chọn):</label>
                        <input type="file" id="broadcast-image" class="form-control" accept="image/*">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-success" style="flex:1;" onclick="sendRadarBroadcast()">🚀 Gửi Thông Báo</button>
                        <button class="btn btn-danger" style="flex:1;" onclick="clearRadarBroadcast()">❌ Hủy / Đặt lại</button>
                    </div>
                </div>
            </div>
            
            <div id="admin-tab-user-detail" class="admin-tab-content" style="display: none;">
                <button class="btn btn-outline" style="margin-bottom:15px;" onclick="switchAdminTab('users')">⬅️ Quay lại danh sách</button>
                <div class="card"><div id="admin-user-detail-info"></div></div>
                <div class="card">
                    <div class="form-label">Thống kê số đã lấy</div>
                    <div id="admin-user-detail-stats" style="display:flex; justify-content:space-around; text-align:center;"></div>
                </div>
                <div class="card">
                    <div class="form-label">Danh sách số đã lấy</div>
                    <div id="admin-user-detail-orders"></div>
                    <div class="pagination" id="user-detail-pagination" style="display: none;">
                        <button id="btn-user-prev" onclick="changeUserDetailPage(-1)">← Trang trước</button>
                        <span id="user-page-info">Trang 1 / 1</span>
                        <button id="btn-user-next" onclick="changeUserDetailPage(1)">Trang sau →</button>
                    </div>
                </div>
            </div>

            <div id="admin-tab-withdraw" class="admin-tab-content" style="display: none;">
                <div class="card"><div class="form-label">💸 Duyệt Rút Tiền</div><div id="admin-wd-list"></div></div>
            </div>

            <div id="admin-tab-bs" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label">➕ Thêm Số BS</div>
                    <textarea class="form-control" id="bs-input" rows="4" placeholder="Mỗi dòng 1 số..."></textarea>
                    <button class="btn btn-success" onclick="addBsNumbers()">Thêm Số</button>
                </div>
                <div class="card"><div class="form-label">⚙️ Quản lý số BS</div><div id="admin-bs-list"></div></div>
            </div>

            <div id="admin-tab-cmds" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label">🛠 Admin Commands</div>
                    <div class="grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <button class="btn btn-outline" onclick="runAdminCmd('health')">Health Check</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('pollnow')">Force Poll OTP</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('whoami')">MK Account</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('testnp')">Test NP API</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('radar')">MK Radar</button>
                    </div>
                    <div id="cmd-output" style="margin-top: 15px; background: #000; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; min-height: 50px;"></div>
                </div>
            </div>

            <div id="admin-tab-maint" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label">🛠 Trạng thái hệ thống</div>
                    <div class="maint-toggle">
                        <button id="btn-maint-on" class="maint-btn" onclick="toggleMaintenance(true)">🟢 ON (Hoạt động)</button>
                        <button id="btn-maint-off" class="maint-btn" onclick="toggleMaintenance(false)">🔴 OFF (Bảo trì)</button>
                    </div>
                </div>
                <div class="card" id="maint-form-container" style="display: none;">
                    <div class="form-label">📝 Nội dung thông báo</div>
                    <div style="display:flex; gap:5px; margin-bottom:10px;">
                        <button class="btn-small copy" onclick="setMaintTemplate(1)">Mẫu 1</button>
                        <button class="btn-small copy" onclick="setMaintTemplate(2)">Mẫu 2</button>
                    </div>
                    <textarea class="form-control" id="maint-msg" rows="4" placeholder="Nhập thông báo bảo trì..."></textarea>
                    <div class="form-label" style="margin-top:10px;">🖼 Ảnh đính kèm (Tùy chọn)</div>
                    <input type="file" id="maint-image" class="form-control" accept="image/*">
                    <button class="btn btn-danger" style="margin-top:15px;" onclick="submitMaintenance()">Xác nhận BẢO TRÌ & Gửi thông báo</button>
                </div>
            </div>
        </div>
    </div>

    <div class="bottom-nav" id="main-bottom-nav">
        <button class="nav-item active" id="nav-home" onclick="navTo('home')"><span class="icon">🏠</span><span data-i18n="home">Trang chủ</span></button>
        <button class="nav-item" id="nav-buy" onclick="navTo('buy')"><span class="icon">🛒</span><span data-i18n="buy">Mua số</span></button>
        <button class="nav-item" id="nav-tempmail" onclick="navTo('tempmail')"><span class="icon">📧</span><span>Temp Mail</span></button>
        <button class="nav-item" id="nav-radar" onclick="navTo('radar')"><span class="icon">📡</span><span data-i18n="radar_title">Radar</span></button>
        <button class="nav-item" id="nav-history" onclick="navTo('history')"><span class="icon">📜</span><span data-i18n="history">Lịch sử</span></button>
        <button class="nav-item" id="nav-wallet" onclick="navTo('wallet')"><span class="icon">💵</span><span data-i18n="wallet">Ví</span></button>
    </div>

    <script>
        const tg = window.Telegram?.WebApp || {
            initData: "", expand: function() {}, setHeaderColor: function() {}, setBackgroundColor: function() {}, ready: function() {}, showAlert: function(msg) { alert(msg); }
        };

        try {
            if (tg.expand) tg.expand();
            if (tg.setHeaderColor) tg.setHeaderColor('#0B1120');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#0B1120');
            if (tg.ready) tg.ready();
        } catch (e) {}

        let userData = null;
        let autoRefreshInterval = null;
        let statsRefreshInterval = null;
        let radarRefreshInterval = null;
        let currentHistoryPage = 1;
        let totalHistoryPages = 1;
        let currentLang = 'vi';
        let currentAdminUid = null;
        let currentUserDetailPage = 1;
        let totalUserDetailPages = 1;
        let isMaintenanceOn = false;
        let lastKnownCompletedOrders = new Set();
        let currentActiveMailAddress = null;

        const translations = {
            vi: { 
                home: "Trang chủ", buy: "Buy OTP Number", radar_title: "Radar OTP", history: "Lịch sử", wallet: "Ví & Rút Tiền", leaderboard: "Bảng Xếp Hạng", stats: "Thống Kê", profile: "Hồ Sơ", admin: "ADMIN PANEL", otp_group: "OTP Group",
                balance: "Số dư khả dụng", today_otp: "OTP Hôm Nay", total_orders: "Tổng Đơn", active_orders: "⏳ Đơn Đang Chờ", 
                select_source: "Chọn Nguồn Số", ton_wallet: "💵 Ví TON", save_address: "Lưu Địa Chỉ", withdraw: "💰 Rút Tiền", withdraw_all: "⚡ Rút Toàn Bộ (Phí $0.1)", send_request: "Gửi Yêu Cầu", 
                invite_friends: "💌 Mời Bạn Bè", copy_link: "📋 Sao Chép Link", top_10: "🏆 TOP 10 CAO THỦ", your_profile: "👤 HỒ SƠ CỦA BẠN", language: "🌐 Ngôn Ngữ (Language)", 
                users: "Người dùng", orders: "Đơn hàng", approve_wd: "💸 Duyệt Rút Tiền", add_bs: "➕ Thêm Số BS", add_number: "Thêm Số", 
                prev_page: "← Trang trước", next_page: "Trang sau →", total_otp: "Tổng OTP đã nhận", joined: "Ngày tham gia", name: "Tên", balance_label: "Số dư",
                stats_today: "📊 THỐNG KÊ HÔM NAY", stats_country: "🌍 OTP THEO QUỐC GIA", stats_platform: "📱 OTP THEO NỀN TẢNG", maint_title: "🛠 BẢO TRÌ HỆ THỐNG",
                remove_plus: "Bỏ dấu (+)", national_fmt: "Định dạng nội địa"
            },
            en: { 
                home: "Home", buy: "Buy OTP Number", radar_title: "Radar OTP", history: "History", wallet: "Wallet & Withdraw", leaderboard: "Leaderboard", stats: "Statistics", profile: "Profile", admin: "ADMIN PANEL", otp_group: "OTP Group",
                balance: "Available Balance", today_otp: "Today's OTP", total_orders: "Total Orders", active_orders: "⏳ Active Orders", 
                select_source: "Select Source", ton_wallet: "💵 TON Wallet", save_address: "Save Address", withdraw: "💰 Withdraw", withdraw_all: "⚡ Withdraw All (Fee $0.1)", send_request: "Send Request", 
                invite_friends: "💌 Invite Friends", copy_link: "📋 Copy Link", top_10: "🏆 TOP 10 PLAYERS", your_profile: "👤 YOUR PROFILE", language: "🌐 Language", 
                users: "Users", orders: "Orders", approve_wd: "💸 Approve Withdrawals", add_bs: "➕ Add BS Numbers", add_number: "Add Number", 
                prev_page: "← Prev", next_page: "Next →", total_otp: "Total OTPs Received", joined: "Joined", name: "Name", balance_label: "Balance",
                stats_today: "📊 TODAY'S STATISTICS", stats_country: "🌍 OTP BY COUNTRY", stats_platform: "📱 OTP BY PLATFORM", maint_title: "🛠 SYSTEM MAINTENANCE",
                remove_plus: "Remove (+)", national_fmt: "National Format"
            }
        };

        function applyLanguage(lang) {
            if (!translations[lang]) lang = 'vi';
            currentLang = lang;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) el.innerText = translations[lang][key];
            });
            const langSelect = document.getElementById('lang-select');
            if (langSelect) langSelect.value = lang;
        }

        async function changeLanguage(lang) {
            try { await api('/api/mini/language', 'POST', { language: lang }); } catch(e) {}
            applyLanguage(lang);
            showToast(lang === 'en' ? "Language changed to English!" : "Đã đổi sang Tiếng Việt!");
        }

        function showCustomModal(title, msg) {
            return new Promise((resolve) => {
                document.getElementById('modal-title').innerText = title;
                document.getElementById('modal-msg').innerText = msg;
                document.getElementById('custom-modal').classList.add('open');
                const btnConfirm = document.getElementById('modal-btn-confirm');
                const btnCancel = document.getElementById('modal-btn-cancel');
                const handleConfirm = () => { cleanup(); resolve(true); };
                const handleCancel = () => { cleanup(); resolve(false); };
                const cleanup = () => {
                    document.getElementById('custom-modal').classList.remove('open');
                    btnConfirm.removeEventListener('click', handleConfirm);
                    btnCancel.removeEventListener('click', handleCancel);
                };
                btnConfirm.addEventListener('click', handleConfirm);
                btnCancel.addEventListener('click', handleCancel);
            });
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2500);
        }

        async function api(path, method = 'GET', body = null) {
            const opts = { method, headers: { 'X-Telegram-Init-Data': tg.initData || '', 'Content-Type': 'application/json' } };
            if (body) opts.body = JSON.stringify(body);
            try {
                const res = await fetch(path, opts);
                const text = await res.text();
                try { return JSON.parse(text); } catch(e) { return { error: 'Lỗi Server: ' + text.substring(0, 50) }; }
            } catch (e) { return { error: 'Lỗi kết nối máy chủ!' }; }
        }

        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('open');
            document.getElementById('overlay').classList.toggle('open');
        }

        function navTo(viewId) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.menu-item').forEach(v => v.classList.remove('active'));

            const targetView = document.getElementById('view-' + viewId);
            if (targetView) targetView.classList.add('active');
            const navBtn = document.getElementById('nav-' + viewId);
            if (navBtn) navBtn.classList.add('active');

            const titleKey = { home: 'home', buy: 'buy', radar: 'radar_title', history: 'history', wallet: 'wallet', leaderboard: 'leaderboard', stats: 'stats', profile: 'profile', admin: 'admin' }[viewId];
            const topTitle = document.getElementById('top-title');
            if (topTitle && titleKey && translations[currentLang][titleKey]) topTitle.innerText = translations[currentLang][titleKey];

            if (document.getElementById('sidebar').classList.contains('open')) toggleSidebar();

            try {
                if (viewId === 'home') loadHome();
                if (viewId === 'buy') renderBuyOptions();
                if (viewId === 'tempmail') loadTempMailData();
                if (viewId === 'radar') { loadRadarFeed(); startRadarRefresh(); } else { stopRadarRefresh(); }
                if (viewId === 'history') loadHistory(1);
                if (viewId === 'wallet') loadWallet();
                if (viewId === 'stats') { loadStats(); startStatsRefresh(); } else { stopStatsRefresh(); }
                if (viewId === 'leaderboard') loadLeaderboard();
                if (viewId === 'profile') loadProfile();
                if (viewId === 'admin') loadAdmin();
            } catch(err) {}
        }

        async function loadUserData() {
            const data = await api('/api/mini/me');
            if (data.error) return;
            userData = data;
            if (data.user.language) applyLanguage(data.user.language);

            isMaintenanceOn = (data.maintenance === 'on');
            if (isMaintenanceOn && !data.is_admin) {
                document.getElementById('maintenance-screen').style.display = 'flex';
                document.getElementById('maint-text').innerText = data.maint_message || "Hệ thống đang bảo trì. Vui lòng quay lại sau!";
                const img = document.getElementById('maint-img');
                if (data.maint_image) { img.src = data.maint_image; img.style.display = 'block'; } else { img.style.display = 'none'; }
                document.getElementById('main-top-bar').style.display = 'none';
                document.getElementById('main-container').style.display = 'none';
                document.getElementById('main-bottom-nav').style.display = 'none';
                return;
            } else {
                document.getElementById('maintenance-screen').style.display = 'none';
                document.getElementById('main-top-bar').style.display = 'flex';
                document.getElementById('main-container').style.display = 'block';
                document.getElementById('main-bottom-nav').style.display = 'flex';
            }

            document.getElementById('home-balance').innerText = '$' + (data.user.usd_milli / 1000).toFixed(3);
            document.getElementById('home-today-otps').innerText = data.today_otps;
            document.getElementById('home-total-orders').innerText = data.total_orders;
            document.getElementById('side-user-info').innerText = 'ID: ' + data.user.id + ' | ' + (data.user.first_name || 'User');
            document.getElementById('ton-address').value = data.user.wallet_ton || '';
            document.getElementById('ref-link').innerText = data.referral_link;
            
            const menuAdmin = document.getElementById('menu-admin');
            if (menuAdmin) menuAdmin.style.display = data.is_admin ? 'flex' : 'none';
        }

        async function loadHome(silent = false) {
            if (!silent) await loadUserData();
            const listDiv = document.getElementById('active-orders-list');
            if (!listDiv) return;
            
            const data = await api('/api/mini/orders/active');
            if (!data.orders) return;
            
            if (data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading" style="background: var(--surface); border-radius: 16px; border: 1px dashed var(--border);">Không có đơn nào đang chờ.</div>';
                return;
            }

            data.orders.forEach(o => {
                if (o.status === 'COMPLETED' && o.otp && !lastKnownCompletedOrders.has(o.id)) {
                    lastKnownCompletedOrders.add(o.id);
                    showToast(`🎉 Đã nhận mã OTP cho số ${o.phone}: ${o.otp}`);
                }
            });

            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, false)).join('');
        }

        async function loadTempMailData() {
            const domainSel = document.getElementById('mail-domain-select');
            const historyDiv = document.getElementById('mail-history-list');
            if (!domainSel || !historyDiv) return;

            const domRes = await api('/api/mini/mail/domains');
            if (domRes.domains && domRes.domains.length > 0) {
                domainSel.innerHTML = domRes.domains.map(d => `<option value="${d}">${d}</option>`).join('');
            } else {
                domainSel.innerHTML = `<option value="inbox.numberpanel.tech">inbox.numberpanel.tech</option>`;
            }

            const histRes = await api('/api/mini/mail/history');
            if (histRes.history && histRes.history.length > 0) {
                historyDiv.innerHTML = histRes.history.map(h => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border);">
                        <span style="font-size: 14px; font-weight: 500; word-break: break-all;">${h.address}</span>
                        <button class="btn-small copy" style="width: auto; padding: 6px 12px;" onclick="selectMailBox('${h.address}')">📥 Xem</button>
                    </div>
                `).join('');
            } else {
                historyDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 14px;">Chưa có hòm thư nào được tạo.</div>';
            }
        }

        async function generateTempMail() {
            const username = document.getElementById('mail-username').value;
            const domain = document.getElementById('mail-domain-select').value;
            const res = await api('/api/mini/mail/generate', 'POST', { username, domain });
            if (res.success && res.mail) {
                selectMailBox(res.mail.address);
                loadTempMailData();
                showToast('Đã tạo hòm thư thành công!');
            } else { alert(res.error || 'Lỗi tạo email ảo'); }
        }

        function selectMailBox(address) {
            currentActiveMailAddress = address;
            document.getElementById('current-mail-address').innerText = address;
            document.getElementById('mail-active-box').style.display = 'block';
            loadMailMessages();
        }

        async function loadMailMessages() {
            if (!currentActiveMailAddress) return;
            const msgList = document.getElementById('mail-messages-list');
            msgList.innerHTML = '<div class="spinner"></div>';
            const res = await api(`/api/mini/mail/messages?address=${encodeURIComponent(currentActiveMailAddress)}`);
            if (res.messages && res.messages.length > 0) {
                msgList.innerHTML = res.messages.map(m => `
                    <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 8px; border: 1px solid var(--border); margin-top: 8px;">
                        <div style="font-weight: bold; font-size: 14px; color: var(--primary); margin-bottom: 4px;">📩 ${m.sender || 'Sender'}</div>
                        <div style="font-size: 13px; color: var(--text); white-space: pre-wrap;">${m.snippet || m.body || 'Không có nội dung'}</div>
                    </div>
                `).join('');
            } else {
                msgList.innerHTML = '<div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 15px;">Hộp thư chưa có tin nhắn nào.</div>';
            }
        }

        function formatPhoneNumber(phone, removePlus, nationalFormat) {
            let p = String(phone || '').trim();
            if (nationalFormat) {
                const prefixes = ["84", "62", "60", "65", "66", "63", "95", "855", "856", "1", "44", "7", "81", "82", "86", "91", "92", "880", "234", "254", "27", "20", "212", "213", "216", "218", "249", "251", "255", "256", "263", "260", "233", "221", "224", "231", "232", "225", "237", "243", "242", "241", "235", "227", "223", "226", "228", "229", "220", "222", "245", "30", "31", "32", "33", "34", "36", "39", "40", "41", "43", "45", "46", "47", "48", "49", "351", "352", "353", "358", "370", "371", "372", "380", "420", "421", "90", "972", "971", "966", "974", "965", "968", "973", "962", "961", "964", "98", "93", "94", "977", "975", "960", "673", "670", "61", "64", "52", "55", "54", "56", "57", "58", "51", "593", "591", "595", "598", "509", "244", "267", "266", "261", "258", "264", "970", "250", "252", "998", "967"];
                prefixes.sort((a,b) => b.length - a.length);
                let cleaned = p.replace(/^\+/, '');
                for (let pfx of prefixes) {
                    if (cleaned.startsWith(pfx) && cleaned.length > pfx.length + 3) {
                        cleaned = cleaned.substring(pfx.length);
                        if (pfx === '84' && !cleaned.startsWith('0')) cleaned = '0' + cleaned;
                        p = cleaned;
                        break;
                    }
                }
            }
            if (removePlus) p = p.replace(/^\+/, '');
            return p;
        }

        function updatePhoneDisplay(orderId, rawPhone) {
            const rpEl = document.getElementById('phone-text-' + orderId);
            const cbPlus = document.getElementById('chk-plus-' + orderId);
            const cbNat = document.getElementById('chk-nat-' + orderId);
            if (!rpEl) return;
            rpEl.innerText = formatPhoneNumber(rawPhone, cbPlus ? cbPlus.checked : false, cbNat ? cbNat.checked : false);
        }

        function formatTimeAgo(timestamp) {
            const nowSec = Math.floor(Date.now() / 1000);
            let tSec = typeof timestamp === 'number' ? timestamp : Math.floor(new Date(timestamp).getTime() / 1000);
            if (isNaN(tSec)) return "Just now";
            const diff = Math.max(0, nowSec - tSec);
            if (diff < 5) return "Just now";
            if (diff < 60) return diff + "s ago";
            if (diff < 3600) return Math.floor(diff / 60) + "m ago";
            return Math.floor(diff / 3600) + "h ago";
        }

        async function loadRadarFeed() {
            const feedDiv = document.getElementById('radar-feed-list');
            const platDiv = document.getElementById('radar-platforms-chart');
            const ctryDiv = document.getElementById('radar-countries-chart');
            const countEl = document.getElementById('radar-records-count');
            if (!feedDiv) return;

            const data = await api('/api/mini/radar');
            if (data.error) return feedDiv.innerHTML = `<div style="color:var(--danger)">${data.error}</div>`;
            if (countEl) countEl.innerText = (data.total_records || (data.items ? data.items.length : 0)) + " records";

            if (platDiv && data.platforms) {
                const maxPlat = Math.max(...data.platforms.map(p => p.count), 1);
                platDiv.innerHTML = data.platforms.map(p => `
                    <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 12px; border: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 14px;">
                            <span style="font-weight: 600;">${p.icon} ${p.name}</span>
                            <span style="color: var(--primary); font-weight: bold;">${p.count}</span>
                        </div>
                        <div style="width: 100%; background: rgba(255,255,255,0.08); height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="width: ${Math.round((p.count / maxPlat) * 100)}%; background: var(--primary); height: 100%; border-radius: 4px;"></div>
                        </div>
                    </div>
                `).join('');
            }

            if (ctryDiv && data.countries) {
                const maxCtry = Math.max(...data.countries.map(c => c.count), 1);
                ctryDiv.innerHTML = data.countries.map(c => `
                    <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 12px; border: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 14px;">
                            <span style="font-weight: 600;">${c.flag} ${c.name}</span>
                            <span style="color: var(--success); font-weight: bold;">${c.count} OTPs</span>
                        </div>
                        <div style="width: 100%; background: rgba(255,255,255,0.08); height: 8px; border-radius: 4px; overflow: hidden;">
                            <div style="width: ${Math.round((c.count / maxCtry) * 100)}%; background: var(--success); height: 100%; border-radius: 4px;"></div>
                        </div>
                    </div>
                `).join('');
            }

            if (!data.items || data.items.length === 0) return feedDiv.innerHTML = '<div class="loading">Không có dữ liệu Radar feed.</div>';

            feedDiv.innerHTML = data.items.map(i => `
                <div class="order-card" style="border-left-color: var(--primary);">
                    <div class="order-header">
                        <div class="order-phone">${i.phone}</div>
                        <div class="order-badge" style="color: var(--success);">🟢 NEW</div>
                    </div>
                    <div class="order-info">
                        <span>${i.flag} ${i.country}</span>
                        <span>🔧 ${i.operator}</span>
                        <span style="color: var(--warning);" class="radar-time" data-timestamp="${i.timestamp}">⏳ ${formatTimeAgo(i.timestamp)}</span>
                    </div>
                    <div class="otp-box">
                        <div>
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">Nội dung SMS:</div>
                            <div style="font-size: 14px; font-weight: 500; color: var(--text);">${i.message}</div>
                        </div>
                    </div>
                </div>
            `).join('');
        }

        setInterval(() => {
            document.querySelectorAll('.radar-time').forEach(el => {
                const ts = parseInt(el.getAttribute('data-timestamp'));
                if (!isNaN(ts)) el.innerText = '⏳ ' + formatTimeAgo(ts);
            });
        }, 1000);

        function startRadarRefresh() { stopRadarRefresh(); radarRefreshInterval = setInterval(loadRadarFeed, 3000); }
        function stopRadarRefresh() { if (radarRefreshInterval) clearInterval(radarRefreshInterval); }

        async function loadStats() {
            const listC = document.getElementById('stats-countries-list');
            const listP = document.getElementById('stats-platforms-list');
            if (!listC || !listP) return;
            
            const data = await api('/api/mini/stats');
            if(data.error) return;

            document.getElementById('stats-total-otps').innerText = data.total_otps;
            listC.innerHTML = data.countries.length === 0 ? '<div style="color:var(--text-muted);font-size:14px;">Chưa có dữ liệu hôm nay.</div>' : data.countries.map(c => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                    <span>${c.flag} ${c.country}</span><b style="color:var(--primary);">${c.count}</b>
                </div>
            `).join('');

            listP.innerHTML = data.platforms.length === 0 ? '<div style="color:var(--text-muted);font-size:14px;">Chưa có dữ liệu hôm nay.</div>' : data.platforms.map(p => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                    <span>${p.icon} ${p.platform}</span><b style="color:var(--success);">${p.count}</b>
                </div>
            `).join('');
        }

        function startStatsRefresh() { stopStatsRefresh(); statsRefreshInterval = setInterval(loadStats, 5000); }
        function stopStatsRefresh() { if (statsRefreshInterval) clearInterval(statsRefreshInterval); }

        async function loadLeaderboard() {
            const listDiv = document.getElementById('leaderboard-list');
            if (!listDiv) return;
            const data = await api('/api/mini/leaderboard');
            if (!data.leaderboard || data.leaderboard.length === 0) return listDiv.innerHTML = '<div class="loading">Chưa có dữ liệu.</div>';
            listDiv.innerHTML = data.leaderboard.map((u, i) => `
                <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border);">
                    <div><div>${i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '🔹'} ${u.name}</div><div style="font-size: 12px; color: var(--text-muted);">OTPs: ${u.total_otps}</div></div>
                    <strong style="color: var(--success); align-self:center;">$${(u.balance/1000).toFixed(3)}</strong>
                </div>
            `).join('');
        }

        async function loadHistory(page = 1) {
            currentHistoryPage = page;
            const listDiv = document.getElementById('history-list');
            const pagDiv = document.getElementById('history-pagination');
            if (!listDiv) return;
            listDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Đang tải...</div>';
            
            const data = await api('/api/mini/orders?page=' + page);
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có lịch sử giao dịch.</div>';
                if (pagDiv) pagDiv.style.display = 'none';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, true)).join('');
            totalHistoryPages = data.total_pages || 1;
            
            if (totalHistoryPages > 1 && pagDiv) {
                pagDiv.style.display = 'flex';
                document.getElementById('page-info').innerText = `Trang ${currentHistoryPage} / ${totalHistoryPages}`;
                document.getElementById('btn-prev').disabled = currentHistoryPage <= 1;
                document.getElementById('btn-next').disabled = currentHistoryPage >= totalHistoryPages;
            } else if (pagDiv) { pagDiv.style.display = 'none'; }
        }

        async function clearHistory() {
            const confirmed = await showCustomModal('Xóa Lịch Sử', 'Bạn có chắc chắn muốn xóa sạch toàn bộ lịch sử đơn hàng cũ không?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/clear', 'POST');
            if (res.ok) { showToast('Đã xóa sạch lịch sử!'); loadHistory(1); }
            else { alert(res.error || 'Lỗi xóa lịch sử'); }
        }

        function changeHistoryPage(delta) {
            const newPage = currentHistoryPage + delta;
            if (newPage >= 1 && newPage <= totalHistoryPages) loadHistory(newPage);
        }

        function renderOrderCard(o, isHistory) {
            const hasOtp = o.status === 'COMPLETED' || (o.otp && o.otp !== 'null' && o.otp !== '');
            const statusText = hasOtp ? '🟢 Nhận OTP thành công' : '⏳ Chờ OTP';
            const cardClass = hasOtp ? 'order-card completed' : `order-card ${o.status.toLowerCase()}`;
            const badgeColor = hasOtp ? 'var(--success)' : 'var(--warning)';

            return `
                <div class="${cardClass}">
                    <div class="order-header">
                        <div class="order-phone" id="phone-text-${o.id}">${o.phone}</div>
                        <div class="order-badge" style="color: ${badgeColor};">${statusText}</div>
                    </div>
                    <div class="order-info">
                        <span>${o.flag} ${o.country}</span>
                        <span>🔧 ${o.provider}</span>
                        <span>${o.icon || '📱'} ${o.platform || 'Other'}</span>
                    </div>
                    <div class="format-toggles">
                        <label><input type="checkbox" id="chk-plus-${o.id}" onchange="updatePhoneDisplay('${o.id}', '${o.phone}')"> Bỏ dấu (+)</label>
                        <label><input type="checkbox" id="chk-nat-${o.id}" onchange="updatePhoneDisplay('${o.id}', '${o.phone}')"> Định dạng nội địa</label>
                    </div>
                    ${hasOtp ? `
                        <div class="otp-box">
                            <div>
                                <div style="font-size: 12px; color: var(--success); margin-bottom: 4px; font-weight: 600;">🔑 MÃ OTP:</div>
                                <div class="otp-code">${o.otp}</div>
                            </div>
                            <button class="btn-small copy" style="background: var(--success); width: 85px;" onclick="copyText('${o.otp}')">📋 Copy</button>
                        </div>
                    ` : ''}
                    <div class="action-row">
                        <button class="btn-small copy" onclick="copyText(document.getElementById('phone-text-${o.id}').innerText)">📋 Copy Số</button>
                        ${o.status === 'PENDING' && !hasOtp && !isHistory ? `<button class="btn-small cancel" onclick="cancelOrder(${o.id})">❌ Hủy</button>` : ''}
                    </div>
                </div>
            `;
        }

        async function cancelOrder(oid) {
            const confirmed = await showCustomModal('Hủy Đơn', 'Bạn chắc chắn muốn hủy đơn này?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/' + oid + '/cancel', 'POST');
            if (res.ok) { loadHome(); showToast('Đã hủy đơn'); }
            else { alert('Lỗi: ' + res.error); }
        }

        async function renderBuyOptions() {
            const providerSel = document.getElementById('provider-select');
            const container = document.getElementById('buy-list-container');
            if (!providerSel || !container) return;
            
            const provider = providerSel.value;
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';

            if (provider === 'MK') {
                const data = await api('/api/mini/mk/ranges');
                if (!data.countries) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Không có dữ liệu.</div>';
                container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('MK', '${c.range}', '${c.name}')"><div class="name">${c.flag} ${c.name}</div></button>
                `).join('');
            } 
            else if (provider === 'NP') {
                const data = await api('/api/mini/np/services');
                if (!data.services) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Không có dữ liệu.</div>';
                container.innerHTML = data.services.map(s => `
                    <button class="list-btn" onclick="loadNpCountries('${s.name}')"><div class="name">🔧 ${s.name}</div><div class="count">Còn ${s.count} số</div></button>
                `).join('');
            }
            else if (provider === 'BASHA') {
                const data = await api('/api/mini/bs/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số BS.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('BASHA', '${c.name}', '${c.name}')"><div class="name">${c.flag} ${c.name}</div><div class="count">Còn ${c.count} số</div></button>
                `).join('');
            }
            else if (provider === 'SLVN') {
                const data = await api('/api/mini/slvn/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số SLVN.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('SLVN', '${c.code}', '${c.name}', '${c.tag}')"><div class="name">${c.flag} ${c.name}</div><div class="count">Rate: $${c.rate}</div></button>
                `).join('');
            }
        }

        async function loadNpCountries(serviceName) {
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';
            const data = await api('/api/mini/np/countries?service=' + encodeURIComponent(serviceName));
            if (!data.countries) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Lỗi tải quốc gia NP.</div>';
            container.innerHTML = data.countries.map(c => `
                <button class="list-btn" onclick="buyNumber('NP', '${c.name}', '${c.name}', '${serviceName}')"><div class="name">🌍 ${c.name}</div><div class="count">Còn ${c.count} số</div></button>
            `).join('');
        }

        async function buyNumber(provider, code, name, param3 = null) {
            const confirmed = await showCustomModal('Xác Nhận', `Bạn có chắc muốn lấy số ${name} không?`);
            if (!confirmed) return;

            let body = { provider };
            if (provider === 'MK') { body.range = code; body.country_name = name; }
            if (provider === 'NP') { body.country = code; body.service = param3; }
            if (provider === 'BASHA') { body.country = code; }
            if (provider === 'SLVN') { body.country_code = code; body.tag = param3; }

            const res = await api('/api/mini/orders', 'POST', body);
            if (res.ok) { showToast('✅ Đã lấy số thành công!'); navTo('home'); }
            else { alert('❌ Lỗi: ' + (res.error || 'Không thể lấy số')); }
        }

        function loadWallet() { loadUserData(); }

        function loadProfile() {
            if (!userData || !userData.user) return;
            const u = userData.user;
            document.getElementById('profile-info').innerHTML = `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">🆔 Telegram ID: <b>${u.id}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">👤 Tên: <b>${u.first_name || 'User'}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">💰 Số dư: <b style="color: var(--success);">$${(u.usd_milli/1000).toFixed(3)}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">📩 Tổng OTP: <b style="color: var(--primary);">${userData.total_otps || 0}</b></div>
                <div style="padding: 10px 0;">📅 Ngày tham gia: <b>${new Date(u.joined_at).toLocaleString('vi-VN')}</b></div>
            `;
        }

        function setWithdrawAmount(type) {
            const input = document.getElementById('withdraw-amount');
            if (!input) return;
            if (type === 'max') {
                if (!userData || !userData.user) return;
                let finalAmt = (userData.user.usd_milli / 1000) - 0.1;
                input.value = (finalAmt < 0 ? 0 : finalAmt).toFixed(3);
                showToast('Đã trừ phí rút toàn bộ $0.1');
            } else { input.value = type; }
        }

        async function saveWallet() {
            const address = document.getElementById('ton-address').value;
            const res = await api('/api/mini/wallet/address', 'POST', { address });
            if (res.ok) showToast('Đã lưu địa chỉ ví!');
            else alert('Lỗi: ' + res.error);
        }

        async function requestWithdraw() {
            const amount = document.getElementById('withdraw-amount').value;
            if (!amount || amount < 1) return alert('Số tiền tối thiểu là $1.00');
            const res = await api('/api/mini/wallet/withdraw', 'POST', { amount });
            if (res.ok) { alert('Đã gửi yêu cầu rút tiền. Vui lòng chờ Admin duyệt.'); loadUserData(); }
            else alert('Lỗi: ' + (res.error || 'Lỗi không xác định'));
        }

        function copyRef() {
            navigator.clipboard.writeText(document.getElementById('ref-link').innerText).then(() => showToast('Đã sao chép link!'));
        }

        // ADMIN PANEL & BROADCAST SLIDER LOGIC
        function selectRadarPlatform(platName) {
            document.getElementById('broadcast-platform').value = platName;
            const sliderVal = document.getElementById('broadcast-rate-slider').value;
            const pct = sliderVal * 10;
            document.getElementById('broadcast-msg').value = `🚨 THÔNG BÁO RADAR OTP CAO\n\nNền tảng / Quốc gia: ${platName}\nTỷ lệ nhận OTP: ${pct}%\nNhanh tay vào ứng dụng lấy số ngay nào anh em!`;
            showToast('Đã chọn: ' + platName);
        }

        function updateRateSlider(val) {
            const pct = val * 10;
            document.getElementById('slider-percent-val').innerText = `${pct}% (Mức ${val})`;
            const plat = document.getElementById('broadcast-platform').value || 'Instagram';
            document.getElementById('broadcast-msg').value = `🚨 THÔNG BÁO RADAR OTP CAO\n\nNền tảng / Quốc gia: ${plat}\nTỷ lệ nhận OTP: ${pct}%\nNhanh tay vào ứng dụng lấy số ngay nào anh em!`;
        }

        function clearRadarBroadcast() {
            document.getElementById('broadcast-platform').value = 'Instagram';
            document.getElementById('broadcast-rate-slider').value = 10;
            updateRateSlider(10);
            document.getElementById('broadcast-image').value = '';
            showToast('Đã đặt lại form!');
        }

        async function sendRadarBroadcast() {
            const platform = document.getElementById('broadcast-platform').value;
            const message = document.getElementById('broadcast-msg').value;
            const fileInput = document.getElementById('broadcast-image');
            let b64 = "";

            if (fileInput && fileInput.files.length > 0) {
                b64 = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(fileInput.files[0]);
                });
            }

            const confirmed = await showCustomModal('Xác Nhận Gửi', 'Bạn có chắc chắn muốn gửi thông báo radar này đến tất cả user?');
            if (!confirmed) return;

            const res = await api('/api/mini/admin/broadcast/radar', 'POST', { platform, message, image_b64: b64 });
            if (res.ok) { alert(res.msg); clearRadarBroadcast(); }
            else { alert(res.error || 'Lỗi gửi thông báo'); }
        }

        async function loadAdmin() {
            const data = await api('/api/mini/admin/data');
            if (data.error) return alert(data.error);
            
            document.getElementById('admin-total-users').innerText = data.stats.users;
            document.getElementById('admin-total-orders').innerText = data.stats.orders;
            
            const statusEl = document.getElementById('admin-bot-status');
            if (statusEl) {
                statusEl.innerText = data.maintenance === 'on' ? '🔴 Đang bảo trì' : '🟢 Đang hoạt động';
                statusEl.style.color = data.maintenance === 'on' ? 'var(--danger)' : 'var(--success)';
                isMaintenanceOn = (data.maintenance === 'on');
            }

            document.getElementById('admin-stock-info').innerHTML = `
                <div class="row"><span>Pending Withdrawals:</span> <b>${data.stats.pending_wd}</b></div>
                <div class="row"><span>BS Stock:</span> <b>${data.stats.bs_count}</b></div>
            `;

            const wdDiv = document.getElementById('admin-wd-list');
            if (wdDiv) {
                wdDiv.innerHTML = (!data.withdrawals || data.withdrawals.length === 0) ? '<div style="color: var(--text-muted); font-size: 14px;">Không có yêu cầu rút tiền.</div>' : data.withdrawals.map(w => `
                    <div class="order-card" style="border-left-color: var(--primary);">
                        <div class="order-header"><div class="order-phone">${w.name} (${w.user_id})</div><div class="order-badge" style="color: var(--primary);">$${(w.amount/1000).toFixed(3)}</div></div>
                        <div style="font-size: 13px; color: var(--text-muted); word-break: break-all; margin-bottom: 12px;">Ví: ${w.wallet}</div>
                        <div class="action-row">
                            <button class="btn-small" style="background: var(--success);" onclick="adminWdAction(${w.id}, 'approve')">✅ Duyệt</button>
                            <button class="btn-small" style="background: var(--danger);" onclick="adminWdAction(${w.id}, 'reject')">❌ Từ chối</button>
                        </div>
                    </div>
                `).join('');
            }
            updateMaintUI();
        }

        function switchAdminTab(tab) {
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.admin-tab-content').forEach(c => c.style.display = 'none');
            event?.target?.classList.add('active');
            const target = document.getElementById('admin-tab-' + tab);
            if (target) target.style.display = 'block';

            if (tab === 'users') loadAdminUsers();
            if (tab === 'bs') loadAdminBs();
            if (tab === 'maint') updateMaintUI();
        }

        function updateMaintUI() {
            const btnOn = document.getElementById('btn-maint-on');
            const btnOff = document.getElementById('btn-maint-off');
            const form = document.getElementById('maint-form-container');
            if (!btnOn || !btnOff || !form) return;
            if (isMaintenanceOn) {
                btnOn.classList.remove('on'); btnOff.classList.add('off'); form.style.display = 'block';
            } else {
                btnOn.classList.add('on'); btnOff.classList.remove('off'); form.style.display = 'none';
            }
        }

        async function toggleMaintenance(enable) {
            if (enable) {
                const res = await api('/api/mini/admin/maintenance', 'POST', { action: 'enable' });
                if (res.ok) { showToast(res.msg); isMaintenanceOn = false; updateMaintUI(); loadAdmin(); }
                else alert(res.error);
            } else { isMaintenanceOn = true; updateMaintUI(); }
        }

        function setMaintTemplate(id) {
            const ta = document.getElementById('maint-msg');
            if (!ta) return;
            if (id === 1) ta.value = "Hệ thống đang được bảo trì để nâng cấp. Vui lòng quay lại sau ít phút!";
            if (id === 2) ta.value = "Server đang gặp sự cố kỹ thuật. Admin đang khắc phục!";
        }

        async function submitMaintenance() {
            const ta = document.getElementById('maint-msg');
            if (!ta || !ta.value) return alert("Vui lòng nhập thông báo!");
            const fileInput = document.getElementById('maint-image');
            let b64 = "";
            if(fileInput && fileInput.files.length > 0) {
                b64 = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(fileInput.files[0]);
                });
            }
            const confirmed = await showCustomModal('Xác Nhận Bảo Trì', 'Hệ thống sẽ BẬT chế độ bảo trì và gửi thông báo đến toàn bộ user. Tiếp tục?');
            if(!confirmed) return;

            const res = await api('/api/mini/admin/maintenance', 'POST', { action: 'disable', message: ta.value, image_b64: b64 });
            if(res.ok) { alert(res.msg); ta.value = ''; if (fileInput) fileInput.value = ''; isMaintenanceOn = true; updateMaintUI(); loadAdmin(); }
            else alert("Lỗi: " + (res.error || 'Không xác định'));
        }

        async function loadAdminUsers() {
            const div = document.getElementById('admin-user-list');
            if (!div) return;
            div.innerHTML = '<div class="spinner"></div>';
            const data = await api('/api/mini/admin/users');
            if(data.error) return div.innerText = data.error;
            div.innerHTML = (data.users || []).map(u => `
                <div style="padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;" onclick="loadAdminUserDetail(${u.id})">
                    <b>${u.name || 'User'}</b> (@${u.username || '—'}) - ID: ${u.id}<br>
                    <span style="color:var(--success);">$${((u.balance || 0)/1000).toFixed(3)}</span> | Joined: ${new Date(u.joined).toLocaleDateString()}
                </div>
            `).join('');
        }

        async function loadAdminUserDetail(uid) {
            currentAdminUid = uid;
            currentUserDetailPage = 1;
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.admin-tab-content').forEach(c => c.style.display = 'none');
            document.getElementById('admin-tab-user-detail').style.display = 'block';
            
            document.getElementById('admin-user-detail-info').innerHTML = `
                <div id="u-detail-text"><div class="spinner"></div></div>
                <div style="margin-top: 15px; display: flex; flex-direction: column; gap: 10px;">
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-bonus-amt" class="form-control" placeholder="Số tiền ($)" step="0.1" style="flex:1;"><button class="btn btn-success" style="margin-top:0; width:120px;" onclick="adminUserAction(${uid}, 'bonus')">➕ Cộng</button></div>
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-deduct-amt" class="form-control" placeholder="Số tiền trừ ($)" step="0.1" style="flex:1;"><button class="btn btn-danger" style="margin-top:0; width:120px; background: #ea580c;" onclick="adminUserAction(${uid}, 'deduct')">➖ Trừ</button></div>
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-min-amt" class="form-control" placeholder="Số dư tối thiểu ($)" step="0.1" style="flex:1;"><button class="btn btn-primary" style="margin-top:0; width:120px;" onclick="adminUserAction(${uid}, 'set_min')">⚙️ Set Min</button></div>
                    <button class="btn btn-danger" style="margin-top:0;" onclick="adminUserAction(${uid}, 'revoke')">🗑️ Thu hồi toàn bộ số dư</button>
                </div>
            `;
            document.getElementById('admin-user-detail-orders').innerHTML = '<div class="spinner"></div>';
            
            const data = await api('/api/mini/admin/users/' + uid + '?page=1');
            if(data.error) return document.getElementById('u-detail-text').innerText = data.error;

            const u = data.user;
            document.getElementById('u-detail-text').innerHTML = `
                <div><b>Tên:</b> ${u.name}</div><div><b>Username:</b> @${u.username || '—'}</div>
                <div><b>Telegram ID:</b> ${u.id}</div><div><b>Số dư:</b> <span style="color:var(--success);">$${(u.balance/1000).toFixed(3)}</span></div>
            `;

            const s = data.stats || {};
            document.getElementById('admin-user-detail-stats').innerHTML = `
                <div><div style="font-size:20px;color:var(--primary);font-weight:bold;">${s.MK || 0}</div>MK</div>
                <div><div style="font-size:20px;color:var(--warning);font-weight:bold;">${s.NP || 0}</div>NP</div>
                <div><div style="font-size:20px;color:var(--success);font-weight:bold;">${s.BASHA || 0}</div>BS</div>
                <div><div style="font-size:20px;color:var(--danger);font-weight:bold;">${s.SLVN || 0}</div>SLVN</div>
            `;
            renderAdminUserOrders(data);
        }

        async function adminUserAction(uid, action) {
            let val = 0;
            if (action === 'bonus') val = document.getElementById('admin-bonus-amt').value;
            if (action === 'deduct') val = document.getElementById('admin-deduct-amt').value;
            if (action === 'set_min') val = document.getElementById('admin-min-amt').value;
            if ((action === 'bonus' || action === 'deduct' || action === 'set_min') && (!val || val <= 0)) return alert('Vui lòng nhập số tiền hợp lệ!');
            if (action === 'revoke' && !confirm('Thu hồi toàn bộ số dư?')) return;

            const res = await api(`/api/mini/admin/users/${uid}/action`, 'POST', { action, amount: val });
            if (res.ok) { showToast(res.msg); loadAdminUserDetail(uid); } else alert(res.error);
        }

        function renderAdminUserOrders(data) {
            const div = document.getElementById('admin-user-detail-orders');
            const pag = document.getElementById('user-detail-pagination');
            if (!div) return;
            if(!data.orders || data.orders.length === 0) {
                div.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">Chưa có số nào.</div>';
                if (pag) pag.style.display = 'none';
                return;
            }
            div.innerHTML = data.orders.map(o => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px;">
                    <div><b>${o.phone}</b><br><span style="font-size:12px;color:var(--text-muted);">${o.provider} | ${new Date(o.date).toLocaleString('vi-VN')}</span></div>
                    <div style="align-self:center;color:${o.status==='COMPLETED'?'var(--success)':'var(--text-muted)'};">${o.status}</div>
                </div>
            `).join('');

            totalUserDetailPages = data.total_pages || 1;
            if (totalUserDetailPages > 1 && pag) {
                pag.style.display = 'flex';
                document.getElementById('user-page-info').innerText = `Trang ${data.current_page} / ${totalUserDetailPages}`;
                document.getElementById('btn-user-prev').disabled = data.current_page <= 1;
                document.getElementById('btn-user-next').disabled = data.current_page >= totalUserDetailPages;
            } else if (pag) pag.style.display = 'none';
        }

        async function changeUserDetailPage(delta) {
            const newPage = currentUserDetailPage + delta;
            if (newPage >= 1 && newPage <= totalUserDetailPages) {
                currentUserDetailPage = newPage;
                const data = await api(`/api/mini/admin/users/${currentAdminUid}?page=${newPage}`);
                if(!data.error) renderAdminUserOrders(data);
            }
        }

        async function loadAdminBs() {
            const div = document.getElementById('admin-bs-list');
            if (!div) return;
            div.innerHTML = '<div class="spinner"></div>';
            const data = await api('/api/mini/bs/countries');
            if(!data.countries || data.countries.length === 0) return div.innerHTML = 'Chưa có số BS.';
            div.innerHTML = data.countries.map(c => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);align-items:center;">
                    <span>${c.flag} ${c.name} (${c.count})</span>
                    <button class="btn-small cancel" style="width:auto;padding:6px 12px;" onclick="deleteBs('${c.name}')">Xóa</button>
                </div>
            `).join('') + `<button class="btn btn-danger" style="margin-top:15px;" onclick="deleteBs('ALL')">XÓA TOÀN BỘ SỐ BS</button>`;
        }

        async function deleteBs(country) {
            if(!await showCustomModal('Xóa Số BS', `Xóa toàn bộ số của ${country}?`)) return;
            const res = await api('/api/mini/admin/bs/delete', 'POST', { country });
            if(res.ok) { showToast('Đã xóa!'); loadAdminBs(); loadAdmin(); } else alert(res.error);
        }

        async function runAdminCmd(cmd) {
            const out = document.getElementById('cmd-output');
            if (!out) return;
            out.innerText = 'Đang chạy...';
            const res = await api('/api/mini/admin/cmd', 'POST', { cmd });
            out.innerText = res.ok ? res.msg : ('Lỗi: ' + (res.error || 'Unknown'));
        }

        async function adminWdAction(wid, action) {
            if(!await showCustomModal('Xác Nhận', `Bạn chắc chắn muốn ${action === 'approve' ? 'DUYỆT' : 'TỪ CHỐI'}?`)) return;
            const res = await api('/api/mini/admin/withdraw/action', 'POST', { wid, action });
            if (res.ok) { loadAdmin(); showToast('Thành công!'); } else alert(res.error);
        }

        async function addBsNumbers() {
            const numbers = document.getElementById('bs-input').value;
            if (!numbers) return alert('Vui lòng nhập số!');
            const res = await api('/api/mini/admin/bs/add', 'POST', { numbers });
            if (res.ok) { alert(`Đã thêm ${res.added} số`); document.getElementById('bs-input').value = ''; loadAdminBs(); } else alert(res.error);
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {
                if (document.querySelector('.view.active')?.id === 'view-home') loadHome(true);
            }, 3000); 
        }

        loadUserData();
        loadHome();
        startAutoRefresh();
    </script>
</body>
</html>
"""
