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
        
        .stats-grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
        .stat-box-3 { background: var(--surface); padding: 12px 6px; border-radius: var(--radius); text-align: center; border: 1px solid var(--border); }
        .stat-box-3 .value { font-size: 18px; font-weight: 700; color: var(--text); margin-top: 5px; }
        .stat-box-3 .label { font-size: 11px; color: var(--text-muted); font-weight: 500; }

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
        .order-card.cancelled { border-left: 4px solid var(--danger); opacity: 0.6; }

        .order-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
        .order-phone { font-size: 18px; font-weight: 700; color: var(--text); letter-spacing: 0.5px; }
        .order-badge { font-size: 12px; padding: 4px 10px; border-radius: 20px; font-weight: 600; background: rgba(255,255,255,0.1); display: flex; align-items: center; gap: 5px; }
        .order-info { display: flex; gap: 15px; font-size: 13px; color: var(--text-muted); margin-bottom: 12px; flex-wrap: wrap;}
        .order-info span { display: flex; align-items: center; gap: 5px; }
        
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
        .nav-item { display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 10px; gap: 3px; background: none; transition: 0.2s; min-width: 18%; font-weight: 500; white-space: nowrap; }
        .nav-item .icon { font-size: 20px; transition: 0.2s; }
        .nav-item.active { color: var(--primary); }
        .nav-item.active .icon { transform: translateY(-3px); }

        .loading { text-align: center; padding: 30px; color: var(--text-muted); }
        .spinner { border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--primary); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        #toast { position: fixed; bottom: 95px; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--surface); backdrop-filter: var(--glass-blur); color: white; padding: 12px 24px; border-radius: 30px; font-weight: 500; border: 1px solid var(--border); box-shadow: var(--shadow); opacity: 0; transition: 0.3s; z-index: 2000; pointer-events: none; }
        #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
    </style>
