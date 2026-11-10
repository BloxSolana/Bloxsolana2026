# File: miniapp_html.py

MINIAPP_HTML = r"""
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
        .order-card.cancelled { border-left: 4px solid var(--danger); opacity: 0.6; }
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
        <p id="maint-text" data-i18n="maint_default_msg">Hệ thống đang được bảo trì. Vui lòng quay lại sau!</p>
    </div>

    <div id="toast">Copied!</div>

    <div id="custom-modal">
        <div class="modal-content">
            <div class="modal-title" id="modal-title" data-i18n="modal_confirm">Xác nhận</div>
            <div class="modal-msg" id="modal-msg" data-i18n="modal_msg">Bạn có chắc chắn muốn thực hiện hành động này?</div>
            <div class="modal-actions">
                <button class="btn-outline" id="modal-btn-cancel" data-i18n="btn_cancel">Hủy bỏ</button>
                <button class="btn-primary" id="modal-btn-confirm" data-i18n="btn_agree">Đồng ý</button>
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
            <a href="#" class="menu-item active" onclick="navTo('home')"><span class="icon">🏠</span> <span data-i18n="menu_home">Trang chủ</span></a>
            <a href="#" class="menu-item" onclick="navTo('buy')"><span class="icon">🛒</span> <span data-i18n="menu_buy">Mua Số OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('tempmail')"><span class="icon">📧</span> <span data-i18n="menu_mail">Tạo Temp Mail</span></a>
            <a href="#" class="menu-item" onclick="navTo('radar')"><span class="icon">📡</span> <span data-i18n="menu_radar">Radar OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('history')"><span class="icon">📜</span> <span data-i18n="menu_history">Lịch sử</span></a>
            <a href="#" class="menu-item" onclick="navTo('wallet')"><span class="icon">💵</span> <span data-i18n="menu_wallet">Ví & Rút Tiền</span></a>
            <a href="#" class="menu-item" onclick="navTo('stats')"><span class="icon">📊</span> <span data-i18n="menu_stats">Thống Kê</span></a>
            <a href="#" class="menu-item" onclick="navTo('leaderboard')"><span class="icon">🏆</span> <span data-i18n="menu_leaderboard">Bảng Xếp Hạng</span></a>
            <a href="#" class="menu-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')"><span class="icon">📢</span> <span data-i18n="menu_group">OTP Group</span></a>
            <a href="#" class="menu-item" onclick="navTo('profile')"><span class="icon">👤</span> <span data-i18n="menu_profile">Hồ Sơ</span></a>
            
            <a href="#" class="menu-item menu-admin" id="menu-admin" onclick="navTo('admin')" style="display: none;">
                <span class="icon">🛡</span> <span data-i18n="menu_admin">ADMIN PANEL</span>
            </a>
        </div>
    </div>

    <div class="top-bar" id="main-top-bar">
        <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        <div class="page-title" id="top-title" data-i18n="menu_home">Trang chủ</div>
    </div>

    <div class="container" id="main-container">
        
        <!-- ================= VIEW HOME ================= -->
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
        <!-- ================= END VIEW HOME ================= -->

        <!-- ================= VIEW BUY ================= -->
        <div id="view-buy" class="view">
            <div class="card">
                <div class="form-group">
                    <label class="form-label" data-i18n="select_source">Chọn Nguồn Số</label>
                    <select class="form-control" id="provider-select" onchange="renderBuyOptions()">
                        <option value="MK">🎱 Numbers 1 (MK)</option>
                        <option value="SLVN">🌐 Numbers 2 (SLVN)</option>
                        <option value="NP">📱 Numbers 3 (NP)</option>
                        <option value="BS">🔢 Numbers 4 (BS)</option>
                    </select>
                </div>
            </div>
            <div id="buy-list-container" class="list-grid"></div>
        </div>
        <!-- ================= END VIEW BUY ================= -->

        <!-- ================= VIEW TEMP MAIL ================= -->
        <div id="view-tempmail" class="view">
            <div class="card" style="border: 1px solid rgba(249,115,22,0.3); background: rgba(30,41,59,0.8);">
                <div style="background: rgba(249,115,22,0.15); color: #fb923c; padding: 10px 14px; border-radius: 10px; font-size: 13px; margin-bottom: 15px; line-height: 1.5; border: 1px solid rgba(249,115,22,0.3);">
                    ⚠️ All users please note earn per otp is in beta version, testing,... it is not scheduled for now... It will start soon ...Thank You......
                </div>
                
                <div class="form-label" style="font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 15px;" data-i18n="generate_mail">Generate Temp Email</div>
                
                <div class="form-group">
                    <label class="form-label" data-i18n="mail_username">Username (Optional)</label>
                    <input type="text" class="form-control" id="mail-username" placeholder="Prefix / username">
                </div>
                
                <div class="form-group">
                    <label class="form-label" data-i18n="mail_domain">Domain</label>
                    <select class="form-control" id="mail-domain-select">
                        <option value="">Auto-select random domain</option>
                    </select>
                </div>
                
                <button class="btn" style="background: linear-gradient(135deg, #f97316, #ea580c); box-shadow: 0 4px 15px rgba(249,115,22,0.4);" onclick="generateTempMail()" data-i18n="btn_gen_mail">Generate Mail ...</button>
            </div>

            <div class="card" id="mail-active-box" style="display: none;">
                <div class="form-label" style="font-size: 16px; font-weight: bold; color: var(--success); margin-bottom: 10px;" data-i18n="live_inbox">📬 Live Inbox:</div>
                <div style="background: rgba(16,185,129,0.1); padding: 12px; border-radius: 10px; border: 1px solid var(--success); display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div id="current-mail-address" style="font-weight: 700; font-size: 15px; color: var(--text); word-break: break-all;"></div>
                    <button class="btn-small copy" style="background: var(--success); width: 85px;" onclick="copyText(document.getElementById('current-mail-address').innerText)" data-i18n="btn_copy">📋 Copy</button>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: 600; font-size: 15px;" data-i18n="messages">📥 Messages:</span>
                    <button class="btn-small copy" style="width: auto; padding: 6px 12px;" onclick="loadMailMessages()" data-i18n="btn_refresh">🔄 Refresh</button>
                </div>
                <div id="mail-messages-list">
                    <div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 15px;" data-i18n="no_msgs">No messages yet.</div>
                </div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 16px; font-weight: bold; margin-bottom: 10px;" data-i18n="recoverable">Recoverable Mails</div>
                <div id="mail-history-list">
                    <div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 10px;" data-i18n="no_history">No saved history yet.</div>
                </div>
            </div>
        </div>
        <!-- ================= END VIEW TEMP MAIL ================= -->

        <!-- ================= VIEW RADAR ================= -->
        <div id="view-radar" class="view">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                <div style="font-size: 16px; font-weight: 700; color: var(--text);" data-i18n="radar_feed">📡 Unified Radar Feed</div>
                <div style="font-size: 12px; color: var(--success); background: rgba(16,185,129,0.1); padding: 4px 10px; border-radius: 20px; border: 1px solid rgba(16,185,129,0.3);" id="radar-records-count">0 records</div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span data-i18n="plat_activity">📊 Platform Activity</span>
                    <span style="font-size: 12px; color: var(--text-muted);" data-i18n="last_30m">Last 30 mins</span>
                </div>
                <div id="radar-platforms-chart" style="display: flex; flex-direction: column; gap: 10px;"></div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 12px; display: flex; justify-content: space-between;">
                    <span data-i18n="country_oper">🌍 Country & Operator</span>
                    <span style="font-size: 12px; color: var(--text-muted);" data-i18n="last_30m">Last 30 mins</span>
                </div>
                <div id="radar-countries-chart" style="display: flex; flex-direction: column; gap: 10px;"></div>
            </div>

            <div class="card">
                <div class="form-label" style="font-size: 15px; color: var(--text); margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;">
                    <span data-i18n="live_otp">⚡ Live OTP Feed (Real-time)</span>
                    <span style="font-size: 11px; color: var(--primary);">● Live Updates</span>
                </div>
                <div id="radar-feed-list"><div class="loading"><div class="spinner"></div>Đang tải radar...</div></div>
            </div>
        </div>
        <!-- ================= END VIEW RADAR ================= -->

        <!-- ================= VIEW HISTORY ================= -->
        <div id="view-history" class="view">
            <div style="margin-bottom: 15px; display: flex; justify-content: flex-end;">
                <button class="btn btn-danger" style="width: auto; padding: 10px 18px; font-size: 14px;" onclick="clearHistory()" data-i18n="clear_history">🗑️ Clear History</button>
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
        <!-- ================= END VIEW HISTORY ================= -->

        <!-- ================= VIEW WALLET ================= -->
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
        <!-- ================= END VIEW WALLET ================= -->

        <!-- ================= VIEW STATS ================= -->
        <div id="view-stats" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="stats_today">📊 THỐNG KÊ</div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="label" data-i18n="total_otp_all">Tổng OTP All-Time</div>
                        <div class="value" id="stats-all-time-otps" style="color: var(--success);">0</div>
                    </div>
                    <div class="stat-box">
                        <div class="label" data-i18n="today_otp">OTP Hôm Nay</div>
                        <div class="value" id="stats-today-otps" style="color: var(--primary);">0</div>
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
        <!-- ================= END VIEW STATS ================= -->

        <!-- ================= VIEW LEADERBOARD ================= -->
        <div id="view-leaderboard" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;" data-i18n="top_10">🏆 TOP 10 CAO THỦ</div>
                <div id="leaderboard-list">
                    <div class="loading"><div class="spinner"></div>Đang tải...</div>
                </div>
            </div>
        </div>
        <!-- ================= END VIEW LEADERBOARD ================= -->

        <!-- ================= VIEW PROFILE ================= -->
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
        <!-- ================= END VIEW PROFILE ================= -->

        <!-- ================= VIEW ADMIN ================= -->
        <div id="view-admin" class="view">
            <div class="admin-tabs">
                <button class="admin-tab active" onclick="switchAdminTab('overview', this)" data-i18n="admin_overview">Tổng quan</button>
                <button class="admin-tab" onclick="switchAdminTab('users', this)" data-i18n="admin_users">Users</button>
                <button class="admin-tab" onclick="switchAdminTab('broadcast', this)" data-i18n="admin_radar">📡 Radar TB</button>
                <button class="admin-tab" onclick="switchAdminTab('withdraw', this)" data-i18n="admin_wd">Rút tiền</button>
                <button class="admin-tab" onclick="switchAdminTab('bs', this)" data-i18n="admin_bs">Số BS</button>
                <button class="admin-tab" onclick="switchAdminTab('cmds', this)" data-i18n="admin_cmds">Commands</button>
                <button class="admin-tab" onclick="switchAdminTab('maint', this)" data-i18n="admin_maint">Bảo trì</button>
            </div>

            <div id="admin-tab-overview" class="admin-tab-content">
                <div class="stats-grid">
                    <div class="stat-box"><div class="label" data-i18n="admin_users_label">Users</div><div class="value" id="admin-total-users">0</div></div>
                    <div class="stat-box"><div class="label" data-i18n="admin_orders_label">Orders</div><div class="value" id="admin-total-orders">0</div></div>
                </div>
                <div class="card" style="text-align: center; font-size: 18px; font-weight: bold;">
                    <span data-i18n="admin_bot_status">Trạng thái Bot:</span> <span id="admin-bot-status" style="color: var(--success);">🟢 Đang hoạt động</span>
                </div>
                <div class="card">
                    <div class="form-label" data-i18n="admin_stock">Chi tiết kho số</div>
                    <div id="admin-stock-info"></div>
                </div>
            </div>

            <div id="admin-tab-users" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div id="admin-user-list" class="loading">Đang tải...</div>
                </div>
            </div>

            <div id="admin-tab-broadcast" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label" style="font-size:16px; font-weight:bold; margin-bottom:10px;" data-i18n="admin_radar_title">📡 Gửi Thông Báo Radar Nền Tảng & MK NETWORK</div>
                    
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 15px;">
                        <button class="btn-small copy" onclick="selectRadarPlatform('Guinea (MK)')">🇬🇳 Guinea (MK)</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Zambia (MK)')">🇿🇲 Zambia (MK)</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Sudan (MK)')">🇸🇩 Sudan (MK)</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Ethiopia (MK)')">🇪🇹 Ethiopia (MK)</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Vietnam')">🇻🇳 Vietnam</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Indonesia')">🇮🇩 Indonesia</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Philippines')">🇵🇭 Philippines</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Malaysia')">🇲🇾 Malaysia</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Thailand')">🇹🇭 Thailand</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Instagram')">📸 Instagram</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Facebook')">📘 Facebook</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('TikTok')">🎬 TikTok</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Telegram')">✈️ Telegram</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('WhatsApp')">💬 WhatsApp</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Threads')">🧵 Threads</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Twitter (X)')">🐦 Twitter (X)</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Google/Gmail')">🇬 Google/Gmail</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Zalo')">💬 Zalo</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Shopee')">🛍 Shopee</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Apple')">🍎 Apple</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Microsoft')">💻 Microsoft</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Binance/Crypto')">🪙 Binance/Crypto</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Viber')">📞 Viber</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Line')">💬 Line</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('KakaoTalk')">💬 KakaoTalk</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('Discord')">🎮 Discord</button>
                        <button class="btn-small copy" onclick="selectRadarPlatform('LinkedIn')">💼 LinkedIn</button>
                        <button class="btn-small copy" style="grid-column: span 2;" onclick="selectRadarPlatform('🌐 Tất cả MXH & Quốc gia khác')">🌐 Tất cả MXH & Quốc gia khác</button>
                    </div>

                    <div class="form-group">
                        <label class="form-label" data-i18n="admin_selected">Quốc gia / Nền tảng đã chọn:</label>
                        <input type="text" class="form-control" id="broadcast-platform" value="Guinea (MK)">
                    </div>

                    <div class="form-group">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <label class="form-label" style="margin-bottom:0;" data-i18n="admin_rate">⚡ Tỷ lệ nhận OTP (%):</label>
                            <span id="slider-percent-val" style="font-weight: 700; color: var(--success); font-size: 16px;">100% (Mức 10)</span>
                        </div>
                        <input type="range" id="broadcast-rate-slider" min="1" max="10" value="10" class="form-control" style="padding: 0; height: 8px; accent-color: var(--success); cursor: pointer;" oninput="updateRateSlider(this.value)">
                    </div>

                    <div class="form-group">
                        <label class="form-label" data-i18n="admin_msg">Nội dung thông báo:</label>
                        <textarea class="form-control" id="broadcast-msg" rows="4"></textarea>
                    </div>
                    <div class="form-group">
                        <label class="form-label" data-i18n="admin_img">Ảnh đính kèm (Tùy chọn):</label>
                        <input type="file" id="broadcast-image" class="form-control" accept="image/*">
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-success" style="flex:1;" onclick="sendRadarBroadcast()" data-i18n="admin_send">🚀 Gửi Thông Báo</button>
                        <button class="btn btn-danger" style="flex:1;" onclick="clearRadarBroadcast()" data-i18n="admin_clear">❌ Hủy / Đặt lại</button>
                    </div>
                </div>
            </div>
            
            <div id="admin-tab-user-detail" class="admin-tab-content" style="display: none;">
                <button class="btn btn-outline" style="margin-bottom:15px;" onclick="switchAdminTab('users', event)" data-i18n="admin_back">⬅️ Quay lại danh sách</button>
                <div class="card"><div id="admin-user-detail-info"></div></div>
                <div class="card">
                    <div class="form-label" data-i18n="admin_stats_orders">Thống kê số đã lấy</div>
                    <div id="admin-user-detail-stats" style="display:flex; justify-content:space-around; text-align:center;"></div>
                </div>
                <div class="card">
                    <div class="form-label" data-i18n="admin_list_orders">Danh sách số đã lấy</div>
                    <div id="admin-user-detail-orders"></div>
                    <div class="pagination" id="user-detail-pagination" style="display: none;">
                        <button id="btn-user-prev" onclick="changeUserDetailPage(-1)" data-i18n="prev_page">← Trang trước</button>
                        <span id="user-page-info">Trang 1 / 1</span>
                        <button id="btn-user-next" onclick="changeUserDetailPage(1)" data-i18n="next_page">Trang sau →</button>
                    </div>
                </div>
            </div>

            <div id="admin-tab-withdraw" class="admin-tab-content" style="display: none;">
                <div class="card"><div class="form-label" data-i18n="admin_wd">💸 Duyệt Rút Tiền</div><div id="admin-wd-list"></div></div>
            </div>

            <div id="admin-tab-bs" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label" data-i18n="admin_add_bs">➕ Thêm Số BS</div>
                    <div class="form-group" style="display: flex; gap: 10px; margin-bottom: 10px;">
                        <input type="file" id="bs-file-input" class="form-control" accept=".txt,.csv" onchange="handleBsFileUpload(event)">
                    </div>
                    <textarea class="form-control" id="bs-input" rows="4" placeholder="Hoặc nhập mỗi dòng 1 số..."></textarea>
                    <button class="btn btn-success" onclick="addBsNumbers()" data-i18n="admin_btn_add">Thêm Số</button>
                </div>
                <div class="card"><div class="form-label" data-i18n="admin_manage_bs">⚙️ Quản lý số BS</div><div id="admin-bs-list"></div></div>
            </div>

            <div id="admin-tab-cmds" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label" data-i18n="admin_cmds">🛠 Admin Commands</div>
                    <div class="grid-2" style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <button class="btn btn-outline" onclick="runAdminCmd('health')" data-i18n="cmd_health">Health Check</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('pollnow')" data-i18n="cmd_poll">Force Poll OTP</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('whoami')" data-i18n="cmd_whoami">MK Account</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('testnp')" data-i18n="cmd_testnp">Test NP API</button>
                        <button class="btn btn-outline" onclick="runAdminCmd('radar')" data-i18n="cmd_radar">MK Radar</button>
                    </div>
                    <div id="cmd-output" style="margin-top: 15px; background: #000; padding: 10px; border-radius: 8px; font-family: monospace; font-size: 12px; white-space: pre-wrap; word-break: break-all; min-height: 50px;"></div>
                </div>
            </div>

            <div id="admin-tab-maint" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label" data-i18n="admin_sys_status">🛠 Trạng thái hệ thống</div>
                    <div class="maint-toggle">
                        <button id="btn-maint-on" class="maint-btn" onclick="toggleMaintenance(true)" data-i18n="admin_on">🟢 ON (Hoạt động)</button>
                        <button id="btn-maint-off" class="maint-btn" onclick="toggleMaintenance(false)" data-i18n="admin_off">🔴 OFF (Bảo trì)</button>
                    </div>
                </div>
                <div class="card" id="maint-form-container" style="display: none;">
                    <div class="form-label" id="maint-form-title" data-i18n="admin_maint_msg">📝 Nội dung thông báo</div>
                    <div style="display:flex; gap:5px; margin-bottom:10px;">
                        <button class="btn-small copy" onclick="setMaintTemplate(1)" data-i18n="admin_template1">Mẫu 1</button>
                        <button class="btn-small copy" onclick="setMaintTemplate(2)" data-i18n="admin_template2">Mẫu 2</button>
                    </div>
                    <textarea class="form-control" id="maint-msg" rows="4" placeholder="Nhập thông báo..."></textarea>
                    <div class="form-label" style="margin-top:10px;" data-i18n="admin_img_opt">🖼 Ảnh đính kèm (Tùy chọn)</div>
                    <input type="file" id="maint-image" class="form-control" accept="image/*">
                    <button class="btn btn-danger" style="margin-top:15px;" id="maint-submit-btn" onclick="submitMaintenance()" data-i18n="admin_confirm_maint">Xác nhận BẢO TRÌ & Gửi thông báo</button>
                </div>
            </div>
        </div>
        <!-- ================= END VIEW ADMIN ================= -->

    </div> <!-- KẾT THÚC MAIN CONTAINER -->

    <div class="bottom-nav" id="main-bottom-nav">
        <button class="nav-item active" id="nav-home" onclick="navTo('home')"><span class="icon">🏠</span><span data-i18n="menu_home">Trang chủ</span></button>
        <button class="nav-item" id="nav-buy" onclick="navTo('buy')"><span class="icon">🛒</span><span data-i18n="menu_buy">Mua số</span></button>
        <button class="nav-item" id="nav-tempmail" onclick="navTo('tempmail')"><span class="icon">📧</span><span data-i18n="menu_mail">Temp Mail</span></button>
        <button class="nav-item" id="nav-radar" onclick="navTo('radar')"><span class="icon">📡</span><span data-i18n="menu_radar">Radar</span></button>
        <button class="nav-item" id="nav-history" onclick="navTo('history')"><span class="icon">📜</span><span data-i18n="menu_history">Lịch sử</span></button>
        <button class="nav-item" id="nav-wallet" onclick="navTo('wallet')"><span class="icon">💵</span><span data-i18n="menu_wallet">Ví</span></button>
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
        let timerInterval = null; // FIX: Khai báo timerInterval
        let currentHistoryPage = 1;
        let totalHistoryPages = 1;
        let currentLang = 'vi';
        let currentAdminUid = null;
        let currentUserDetailPage = 1;
        let totalUserDetailPages = 1;
        let isMaintenanceOn = false;
        let lastKnownCompletedOrders = new Set();
        let currentActiveMailAddress = null;

        // Cờ chống spam API gây đơ
        let isLoadingRadar = false;
        let isLoadingStats = false;

        const translations = {
            vi: { 
                menu_home: "Trang chủ", menu_buy: "Mua Số OTP", menu_mail: "Tạo Temp Mail", menu_radar: "Radar OTP", menu_history: "Lịch sử", menu_wallet: "Ví & Rút Tiền", menu_stats: "Thống Kê", menu_leaderboard: "Bảng Xếp Hạng", menu_group: "OTP Group", menu_profile: "Hồ Sơ", menu_admin: "ADMIN PANEL",
                balance: "Số dư khả dụng", today_otp: "OTP Hôm Nay", total_orders: "Tổng Đơn", active_orders: "⏳ Đơn Đang Chờ", 
                select_source: "Chọn Nguồn Số", ton_wallet: "💵 Ví TON", save_address: "Lưu Địa Chỉ", withdraw: "💰 Rút Tiền", withdraw_all: "⚡ Rút Toàn Bộ (Phí $0.1)", send_request: "Gửi Yêu Cầu", 
                invite_friends: "💌 Mời Bạn Bè", copy_link: "📋 Sao Chép Link", top_10: "🏆 TOP 10 CAO THỦ", your_profile: "👤 HỒ SƠ CỦA BẠN", language: "🌐 Ngôn Ngữ (Language)", 
                prev_page: "← Trang trước", next_page: "Trang sau →", total_otp: "Tổng OTP đã nhận", total_otp_all: "Tổng OTP All-Time", joined: "Ngày tham gia", name: "Tên", balance_label: "Số dư",
                stats_today: "📊 THỐNG KÊ", stats_country: "🌍 OTP THEO QUỐC GIA", stats_platform: "📱 OTP THEO NỀN TẢNG", maint_title: "🛠 BẢO TRÌ HỆ THỐNG", maint_default_msg: "Hệ thống đang được bảo trì. Vui lòng quay lại sau!",
                remove_plus: "Bỏ dấu (+)", national_fmt: "Định dạng nội địa", clear_history: "🗑️ Xóa Lịch Sử",
                generate_mail: "Generate Temp Email", mail_username: "Username (Optional)", mail_domain: "Domain", btn_gen_mail: "Generate Mail ...", live_inbox: "📬 Live Inbox:", btn_copy: "📋 Copy", messages: "📥 Messages:", btn_refresh: "🔄 Refresh", no_msgs: "No messages yet.", recoverable: "Recoverable Mails", no_history: "No saved history yet.",
                radar_feed: "📡 Unified Radar Feed", plat_activity: "📊 Platform Activity", last_30m: "Last 30 mins", country_oper: "🌍 Country & Operator", live_otp: "⚡ Live OTP Feed (Real-time)",
                modal_confirm: "Xác nhận", modal_msg: "Bạn có chắc chắn muốn thực hiện hành động này?", btn_cancel: "Hủy bỏ", btn_agree: "Đồng ý",
                admin_overview: "Tổng quan", admin_users: "Users", admin_radar: "📡 Radar TB", admin_wd: "Rút tiền", admin_bs: "Số BS", admin_cmds: "Commands", admin_maint: "Bảo trì",
                admin_users_label: "Users", admin_orders_label: "Orders", admin_bot_status: "Trạng thái Bot:", admin_stock: "Chi tiết kho số", admin_radar_title: "📡 Gửi Thông Báo Radar Nền Tảng & MK NETWORK", admin_selected: "Quốc gia / Nền tảng đã chọn:", admin_rate: "⚡ Tỷ lệ nhận OTP (%):", admin_msg: "Nội dung thông báo:", admin_img: "Ảnh đính kèm (Tùy chọn):", admin_send: "🚀 Gửi Thông Báo", admin_clear: "❌ Hủy / Đặt lại",
                admin_back: "⬅️ Quay lại danh sách", admin_stats_orders: "Thống kê số đã lấy", admin_list_orders: "Danh sách số đã lấy", admin_add_bs: "➕ Thêm Số BS", admin_btn_add: "Thêm Số", admin_manage_bs: "⚙️ Quản lý số BS",
                cmd_health: "Health Check", cmd_poll: "Force Poll OTP", cmd_whoami: "MK Account", cmd_testnp: "Test NP API", cmd_radar: "MK Radar", admin_sys_status: "🛠 Trạng thái hệ thống", admin_on: "🟢 ON (Hoạt động)", admin_off: "🔴 OFF (Bảo trì)", admin_maint_msg: "📝 Nội dung thông báo", admin_template1: "Mẫu 1", admin_template2: "Mẫu 2", admin_img_opt: "🖼 Ảnh đính kèm (Tùy chọn)", admin_confirm_maint: "Xác nhận BẢO TRÌ & Gửi thông báo"
            },
            en: { 
                menu_home: "Home", menu_buy: "Buy OTP Number", menu_mail: "Temp Mail", menu_radar: "Radar OTP", menu_history: "History", menu_wallet: "Wallet & Withdraw", menu_stats: "Statistics", menu_leaderboard: "Leaderboard", menu_group: "OTP Group", menu_profile: "Profile", menu_admin: "ADMIN PANEL",
                balance: "Available Balance", today_otp: "Today's OTP", total_orders: "Total Orders", active_orders: "⏳ Active Orders", 
                select_source: "Select Source", ton_wallet: "💵 TON Wallet", save_address: "Save Address", withdraw: "💰 Withdraw", withdraw_all: "⚡ Withdraw All (Fee $0.1)", send_request: "Send Request", 
                invite_friends: "💌 Invite Friends", copy_link: "📋 Copy Link", top_10: "🏆 TOP 10 PLAYERS", your_profile: "👤 YOUR PROFILE", language: "🌐 Language", 
                prev_page: "← Prev", next_page: "Next →", total_otp: "Total OTPs Received", total_otp_all: "Total OTPs All-Time", joined: "Joined", name: "Name", balance_label: "Balance",
                stats_today: "📊 TODAY'S STATISTICS", stats_country: "🌍 OTP BY COUNTRY", stats_platform: "📱 OTP BY PLATFORM", maint_title: "🛠 SYSTEM MAINTENANCE", maint_default_msg: "System is under maintenance. Please come back later!",
                remove_plus: "Remove (+)", national_fmt: "National Format", clear_history: "🗑️ Clear History",
                generate_mail: "Generate Temp Email", mail_username: "Username (Optional)", mail_domain: "Domain", btn_gen_mail: "Generate Mail ...", live_inbox: "📬 Live Inbox:", btn_copy: "📋 Copy", messages: "📥 Messages:", btn_refresh: "🔄 Refresh", no_msgs: "No messages yet.", recoverable: "Recoverable Mails", no_history: "No saved history yet.",
                radar_feed: "📡 Unified Radar Feed", plat_activity: "📊 Platform Activity", last_30m: "Last 30 mins", country_oper: "🌍 Country & Operator", live_otp: "⚡ Live OTP Feed (Real-time)",
                modal_confirm: "Confirm", modal_msg: "Are you sure you want to do this?", btn_cancel: "Cancel", btn_agree: "Agree",
                admin_overview: "Overview", admin_users: "Users", admin_radar: "📡 Radar Broadcast", admin_wd: "Withdrawals", admin_bs: "BS Stock", admin_cmds: "Commands", admin_maint: "Maintenance",
                admin_users_label: "Users", admin_orders_label: "Orders", admin_bot_status: "Bot Status:", admin_stock: "Stock Details", admin_radar_title: "📡 Send Radar Broadcast & MK NETWORK", admin_selected: "Selected Country / Platform:", admin_rate: "⚡ OTP Receive Rate (%):", admin_msg: "Message Content:", admin_img: "Attachment Image (Optional):", admin_send: "🚀 Send Broadcast", admin_clear: "❌ Cancel / Reset",
                admin_back: "⬅️ Back to list", admin_stats_orders: "Order Statistics", admin_list_orders: "Order History", admin_add_bs: "➕ Add BS Numbers", admin_btn_add: "Add Numbers", admin_manage_bs: "⚙️ Manage BS Stock",
                cmd_health: "Health Check", cmd_poll: "Force Poll OTP", cmd_whoami: "MK Account", cmd_testnp: "Test NP API", cmd_radar: "MK Radar", admin_sys_status: "🛠 System Status", admin_on: "🟢 ON (Active)", admin_off: "🔴 OFF (Maintenance)", admin_maint_msg: "📝 Message Content", admin_template1: "Template 1", admin_template2: "Template 2", admin_img_opt: "🖼 Attachment Image (Optional)", admin_confirm_maint: "Confirm MAINTENANCE & Send Alert"
            }
        };

        function applyLanguage(lang) {
            if (!translations[lang]) lang = 'vi';
            currentLang = lang;
            
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) {
                    if (el.children.length > 0 && el.tagName !== 'BUTTON' && el.tagName !== 'OPTION') {
                        el.lastChild.textContent = ' ' + translations[lang][key];
                    } else {
                        el.innerText = translations[lang][key];
                    }
                }
            });
            
            const langSelect = document.getElementById('lang-select');
            if (langSelect) langSelect.value = lang;
            
            const activeViewId = document.querySelector('.view.active')?.id.replace('view-', '') || 'home';
            const topTitle = document.getElementById('top-title');
            if (topTitle && translations[lang]['menu_' + activeViewId]) {
                topTitle.innerText = translations[lang]['menu_' + activeViewId];
            }
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
                try { return JSON.parse(text); } catch(e) { return { error: 'Server Error: ' + text.substring(0, 50) }; }
            } catch (e) { return { error: 'Connection error!' }; }
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

            const topTitle = document.getElementById('top-title');
            if (topTitle && translations[currentLang]['menu_' + viewId]) {
                topTitle.innerText = translations[currentLang]['menu_' + viewId];
            }

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
                document.getElementById('maint-text').innerText = data.maint_message || translations[currentLang].maint_default_msg;
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
            
            const validOrders = data.orders.filter(o => {
                if (o.status === 'CANCELLED' || o.status === 'EXPIRED') return false;
                // FIX: Lọc bỏ các đơn đã quá hạn từ server trả về (đề phòng cronjob chưa kịp update)
                if (o.status === 'PENDING' && o.expires_at) {
                    const exp = new Date(o.expires_at);
                    if (exp.getTime() < Date.now()) return false;
                }
                return true;
            });

            if (validOrders.length === 0) {
                listDiv.innerHTML = `<div class="loading" style="background: var(--surface); border-radius: 16px; border: 1px dashed var(--border);">${translations[currentLang].no_active_orders || 'Không có đơn nào đang chờ.'}</div>`;
                return;
            }

            validOrders.forEach(o => {
                if (o.status === 'COMPLETED' && o.otp && !lastKnownCompletedOrders.has(o.id)) {
                    lastKnownCompletedOrders.add(o.id);
                    showToast(`🎉 Nhận OTP cho số ${o.phone}: ${o.otp}`);
                }
            });

            listDiv.innerHTML = validOrders.map(o => renderOrderCard(o, false)).join('');
        }

        async function loadTempMailData() {
            const domainSel = document.getElementById('mail-domain-select');
            const historyDiv = document.getElementById('mail-history-list');
            if (!domainSel || !historyDiv) return;

            const domRes = await api('/api/mini/mail/domains');
            if (domRes.domains && domRes.domains.length > 0) {
                domainSel.innerHTML = domRes.domains.map((d, i) => `<option value="${d}">🔒 Máy chủ Mail #${i+1} (${d})</option>`).join('');
            } else {
                domainSel.innerHTML = `<option value="inbox.numberpanel.tech">🔒 Máy chủ Mail #1</option>`;
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
                historyDiv.innerHTML = `<div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 10px;">${translations[currentLang].no_history}</div>`;
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
                        <div style="font-weight: bold; font-size: 14px; color: var(--primary); margin-bottom: 4px;">📩 ${m.from || 'Sender'}</div>
                        <div style="font-size: 13px; color: var(--text); white-space: pre-wrap;">${m.subject || 'No subject'}</div>
                        <div style="font-size: 11px; color: var(--text-muted); margin-top: 6px;">${new Date(m.date).toLocaleString()}</div>
                    </div>
                `).join('');
            } else {
                msgList.innerHTML = `<div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 15px;">${translations[currentLang].no_msgs}</div>`;
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
            if (isLoadingRadar) return; 
            isLoadingRadar = true;
            
            const feedDiv = document.getElementById('radar-feed-list');
            const platDiv = document.getElementById('radar-platforms-chart');
            const ctryDiv = document.getElementById('radar-countries-chart');
            const countEl = document.getElementById('radar-records-count');
            if (!feedDiv) { isLoadingRadar = false; return; }

            try {
                const data = await api('/api/mini/radar');
                if (data.error) { feedDiv.innerHTML = `<div style="color:var(--danger)">${data.error}</div>`; isLoadingRadar = false; return; }
                if (countEl) countEl.innerText = (data.total_records || 0) + " records";

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

                if (!data.items || data.items.length === 0) { feedDiv.innerHTML = '<div class="loading">No Radar Data.</div>'; isLoadingRadar = false; return; }

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
                                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">SMS Content:</div>
                                <div style="font-size: 14px; font-weight: 500; color: var(--text);">${i.message}</div>
                            </div>
                        </div>
                    </div>
                `).join('');
            } finally {
                isLoadingRadar = false;
            }
        }

        setInterval(() => {
            document.querySelectorAll('.radar-time').forEach(el => {
                const ts = parseInt(el.getAttribute('data-timestamp'));
                if (!isNaN(ts)) el.innerText = '⏳ ' + formatTimeAgo(ts);
            });
        }, 1000);

        function startRadarRefresh() { stopRadarRefresh(); radarRefreshInterval = setInterval(loadRadarFeed, 3000); }
        function stopRadarRefresh() { if (radarRefreshInterval) clearInterval(radarRefreshInterval); }

        // FIX: Hàm đếm ngược chạy mỗi 1 giây
        function startTimer() {
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = setInterval(() => {
                document.querySelectorAll('.countdown').forEach(el => {
                    const expStr = el.getAttribute('data-exp');
                    if(!expStr) return;
                    const exp = new Date(expStr);
                    const now = new Date();
                    const diff = Math.max(0, Math.floor((exp - now) / 1000));
                    
                    if (diff <= 0) {
                        el.innerText = "⌛ Đã hết hạn";
                        // Tự động xóa đơn khỏi giao diện nếu đã hết hạn
                        const card = el.closest('.order-card');
                        if(card) card.style.display = 'none';
                    } else {
                        const m = Math.floor(diff / 60).toString().padStart(2, '0');
                        const s = (diff % 60).toString().padStart(2, '0');
                        el.innerText = `⏳ Còn lại: ${m}:${s}`;
                    }
                });
            }, 1000);
        }

        async function loadStats() {
            if (isLoadingStats) return; 
            isLoadingStats = true;
            
            const listC = document.getElementById('stats-countries-list');
            const listP = document.getElementById('stats-platforms-list');
            if (!listC || !listP) { isLoadingStats = false; return; }
            
            try {
                const data = await api('/api/mini/stats');
                if(data.error) { isLoadingStats = false; return; }

                document.getElementById('stats-all-time-otps').innerText = data.total_all_otps || 0;
                document.getElementById('stats-today-otps').innerText = data.today_otps || 0;

                if (data.countries) {
                    listC.innerHTML = data.countries.length === 0 ? '<div style="color:var(--text-muted);font-size:14px;">No data today.</div>' : data.countries.map(c => `
                        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                            <span>${c.flag} ${c.country}</span><b style="color:var(--primary);">${c.count}</b>
                        </div>
                    `).join('');
                }

                if (data.platforms) {
                    listP.innerHTML = data.platforms.length === 0 ? '<div style="color:var(--text-muted);font-size:14px;">No data today.</div>' : data.platforms.map(p => `
                        <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                            <span>${p.icon} ${p.platform}</span><b style="color:var(--success);">${p.count}</b>
                        </div>
                    `).join('');
                }
            } finally {
                isLoadingStats = false;
            }
        }

        function startStatsRefresh() { stopStatsRefresh(); statsRefreshInterval = setInterval(loadStats, 5000); }
        function stopStatsRefresh() { if (statsRefreshInterval) clearInterval(statsRefreshInterval); }

        async function loadLeaderboard() {
            const listDiv = document.getElementById('leaderboard-list');
            if (!listDiv) return;
            const data = await api('/api/mini/leaderboard');
            if (!data.leaderboard || data.leaderboard.length === 0) return listDiv.innerHTML = '<div class="loading">No data.</div>';
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
            listDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Loading...</div>';
            
            const data = await api('/api/mini/orders?page=' + page);
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading">No transaction history.</div>';
                if (pagDiv) pagDiv.style.display = 'none';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, true)).join('');
            totalHistoryPages = data.total_pages || 1;
            
            if (totalHistoryPages > 1 && pagDiv) {
                pagDiv.style.display = 'flex';
                document.getElementById('page-info').innerText = `Page ${currentHistoryPage} / ${totalHistoryPages}`;
                document.getElementById('btn-prev').disabled = currentHistoryPage <= 1;
                document.getElementById('btn-next').disabled = currentHistoryPage >= totalHistoryPages;
            } else if (pagDiv) { pagDiv.style.display = 'none'; }
        }

        async function clearHistory() {
            const confirmed = await showCustomModal('Clear History', 'Are you sure you want to clear all past orders?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/clear', 'POST');
            if (res.ok) { showToast('History cleared!'); loadHistory(1); }
            else { alert(res.error || 'Error clearing history'); }
        }

        function changeHistoryPage(delta) {
            const newPage = currentHistoryPage + delta;
            if (newPage >= 1 && newPage <= totalHistoryPages) loadHistory(newPage);
        }

        function renderOrderCard(o, isHistory) {
            const hasOtp = o.status === 'COMPLETED' || (o.otp && o.otp !== 'null' && o.otp !== '');
            let statusText = '⏳ Waiting OTP';
            let badgeColor = 'var(--warning)';
            let cardClass = 'order-card pending';
            
            if (hasOtp) {
                statusText = '🟢 OTP Received';
                badgeColor = 'var(--success)';
                cardClass = 'order-card completed';
            } else if (o.status === 'CANCELLED') {
                statusText = '🚫 Cancelled';
                badgeColor = 'var(--danger)';
                cardClass = 'order-card cancelled';
            } else if (o.status === 'EXPIRED') {
                statusText = '⌛ Expired';
                badgeColor = 'var(--danger)';
                cardClass = 'order-card expired';
            }

            // FIX: Thêm div countdown nếu có expires_at
            let countdownHtml = '';
            if (o.status === 'PENDING' && o.expires_at) {
                countdownHtml = `<div id="timer-${o.id}" class="countdown" data-exp="${o.expires_at}">⏳ Đang tính toán...</div>`;
            }

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
                        <label><input type="checkbox" id="chk-plus-${o.id}" onchange="updatePhoneDisplay('${o.id}', '${o.phone}')"> Remove (+)</label>
                        <label><input type="checkbox" id="chk-nat-${o.id}" onchange="updatePhoneDisplay('${o.id}', '${o.phone}')"> National Format</label>
                    </div>
                    ${countdownHtml} <!-- CHÈN ĐẾM NGƯỢC VÀO ĐÂY -->
                    ${hasOtp ? `
                        <div class="otp-box">
                            <div>
                                <div style="font-size: 12px; color: var(--success); margin-bottom: 4px; font-weight: 600;">🔑 OTP CODE:</div>
                                <div class="otp-code">${o.otp}</div>
                            </div>
                            <button class="btn-small copy" style="background: var(--success); width: 85px;" onclick="copyText('${o.otp}')">📋 Copy</button>
                        </div>
                    ` : ''}
                    <div class="action-row">
                        <button class="btn-small copy" onclick="copyText(document.getElementById('phone-text-${o.id}').innerText)">📋 Copy Phone</button>
                        ${o.status === 'PENDING' && !hasOtp && !isHistory ? `<button class="btn-small cancel" onclick="cancelOrder(${o.id})">❌ Cancel</button>` : ''}
                    </div>
                </div>
            `;
        }

        async function cancelOrder(oid) {
            const confirmed = await showCustomModal('Cancel Order', 'Are you sure you want to cancel this order?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/' + oid + '/cancel', 'POST');
            if (res.ok) { loadHome(); showToast('Order cancelled'); }
            else { alert('Error: ' + res.error); }
        }

        async function renderBuyOptions() {
            const providerSel = document.getElementById('provider-select');
            const container = document.getElementById('buy-list-container');
            if (!providerSel || !container) return;
            
            const provider = providerSel.value;
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Loading...</div>';

            if (provider === 'MK') {
                const data = await api('/api/mini/mk/ranges');
                if (!data.countries) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">No data.</div>';
                container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('MK', '${c.range}', '${c.name}')"><div class="name">${c.flag} ${c.name}</div></button>
                `).join('');
            } 
            else if (provider === 'SLVN') {
                const data = await api('/api/mini/slvn/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">No SLVN numbers.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('SLVN', '${c.code}', '${c.name}', '${c.tag}')"><div class="name">${c.flag} ${c.name}</div></button>
                `).join('');
            }
            else if (provider === 'NP') {
                const data = await api('/api/mini/np/services');
                if (!data.services || data.services.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">No NP services.</div>';
                else container.innerHTML = data.services.map(s => `
                    <button class="list-btn" onclick="loadNpCountries('${s.key}')"><div class="name">🔧 ${s.name}</div><div class="count">Còn ${s.count} số</div></button>
                `).join('');
            }
            else if (provider === 'BS') {
                const data = await api('/api/mini/bs/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">No BS Stock.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('BS', '${c.name}', '${c.name}')"><div class="name">${c.flag} ${c.name}</div><div class="count">Còn ${c.count} số</div></button>
                `).join('');
            }
        }

        async function loadNpCountries(serviceName) {
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Loading...</div>';
            const data = await api('/api/mini/np/countries?service=' + encodeURIComponent(serviceName));
            if (!data.countries) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Error loading NP countries.</div>';
            container.innerHTML = data.countries.map(c => `
                <button class="list-btn" onclick="buyNumber('NP', '${c.name}', '${c.name}', '${serviceName}')"><div class="name">🌍 ${c.name}</div><div class="count">Còn ${c.count} số</div></button>
            `).join('');
        }

        async function buyNumber(provider, code, name, param3 = null) {
            const confirmed = await showCustomModal('Confirm', `Do you want to get a number from ${name}?`);
            if (!confirmed) return;

            let body = { provider };
            if (provider === 'MK') { body.range = code; body.country_name = name; }
            if (provider === 'SLVN') { body.country_code = code; body.tag = param3; }
            if (provider === 'NP') { body.country = code; body.service = param3; }
            if (provider === 'BS') { body.country = code; }

            const res = await api('/api/mini/orders', 'POST', body);
            if (res.ok) { showToast('✅ Number acquired!'); navTo('home'); }
            else { alert('❌ Error: ' + (res.error || 'Cannot get number')); }
        }

        function loadWallet() { loadUserData(); }

        function loadProfile() {
            if (!userData || !userData.user) return;
            const u = userData.user;
            const t = translations[currentLang];
            document.getElementById('profile-info').innerHTML = `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">🆔 Telegram ID: <b>${u.id}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">👤 ${t.name}: <b>${u.first_name || 'User'}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">💰 ${t.balance_label}: <b style="color: var(--success);">$${(u.usd_milli/1000).toFixed(3)}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">📩 ${t.total_otp}: <b style="color: var(--primary);">${userData.total_otps || 0}</b></div>
                <div style="padding: 10px 0;">📅 ${t.joined}: <b>${new Date(u.joined_at).toLocaleString('vi-VN')}</b></div>
            `;
        }

        function setWithdrawAmount(type) {
            const input = document.getElementById('withdraw-amount');
            if (!input) return;
            if (type === 'max') {
                if (!userData || !userData.user) return;
                let finalAmt = (userData.user.usd_milli / 1000) - 0.1;
                input.value = (finalAmt < 0 ? 0 : finalAmt).toFixed(3);
                showToast('Fee $0.1 applied');
            } else { input.value = type; }
        }

        async function saveWallet() {
            const address = document.getElementById('ton-address').value;
            const res = await api('/api/mini/wallet/address', 'POST', { address });
            if (res.ok) showToast('Wallet saved!');
            else alert('Error: ' + res.error);
        }

        async function requestWithdraw() {
            const amount = document.getElementById('withdraw-amount').value;
            if (!amount || amount < 1) return alert('Minimum amount is $1.00');
            const res = await api('/api/mini/wallet/withdraw', 'POST', { amount });
            if (res.ok) { alert('Withdrawal request sent. Please wait for Admin approval.'); loadUserData(); }
            else alert('Error: ' + (res.error || 'Unknown error'));
        }

        function copyRef() {
            navigator.clipboard.writeText(document.getElementById('ref-link').innerText).then(() => showToast('Link copied!'));
        }

        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => showToast('Copied: ' + text));
        }

        // ADMIN PANEL
        function selectRadarPlatform(platName) {
            document.getElementById('broadcast-platform').value = platName;
            const sliderVal = document.getElementById('broadcast-rate-slider').value;
            const pct = sliderVal * 10;
            document.getElementById('broadcast-msg').value = `🚨 HIGH OTP RADAR ALERT\n\nPlatform / Country: ${platName}\nOTP Receive Rate: ${pct}%\nGrab a number now!`;
            showToast('Selected: ' + platName);
        }

        function updateRateSlider(val) {
            const pct = val * 10;
            document.getElementById('slider-percent-val').innerText = `${pct}% (Level ${val})`;
            const plat = document.getElementById('broadcast-platform').value || 'Guinea';
            document.getElementById('broadcast-msg').value = `🚨 HIGH OTP RADAR ALERT\n\nPlatform / Country: ${plat}\nOTP Receive Rate: ${pct}%\nGrab a number now!`;
        }

        function clearRadarBroadcast() {
            document.getElementById('broadcast-platform').value = 'Guinea (MK)';
            document.getElementById('broadcast-rate-slider').value = 10;
            updateRateSlider(10);
            document.getElementById('broadcast-image').value = '';
            showToast('Form reset!');
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

            const confirmed = await showCustomModal('Confirm Send', 'Send this radar broadcast to all users?');
            if (!confirmed) return;

            const res = await api('/api/mini/admin/broadcast/radar', 'POST', { platform, message, image_b64: b64 });
            if (res.ok) { alert(res.msg); clearRadarBroadcast(); }
            else { alert(res.error || 'Error sending broadcast'); }
        }

        async function loadAdmin() {
            const data = await api('/api/mini/admin/data');
            if (data.error) return alert(data.error);
            
            document.getElementById('admin-total-users').innerText = data.stats.users;
            document.getElementById('admin-total-orders').innerText = data.stats.orders;
            
            const statusEl = document.getElementById('admin-bot-status');
            if (statusEl) {
                if (data.maintenance === 'on') {
                    statusEl.innerText = translations[currentLang].admin_status_off || '🔴 Maintenance';
                    statusEl.style.color = 'var(--danger)';
                } else {
                    statusEl.innerText = translations[currentLang].admin_status_on || '🟢 Active';
                    statusEl.style.color = 'var(--success)';
                }
                isMaintenanceOn = (data.maintenance === 'on');
            }

            document.getElementById('admin-stock-info').innerHTML = `
                <div class="row"><span>Pending Withdrawals:</span> <b>${data.stats.pending_wd}</b></div>
                <div class="row"><span>BS Stock:</span> <b>${data.stats.bs_count}</b></div>
            `;

            const wdDiv = document.getElementById('admin-wd-list');
            if (wdDiv) {
                wdDiv.innerHTML = (!data.withdrawals || data.withdrawals.length === 0) ? '<div style="color: var(--text-muted); font-size: 14px;">No withdrawal requests.</div>' : data.withdrawals.map(w => `
                    <div class="order-card" style="border-left-color: var(--primary);">
                        <div class="order-header"><div class="order-phone">${w.name} (${w.user_id})</div><div class="order-badge" style="color: var(--primary);">$${(w.amount/1000).toFixed(3)}</div></div>
                        <div style="font-size: 13px; color: var(--text-muted); word-break: break-all; margin-bottom: 12px;">Wallet: ${w.wallet}</div>
                        <div class="action-row">
                            <button class="btn-small" style="background: var(--success);" onclick="adminWdAction(${w.id}, 'approve')">✅ Approve</button>
                            <button class="btn-small" style="background: var(--danger);" onclick="adminWdAction(${w.id}, 'reject')">❌ Reject</button>
                        </div>
                    </div>
                `).join('');
            }
            updateMaintUI();
        }

        function switchAdminTab(tab, btn) {
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.admin-tab-content').forEach(c => c.style.display = 'none');
            if (btn) btn.classList.add('active');
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
            
            const formTitle = document.getElementById('maint-form-title');
            const submitBtn = document.getElementById('maint-submit-btn');
            
            if (isMaintenanceOn) {
                btnOn.classList.remove('on'); btnOff.classList.add('off'); form.style.display = 'block';
                formTitle.innerText = "📝 Nội dung thông báo (Bảo trì)";
                submitBtn.innerText = "Xác nhận BẢO TRÌ & Gửi thông báo";
                submitBtn.onclick = function() { submitMaintenanceAction('disable'); };
            } else {
                btnOn.classList.add('on'); btnOff.classList.remove('off'); form.style.display = 'none';
            }
        }

        async function toggleMaintenance(enable) {
            if (enable) {
                // Khi bấm ON -> Hiển thị form nhập thông báo (Bot hoạt động lại)
                const form = document.getElementById('maint-form-container');
                const formTitle = document.getElementById('maint-form-title');
                const submitBtn = document.getElementById('maint-submit-btn');
                form.style.display = 'block';
                formTitle.innerText = "📝 Thông báo hoạt động trở lại";
                submitBtn.innerText = "Xác nhận HOẠT ĐỘNG & Thông báo";
                submitBtn.onclick = function() { submitMaintenanceAction('enable'); };
                document.getElementById('maint-msg').value = "🎉 <b>Bot đã hoạt động trở lại!</b>\nMời anh em vào lấy số tiếp nhé!";
            } else {
                isMaintenanceOn = true;
                updateMaintUI();
            }
        }

        function setMaintTemplate(id) {
            const ta = document.getElementById('maint-msg');
            if (!ta) return;
            if (id === 1) ta.value = "Hệ thống đang được bảo trì để nâng cấp. Vui lòng quay lại sau ít phút!";
            if (id === 2) ta.value = "Server đang gặp sự cố kỹ thuật. Admin đang khắc phục!";
        }

        async function submitMaintenanceAction(action) {
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
            const confirmed = await showCustomModal('Confirm', `Xác nhận thực hiện?`);
            if(!confirmed) return;

            const res = await api('/api/mini/admin/maintenance', 'POST', { action: action, message: ta.value, image_b64: b64 });
            if(res.ok) { 
                alert(res.msg); 
                ta.value = ''; 
                if (fileInput) fileInput.value = ''; 
                isMaintenanceOn = (action === 'disable'); 
                document.getElementById('maint-form-container').style.display = 'none';
                loadAdmin(); 
            }
            else alert("Error: " + (res.error || 'Unknown'));
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
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-bonus-amt" class="form-control" placeholder="Amount ($)" step="0.1" style="flex:1;"><button class="btn btn-success" style="margin-top:0; width:120px;" onclick="adminUserAction(${uid}, 'bonus')">➕ Add</button></div>
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-deduct-amt" class="form-control" placeholder="Amount to deduct ($)" step="0.1" style="flex:1;"><button class="btn btn-danger" style="margin-top:0; width:120px; background: #ea580c;" onclick="adminUserAction(${uid}, 'deduct')">➖ Deduct</button></div>
                    <div style="display: flex; gap: 8px;"><input type="number" id="admin-min-amt" class="form-control" placeholder="Set balance ($)" step="0.1" style="flex:1;"><button class="btn btn-primary" style="margin-top:0; width:120px;" onclick="adminUserAction(${uid}, 'set_min')">⚙️ Set</button></div>
                    <button class="btn btn-danger" style="margin-top:0;" onclick="adminUserAction(${uid}, 'revoke')">🗑️ Revoke All Balance</button>
                </div>
            `;
            document.getElementById('admin-user-detail-orders').innerHTML = '<div class="spinner"></div>';
            
            const data = await api('/api/mini/admin/users/' + uid + '?page=1');
            if(data.error) return document.getElementById('u-detail-text').innerText = data.error;

            const u = data.user;
            document.getElementById('u-detail-text').innerHTML = `
                <div><b>Name:</b> ${u.name}</div><div><b>Username:</b> @${u.username || '—'}</div>
                <div><b>Telegram ID:</b> ${u.id}</div><div><b>Balance:</b> <span style="color:var(--success);">$${(u.balance/1000).toFixed(3)}</span></div>
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
            if ((action === 'bonus' || action === 'deduct' || action === 'set_min') && (!val || val <= 0)) return alert('Enter a valid amount!');
            if (action === 'revoke' && !confirm('Revoke all balance?')) return;

            const res = await api(`/api/mini/admin/users/${uid}/action`, 'POST', { action, amount: val });
            if (res.ok) { showToast(res.msg); loadAdminUserDetail(uid); } else alert(res.error);
        }

        function renderAdminUserOrders(data) {
            const div = document.getElementById('admin-user-detail-orders');
            const pag = document.getElementById('user-detail-pagination');
            if (!div) return;
            if(!data.orders || data.orders.length === 0) {
                div.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">No orders yet.</div>';
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
                document.getElementById('user-page-info').innerText = `Page ${data.current_page} / ${totalUserDetailPages}`;
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

        // Upload file xử lý
        function handleBsFileUpload(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = function(e) {
                const content = e.target.result;
                const bsInput = document.getElementById('bs-input');
                bsInput.value += (bsInput.value ? '\n' : '') + content;
                showToast('Đã tải file! Bấm "Thêm Số" để lưu.');
            };
            reader.readAsText(file);
            event.target.value = ''; // reset input
        }

        async function loadAdminBs() {
            const div = document.getElementById('admin-bs-list');
            if (!div) return;
            div.innerHTML = '<div class="spinner"></div>';
            const data = await api('/api/mini/bs/countries');
            if(!data.countries || data.countries.length === 0) return div.innerHTML = 'No BS Stock.';
            div.innerHTML = data.countries.map(c => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);align-items:center;">
                    <span>${c.flag} ${c.name} (${c.count})</span>
                    <button class="btn-small cancel" style="width:auto;padding:6px 12px;" onclick="deleteBs('${c.name}')">Delete</button>
                </div>
            `).join('') + `<button class="btn btn-danger" style="margin-top:15px;" onclick="deleteBs('ALL')">DELETE ALL BS STOCK</button>`;
        }

        async function deleteBs(country) {
            if(!await showCustomModal('Delete BS', `Delete all numbers for ${country}?`)) return;
            const res = await api('/api/mini/admin/bs/delete', 'POST', { country });
            if(res.ok) { showToast('Deleted!'); loadAdminBs(); loadAdmin(); } else alert(res.error);
        }

        async function runAdminCmd(cmd) {
            const out = document.getElementById('cmd-output');
            if (!out) return;
            out.innerText = 'Running...';
            const res = await api('/api/mini/admin/cmd', 'POST', { cmd });
            out.innerText = res.ok ? res.msg : ('Error: ' + (res.error || 'Unknown'));
        }

        async function adminWdAction(wid, action) {
            if(!await showCustomModal('Confirm', `Are you sure you want to ${action === 'approve' ? 'APPROVE' : 'REJECT'}?`)) return;
            const res = await api('/api/mini/admin/withdraw/action', 'POST', { wid, action });
            if (res.ok) { loadAdmin(); showToast('Success!'); } else alert(res.error);
        }

        async function addBsNumbers() {
            const numbers = document.getElementById('bs-input').value;
            if (!numbers) return alert('Please enter numbers!');
            const res = await api('/api/mini/admin/bs/add', 'POST', { numbers });
            if (res.ok) { alert(`Added ${res.added} numbers`); document.getElementById('bs-input').value = ''; loadAdminBs(); } else alert(res.error);
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {
                if (document.querySelector('.view.active')?.id === 'view-home') loadHome(true);
            }, 2000);
        }

        loadUserData();
        loadHome();
        startAutoRefresh();
        startTimer(); // FIX: Kích hoạt đếm ngược
    </script>
</body>
</html>
"""
