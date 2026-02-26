import flet as ft
import asyncio
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession 
import datetime
import random
import math
import os

# --- CẤU HÌNH (HARDCODE) ---
API_ID = 31790219  
API_HASH = 'd508336ebaab56d17ffb3fe22a703595'

# --- HỆ THỐNG MÀU SẮC SAAS CAO CẤP (LAYERED DARK) ---
BG_BASE = "#030712"        # Nền trang web: Đen không gian sâu
BG_CARD = "#0B0F19"        # Nền thẻ kính: Xanh đen tối (Tạo chiều sâu)
BG_INPUT = "#111827"       # Nền input/button phụ: Xám chì
BORDER_COLOR = "#1F2937"   # Viền vi mô
BORDER_LIGHT = "#2A313C"   # Viền nổi khối (Subtle highlight)
TEXT_PRIMARY = "#F9FAFB"   # Trắng chính
TEXT_MUTED = "#9CA3AF"     # Xám nhạt mờ
ACCENT_CYAN = "#06B6D4"    # Cyan chủ đạo
ACCENT_CYAN_GLOW = "#4006B6D4" # Cyan Shadow (25% Opacity)
ACCENT_ORANGE = "#F59E0B"
ACCENT_ORANGE_GLOW = "#40F59E0B"

class CyberPulseApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.client = None
        self.phone = ""
        self.phone_code_hash = ""
        self.chart_points = 65 
        self.pulse_data = [15] * self.chart_points 
        self.tick = 0 
        self.running = False
        
        self.page.on_disconnect = self.handle_disconnect

        # ==========================================
        # CONTAINER CHÍNH: GLASSMORPHISM CARD CAO CẤP
        # Dùng ft.Alignment(0, 0) thay cho center
        # ==========================================
        self.main_wrapper = ft.Container(
            width=432, # Lưới 8pt (432 chia hết cho 8)
            height=720, # Chiều cao cố định
            bgcolor=BG_CARD,
            border_radius=ft.border_radius.all(24), 
            border=ft.border.all(1, BORDER_LIGHT),
            shadow=[
                ft.BoxShadow(blur_radius=64, color="#80000000", offset=ft.Offset(0, 24)),
                ft.BoxShadow(blur_radius=120, spread_radius=-24, color="#1A06B6D4", offset=ft.Offset(0, 0))
            ],
            padding=ft.padding.all(40),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            # CHỐNG CRASH: Khai báo tọa độ trực tiếp
            alignment=ft.Alignment(0.0, 0.0) 
        )
        
        # CHỐNG LỆCH: Căn giữa tuyệt đối trên trình duyệt
        self.page.add(
            ft.Container(
                content=self.main_wrapper,
                expand=True,
                alignment=ft.Alignment(0.0, 0.0)
            )
        )
        asyncio.create_task(self.startup_routine())

    def handle_disconnect(self, e):
        self.running = False
        if self.client: asyncio.create_task(self.client.disconnect())

    def switch_view(self, new_content):
        self.main_wrapper.content = new_content
        self.page.update()

    # --- HÀM TẠO COMPONENT (CHUẨN DESIGN SYSTEM 8PT GRID) ---
    def build_input(self, label_text, icon_data, is_pwd=False, accent=ACCENT_CYAN):
        return ft.TextField(
            label=label_text,
            prefix_icon=icon_data,
            password=is_pwd,
            can_reveal_password=is_pwd,
            bgcolor=BG_INPUT,
            border_color=BORDER_COLOR,
            focused_border_color=accent,
            color=TEXT_PRIMARY,
            border_radius=ft.border_radius.all(12),
            text_size=14,
            height=48, # Chuẩn lưới 8pt
            content_padding=ft.padding.symmetric(vertical=0, horizontal=16),
            label_style=ft.TextStyle(color=TEXT_MUTED, size=13, weight=ft.FontWeight.W_500),
            cursor_color=accent,
            selection_color=accent + "40"
        )

    def build_primary_btn(self, text, gradient_colors, glow_color, icon_data, on_click_handler):
        btn_text = ft.Text(text, size=14, weight=ft.FontWeight.W_700, color="#ffffff")
        btn_icon = ft.Icon(icon=icon_data, color="#ffffff", size=18)
        content_row = ft.Row(
            [btn_text, btn_icon], 
            alignment=ft.MainAxisAlignment.CENTER, 
            vertical_alignment=ft.CrossAxisAlignment.CENTER, 
            spacing=8
        )
        
        btn = ft.Container(
            content=content_row,
            height=48,
            border_radius=ft.border_radius.all(12),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1.0, 0.0), # Từ trái sang
                end=ft.Alignment(1.0, 0.0),    # Sang phải
                colors=gradient_colors
            ),
            shadow=ft.BoxShadow(blur_radius=16, color=glow_color, offset=ft.Offset(0, 4)),
            alignment=ft.Alignment(0.0, 0.0), # Căn giữa
            on_click=on_click_handler,
            animate_scale=250, 
            scale=1.0
        )
        
        def on_hover(e):
            btn.scale = 0.98 if e.data == "true" else 1.0
            btn.update()
            
        btn.on_hover = on_hover
        return btn, content_row

    async def startup_routine(self):
        loading_view = ft.Container(
            content=ft.Column([
                ft.Icon(icon=ft.Icons.FINGERPRINT, size=56, color=ACCENT_CYAN),
                ft.Container(height=24),
                ft.Text("ĐANG BẢO MẬT KẾT NỐI...", size=13, weight=ft.FontWeight.W_700, color=ACCENT_CYAN),
                ft.Container(height=16),
                ft.ProgressBar(width=180, color=ACCENT_CYAN, bgcolor=BG_INPUT)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0),
            alignment=ft.Alignment(0.0, 0.0),
            expand=True
        )
        self.switch_view(loading_view)

        try:
            await asyncio.sleep(1.2) 
            saved_session = None
            if hasattr(self.page, "client_storage"):
                saved_session = await self.page.client_storage.get_async("kealix_cloud_session")
            
            if saved_session: await self.check_existing_session(saved_session)
            else: self.show_login_ui()
        except Exception:
            self.show_login_ui()

    # ==========================================
    # GIAO DIỆN ĐĂNG NHẬP SAAS TIẾNG VIỆT
    # ==========================================
    def show_login_ui(self):
        logo_ph = ft.Container(
            content=ft.Icon(icon=ft.Icons.SATELLITE_ALT, size=32, color=ACCENT_CYAN),
            width=72, height=72, border_radius=ft.border_radius.all(36), bgcolor=BG_INPUT,
            border=ft.border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 0.0),
            shadow=ft.BoxShadow(blur_radius=24, color=ACCENT_CYAN_GLOW)
        )
        
        self.phone_input = self.build_input("Số điện thoại Telegram", ft.Icons.PHONE, accent=ACCENT_CYAN)
        self.phone_btn, self.phone_btn_content = self.build_primary_btn(
            "KHỞI ĐỘNG LÕI", ["#06B6D4", "#3B82F6"], ACCENT_CYAN_GLOW, ft.Icons.BOLT, self.handle_phone_submit
        )
        self.auth_error = ft.Text("", color="#EF4444", size=13, weight=ft.FontWeight.W_500)

        self.phone_view = ft.Column([
            logo_ph,
            ft.Container(height=24),
            ft.Text("LIÊN KẾT HỆ THỐNG", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
            ft.Container(height=4),
            ft.Text("Nhập thông tin xác thực để tiếp tục.", size=14, weight=ft.FontWeight.W_400, color=TEXT_MUTED),
            ft.Container(height=32),
            self.phone_input,
            ft.Container(height=16),
            self.phone_btn,
            ft.Container(height=8),
            self.auth_error 
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0)

        logo_otp = ft.Container(
            content=ft.Icon(icon=ft.Icons.SECURITY, size=32, color=ACCENT_ORANGE),
            width=72, height=72, border_radius=ft.border_radius.all(36), bgcolor=BG_INPUT,
            border=ft.border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 0.0),
            shadow=ft.BoxShadow(blur_radius=24, color=ACCENT_ORANGE_GLOW)
        )
        
        self.otp_input = self.build_input("Mã xác thực (OTP)", ft.Icons.VPN_KEY, accent=ACCENT_ORANGE)
        self.password_input = self.build_input("Mật khẩu 2FA (Nếu có)", ft.Icons.LOCK, is_pwd=True, accent=ACCENT_ORANGE)
        
        self.otp_btn, self.otp_btn_content = self.build_primary_btn(
            "XÁC MINH DANH TÍNH", ["#F59E0B", "#EA580C"], ACCENT_ORANGE_GLOW, ft.Icons.CHECK_CIRCLE, self.handle_otp_submit
        )
        self.otp_error = ft.Text("", color="#EF4444", size=13, weight=ft.FontWeight.W_500)

        self.otp_view = ft.Column([
            logo_otp,
            ft.Container(height=24),
            ft.Text("KIỂM TRA BẢO MẬT", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
            ft.Container(height=4),
            ft.Text("Kiểm tra Telegram để lấy mã 5 chữ số.", size=14, weight=ft.FontWeight.W_400, color=TEXT_MUTED),
            ft.Container(height=32),
            self.otp_input,
            ft.Container(height=16),
            self.password_input,
            ft.Container(height=16),
            self.otp_btn,
            ft.Container(height=8),
            self.otp_error 
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0, visible=False)

        self.switch_view(ft.Column([self.phone_view, self.otp_view], alignment=ft.MainAxisAlignment.CENTER, spacing=0))

    async def connect_client(self, session_str=""):
        if not self.client:
            self.client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        if not self.client.is_connected():
            await self.client.connect()

    async def check_existing_session(self, saved_session):
        try:
            await self.connect_client(saved_session)
            if await self.client.is_user_authorized(): self.show_dashboard_ui() 
            else:
                if hasattr(self.page, "client_storage"): await self.page.client_storage.remove_async("kealix_cloud_session")
                self.show_login_ui()
        except:
            if hasattr(self.page, "client_storage"): await self.page.client_storage.remove_async("kealix_cloud_session")
            self.show_login_ui()

    def handle_phone_submit(self, e):
        self.phone = self.phone_input.value.strip()
        if not self.phone:
            self.auth_error.value = "Vui lòng nhập số điện thoại"
            self.page.update()
            return
            
        self.phone_btn.disabled = True
        self.phone_btn_content.controls = [
            ft.ProgressRing(width=16, height=16, color="#ffffff", stroke_width=2),
            ft.Text("ĐANG TRUYỀN TẢI...", size=14, weight=ft.FontWeight.W_700, color="#ffffff")
        ]
        self.page.update()
        asyncio.create_task(self.request_otp())

    async def request_otp(self):
        try:
            await self.connect_client("") 
            sent_code = await self.client.send_code_request(self.phone)
            self.phone_code_hash = sent_code.phone_code_hash
            self.phone_view.visible = False
            self.otp_view.visible = True
        except Exception as ex:
            self.auth_error.value = str(ex)
            self.phone_btn.disabled = False
            self.phone_btn_content.controls = [
                ft.Text("KHỞI ĐỘNG LÕI", size=14, weight=ft.FontWeight.W_700, color="#ffffff"),
                ft.Icon(icon=ft.Icons.BOLT, color="#ffffff", size=18)
            ]
        self.page.update()

    def handle_otp_submit(self, e):
        otp = self.otp_input.value.strip()
        pwd = self.password_input.value.strip()
        if not otp:
            self.otp_error.value = "Vui lòng nhập mã xác thực"
            self.page.update()
            return
            
        self.otp_btn.disabled = True
        self.otp_btn_content.controls = [
            ft.ProgressRing(width=16, height=16, color="#ffffff", stroke_width=2),
            ft.Text("ĐANG XÁC MINH...", size=14, weight=ft.FontWeight.W_700, color="#ffffff")
        ]
        self.page.update()
        asyncio.create_task(self.verify_login(otp, pwd))

    async def verify_login(self, otp, pwd):
        try:
            await self.client.sign_in(phone=self.phone, code=otp, phone_code_hash=self.phone_code_hash)
            if hasattr(self.page, "client_storage"): await self.page.client_storage.set_async("kealix_cloud_session", self.client.session.save())
            self.show_dashboard_ui()
        except errors.SessionPasswordNeededError:
            if not pwd:
                self.otp_error.value = "Vui lòng nhập mật khẩu 2FA"
                self.reset_otp_btn()
            else:
                try:
                    await self.client.sign_in(password=pwd)
                    if hasattr(self.page, "client_storage"): await self.page.client_storage.set_async("kealix_cloud_session", self.client.session.save())
                    self.show_dashboard_ui()
                except Exception:
                    self.otp_error.value = "Mật khẩu 2FA không hợp lệ"
                    self.reset_otp_btn()
        except Exception:
            self.otp_error.value = "Mã xác thực không hợp lệ"
            self.reset_otp_btn()
        self.page.update()

    def reset_otp_btn(self):
        self.otp_btn.disabled = False
        self.otp_btn_content.controls = [
            ft.Text("XÁC MINH DANH TÍNH", size=14, weight=ft.FontWeight.W_700, color="#ffffff"),
            ft.Icon(icon=ft.Icons.CHECK_CIRCLE, color="#ffffff", size=18)
        ]

    # ==========================================
    # GIAO DIỆN DASHBOARD CHÍNH TÂM
    # ==========================================
    def show_dashboard_ui(self):
        header = ft.Container(
            content=ft.Row([
                ft.Text("KAELIX", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
                ft.Text("CORE", size=24, weight=ft.FontWeight.W_300, color=ACCENT_CYAN),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            margin=ft.margin.only(bottom=32)
        )

        self.power_symbol = ft.Icon(icon=ft.Icons.POWER_SETTINGS_NEW, size=48, color="#4B5563")
        self.power_btn = ft.Container(
            content=self.power_symbol,
            width=120, height=120, border_radius=ft.border_radius.all(60),
            bgcolor=BG_INPUT, border=ft.border.all(2, BORDER_COLOR),
            alignment=ft.Alignment(0.0, 0.0), on_click=self.toggle_system,
            animate_scale=ft.Animation(300, ft.AnimationCurve.EASE_OUT_BACK), scale=1.0,
            shadow=ft.BoxShadow(blur_radius=24, color="#00000000") 
        )
        
        self.status_label = ft.Text("HỆ THỐNG CHỜ", size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_600)

        self.schedule_input = self.build_input("Lịch trình (08:00-17:30)", ft.Icons.SCHEDULE, accent=ACCENT_CYAN)
        
        # FIX LỖI "PAGE UNRESPONSIVE" TẠI ĐÂY: Khởi tạo padding = 0 thay vì padding = 16
        self.setup_panel = ft.Container(
            content=ft.Column([self.schedule_input], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            height=0, opacity=0, animate=ft.Animation(300, ft.AnimationCurve.EASE_IN_OUT), padding=0,
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

        self.is_setup_open = False
        self.setup_icon = ft.Icon(icon=ft.Icons.EXPAND_MORE, size=18, color=TEXT_MUTED)
        
        self.setup_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Icon(icon=ft.Icons.SETTINGS, size=14, color=TEXT_MUTED),
                ft.Text("THÔNG SỐ CẤU HÌNH", size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_700),
                self.setup_icon 
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            width=176, height=40, border_radius=ft.border_radius.all(20),
            bgcolor=BG_INPUT, border=ft.border.all(1, BORDER_COLOR),
            on_click=self.toggle_setup_menu, animate=200
        )
        
        def setup_hover(e):
            self.setup_toggle_btn.bgcolor = BORDER_COLOR if e.data == "true" else BG_INPUT
            self.setup_toggle_btn.update()
        self.setup_toggle_btn.on_hover = setup_hover

        self.console = ft.ListView(expand=True, spacing=6, auto_scroll=True)
        log_panel = ft.Container(
            content=self.console,
            height=128, bgcolor=BG_BASE, border_radius=ft.border_radius.all(16), 
            padding=ft.padding.all(16), border=ft.border.all(1, BORDER_COLOR)
        )

        self.monitor_bars = [
            ft.Container(width=4, height=15, bgcolor=ACCENT_CYAN, border_radius=ft.border_radius.all(2), opacity=0.15, animate=100)
            for _ in range(self.chart_points)
        ]
        
        monitor_panel = ft.Container(
            content=ft.Row(self.monitor_bars, spacing=2, vertical_alignment=ft.CrossAxisAlignment.END, alignment=ft.MainAxisAlignment.CENTER),
            height=72, bgcolor=BG_BASE, border_radius=ft.border_radius.all(16), 
            padding=ft.padding.all(16), border=ft.border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 1.0)
        )

        self.logout_btn = ft.Container(
            content=ft.Row([
                ft.Icon(icon=ft.Icons.LOGOUT, color="#FCA5A5", size=16),
                ft.Text("NGẮT KẾT NỐI", size=12, weight=ft.FontWeight.W_700, color="#FCA5A5")
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            width=160, height=40, border_radius=ft.border_radius.all(20),
            bgcolor="#450A0A", border=ft.border.all(1, "#7F1D1D"),
            on_click=lambda e: asyncio.create_task(self.process_logout()), animate=200
        )
        def logout_hover(e):
            self.logout_btn.bgcolor = "#7F1D1D" if e.data == "true" else "#450A0A"
            self.logout_btn.update()
        self.logout_btn.on_hover = logout_hover

        dashboard_layout = ft.Column([
            header,
            ft.Column([
                self.power_btn,
                ft.Container(height=16),
                self.status_label,
                ft.Container(height=24),
                self.setup_toggle_btn,
                self.setup_panel 
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            ft.Container(height=24), 
            ft.Text("LUỒNG DỮ LIỆU ĐO XA", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_700),
            ft.Container(height=8),
            log_panel,
            ft.Container(height=8), 
            monitor_panel,
            ft.Container(height=24),
            self.logout_btn
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        self.switch_view(dashboard_layout)

    async def process_logout(self):
        self.running = False
        if hasattr(self.page, "client_storage"): await self.page.client_storage.remove_async("kealix_cloud_session")
        if self.client: 
            await self.client.disconnect()
            self.client = None
        self.show_login_ui()

    # FIX LỖI "PAGE UNRESPONSIVE" TẠI ĐÂY: Thêm và bớt padding logic
    def toggle_setup_menu(self, e):
        self.is_setup_open = not self.is_setup_open
        if self.is_setup_open:
            self.setup_panel.height = 72
            self.setup_panel.opacity = 1
            self.setup_panel.padding = ft.padding.only(top=16, bottom=8) # Thêm padding khi mở
            self.setup_icon.icon = ft.Icons.EXPAND_LESS
            self.setup_icon.color = ACCENT_CYAN
            self.setup_toggle_btn.border = ft.border.all(1, ACCENT_CYAN)
        else:
            self.setup_panel.height = 0
            self.setup_panel.opacity = 0
            self.setup_panel.padding = 0 # Xóa padding khi đóng
            self.setup_icon.icon = ft.Icons.EXPAND_MORE
            self.setup_icon.color = TEXT_MUTED
            self.setup_toggle_btn.border = ft.border.all(1, BORDER_COLOR)
        self.page.update()

    async def animate_vital_signs(self):
        while self.running:
            self.tick += 0.5
            base_wave = math.sin(self.tick) * 5 + 20
            spike = random.randint(25, 50) if 3.0 < (self.tick % 8) < 3.3 else 0
            current_val = base_wave + spike

            self.pulse_data.pop(0)
            self.pulse_data.append(current_val)

            for i in range(self.chart_points):
                h = self.pulse_data[i]
                bar = self.monitor_bars[i]
                bar.height = h
                bar.bgcolor = "#ffffff" if h > 35 else ACCENT_CYAN
                bar.opacity = 1.0 if h > 35 else 0.2

            self.page.update()
            await asyncio.sleep(0.04) 

    def add_log(self, text, clr=ACCENT_CYAN):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.controls.append(
            ft.Text(f"[{now}] > {text}", color=clr, size=11, font_family="monospace", weight=ft.FontWeight.W_500)
        )
        self.page.update()

    def toggle_system(self, e):
        self.running = not self.running
        if self.running:
            self.power_symbol.icon = ft.Icons.BOLT 
            self.power_symbol.color = "#FFFFFF" 
            self.power_btn.bgcolor = ACCENT_CYAN 
            self.power_btn.border = ft.border.all(0, ft.Colors.TRANSPARENT) 
            self.power_btn.scale = 1.05
            self.power_btn.shadow = ft.BoxShadow(blur_radius=32, color=ACCENT_CYAN_GLOW, offset=ft.Offset(0, 8)) 
            
            self.status_label.value = "LÕI HOẠT ĐỘNG - CHẾ ĐỘ ẨN"
            self.status_label.color = ACCENT_CYAN
            
            if self.is_setup_open: self.toggle_setup_menu(None) 
            
            asyncio.create_task(self.main_loop())
            asyncio.create_task(self.animate_vital_signs())
            self.add_log("ĐÃ KHỞI TẠO LÕI. ĐANG BẢO MẬT KẾT NỐI...")
        else:
            self.power_symbol.icon = ft.Icons.POWER_SETTINGS_NEW 
            self.power_symbol.color = "#4B5563" 
            self.power_btn.bgcolor = BG_INPUT
            self.power_btn.border = ft.border.all(2, BORDER_COLOR)
            self.power_btn.scale = 1.0 
            self.power_btn.shadow = ft.BoxShadow(blur_radius=24, color="#00000000")
            
            self.status_label.value = "HỆ THỐNG CHỜ"
            self.status_label.color = TEXT_MUTED
            self.pulse_data = [15] * self.chart_points
            self.add_log("HỆ THỐNG NGOẠI TUYẾN.", "#EF4444")
            
        self.page.update()

    async def main_loop(self):
        try:
            while self.running:
                now = datetime.datetime.now().time()
                is_work = False
                try:
                    for part in self.schedule_input.value.split(","):
                        s, e = part.strip().split("-")
                        if datetime.datetime.strptime(s, "%H:%M").time() <= now <= datetime.datetime.strptime(e, "%H:%M").time():
                            is_work = True; break
                except: is_work = True

                if is_work:
                    await self.client(functions.account.UpdateStatusRequest(offline=False))
                    self.add_log(f"Đã truyền xung. Mạng ổn định.")
                else:
                    self.add_log("Ngoài lịch trình. Ngủ sâu...", TEXT_MUTED)
                
                await asyncio.sleep(random.randint(45, 75)) 
        except Exception as ex:
            if self.running:
                self.add_log(f"LỖI NGHIÊM TRỌNG: {ex}", "#EF4444")
            self.running = False
            self.page.update()

async def main(page: ft.Page):
    page.title = "Kaelix Matrix Core"
    page.bgcolor = BG_BASE
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.DARK
    
    # Thiết lập Typography hiện đại
    page.theme = ft.Theme(font_family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif")

    CyberPulseApp(page)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)