</head>
<body>
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
            <a href="#" class="menu-item active" onclick="navTo('home')"><span class="icon">🏠</span> <span>Trang chủ</span></a>
            <a href="#" class="menu-item" onclick="navTo('buy')"><span class="icon">🛒</span> <span>Mua Số OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('tempmail')"><span class="icon">📧</span> <span>Tạo Temp Mail</span></a>
            <a href="#" class="menu-item" onclick="navTo('radar')"><span class="icon">📡</span> <span>Radar OTP</span></a>
            <a href="#" class="menu-item" onclick="navTo('history')"><span class="icon">📜</span> <span>Lịch sử</span></a>
            <a href="#" class="menu-item" onclick="navTo('wallet')"><span class="icon">💵</span> <span>Ví & Rút Tiền</span></a>
            <a href="#" class="menu-item" onclick="navTo('stats')"><span class="icon">📊</span> <span>Thống Kê</span></a>
            <a href="#" class="menu-item" onclick="navTo('leaderboard')"><span class="icon">🏆</span> <span>Bảng Xếp Hạng</span></a>
            <a href="#" class="menu-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')"><span class="icon">📢</span> <span>OTP Group</span></a>
            <a href="#" class="menu-item" onclick="navTo('profile')"><span class="icon">👤</span> <span>Hồ Sơ</span></a>
            <a href="#" class="menu-item menu-admin" id="menu-admin" onclick="navTo('admin')" style="display: none;">
                <span class="icon">🛡</span> <span>ADMIN PANEL</span>
            </a>
        </div>
    </div>

    <div class="top-bar" id="main-top-bar">
        <button class="menu-btn" onclick="toggleSidebar()">☰</button>
        <div class="page-title" id="top-title">Trang chủ</div>
    </div>

    <div class="container" id="main-container">
        <!-- HOME -->
        <div id="view-home" class="view active">
            <div class="card balance-card">
                <div class="balance-title">Số dư khả dụng</div>
                <div class="balance-amount" id="home-balance">$0.000</div>
            </div>

            <div class="stats-grid-3">
                <div class="stat-box-3">
                    <div class="label">OTP Hôm Nay</div>
                    <div class="value" id="home-today-otps">0</div>
                </div>
                <div class="stat-box-3">
                    <div class="label">Tổng OTP</div>
                    <div class="value" id="home-total-otps" style="color: var(--success);">0</div>
                </div>
                <div class="stat-box-3">
                    <div class="label">Tổng Đơn</div>
                    <div class="value" id="home-total-orders">0</div>
                </div>
            </div>

            <h3 style="margin-bottom: 15px; font-size: 18px; font-weight: 600;">⏳ Đơn Đang Chờ</h3>
            <div id="active-orders-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
        </div>

        <!-- BUY -->
        <div id="view-buy" class="view">
            <div class="card">
                <div class="form-group">
                    <label class="form-label">Chọn Nguồn Số</label>
                    <select class="form-control" id="provider-select" onchange="renderBuyOptions()">
                        <option value="MK">🎱 Numbers 1 (MK)</option>
                        <option value="NP">📱 Numbers 2 (NP - NumberPanel)</option>
                        <option value="BASHA">🔢 Numbers BS (Basha)</option>
                        <option value="SLVN">🌐 Numbers 4 (SLVN)</option>
                    </select>
                </div>
            </div>
            <div id="buy-list-container" class="list-grid"></div>
        </div>

        <!-- TEMP MAIL (TẠO GMAIL ẢO GIAO DIỆN CHUẨN GỐC) -->
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
            <div class="card"><div id="radar-feed-list"><div class="loading"><div class="spinner"></div>Đang tải radar...</div></div></div>
        </div>

        <!-- HISTORY -->
        <div id="view-history" class="view">
            <div id="history-list">
                <div class="loading"><div class="spinner"></div>Đang tải...</div>
            </div>
            <div class="pagination" id="history-pagination" style="display: none;">
                <button id="btn-prev" onclick="changeHistoryPage(-1)">← Trang trước</button>
                <span id="page-info">Trang 1 / 1</span>
                <button id="btn-next" onclick="changeHistoryPage(1)">Trang sau →</button>
            </div>
        </div>

        <!-- WALLET -->
        <div id="view-wallet" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💵 Ví TON</div>
                <div class="form-group"><input type="text" class="form-control" id="ton-address" placeholder="UQ... hoặc EQ..."></div>
                <button class="btn btn-primary" onclick="saveWallet()">Lưu Địa Chỉ</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💰 Rút Tiền</div>
                <div class="form-group"><input type="number" class="form-control" id="withdraw-amount" placeholder="Nhập số tiền ($)" step="0.1"></div>
                <button class="btn btn-success" onclick="requestWithdraw()">Gửi Yêu Cầu</button>
            </div>
        </div>

        <!-- STATS & PROFILE & LEADERBOARD -->
        <div id="view-stats" class="view"><div class="card"><div id="stats-content"></div></div></div>
        <div id="view-leaderboard" class="view"><div class="card"><div id="leaderboard-list"></div></div></div>
        <div id="view-profile" class="view"><div class="card"><div id="profile-info"></div></div></div>

        <!-- ADMIN -->
        <div id="view-admin" class="view">
            <div class="card">
                <div class="form-label" style="font-size:16px; font-weight:bold; margin-bottom:10px;">📡 Gửi Thông Báo Radar Nền Tảng & Quốc Gia</div>
                <div class="form-group">
                    <label class="form-label">Chọn Nền Tảng:</label>
                    <select class="form-control" id="broadcast-platform">
                        <option value="Instagram">📸 Instagram</option>
                        <option value="Facebook">📘 Facebook</option>
                        <option value="TikTok">🎬 TikTok</option>
                        <option value="Telegram">✈️ Telegram</option>
                        <option value="WhatsApp">💬 WhatsApp</option>
                    </select>
                </div>
                <button class="btn btn-success" onclick="sendRadarBroadcast()">🚀 Gửi Thông Báo</button>
            </div>
        </div>
    </div>

    <div class="bottom-nav" id="main-bottom-nav">
        <button class="nav-item active" id="nav-home" onclick="navTo('home')"><span class="icon">🏠</span><span>Trang chủ</span></button>
        <button class="nav-item" id="nav-buy" onclick="navTo('buy')"><span class="icon">🛒</span><span>Mua số</span></button>
        <button class="nav-item" id="nav-tempmail" onclick="navTo('tempmail')"><span class="icon">📧</span><span>Temp Mail</span></button>
        <button class="nav-item" id="nav-radar" onclick="navTo('radar')"><span class="icon">📡</span><span>Radar</span></button>
        <button class="nav-item" id="nav-history" onclick="navTo('history')"><span class="icon">📜</span><span>Lịch sử</span></button>
    </div>

    <script>
        const tg = window.Telegram?.WebApp || { initData: "", expand: function() {}, ready: function() {} };
        try { tg.expand(); tg.ready(); } catch(e) {}

        let userData = null;
        let currentActiveMailAddress = null;

        async function api(path, method = 'GET', body = null) {
            const opts = { method, headers: { 'X-Telegram-Init-Data': tg.initData || '', 'Content-Type': 'application/json' } };
            if (body) opts.body = JSON.stringify(body);
            try {
                const res = await fetch(path, opts);
                return await res.json();
            } catch(e) { return { error: 'Lỗi kết nối' }; }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2500);
        }

        function toggleSidebar() { document.getElementById('sidebar').classList.toggle('open'); document.getElementById('overlay').classList.toggle('open'); }
        function navTo(viewId) {
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(v => v.classList.remove('active'));
            document.getElementById('view-' + viewId).classList.add('active');
            const navBtn = document.getElementById('nav-' + viewId);
            if(navBtn) navBtn.classList.add('active');

            if (document.getElementById('sidebar').classList.contains('open')) toggleSidebar();
            if (viewId === 'home') loadHome();
            if (viewId === 'buy') renderBuyOptions();
            if (viewId === 'tempmail') loadTempMailData();
            if (viewId === 'history') loadHistory(1);
        }

        async function loadUserData() {
            const data = await api('/api/mini/me');
            if (data.error) return;
            userData = data;
            document.getElementById('home-balance').innerText = '$' + (data.user.usd_milli / 1000).toFixed(3);
            document.getElementById('home-today-otps').innerText = data.today_otps || 0;
            document.getElementById('home-total-otps').innerText = data.total_otps || 0;
            document.getElementById('home-total-orders').innerText = data.total_orders || 0;
            
            const menuAdmin = document.getElementById('menu-admin');
            if (menuAdmin) menuAdmin.style.display = data.is_admin ? 'flex' : 'none';
        }

        async function loadHome(silent = false) {
            if (!silent) await loadUserData();
            const listDiv = document.getElementById('active-orders-list');
            const data = await api('/api/mini/orders/active');
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading" style="background: var(--surface); border-radius: 16px; border: 1px dashed var(--border);">Không có đơn nào đang chờ.</div>';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, false)).join('');
        }

        function renderOrderCard(o, isHistory) {
            let statusText = '⏳ Chờ OTP';
            let cardClass = 'order-card pending';
            let badgeColor = 'var(--warning)';

            let isExpired = false;
            if (o.created_at) {
                const createdTime = new Date(o.created_at).getTime();
                const now = Date.now();
                if ((now - createdTime) > 15 * 60 * 1000 && o.status === 'PENDING' && !o.otp) {
                    isExpired = true;
                }
            }

            if (o.status === 'COMPLETED' || (o.otp && o.otp !== 'null' && o.otp !== '')) {
                statusText = '🟢 Nhận OTP thành công';
                cardClass = 'order-card completed';
                badgeColor = 'var(--success)';
            } else if (o.status === 'CANCELLED') {
                statusText = '❌ Đã hủy';
                cardClass = 'order-card cancelled';
                badgeColor = 'var(--danger)';
            } else if (o.status === 'EXPIRED' || isExpired) {
                statusText = '⏳ Hết hạn (15p)';
                cardClass = 'order-card expired';
                badgeColor = 'var(--danger)';
            }

            let otpHtml = (o.otp && o.otp !== 'null' && o.otp !== '') ? `
                <div class="otp-box">
                    <div>
                        <div style="font-size: 12px; color: var(--success); margin-bottom: 4px; font-weight: 600;">🔑 MÃ OTP:</div>
                        <div class="otp-code">${o.otp}</div>
                    </div>
                    <button class="btn-small copy" style="background: var(--success); width: 85px;" onclick="navigator.clipboard.writeText('${o.otp}'); showToast('Đã copy!');">📋 Copy</button>
                </div>
            ` : '';

            return `
                <div class="${cardClass}">
                    <div class="order-header">
                        <div class="order-phone">${o.phone}</div>
                        <div class="order-badge" style="color: ${badgeColor};">${statusText}</div>
                    </div>
                    <div class="order-info">
                        <span>${o.flag || '🌐'} ${o.country || 'N/A'}</span>
                        <span>🔧 ${o.provider}</span>
                    </div>
                    ${otpHtml}
                    ${o.status === 'PENDING' && !o.otp && !isExpired && !isHistory ? `
                        <div class="action-row">
                            <button class="btn-small cancel" onclick="cancelOrder(${o.id})">❌ Hủy đơn</button>
                        </div>
                    ` : ''}
                </div>
            `;
        }

        async function cancelOrder(oid) {
            const res = await api(`/api/mini/orders/${oid}/cancel`, 'POST');
            if (res.ok) { loadHome(); showToast('Đã hủy đơn thành công!'); }
            else { alert(res.error || 'Lỗi hủy đơn'); }
        }

        async function loadTempMailData() {
            const domainSel = document.getElementById('mail-domain-select');
            const historyDiv = document.getElementById('mail-history-list');

            const domRes = await api('/api/mini/mail/domains');
            let domainsList = ["inbox.numberpanel.tech", "mail.numberpanel.tech", "bwmyga.com", "lnovic.com", "ruutukf.com", "gmeenramy.com", "olipii.com"];
            if (domRes.domains && domRes.domains.length > 0) {
                domainsList = domRes.domains;
            }
            domainSel.innerHTML = `<option value="">Auto-select random domain</option>` + domainsList.map(d => `<option value="${d}">${d}</option>`).join('');

            const histRes = await api('/api/mini/mail/history');
            if (histRes.history && histRes.history.length > 0) {
                historyDiv.innerHTML = histRes.history.map(h => `
                    <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--border);">
                        <span style="font-size: 14px; font-weight: 500; word-break: break-all;">${h.address}</span>
                        <button class="btn-small copy" style="width: auto; padding: 6px 12px;" onclick="selectMailBox('${h.address}')">Inbox</button>
                    </div>
                `).join('');
            } else {
                historyDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 10px;">No saved history yet.</div>';
            }
        }

        async function generateTempMail() {
            const username = document.getElementById('mail-username').value;
            const domain = document.getElementById('mail-domain-select').value;
            const res = await api('/api/mini/mail/generate', 'POST', { username, domain });
            if (res.success && res.mail) {
                selectMailBox(res.mail.address);
                loadTempMailData();
                showToast('Generated mail successfully!');
            } else {
                alert(res.error || 'Lỗi tạo email ảo');
            }
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
                        <div style="font-size: 13px; color: var(--text); white-space: pre-wrap;">${m.snippet || m.body || 'No content'}</div>
                    </div>
                `).join('');
            } else {
                msgList.innerHTML = '<div style="color: var(--text-muted); font-size: 14px; text-align: center; padding: 15px;">No messages yet.</div>';
            }
        }

        async function renderBuyOptions() {
            const providerSel = document.getElementById('provider-select');
            const container = document.getElementById('buy-list-container');
            if (!providerSel || !container) return;
            
            const provider = providerSel.value;
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải dữ liệu...</div>';

            if (provider === 'MK') {
                const data = await api('/api/mini/mk/ranges');
                if (!data.countries) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Không có dữ liệu.</div>';
                container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('MK', '${c.range}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                    </button>
                `).join('');
            } 
            else if (provider === 'NP') {
                const data = await api('/api/mini/np/services');
                if (!data.services || data.services.length === 0) return container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Không có dịch vụ nào từ NumberPanel.</div>';
                container.innerHTML = data.services.map(s => `
                    <button class="list-btn" onclick="loadNpCountries('${s.name}')">
                        <div class="name">📱 ${s.name}</div>
                        <div class="count">Còn ${s.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'BASHA') {
                const data = await api('/api/mini/bs/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số BS.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('BASHA', '${c.name}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Còn ${c.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'SLVN') {
                const data = await api('/api/mini/slvn/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số SLVN.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('SLVN', '${c.code}', '${c.name}', '${c.tag}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Rate: $${c.rate}</div>
                    </button>
                `).join('');
            }
        }

        async function loadNpCountries(serviceName) {
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải quốc gia...</div>';
            const data = await api('/api/mini/np/countries?service=' + encodeURIComponent(serviceName));
            if (!data.countries || data.countries.length === 0) {
                container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Không có quốc gia khả dụng.</div>';
                return;
            }
            container.innerHTML = data.countries.map(c => `
                <button class="list-btn" onclick="buyNumber('NP', '${c.name}', '${c.name}', '${serviceName}')">
                    <div class="name">🌍 ${c.name}</div>
                    <div class="count">Còn ${c.count} số</div>
                </button>
            `).join('');
        }

        async function buyNumber(provider, code, name, param3 = null) {
            let body = { provider };
            if (provider === 'MK') { body.range = code; body.country_name = name; }
            if (provider === 'NP') { body.country = code; body.service = param3; }
            if (provider === 'BASHA') { body.country = code; }
            if (provider === 'SLVN') { body.country_code = code; body.tag = param3; }

            const res = await api('/api/mini/orders', 'POST', body);
            if (res.ok) { showToast('✅ Lấy số thành công!'); navTo('home'); }
            else { alert('❌ Lỗi: ' + (res.error || 'Không thể lấy số')); }
        }

        async function loadHistory(page = 1) {
            const listDiv = document.getElementById('history-list');
            const data = await api('/api/mini/orders?page=' + page);
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có lịch sử.</div>';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, true)).join('');
        }

        async function saveWallet() {
            const address = document.getElementById('ton-address').value;
            const res = await api('/api/mini/wallet/address', 'POST', { address });
            if (res.ok) showToast('Đã lưu địa chỉ ví!');
            else alert('Lỗi: ' + res.error);
        }

        async function requestWithdraw() {
            const amount = document.getElementById('withdraw-amount').value;
            if (!amount || amount < 1) return alert('Số tiền rút tối thiểu là $1.00');
            const res = await api('/api/mini/wallet/withdraw', 'POST', { amount });
            if (res.ok) { alert('Đã gửi yêu cầu rút tiền thành công!'); loadUserData(); }
            else alert('Lỗi: ' + (res.error || 'Không xác định'));
        }

        async function sendRadarBroadcast() {
            const platform = document.getElementById('broadcast-platform').value;
            const res = await api('/api/mini/admin/broadcast/radar', 'POST', { platform, message: '🚀 Radar OTP cao cho ' + platform });
            if (res.ok) alert(res.msg);
            else alert(res.error || 'Lỗi gửi thông báo');
        }

        loadHome();
    </script>
</body>
</html>
"""
