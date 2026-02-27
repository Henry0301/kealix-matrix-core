import flet as ft
import asyncio
import urllib.parse
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession 
import datetime
import random
import math
import os
import uuid

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

# Tạo thư mục chứa các session để nhiều người dùng chung độc lập
if not os.path.exists("sessions"):
    os.makedirs("sessions")

# QUẢN LÝ CÁC LÕI CHẠY NGẦM DÙ TẮT TRÌNH DUYỆT / MINI APP
GLOBAL_CORES = {}

class CoreSystem:
    """ Lõi hoạt động ngầm độc lập với Giao diện Flet """
    def __init__(self, session_id):
        self.session_id = session_id
        # Dùng file session SQLite mặc định của Telethon để lưu kết nối cứng
        self.client = TelegramClient(f"sessions/{session_id}", API_ID, API_HASH)
        self.running = False
        self.schedule = "08:00-17:30"
        self.logs = []
        self.task = None

    def add_log(self, text, clr=ACCENT_CYAN):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append({"time": now, "text": text, "color": clr})
        if len(self.logs) > 60: # Giữ 60 log gần nhất
            self.logs.pop(0)

    async def start_loop(self):
        if self.running: return
        self.running = True
        self.task = asyncio.create_task(self.main_loop())

    async def stop_loop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            self.task = None
        self.add_log("HỆ THỐNG NGOẠI TUYẾN.", "#EF4444")

    async def main_loop(self):
        self.add_log("ĐÃ KHỞI TẠO LÕI. ĐANG BẢO MẬT KẾT NỐI...")
        try:
            while self.running:
                # Tự động kết nối lại nếu rớt mạng
                if not self.client.is_connected():
                    self.add_log("Mất kết nối. Đang nối lại lõi...", ACCENT_ORANGE)
                    await self.client.connect()

                now = datetime.datetime.now().time()
                is_work = False
                try:
                    for part in self.schedule.split(","):
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
        except asyncio.CancelledError:
            pass # Bị dừng chủ động
        except Exception as ex:
            self.running = False
            self.add_log(f"LỖI NGHIÊM TRỌNG: {ex}", "#EF4444")


class CyberPulseApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.device_id = None
        self.core = None # Sẽ nối vào CoreSystem
        
        self.phone = ""
        self.phone_code_hash = ""
        self.chart_points = 65 
        self.pulse_data = [15] * self.chart_points 
        self.tick = 0 
        self.page_connected = True
        self.in_dashboard = False
        self.qr_login_obj = None
        self.login_mode = "QR"
        
        self.page.on_disconnect = self.handle_disconnect

        # ==========================================
        # CHUẨN CÚ PHÁP FLET 0.81.0
        # ==========================================
        self.main_wrapper = ft.Container(
            width=432, 
            height=720, 
            bgcolor=BG_CARD,
            border_radius=ft.BorderRadius.all(24), 
            border=ft.Border.all(1, BORDER_LIGHT),
            shadow=[
                ft.BoxShadow(blur_radius=64, color="#80000000", offset=ft.Offset(0, 24)),
                ft.BoxShadow(blur_radius=120, spread_radius=-24, color="#1A06B6D4", offset=ft.Offset(0, 0))
            ],
            padding=ft.Padding.all(40),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            alignment=ft.Alignment(0.0, 0.0) 
        )
        
        self.page.add(
            ft.Container(
                content=self.main_wrapper,
                expand=True,
                alignment=ft.Alignment(0.0, 0.0)
            )
        )
        asyncio.create_task(self.startup_routine())

    async def handle_disconnect(self, e):
        # Tắt cờ để dừng các hiệu ứng UI, nhưng KHÔNG TẮT LÕI (self.core)
        self.page_connected = False
        self.in_dashboard = False

    def switch_view(self, new_content):
        self.main_wrapper.content = new_content
        self.page.update()

    # Thêm tham số on_submit để đồng bộ bấm phím Enter
    def build_input(self, label_text, icon_data, is_pwd=False, accent=ACCENT_CYAN, on_submit_handler=None):
        return ft.TextField(
            label=label_text,
            prefix_icon=icon_data,
            password=is_pwd,
            can_reveal_password=is_pwd,
            bgcolor=BG_INPUT,
            border_color=BORDER_COLOR,
            focused_border_color=accent,
            color=TEXT_PRIMARY,
            border_radius=ft.BorderRadius.all(12),
            text_size=14,
            height=48, 
            content_padding=ft.Padding.symmetric(vertical=0, horizontal=16),
            label_style=ft.TextStyle(color=TEXT_MUTED, size=13, weight=ft.FontWeight.W_500),
            cursor_color=accent,
            selection_color=accent + "40",
            on_submit=on_submit_handler
        )

    def build_primary_btn(self, text, gradient_colors, glow_color, icon_data, on_click_handler):
        btn_text = ft.Text(value=text, size=14, weight=ft.FontWeight.W_700, color="#ffffff")
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
            border_radius=ft.BorderRadius.all(12),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1.0, 0.0), 
                end=ft.Alignment(1.0, 0.0),    
                colors=gradient_colors
            ),
            shadow=ft.BoxShadow(blur_radius=16, color=glow_color, offset=ft.Offset(0, 4)),
            alignment=ft.Alignment(0.0, 0.0), 
            on_click=on_click_handler,
            animate_scale=250, 
            scale=1.0
        )
        
        def on_hover(e):
            btn.scale = 0.98 if e.data == "true" else 1.0
            btn.update()
            
        btn.on_hover = on_hover
        return btn, content_row

    def build_tab_btn(self, text, icon_data, is_active, on_click_handler):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon=icon_data, size=16, color=TEXT_PRIMARY if is_active else TEXT_MUTED),
                ft.Text(value=text, size=13, weight=ft.FontWeight.W_700, color=TEXT_PRIMARY if is_active else TEXT_MUTED)
            ], alignment=ft.MainAxisAlignment.CENTER),
            expand=True,
            height=40,
            bgcolor=BORDER_COLOR if is_active else "transparent",
            border_radius=ft.BorderRadius.all(8),
            on_click=on_click_handler,
            ink=True
        )

    async def startup_routine(self):
        loading_view = ft.Container(
            content=ft.Column([
                ft.Icon(icon=ft.Icons.FINGERPRINT, size=56, color=ACCENT_CYAN),
                ft.Container(height=24),
                ft.Text(value="ĐANG BẢO MẬT KẾT NỐI...", size=13, weight=ft.FontWeight.W_700, color=ACCENT_CYAN),
                ft.Container(height=16),
                ft.ProgressBar(width=180, color=ACCENT_CYAN, bgcolor=BG_INPUT)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0),
            alignment=ft.Alignment(0.0, 0.0),
            expand=True
        )
        self.switch_view(loading_view)

        await asyncio.sleep(1.2)
        try:
            # Nhận dạng thiết bị/Telegram App độc lập
            if hasattr(self.page, "client_storage"):
                self.device_id = await self.page.client_storage.get_async("kealix_device_uuid")
                if not self.device_id:
                    self.device_id = str(uuid.uuid4())
                    await self.page.client_storage.set_async("kealix_device_uuid", self.device_id)
            else:
                self.device_id = str(uuid.uuid4())

            # Cấp phát 1 lõi riêng cho device_id này
            if self.device_id not in GLOBAL_CORES:
                GLOBAL_CORES[self.device_id] = CoreSystem(self.device_id)
            self.core = GLOBAL_CORES[self.device_id]

            if not self.core.client.is_connected():
                await self.core.client.connect()

            if await self.core.client.is_user_authorized(): 
                self.show_dashboard_ui() 
            else:
                self.show_login_ui()
        except Exception:
            self.show_login_ui()

    # ==========================================
    # GIAO DIỆN ĐĂNG NHẬP SAAS KÉP (QR + PHONE)
    # ==========================================
    def show_login_ui(self):
        logo_main = ft.Container(
            content=ft.Icon(icon=ft.Icons.SATELLITE_ALT, size=32, color=ACCENT_CYAN),
            width=72, height=72, border_radius=ft.BorderRadius.all(36), bgcolor=BG_INPUT,
            border=ft.Border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 0.0),
            shadow=ft.BoxShadow(blur_radius=24, color=ACCENT_CYAN_GLOW)
        )

        self.tab_qr = self.build_tab_btn("MÃ QR", ft.Icons.QR_CODE, True, lambda e: self.switch_login_mode("QR"))
        self.tab_phone = self.build_tab_btn("SỐ ĐT", ft.Icons.PHONE, False, lambda e: self.switch_login_mode("PHONE"))
        self.login_tabs = ft.Row([self.tab_qr, self.tab_phone], spacing=8)

        # ---- VIEW: QUÉT MÃ QR ----
        self.qr_image = ft.Image(src="", width=180, height=180, fit="contain", visible=False)
        self.qr_loading = ft.ProgressRing(width=24, height=24, color=ACCENT_CYAN)
        self.qr_stack = ft.Stack([
            ft.Container(self.qr_loading, alignment=ft.Alignment(0.0, 0.0), width=180, height=180),
            ft.Container(self.qr_image, alignment=ft.Alignment(0.0, 0.0), width=180, height=180)
        ], width=180, height=180)

        self.qr_error = ft.Text(value="", color="#EF4444", size=13, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)

        self.qr_view = ft.Column([
            ft.Container(height=16),
            ft.Container(
                content=self.qr_stack,
                width=204, height=204,
                bgcolor="#ffffff", 
                padding=ft.Padding.all(12),
                border_radius=ft.BorderRadius.all(12),
                shadow=ft.BoxShadow(blur_radius=24, color=ACCENT_CYAN_GLOW),
                alignment=ft.Alignment(0.0, 0.0)
            ),
            ft.Container(height=16),
            ft.Text(value="Mở Telegram trên điện thoại", size=15, weight=ft.FontWeight.W_700, color=TEXT_PRIMARY),
            ft.Text(value="Cài đặt > Thiết bị > Liên kết thiết bị", size=13, color=TEXT_MUTED),
            ft.Container(height=8),
            self.qr_error
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)

        # ---- VIEW: NHẬP SỐ ĐIỆN THOẠI ----
        # Đồng bộ sự kiện nhập qua on_submit_handler
        self.phone_input = self.build_input("Số điện thoại Telegram", ft.Icons.PHONE, accent=ACCENT_CYAN, on_submit_handler=self.handle_phone_submit)
        self.phone_btn, self.phone_btn_content = self.build_primary_btn(
            "GỬI MÃ XÁC NHẬN", ["#06B6D4", "#3B82F6"], ACCENT_CYAN_GLOW, ft.Icons.SEND, self.handle_phone_submit
        )
        self.auth_error = ft.Text(value="", color="#EF4444", size=13, weight=ft.FontWeight.W_500)

        self.phone_view = ft.Column([
            ft.Container(height=24),
            self.phone_input,
            ft.Container(height=16),
            self.phone_btn,
            ft.Container(height=8),
            self.auth_error 
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, visible=False)

        self.step1_view = ft.Column([
            logo_main,
            ft.Container(height=24),
            ft.Text(value="LIÊN KẾT HỆ THỐNG", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
            ft.Container(height=24),
            self.login_tabs,
            self.qr_view,
            self.phone_view
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0)

        # ---- VIEW: BƯỚC 2 (OTP HOẶC 2FA) ----
        logo_otp = ft.Container(
            content=ft.Icon(icon=ft.Icons.SECURITY, size=32, color=ACCENT_ORANGE),
            width=72, height=72, border_radius=ft.BorderRadius.all(36), bgcolor=BG_INPUT,
            border=ft.Border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 0.0),
            shadow=ft.BoxShadow(blur_radius=24, color=ACCENT_ORANGE_GLOW)
        )
        
        self.otp_input = self.build_input("Mã xác thực (OTP)", ft.Icons.VPN_KEY, accent=ACCENT_ORANGE, on_submit_handler=self.handle_otp_submit)
        self.password_input = self.build_input("Mật khẩu 2FA (Nếu có)", ft.Icons.LOCK, is_pwd=True, accent=ACCENT_ORANGE, on_submit_handler=self.handle_otp_submit)
        self.password_input.visible = False 
        
        self.otp_btn, self.otp_btn_content = self.build_primary_btn(
            "XÁC MINH DANH TÍNH", ["#F59E0B", "#EA580C"], ACCENT_ORANGE_GLOW, ft.Icons.CHECK_CIRCLE, self.handle_otp_submit
        )
        self.otp_error = ft.Text(value="", color="#EF4444", size=13, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)

        self.otp_view = ft.Column([
            logo_otp,
            ft.Container(height=24),
            ft.Text(value="KIỂM TRA BẢO MẬT", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
            ft.Container(height=4),
            ft.Text(value="Vui lòng hoàn thành bước xác thực.", size=14, weight=ft.FontWeight.W_400, color=TEXT_MUTED),
            ft.Container(height=32),
            self.otp_input,
            ft.Container(height=16),
            self.password_input,
            ft.Container(height=16),
            self.otp_btn,
            ft.Container(height=8),
            self.otp_error 
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=0, visible=False)

        self.switch_view(ft.Column([self.step1_view, self.otp_view], alignment=ft.MainAxisAlignment.CENTER, spacing=0))

        self.login_mode = "QR"
        asyncio.create_task(self.start_qr_login())

    def switch_login_mode(self, mode):
        self.login_mode = mode
        
        self.tab_qr.bgcolor = BORDER_COLOR if mode == "QR" else "transparent"
        self.tab_qr.content.controls[0].color = TEXT_PRIMARY if mode == "QR" else TEXT_MUTED
        self.tab_qr.content.controls[1].color = TEXT_PRIMARY if mode == "QR" else TEXT_MUTED
        
        self.tab_phone.bgcolor = BORDER_COLOR if mode == "PHONE" else "transparent"
        self.tab_phone.content.controls[0].color = TEXT_PRIMARY if mode == "PHONE" else TEXT_MUTED
        self.tab_phone.content.controls[1].color = TEXT_PRIMARY if mode == "PHONE" else TEXT_MUTED

        self.qr_view.visible = (mode == "QR")
        self.phone_view.visible = (mode == "PHONE")
        self.page.update()

        if mode == "QR":
            asyncio.create_task(self.start_qr_login())

    async def start_qr_login(self):
        # TỰ ĐỘNG LÀM MỚI QR KHI HẾT HẠN
        while self.login_mode == "QR" and self.page_connected:
            self.qr_error.value = "Đang tạo mã bảo mật..."
            self.qr_error.color = ACCENT_CYAN
            self.qr_image.visible = False
            self.qr_loading.visible = True
            self.page.update()

            try:
                if not self.core.client.is_connected():
                    await self.core.client.connect()
                
                self.qr_login_obj = await self.core.client.qr_login()
                qr_url = self.qr_login_obj.url
                
                encoded_url = urllib.parse.quote(qr_url)
                self.qr_image.src = f"https://api.qrserver.com/v1/create-qr-code/?size=256x256&data={encoded_url}"
                self.qr_image.visible = True
                self.qr_loading.visible = False
                self.qr_error.value = "Mã QR sẽ tự làm mới khi hết hạn."
                self.qr_error.color = TEXT_MUTED
                self.page.update()

                await self.qr_login_obj.wait()

                if self.login_mode != "QR": return 
                self.show_dashboard_ui()
                break # Thành công thoát vòng lặp QR
            except errors.SessionPasswordNeededError:
                if self.login_mode == "QR": self.show_2fa_ui_only()
                break # Cần 2FA thoát vòng lặp
            except Exception as e:
                # Bắt lỗi QR hết hạn -> Vòng lặp tự động quay lại tạo QR mới
                if self.login_mode == "QR":
                    self.qr_error.value = "Mã QR đã hết hạn. Đang tải lại mã mới..."
                    self.qr_error.color = "#EF4444"
                    self.page.update()
                    await asyncio.sleep(2) # Chờ xíu rồi vòng lên tạo lại

    def show_2fa_ui_only(self):
        self.step1_view.visible = False
        self.otp_view.visible = True
        self.otp_input.visible = False 
        self.password_input.visible = True 
        self.otp_error.value = "Tài khoản có bảo mật 2 lớp. Nhập mật khẩu để tiếp tục."
        self.otp_error.color = ACCENT_CYAN
        self.page.update()

    def handle_phone_submit(self, e):
        self.phone = self.phone_input.value.strip()
        if not self.phone:
            self.auth_error.value = "Vui lòng nhập số điện thoại"
            self.page.update()
            return
            
        self.phone_btn.disabled = True
        self.phone_btn_content.controls = [
            ft.ProgressRing(width=16, height=16, color="#ffffff", stroke_width=2),
            ft.Text(value="ĐANG TRUYỀN TẢI...", size=14, weight=ft.FontWeight.W_700, color="#ffffff")
        ]
        self.page.update()
        asyncio.create_task(self.request_otp())

    async def request_otp(self):
        try:
            if not self.core.client.is_connected():
                await self.core.client.connect()
            sent_code = await self.core.client.send_code_request(self.phone)
            self.phone_code_hash = sent_code.phone_code_hash
            self.step1_view.visible = False
            self.otp_view.visible = True
            self.otp_input.visible = True
            # Tự động focus vào ô OTP
            self.otp_input.focus()
        except Exception as ex:
            self.auth_error.value = str(ex)
            self.phone_btn.disabled = False
            self.phone_btn_content.controls = [
                ft.Text(value="GỬI MÃ XÁC NHẬN", size=14, weight=ft.FontWeight.W_700, color="#ffffff"),
                ft.Icon(icon=ft.Icons.SEND, color="#ffffff", size=18)
            ]
        self.page.update()

    def handle_otp_submit(self, e):
        otp = self.otp_input.value.strip()
        pwd = self.password_input.value.strip()
        
        if self.otp_input.visible and not otp:
            self.otp_error.value = "Vui lòng nhập mã xác thực"
            self.otp_error.color = "#EF4444"
            self.page.update()
            return
            
        if not self.otp_input.visible and not pwd:
            self.otp_error.value = "Vui lòng nhập mật khẩu 2FA"
            self.otp_error.color = "#EF4444"
            self.page.update()
            return
            
        self.otp_btn.disabled = True
        self.otp_btn_content.controls = [
            ft.ProgressRing(width=16, height=16, color="#ffffff", stroke_width=2),
            ft.Text(value="ĐANG XÁC MINH...", size=14, weight=ft.FontWeight.W_700, color="#ffffff")
        ]
        self.page.update()
        asyncio.create_task(self.verify_login(otp, pwd))

    async def verify_login(self, otp, pwd):
        try:
            if self.otp_input.visible:
                await self.core.client.sign_in(phone=self.phone, code=otp, phone_code_hash=self.phone_code_hash)
            else:
                await self.core.client.sign_in(password=pwd)

            self.show_dashboard_ui()
        except errors.SessionPasswordNeededError:
            self.otp_error.value = "Vui lòng nhập mật khẩu 2FA"
            self.otp_error.color = "#EF4444"
            self.password_input.visible = True
            self.otp_input.visible = False
            self.reset_otp_btn()
            self.password_input.focus()
        except Exception:
            self.otp_error.value = "Dữ liệu xác minh không hợp lệ"
            self.otp_error.color = "#EF4444"
            self.reset_otp_btn()
        self.page.update()

    def reset_otp_btn(self):
        self.otp_btn.disabled = False
        self.otp_btn_content.controls = [
            ft.Text(value="XÁC MINH DANH TÍNH", size=14, weight=ft.FontWeight.W_700, color="#ffffff"),
            ft.Icon(icon=ft.Icons.CHECK_CIRCLE, color="#ffffff", size=18)
        ]

    # ==========================================
    # GIAO DIỆN DASHBOARD ĐÃ ĐƯỢC ĐỒNG BỘ HOÁ
    # ==========================================
    def show_dashboard_ui(self):
        self.in_dashboard = True
        header = ft.Container(
            content=ft.Row([
                ft.Text(value="KAELIX", size=24, weight=ft.FontWeight.W_800, color=TEXT_PRIMARY),
                ft.Text(value="CORE", size=24, weight=ft.FontWeight.W_300, color=ACCENT_CYAN),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=6),
            margin=ft.margin.only(bottom=32)
        )

        self.power_symbol = ft.Icon(icon=ft.Icons.POWER_SETTINGS_NEW, size=48, color="#4B5563")
        self.power_btn = ft.Container(
            content=self.power_symbol,
            width=120, height=120, border_radius=ft.BorderRadius.all(60),
            bgcolor=BG_INPUT, border=ft.Border.all(2, BORDER_COLOR),
            alignment=ft.Alignment(0.0, 0.0), on_click=self.toggle_system,
            animate_scale=300, scale=1.0,
            shadow=ft.BoxShadow(blur_radius=24, color="#00000000") 
        )
        
        self.status_label = ft.Text(value="HỆ THỐNG CHỜ", size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_600)

        # Lấy lịch trình từ Lõi
        self.schedule_input = self.build_input("Lịch trình (08:00-17:30)", ft.Icons.SCHEDULE, accent=ACCENT_CYAN, on_submit_handler=self.update_schedule)
        self.schedule_input.value = self.core.schedule
        
        self.setup_panel = ft.Container(
            content=ft.Column([self.schedule_input], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            height=0, opacity=0, animate=300, padding=ft.Padding.all(0),
            clip_behavior=ft.ClipBehavior.HARD_EDGE
        )

        self.is_setup_open = False
        self.setup_icon = ft.Icon(icon=ft.Icons.EXPAND_MORE, size=18, color=TEXT_MUTED)
        
        self.setup_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Icon(icon=ft.Icons.SETTINGS, size=14, color=TEXT_MUTED),
                ft.Text(value="THÔNG SỐ CẤU HÌNH", size=12, color=TEXT_MUTED, weight=ft.FontWeight.W_700),
                self.setup_icon 
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            width=176, height=40, border_radius=ft.BorderRadius.all(20),
            bgcolor=BG_INPUT, border=ft.Border.all(1, BORDER_COLOR),
            on_click=self.toggle_setup_menu, animate=200
        )
        
        def setup_hover(e):
            self.setup_toggle_btn.bgcolor = BORDER_COLOR if e.data == "true" else BG_INPUT
            self.setup_toggle_btn.update()
        self.setup_toggle_btn.on_hover = setup_hover

        self.console = ft.ListView(expand=True, spacing=6, auto_scroll=True)
        log_panel = ft.Container(
            content=self.console,
            height=128, bgcolor=BG_BASE, border_radius=ft.BorderRadius.all(16), 
            padding=ft.Padding.all(16), border=ft.Border.all(1, BORDER_COLOR)
        )

        self.monitor_bars = [
            ft.Container(width=4, height=15, bgcolor=ACCENT_CYAN, border_radius=ft.BorderRadius.all(2), opacity=0.15, animate=100)
            for _ in range(self.chart_points)
        ]
        
        monitor_panel = ft.Container(
            content=ft.Row(self.monitor_bars, spacing=2, vertical_alignment=ft.CrossAxisAlignment.END, alignment=ft.MainAxisAlignment.CENTER),
            height=72, bgcolor=BG_BASE, border_radius=ft.BorderRadius.all(16), 
            padding=ft.Padding.all(16), border=ft.Border.all(1, BORDER_COLOR), alignment=ft.Alignment(0.0, 1.0)
        )

        self.logout_btn = ft.Container(
            content=ft.Row([
                ft.Icon(icon=ft.Icons.LOGOUT, color="#FCA5A5", size=16),
                ft.Text(value="NGẮT KẾT NỐI", size=12, weight=ft.FontWeight.W_700, color="#FCA5A5")
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            width=160, height=40, border_radius=ft.BorderRadius.all(20),
            bgcolor="#450A0A", border=ft.Border.all(1, "#7F1D1D"),
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
            ft.Text(value="LUỒNG DỮ LIỆU ĐO XA", size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_700),
            ft.Container(height=8),
            log_panel,
            ft.Container(height=8), 
            monitor_panel,
            ft.Container(height=24),
            self.logout_btn
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
        
        self.switch_view(dashboard_layout)

        # Cập nhật UI theo Lõi (nếu nó đang chạy sẵn)
        self.update_ui_power_state(self.core.running)
        
        # Bắt đầu các vòng lặp đồng bộ UI với Lõi
        asyncio.create_task(self.ui_sync_logs_loop())
        asyncio.create_task(self.animate_vital_signs())

    def update_schedule(self, e):
        # Đồng bộ lịch trình từ TextField vào lõi khi bấm Enter
        if self.core:
            self.core.schedule = self.schedule_input.value
            self.core.add_log(f"Đã cập nhật cấu hình thời gian.", TEXT_MUTED)

    async def ui_sync_logs_loop(self):
        """ Luồng chuyên đồng bộ Logs và trạng thái Nút Nguồn từ Core lên giao diện """
        last_log_idx = 0
        while self.page_connected and self.in_dashboard:
            # Nếu lõi ngưng chạy vì lỗi, tự cập nhật UI
            if self.power_symbol.color == "#FFFFFF" and not self.core.running:
                self.update_ui_power_state(False)
                
            # Copy log mới
            current_logs = self.core.logs
            if len(current_logs) > last_log_idx:
                for idx in range(last_log_idx, len(current_logs)):
                    log = current_logs[idx]
                    self.console.controls.append(
                        ft.Text(value=f"[{log['time']}] > {log['text']}", color=log['color'], size=11, font_family="monospace", weight=ft.FontWeight.W_500)
                    )
                last_log_idx = len(current_logs)
                self.page.update()
                
            await asyncio.sleep(0.5)

    def update_ui_power_state(self, is_running):
        if is_running:
            self.power_symbol.icon = ft.Icons.BOLT 
            self.power_symbol.color = "#FFFFFF" 
            self.power_btn.bgcolor = ACCENT_CYAN 
            self.power_btn.border = ft.Border.all(0, "transparent") 
            self.power_btn.scale = 1.05
            self.power_btn.shadow = ft.BoxShadow(blur_radius=32, color=ACCENT_CYAN_GLOW, offset=ft.Offset(0, 8)) 
            self.status_label.value = "LÕI HOẠT ĐỘNG - CHẾ ĐỘ ẨN"
            self.status_label.color = ACCENT_CYAN
        else:
            self.power_symbol.icon = ft.Icons.POWER_SETTINGS_NEW 
            self.power_symbol.color = "#4B5563" 
            self.power_btn.bgcolor = BG_INPUT
            self.power_btn.border = ft.Border.all(2, BORDER_COLOR)
            self.power_btn.scale = 1.0 
            self.power_btn.shadow = ft.BoxShadow(blur_radius=24, color="#00000000")
            self.status_label.value = "HỆ THỐNG CHỜ"
            self.status_label.color = TEXT_MUTED
            self.pulse_data = [15] * self.chart_points
            
        self.page.update()

    async def process_logout(self):
        self.in_dashboard = False
        if self.core:
            await self.core.stop_loop()
            try:
                await self.core.client.log_out() # Đăng xuất hẳn Telegram
            except: pass
            
            # Xóa session file cứng để sạch dữ liệu
            session_file = f"sessions/{self.device_id}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            
            # Gỡ Lõi ra khỏi danh sách hệ thống
            if self.device_id in GLOBAL_CORES:
                del GLOBAL_CORES[self.device_id]
            self.core = None

        self.show_login_ui()

    def toggle_setup_menu(self, e):
        self.is_setup_open = not self.is_setup_open
        if self.is_setup_open:
            self.setup_panel.height = 72
            self.setup_panel.opacity = 1
            self.setup_panel.padding = ft.Padding.only(top=16, bottom=8)
            self.setup_icon.icon = ft.Icons.EXPAND_LESS
            self.setup_icon.color = ACCENT_CYAN
            self.setup_toggle_btn.border = ft.Border.all(1, ACCENT_CYAN)
        else:
            self.setup_panel.height = 0
            self.setup_panel.opacity = 0
            self.setup_panel.padding = ft.Padding.all(0)
            self.setup_icon.icon = ft.Icons.EXPAND_MORE
            self.setup_icon.color = TEXT_MUTED
            self.setup_toggle_btn.border = ft.Border.all(1, BORDER_COLOR)
            self.update_schedule(None) # Tự lưu khi đóng menu cấu hình
        self.page.update()

    async def animate_vital_signs(self):
        while self.page_connected and self.in_dashboard:
            if self.core and self.core.running:
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

    def toggle_system(self, e):
        if not self.core: return
        
        if self.core.running:
            asyncio.create_task(self.core.stop_loop())
            self.update_ui_power_state(False)
        else:
            if self.is_setup_open: self.toggle_setup_menu(None) 
            asyncio.create_task(self.core.start_loop())
            self.update_ui_power_state(True)


async def main(page: ft.Page):
    page.title = "Kaelix Matrix Core"
    page.bgcolor = BG_BASE
    page.padding = 0 
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = ft.Theme(font_family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif")

    CyberPulseApp(page)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)