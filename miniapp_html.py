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
        body { background-color: var(--bg); background-image: radial-gradient(circle at 10% 20%, rgba(59, 130, 246, 0.15) 0%, transparent 20%), radial-gradient(circle at 90% 80%, rgba(139, 92, 246, 0.15) 0%, transparent 20%); color: var(--text); padding-bottom: 80px; overflow-x: hidden; min-height: 100vh; }
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
        .order-info { display: flex; gap: 15px; font-size: 13px; color: var(--text-muted); margin-bottom: 15px; flex-wrap: wrap;}
        .order-info span { display: flex; align-items: center; gap: 5px; }
        .otp-box { background: rgba(15, 23, 42, 0.8); padding: 12px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border: 1px dashed rgba(16, 185, 129, 0.5); }
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

        .bottom-nav { position: fixed; bottom: 0; left: 0; width: 100%; height: 70px; background: rgba(15, 23, 42, 0.9); backdrop-filter: var(--glass-blur); display: flex; justify-content: space-around; align-items: center; border-top: 1px solid var(--border); z-index: 100; }
        .nav-item { display: flex; flex-direction: column; align-items: center; color: var(--text-muted); font-size: 11px; gap: 4px; background: none; transition: 0.2s; width: 25%; font-weight: 500; }
        .nav-item .icon { font-size: 24px; transition: 0.2s; }
        .nav-item.active { color: var(--primary); }
        .nav-item.active .icon { transform: translateY(-3px); }

        .loading { text-align: center; padding: 30px; color: var(--text-muted); }
        .spinner { border: 3px solid rgba(255,255,255,0.1); border-top-color: var(--primary); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 15px; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        #toast { position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%) translateY(20px); background: var(--surface); backdrop-filter: var(--glass-blur); color: white; padding: 12px 24px; border-radius: 30px; font-weight: 500; border: 1px solid var(--border); box-shadow: var(--shadow); opacity: 0; transition: 0.3s; z-index: 2000; pointer-events: none; }
        #toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

        .admin-tabs { display: flex; overflow-x: auto; gap: 8px; margin-bottom: 15px; padding-bottom: 5px; }
        .admin-tab { padding: 8px 16px; border-radius: 20px; background: var(--surface); color: var(--text-muted); white-space: nowrap; font-size: 14px; }
        .admin-tab.active { background: var(--primary); color: white; }
        
        .maint-toggle { display: flex; gap: 10px; margin-bottom: 20px; }
        .maint-btn { flex: 1; padding: 15px; border-radius: 12px; font-weight: 700; font-size: 16px; background: var(--surface); color: var(--text-muted); border: 2px solid transparent; }
        .maint-btn.on { background: rgba(16, 185, 129, 0.2); border-color: var(--success); color: var(--success); }
        .maint-btn.off { background: rgba(239, 68, 68, 0.2); border-color: var(--danger); color: var(--danger); }

        /* MAINTENANCE SCREEN */
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
    <!-- MAINTENANCE SCREEN -->
    <div id="maintenance-screen">
        <img id="maint-img" src="" style="display: none;">
        <h1>🛠 BẢO TRÌ HỆ THỐNG</h1>
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
            <a href="#" class="menu-item active" onclick="navTo('home')"><span class="icon">🏠</span> Trang chủ</a>
            <a href="#" class="menu-item" onclick="navTo('buy')"><span class="icon">🛒</span> Mua Số OTP</a>
            <a href="#" class="menu-item" onclick="navTo('history')"><span class="icon">📜</span> Lịch sử</a>
            <a href="#" class="menu-item" onclick="navTo('wallet')"><span class="icon">💵</span> Ví & Rút Tiền</a>
            <a href="#" class="menu-item" onclick="navTo('stats')"><span class="icon">📊</span> Thống Kê</a>
            <a href="#" class="menu-item" onclick="navTo('leaderboard')"><span class="icon">🏆</span> Bảng Xếp Hạng</a>
            <a href="#" class="menu-item" onclick="window.open('https://t.me/LIVEOTPIVAS', '_blank')"><span class="icon">📢</span> OTP Group</a>
            <a href="#" class="menu-item" onclick="navTo('profile')"><span class="icon">👤</span> Hồ Sơ</a>
            
            <a href="#" class="menu-item menu-admin" id="menu-admin" onclick="navTo('admin')" style="display: none;">
                <span class="icon">🛡</span> ADMIN PANEL
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
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="label">OTP Hôm Nay</div>
                    <div class="value" id="home-today-otps">0</div>
                </div>
                <div class="stat-box">
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
                        <option value="NP">📱 Numbers 2 (NP)</option>
                        <option value="BASHA">🔢 Numbers BS (Basha)</option>
                        <option value="SLVN">🌐 Numbers 4 (SLVN)</option>
                    </select>
                </div>
            </div>
            <div id="buy-list-container" class="list-grid"></div>
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
                <div class="form-group">
                    <input type="text" class="form-control" id="ton-address" placeholder="UQ... hoặc EQ...">
                </div>
                <button class="btn btn-primary" onclick="saveWallet()">Lưu Địa Chỉ</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💰 Rút Tiền</div>
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px;">
                    <button class="btn-small copy" onclick="setWithdrawAmount(1)">$1</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(2)">$2</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(5)">$5</button>
                    <button class="btn-small copy" onclick="setWithdrawAmount(8)">$8</button>
                </div>
                <button class="btn-small copy" style="width: 100%; margin-bottom: 15px; background: rgba(59, 130, 246, 0.15); border-color: rgba(59, 130, 246, 0.4); color: #93c5fd;" onclick="setWithdrawAmount('max')">
                    ⚡ Rút Toàn Bộ (Phí $0.1)
                </button>
                <div class="form-group">
                    <input type="number" class="form-control" id="withdraw-amount" placeholder="Nhập số tiền ($)" step="0.1">
                </div>
                <button class="btn btn-success" onclick="requestWithdraw()">Gửi Yêu Cầu</button>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">💌 Mời Bạn Bè</div>
                <div style="background: rgba(15,23,42,0.6); padding: 12px; border-radius: 8px; word-break: break-all; font-size: 13px; margin-bottom: 10px; border: 1px solid var(--border);" id="ref-link"></div>
                <button class="btn btn-outline" onclick="copyRef()">📋 Sao Chép Link</button>
            </div>
        </div>

        <!-- STATS -->
        <div id="view-stats" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">📊 THỐNG KÊ HÔM NAY <span style="font-size: 12px; color: var(--success);" id="stats-realtime-indicator">● Real-time</span></div>
                <div class="stats-grid">
                    <div class="stat-box">
                        <div class="label">Tổng OTP</div>
                        <div class="value" id="stats-total-otps" style="color: var(--primary);">0</div>
                    </div>
                </div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">🌍 OTP THEO QUỐC GIA</div>
                <div id="stats-countries-list"></div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">📱 OTP THEO NỀN TẢNG</div>
                <div id="stats-platforms-list"></div>
            </div>
        </div>

        <!-- LEADERBOARD -->
        <div id="view-leaderboard" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">🏆 TOP 10 CAO THỦ</div>
                <div id="leaderboard-list">
                    <div class="loading"><div class="spinner"></div>Đang tải...</div>
                </div>
            </div>
        </div>

        <!-- PROFILE -->
        <div id="view-profile" class="view">
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">👤 HỒ SƠ CỦA BẠN</div>
                <div id="profile-info" style="font-size: 15px; line-height: 2;"></div>
            </div>
            <div class="card">
                <div class="form-label" style="font-size: 16px; color: var(--text); margin-bottom: 15px;">🌐 Ngôn Ngữ (Language)</div>
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
            
            <div id="admin-tab-user-detail" class="admin-tab-content" style="display: none;">
                <button class="btn btn-outline" style="margin-bottom:15px;" onclick="switchAdminTab('users')">⬅️ Quay lại danh sách</button>
                <div class="card">
                    <div id="admin-user-detail-info"></div>
                </div>
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
                <div class="card">
                    <div class="form-label">💸 Duyệt Rút Tiền</div>
                    <div id="admin-wd-list"></div>
                </div>
            </div>

            <div id="admin-tab-bs" class="admin-tab-content" style="display: none;">
                <div class="card">
                    <div class="form-label">➕ Thêm Số BS</div>
                    <textarea class="form-control" id="bs-input" rows="4" placeholder="Mỗi dòng 1 số..."></textarea>
                    <button class="btn btn-success" onclick="addBsNumbers()">Thêm Số</button>
                </div>
                <div class="card">
                    <div class="form-label">⚙️ Quản lý số BS</div>
                    <div id="admin-bs-list"></div>
                </div>
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
        <button class="nav-item active" id="nav-home" onclick="navTo('home')"><span class="icon">🏠</span>Trang chủ</button>
        <button class="nav-item" id="nav-buy" onclick="navTo('buy')"><span class="icon">🛒</span>Mua số</button>
        <button class="nav-item" id="nav-history" onclick="navTo('history')"><span class="icon">📜</span>Lịch sử</button>
        <button class="nav-item" id="nav-wallet" onclick="navTo('wallet')"><span class="icon">💵</span>Ví</button>
    </div>

    <script>
        const tg = window.Telegram?.WebApp || {
            initData: "",
            expand: function() {},
            setHeaderColor: function() {},
            setBackgroundColor: function() {},
            ready: function() {},
            showAlert: function(msg) { alert(msg); }
        };

        try {
            if (tg.expand) tg.expand();
            if (tg.setHeaderColor) tg.setHeaderColor('#0B1120');
            if (tg.setBackgroundColor) tg.setBackgroundColor('#0B1120');
            if (tg.ready) tg.ready();
        } catch (e) {
            console.log("WebApp Init Error:", e);
        }

        let userData = null;
        let autoRefreshInterval = null;
        let statsRefreshInterval = null;
        let currentHistoryPage = 1;
        let totalHistoryPages = 1;
        let currentLang = 'vi';
        let currentAdminUid = null;
        let currentUserDetailPage = 1;
        let totalUserDetailPages = 1;
        let isMaintenanceOn = false;

        const translations = {
            vi: { home: "Trang chủ", buy: "Mua Số OTP", history: "Lịch sử", wallet: "Ví & Rút Tiền", leaderboard: "Bảng Xếp Hạng", stats: "Thống Kê", profile: "Hồ Sơ", admin: "ADMIN PANEL", balance: "Số dư khả dụng", today_otp: "OTP Hôm Nay", total_orders: "Tổng Đơn", active_orders: "⏳ Đơn Đang Chờ", select_source: "Chọn Nguồn Số", ton_wallet: "💵 Ví TON", save_address: "Lưu Địa Chỉ", withdraw: "💰 Rút Tiền", withdraw_all: "⚡ Rút Toàn Bộ (Phí $0.1)", send_request: "Gửi Yêu Cầu", invite_friends: "💌 Mời Bạn Bè", copy_link: "📋 Sao Chép Link", top_10: "🏆 TOP 10 CAO THỦ", your_profile: "👤 HỒ SƠ CỦA BẠN", language: "🌐 Ngôn Ngữ (Language)", users: "Người dùng", orders: "Đơn hàng", approve_wd: "💸 Duyệt Rút Tiền", add_bs: "➕ Thêm Số BS", add_number: "Thêm Số", buy_short: "Mua số", wallet_short: "Ví", prev_page: "← Trang trước", next_page: "Trang sau →", total_otp: "Tổng OTP đã nhận", joined: "Ngày tham gia", name: "Tên", balance_label: "Số dư" },
            en: { home: "Home", buy: "Buy OTP Number", history: "History", wallet: "Wallet & Withdraw", leaderboard: "Leaderboard", stats: "Statistics", profile: "Profile", admin: "ADMIN PANEL", balance: "Available Balance", today_otp: "Today's OTP", total_orders: "Total Orders", active_orders: "⏳ Active Orders", select_source: "Select Source", ton_wallet: "💵 TON Wallet", save_address: "Save Address", withdraw: "💰 Withdraw", withdraw_all: "⚡ Withdraw All (Fee $0.1)", send_request: "Send Request", invite_friends: "💌 Invite Friends", copy_link: "📋 Copy Link", top_10: "🏆 TOP 10 PLAYERS", your_profile: "👤 YOUR PROFILE", language: "🌐 Language", users: "Users", orders: "Orders", approve_wd: "💸 Approve Withdrawals", add_bs: "➕ Add BS Numbers", add_number: "Add Number", buy_short: "Buy", wallet_short: "Wallet", prev_page: "← Prev", next_page: "Next →", total_otp: "Total OTPs Received", joined: "Joined", name: "Name", balance_label: "Balance" }
        };

        function applyLanguage(lang) {
            if (!translations[lang]) lang = 'vi';
            currentLang = lang;
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) el.innerText = translations[lang][key];
            });
            document.getElementById('lang-select').value = lang;
            const activeViewId = document.querySelector('.view.active').id.replace('view-', '');
            document.getElementById('top-title').innerText = translations[lang][activeViewId] || activeViewId;
            navTo(activeViewId);
        }

        async function changeLanguage(lang) {
            try {
                if (tg.showLoading) tg.showLoading();
                await api('/api/mini/language', 'POST', { language: lang });
                if (tg.hideLoading) tg.hideLoading();
            } catch(e) {}
            applyLanguage(lang);
            showToast("Language changed!");
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
            setTimeout(() => toast.classList.remove('show'), 2000);
        }

        async function api(path, method = 'GET', body = null) {
            const opts = {
                method,
                headers: { 'X-Telegram-Init-Data': tg.initData || '', 'Content-Type': 'application/json' }
            };
            if (body) opts.body = JSON.stringify(body);
            try {
                const res = await fetch(path, opts);
                const text = await res.text();
                try { return JSON.parse(text); } 
                catch(e) { return { error: 'Lỗi Server: ' + text.substring(0, 50) }; }
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

            document.getElementById('view-' + viewId).classList.add('active');
            const navBtn = document.getElementById('nav-' + viewId);
            if (navBtn) navBtn.classList.add('active');

            const titleKey = { home: 'home', buy: 'buy', history: 'history', wallet: 'wallet', leaderboard: 'leaderboard', stats: 'stats', profile: 'profile', admin: 'admin' }[viewId];
            document.getElementById('top-title').setAttribute('data-i18n', titleKey);
            document.getElementById('top-title').innerText = translations[currentLang][titleKey] || viewId;

            if (document.getElementById('sidebar').classList.contains('open')) toggleSidebar();

            if (viewId === 'home') loadHome();
            if (viewId === 'buy') renderBuyOptions();
            if (viewId === 'history') loadHistory(1);
            if (viewId === 'wallet') loadWallet();
            if (viewId === 'stats') { loadStats(); startStatsRefresh(); } else { stopStatsRefresh(); }
            if (viewId === 'leaderboard') loadLeaderboard();
            if (viewId === 'profile') loadProfile();
            if (viewId === 'admin') loadAdmin();
        }

        async function loadUserData() {
            const data = await api('/api/mini/me');
            if (data.error) return showToast(data.error);
            
            userData = data;
            if (data.user.language && data.user.language !== currentLang) applyLanguage(data.user.language);

            isMaintenanceOn = (data.maintenance === 'on');
            if (isMaintenanceOn && !data.is_admin) {
                document.getElementById('maintenance-screen').style.display = 'flex';
                document.getElementById('maint-text').innerText = data.maint_message || "Hệ thống đang bảo trì. Vui lòng quay lại sau!";
                const img = document.getElementById('maint-img');
                if (data.maint_image) {
                    img.src = data.maint_image;
                    img.style.display = 'block';
                } else {
                    img.style.display = 'none';
                }
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
            document.getElementById('side-user-info').innerText = 'ID: ' + data.user.id + ' | ' + data.user.first_name;
            document.getElementById('ton-address').value = data.user.wallet_ton || '';
            document.getElementById('ref-link').innerText = data.referral_link;
            
            if (data.is_admin) document.getElementById('menu-admin').style.display = 'flex';
            else document.getElementById('menu-admin').style.display = 'none';
        }

        async function loadHome() {
            loadUserData();
            const listDiv = document.getElementById('active-orders-list');
            const data = await api('/api/mini/orders/active');
            if (!data.orders) return;
            
            if (data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading" style="background: var(--surface); border-radius: 16px; border: 1px dashed var(--border);">Không có đơn nào đang chờ.</div>';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, false)).join('');
        }

        async function loadStats() {
            const listC = document.getElementById('stats-countries-list');
            const listP = document.getElementById('stats-platforms-list');
            
            const data = await api('/api/mini/stats');
            if(data.error) {
                listC.innerHTML = `<div style="color:var(--danger)">${data.error}</div>`;
                listP.innerHTML = `<div style="color:var(--danger)">${data.error}</div>`;
                return;
            }

            document.getElementById('stats-total-otps').innerText = data.total_otps;

            if(data.countries.length === 0) listC.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">Chưa có dữ liệu hôm nay.</div>';
            else listC.innerHTML = data.countries.map(c => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                    <span>${c.flag} ${c.country}</span>
                    <b style="color:var(--primary);">${c.count}</b>
                </div>
            `).join('');

            if(data.platforms.length === 0) listP.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">Chưa có dữ liệu hôm nay.</div>';
            else listP.innerHTML = data.platforms.map(p => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);">
                    <span>${p.icon} ${p.platform}</span>
                    <b style="color:var(--success);">${p.count}</b>
                </div>
            `).join('');
        }

        function startStatsRefresh() {
            stopStatsRefresh();
            statsRefreshInterval = setInterval(loadStats, 5000);
        }
        function stopStatsRefresh() {
            if (statsRefreshInterval) clearInterval(statsRefreshInterval);
        }

        async function loadLeaderboard() {
            const listDiv = document.getElementById('leaderboard-list');
            const data = await api('/api/mini/leaderboard');
            if (!data.leaderboard || data.leaderboard.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có dữ liệu.</div>';
                return;
            }
            listDiv.innerHTML = data.leaderboard.map((u, i) => {
                let medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : '🔹';
                return `
                    <div style="display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid var(--border); cursor: pointer;" onclick="showUserDetails('${u.name}', ${u.total_otps}, ${u.balance})">
                        <div>
                            <div>${medal} ${u.name}</div>
                            <div style="font-size: 12px; color: var(--text-muted);">OTPs: ${u.total_otps}</div>
                        </div>
                        <strong style="color: var(--success); align-self:center;">$${(u.balance/1000).toFixed(3)}</strong>
                    </div>
                `;
            }).join('');
        }

        async function showUserDetails(name, otps, balance) {
            await showCustomModal(name, `Tổng OTP đã nhận: ${otps}\nSố dư: $${(balance/1000).toFixed(3)}`);
        }

        async function loadHistory(page = 1) {
            currentHistoryPage = page;
            const listDiv = document.getElementById('history-list');
            const pagDiv = document.getElementById('history-pagination');
            listDiv.innerHTML = '<div class="loading"><div class="spinner"></div>Đang tải...</div>';
            
            const data = await api('/api/mini/orders?page=' + page);
            if (!data.orders || data.orders.length === 0) {
                listDiv.innerHTML = '<div class="loading">Chưa có lịch sử giao dịch.</div>';
                pagDiv.style.display = 'none';
                return;
            }
            listDiv.innerHTML = data.orders.map(o => renderOrderCard(o, true)).join('');
            totalHistoryPages = data.total_pages || 1;
            currentHistoryPage = data.current_page || 1;
            
            if (totalHistoryPages > 1) {
                pagDiv.style.display = 'flex';
                document.getElementById('page-info').innerText = `Trang ${currentHistoryPage} / ${totalHistoryPages}`;
                document.getElementById('btn-prev').disabled = currentHistoryPage <= 1;
                document.getElementById('btn-next').disabled = currentHistoryPage >= totalHistoryPages;
            } else {
                pagDiv.style.display = 'none';
            }
        }

        function changeHistoryPage(delta) {
            const newPage = currentHistoryPage + delta;
            if (newPage >= 1 && newPage <= totalHistoryPages) loadHistory(newPage);
        }

        function renderOrderCard(o, isHistory) {
            const statusColors = { 'PENDING': 'var(--warning)', 'COMPLETED': 'var(--success)', 'EXPIRED': 'var(--danger)', 'CANCELLED': 'var(--danger)' };
            const statusTexts = { 'PENDING': '⏳ Chờ OTP', 'COMPLETED': '✅ Đã nhận', 'EXPIRED': '⌛ Hết hạn', 'CANCELLED': '🚫 Đã hủy' };
            const color = statusColors[o.status] || 'var(--text-muted)';
            const text = statusTexts[o.status] || o.status;
            let dateStr = o.created_at ? new Date(o.created_at).toLocaleString('vi-VN') : '';
            
            let otpHtml = '';
            if (o.status === 'COMPLETED' && o.otp) {
                otpHtml = `
                    <div class="otp-box">
                        <div>
                            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 4px;">Mã OTP:</div>
                            <div class="otp-code">${o.otp}</div>
                        </div>
                        <button class="btn-small copy" style="background: var(--success); width: 80px;" onclick="copyText('${o.otp}')">📋 Copy</button>
                    </div>
                `;
            }
            return `
                <div class="order-card ${o.status.toLowerCase()}">
                    <div class="order-header">
                        <div class="order-phone">${o.phone}</div>
                        <div class="order-badge" style="color: ${color};">${text}</div>
                    </div>
                    <div class="order-info">
                        <span>${o.flag} ${o.country}</span>
                        <span>🔧 ${o.provider}</span>
                        ${o.platform ? `<span>🌐 ${o.platform}</span>` : ''}
                        <span>🕒 ${dateStr}</span>
                    </div>
                    ${otpHtml}
                    <div class="action-row">
                        <button class="btn-small copy" onclick="copyText('${o.phone}')">📋 Copy Số</button>
                        ${o.status === 'PENDING' && !isHistory ? `<button class="btn-small cancel" onclick="cancelOrder(${o.id})">❌ Hủy</button>` : ''}
                    </div>
                </div>
            `;
        }

        function copyText(text) {
            navigator.clipboard.writeText(text).then(() => showToast('Đã sao chép: ' + text));
        }

        async function cancelOrder(oid) {
            const confirmed = await showCustomModal('Hủy Đơn', 'Bạn chắc chắn muốn hủy đơn này?');
            if (!confirmed) return;
            const res = await api('/api/mini/orders/' + oid + '/cancel', 'POST');
            if (res.ok) { loadHome(); showToast('Đã hủy đơn'); }
            else { if (tg.showAlert) tg.showAlert('Lỗi: ' + res.error); else alert('Lỗi: ' + res.error); }
        }

        async function renderBuyOptions() {
            const provider = document.getElementById('provider-select').value;
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';

            if (provider === 'MK') {
                const data = await api('/api/mini/mk/ranges');
                container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('MK', '${c.range}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                    </button>
                `).join('');
            } 
            else if (provider === 'NP') {
                const data = await api('/api/mini/np/services');
                container.innerHTML = data.services.map(s => `
                    <button class="list-btn" onclick="loadNpCountries('${s.key}')">
                        <div class="name">🔧 ${s.name}</div>
                        <div class="count">Còn ${s.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'BASHA') {
                const data = await api('/api/mini/bs/countries');
                if (data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số BS.</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('BASHA', '${c.name}', '${c.name}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Còn ${c.count} số</div>
                    </button>
                `).join('');
            }
            else if (provider === 'SLVN') {
                const data = await api('/api/mini/slvn/countries');
                if (!data.countries || data.countries.length === 0) container.innerHTML = '<div class="loading" style="grid-column: 1/-1;">Chưa có số (Hoặc lỗi API Key).</div>';
                else container.innerHTML = data.countries.map(c => `
                    <button class="list-btn" onclick="buyNumber('SLVN', '${c.code}', '${c.name}', '${c.tag}')">
                        <div class="name">${c.flag} ${c.name}</div>
                        <div class="count">Rate: $${c.rate}</div>
                    </button>
                `).join('');
            }
        }

        async function loadNpCountries(service) {
            const container = document.getElementById('buy-list-container');
            container.innerHTML = '<div class="loading" style="grid-column: 1/-1;"><div class="spinner"></div>Đang tải...</div>';
            const data = await api('/api/mini/np/countries/' + service);
            container.innerHTML = data.countries.map(c => `
                <button class="list-btn" onclick="buyNumber('NP', '${c.code}', '${c.name}', '${service}')">
                    <div class="name">🌍 ${c.name}</div>
                    <div class="count">Còn ${c.count} số</div>
                </button>
            `).join('');
        }

        async function buyNumber(provider, code, name, param3 = null) {
            const confirmed = await showCustomModal('Xác Nhận', `Bạn có chắc muốn lấy số ${name} không?`);
            if (!confirmed) return;

            try { if (tg.showLoading) tg.showLoading(); } catch(e) {}
            let body = { provider };
            if (provider === 'MK') { body.range = code; body.country_name = name; }
            if (provider === 'NP') { body.country = code; body.service = param3; }
            if (provider === 'BASHA') { body.country = code; }
            if (provider === 'SLVN') { body.country_code = code; body.tag = param3; }

            try {
                const res = await api('/api/mini/orders', 'POST', body);
                try { if (tg.hideLoading) tg.hideLoading(); } catch(e) {}
                if (res.ok) { showToast('✅ Đã lấy số thành công!'); navTo('home'); }
                else { if (tg.showAlert) tg.showAlert('❌ Lỗi: ' + (res.error || 'Không thể lấy số')); else alert('❌ Lỗi: ' + (res.error || 'Không thể lấy số')); }
            } catch (err) {
                try { if (tg.hideLoading) tg.hideLoading(); } catch(e) {}
                alert('❌ Lỗi kết nối máy chủ!');
            }
        }

        function loadWallet() { loadUserData(); }

        function loadProfile() {
            if (!userData || !userData.user) return;
            const u = userData.user;
            const t = translations[currentLang];
            document.getElementById('profile-info').innerHTML = `
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">🆔 Telegram ID: <b>${u.id}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">👤 ${t.name}: <b>${u.first_name}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">💰 ${t.balance_label}: <b style="color: var(--success);">$${(u.usd_milli/1000).toFixed(3)}</b></div>
                <div style="padding: 10px 0; border-bottom: 1px solid var(--border);">📩 ${t.total_otp}: <b style="color: var(--primary);">${userData.total_otps}</b></div>
                <div style="padding: 10px 0;">📅 ${t.joined}: <b>${new Date(u.joined_at).toLocaleDateString()}</b></div>
            `;
        }

        function setWithdrawAmount(type) {
            const input = document.getElementById('withdraw-amount');
            if (type === 'max') {
                if (!userData || !userData.user) return;
                const maxAmount = (userData.user.usd_milli / 1000).toFixed(3);
                let finalAmt = parseFloat(maxAmount) - 0.1;
                if (finalAmt < 0) finalAmt = 0;
                input.value = finalAmt.toFixed(3);
                showToast('Đã trừ phí rút toàn bộ $0.1');
            } else { input.value = type; }
        }

        async function saveWallet() {
            const address = document.getElementById('ton-address').value;
            const res = await api('/api/mini/wallet/address', 'POST', { address });
            if (res.ok) showToast('Đã lưu địa chỉ ví!');
            else { if (tg.showAlert) tg.showAlert('Lỗi: ' + res.error); else alert('Lỗi: ' + res.error); }
        }

        async function requestWithdraw() {
            const amount = document.getElementById('withdraw-amount').value;
            if (!amount || amount < 1) {
                if (tg.showAlert) tg.showAlert('Số tiền tối thiểu là $1.00'); else alert('Số tiền tối thiểu là $1.00');
                return;
            }
            const res = await api('/api/mini/wallet/withdraw', 'POST', { amount });
            if (res.ok) { 
                if (tg.showAlert) tg.showAlert('Đã gửi yêu cầu rút tiền. Vui lòng chờ Admin duyệt.'); 
                else alert('Đã gửi yêu cầu rút tiền. Vui lòng chờ Admin duyệt.'); 
                loadUserData(); 
            } else { 
                if (tg.showAlert) tg.showAlert('Lỗi: ' + res.error); else alert('Lỗi: ' + res.error); 
            }
        }

        function copyRef() {
            const text = document.getElementById('ref-link').innerText;
            navigator.clipboard.writeText(text).then(() => showToast('Đã sao chép link!'));
        }

        // ADMIN
        async function loadAdmin() {
            const data = await api('/api/mini/admin/data');
            if (data.error) {
                if (tg.showAlert) tg.showAlert(data.error); else alert(data.error);
                return;
            }
            
            document.getElementById('admin-total-users').innerText = data.stats.users;
            document.getElementById('admin-total-orders').innerText = data.stats.orders;
            
            const statusEl = document.getElementById('admin-bot-status');
            if (data.maintenance === 'on') {
                statusEl.innerText = '🔴 Đang bảo trì';
                statusEl.style.color = 'var(--danger)';
                isMaintenanceOn = true;
            } else {
                statusEl.innerText = '🟢 Đang hoạt động';
                statusEl.style.color = 'var(--success)';
                isMaintenanceOn = false;
            }

            document.getElementById('admin-stock-info').innerHTML = `
                <div class="row"><span>Pending Withdrawals:</span> <b>${data.stats.pending_wd}</b></div>
                <div class="row"><span>BS Stock:</span> <b>${data.stats.bs_count}</b></div>
            `;

            const wdDiv = document.getElementById('admin-wd-list');
            if (!data.withdrawals || data.withdrawals.length === 0) wdDiv.innerHTML = '<div style="color: var(--text-muted); font-size: 14px;">Không có yêu cầu rút tiền.</div>';
            else {
                wdDiv.innerHTML = data.withdrawals.map(w => `
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
            event.target.classList.add('active');
            document.getElementById('admin-tab-' + tab).style.display = 'block';

            if (tab === 'users') loadAdminUsers();
            if (tab === 'bs') loadAdminBs();
            if (tab === 'maint') updateMaintUI();
        }

        function updateMaintUI() {
            const btnOn = document.getElementById('btn-maint-on');
            const btnOff = document.getElementById('btn-maint-off');
            const form = document.getElementById('maint-form-container');
            
            if (isMaintenanceOn) {
                btnOn.classList.remove('on');
                btnOff.classList.add('off');
                form.style.display = 'block';
            } else {
                btnOn.classList.add('on');
                btnOff.classList.remove('off');
                form.style.display = 'none';
            }
        }

        async function toggleMaintenance(enable) {
            if (enable) {
                try { if (tg.showLoading) tg.showLoading(); } catch(e) {}
                const res = await api('/api/mini/admin/maintenance', 'POST', { action: 'enable' });
                try { if (tg.hideLoading) tg.hideLoading(); } catch(e) {}
                if (res.ok) {
                    showToast(res.msg);
                    isMaintenanceOn = false;
                    updateMaintUI();
                    loadAdmin();
                } else {
                    if (tg.showAlert) tg.showAlert(res.error); else alert(res.error);
                }
            } else {
                isMaintenanceOn = true;
                updateMaintUI();
            }
        }

        function setMaintTemplate(id) {
            const ta = document.getElementById('maint-msg');
            if (id === 1) ta.value = "Hệ thống đang được bảo trì để nâng cấp. Vui lòng quay lại sau ít phút. Xin lỗi vì sự bất tiện này!";
            if (id === 2) ta.value = "Server đang gặp sự cố kỹ thuật. Admin đang khắc phục. Vui lòng quay lại sau!";
        }

        async function submitMaintenance() {
            const msg = document.getElementById('maint-msg').value;
            if(!msg) {
                if (tg.showAlert) tg.showAlert("Vui lòng nhập thông báo!"); else alert("Vui lòng nhập thông báo!");
                return;
            }
            
            const fileInput = document.getElementById('maint-image');
            let b64 = "";
            if(fileInput.files.length > 0) {
                b64 = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = (e) => resolve(e.target.result);
                    reader.readAsDataURL(fileInput.files[0]);
                });
            }
            
            const confirmed = await showCustomModal('Xác Nhận Bảo Trì', 'Hệ thống sẽ BẬT chế độ bảo trì và gửi thông báo đến toàn bộ user. Tiếp tục?');
            if(!confirmed) return;

            try { if (tg.showLoading) tg.showLoading(); } catch(e) {}
            const res = await api('/api/mini/admin/maintenance', 'POST', { action: 'disable', message: msg, image_b64: b64 });
            try { if (tg.hideLoading) tg.hideLoading(); } catch(e) {}
            
            if(res.ok) {
                if (tg.showAlert) tg.showAlert(res.msg); else alert(res.msg);
                document.getElementById('maint-msg').value = '';
                document.getElementById('maint-image').value = '';
                isMaintenanceOn = true;
                updateMaintUI();
                loadAdmin();
            } else {
                if (tg.showAlert) tg.showAlert("Lỗi: " + res.error); else alert("Lỗi: " + res.error);
            }
        }

        async function loadAdminUsers() {
            const div = document.getElementById('admin-user-list');
            div.innerHTML = '<div class="spinner"></div>';
            const data = await api('/api/mini/admin/users');
            if(data.error) return div.innerText = data.error;
            div.innerHTML = data.users.map(u => `
                <div style="padding:10px 0;border-bottom:1px solid var(--border);cursor:pointer;" onclick="loadAdminUserDetail(${u.id})">
                    <b>${u.name}</b> (@${u.username || '—'}) - ID: ${u.id}<br>
                    <span style="color:var(--success);">$${(u.balance/1000).toFixed(3)}</span> | Joined: ${new Date(u.joined).toLocaleDateString()}
                </div>
            `).join('');
        }

        async function loadAdminUserDetail(uid) {
            currentAdminUid = uid;
            currentUserDetailPage = 1;
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.admin-tab-content').forEach(c => c.style.display = 'none');
            document.getElementById('admin-tab-user-detail').style.display = 'block';
            document.getElementById('admin-user-detail-info').innerHTML = '<div class="spinner"></div>';
            document.getElementById('admin-user-detail-orders').innerHTML = '<div class="spinner"></div>';
            
            const data = await api('/api/mini/admin/users/' + uid + '?page=1');
            if(data.error) return document.getElementById('admin-user-detail-info').innerText = data.error;

            const u = data.user;
            document.getElementById('admin-user-detail-info').innerHTML = `
                <div><b>Tên:</b> ${u.name}</div>
                <div><b>Username:</b> @${u.username || '—'}</div>
                <div><b>Telegram ID:</b> ${u.id}</div>
                <div><b>Số dư:</b> <span style="color:var(--success);">$${(u.balance/1000).toFixed(3)}</span></div>
                <div><b>Ngày tham gia:</b> ${new Date(u.joined).toLocaleDateString()}</div>
            `;

            const s = data.stats;
            document.getElementById('admin-user-detail-stats').innerHTML = `
                <div><div style="font-size:20px;color:var(--primary);font-weight:bold;">${s.MK || 0}</div>MK</div>
                <div><div style="font-size:20px;color:var(--warning);font-weight:bold;">${s.NP || 0}</div>NP</div>
                <div><div style="font-size:20px;color:var(--success);font-weight:bold;">${s.BASHA || 0}</div>BS</div>
                <div><div style="font-size:20px;color:var(--danger);font-weight:bold;">${s.SLVN || 0}</div>SLVN</div>
            `;
            renderAdminUserOrders(data);
        }

        function renderAdminUserOrders(data) {
            const div = document.getElementById('admin-user-detail-orders');
            const pag = document.getElementById('user-detail-pagination');
            
            if(!data.orders || data.orders.length === 0) {
                div.innerHTML = '<div style="color:var(--text-muted);font-size:14px;">Chưa có số nào.</div>';
                pag.style.display = 'none';
                return;
            }
            
            div.innerHTML = data.orders.map(o => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);font-size:14px;">
                    <div>
                        <b>${o.phone}</b><br>
                        <span style="font-size:12px;color:var(--text-muted);">${o.provider} | ${new Date(o.date).toLocaleString('vi-VN')}</span>
                    </div>
                    <div style="align-self:center;color:${o.status==='COMPLETED'?'var(--success)':'var(--text-muted)'};">
                        ${o.status}
                    </div>
                </div>
            `).join('');

            totalUserDetailPages = data.total_pages || 1;
            if (totalUserDetailPages > 1) {
                pag.style.display = 'flex';
                document.getElementById('user-page-info').innerText = `Trang ${data.current_page} / ${totalUserDetailPages}`;
                document.getElementById('btn-user-prev').disabled = data.current_page <= 1;
                document.getElementById('btn-user-next').disabled = data.current_page >= totalUserDetailPages;
            } else {
                pag.style.display = 'none';
            }
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
            div.innerHTML = '<div class="spinner"></div>';
            const data = await api('/api/mini/bs/countries');
            if(!data.countries || data.countries.length === 0) return div.innerHTML = 'Chưa có số BS.';
            
            div.innerHTML = data.countries.map(c => `
                <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid var(--border);align-items:center;">
                    <span>${c.flag} ${c.name} (${c.count})</span>
                    <button class="btn-small cancel" style="width:auto;padding:6px 12px;" onclick="deleteBs('${c.name}')">Xóa</button>
                </div>
            `).join('') + `
                <button class="btn btn-danger" style="margin-top:15px;" onclick="deleteBs('ALL')">XÓA TOÀN BỘ SỐ BS</button>
            `;
        }

        async function deleteBs(country) {
            const confirmed = await showCustomModal('Xóa Số BS', `Bạn chắc chắn muốn xóa toàn bộ số của ${country}?`);
            if(!confirmed) return;
            const res = await api('/api/mini/admin/bs/delete', 'POST', { country });
            if(res.ok) { showToast('Đã xóa!'); loadAdminBs(); loadAdmin(); }
            else { if (tg.showAlert) tg.showAlert(res.error); else alert(res.error); }
        }

        async function runAdminCmd(cmd) {
            const out = document.getElementById('cmd-output');
            out.innerText = 'Đang chạy...';
            const res = await api('/api/mini/admin/cmd', 'POST', { cmd });
            if(res.ok) out.innerText = res.msg;
            else out.innerText = 'Lỗi: ' + res.error;
        }

        async function adminWdAction(wid, action) {
            const confirmed = await showCustomModal('Xác Nhận', `Bạn chắc chắn muốn ${action === 'approve' ? 'DUYỆT' : 'TỪ CHỐI'} yêu cầu này?`);
            if (!confirmed) return;
            const res = await api('/api/mini/admin/withdraw/action', 'POST', { wid, action });
            if (res.ok) { loadAdmin(); showToast('Thành công!'); }
            else { if (tg.showAlert) tg.showAlert(res.error); else alert(res.error); }
        }

        async function addBsNumbers() {
            const numbers = document.getElementById('bs-input').value;
            if (!numbers) {
                if (tg.showAlert) tg.showAlert('Vui lòng nhập số!'); else alert('Vui lòng nhập số!');
                return;
            }
            const res = await api('/api/mini/admin/bs/add', 'POST', { numbers });
            if (res.ok) { 
                if (tg.showAlert) tg.showAlert(`Đã thêm ${res.added} số`); else alert(`Đã thêm ${res.added} số`); 
                document.getElementById('bs-input').value = ''; 
                loadAdminBs(); 
            } else { 
                if (tg.showAlert) tg.showAlert(res.error); else alert(res.error); 
            }
        }

        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(() => {
                const activeView = document.querySelector('.view.active')?.id;
                if (activeView === 'view-home') loadHome();
            }, 5000); 
        }

        try {
            if (tg.ready) tg.ready();
            if (tg.expand) tg.expand();
        } catch(e) {}

        loadUserData();
        loadHome();
        startAutoRefresh();
    </script>
</body>
</html>
"""
