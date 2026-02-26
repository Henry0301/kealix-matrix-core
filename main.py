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
        
        # Ngắt tool ngầm khi tắt web
        self.page.on_disconnect = self.handle_disconnect
        
        # 1. VẼ NGAY MÀN HÌNH LOADING ĐỂ CHỐNG ĐEN MÀN HÌNH
        self.loading_text = ft.Text("SYSTEM INITIALIZING...", size=16, weight="bold", color="#00f2ff")
        self.main_container = ft.Container(
            content=ft.Column([
                self.loading_text,
                ft.ProgressBar(width=200, color="#00f2ff", bgcolor="#111111")
            ], horizontal_alignment="center", alignment="center"),
            padding=30, expand=True, alignment=ft.Alignment(0,0)
        )
        self.page.add(self.main_container)
        self.page.update()

        # 2. KHỞI CHẠY LUỒNG KIỂM TRA BỘ NHỚ TRÌNH DUYỆT (CÓ BẢO VỆ)
        asyncio.create_task(self.startup_routine())

    def handle_disconnect(self, e):
        self.running = False
        if self.client:
            asyncio.create_task(self.client.disconnect())
        print("User disconnected. Task terminated.")

    async def startup_routine(self):
        """Khởi động trễ để chắc chắn Web đã load xong DOM và WebSocket"""
        try:
            await asyncio.sleep(0.5) # Đợi 0.5s cho an toàn tuyệt đối
            
            saved_session = None
            # Kiểm tra xem trình duyệt có hỗ trợ client_storage không
            if hasattr(self.page, "client_storage"):
                self.loading_text.value = "CHECKING CLOUD SESSION..."
                self.page.update()
                # Phải dùng get_async trong môi trường Web Async
                saved_session = await self.page.client_storage.get_async("kealix_cloud_session")
            
            if saved_session:
                await self.check_existing_session(saved_session)
            else:
                self.show_login_ui()
                
        except Exception as e:
            print(f"Storage Error: {e}")
            # Nếu bộ nhớ lỗi, vẫn phải hiện màn hình đăng nhập để xài tiếp
            self.show_login_ui()

    # ==========================================
    # LUỒNG 1: GIAO DIỆN ĐĂNG NHẬP 
    # ==========================================
    def show_login_ui(self):
        # --- UI NHẬP SĐT ---
        self.phone_input = ft.TextField(label="Phone Number (e.g. +84987654321)", bgcolor="#080808", border_color="#333333", color="#00f2ff", focused_border_color="#00f2ff")
        self.phone_submit_btn = ft.ElevatedButton("SEND OTP", bgcolor="#00f2ff", color="black", on_click=self.handle_phone_submit)
        self.auth_error_label = ft.Text("", color="red", size=11)

        self.phone_view = ft.Column([
            ft.Text("AUTHENTICATION", size=20, weight="bold", color="#00f2ff"),
            ft.Text("Enter your Telegram phone number.", size=12, color="#666666"),
            ft.Container(height=20),
            self.phone_input,
            ft.Container(height=10),
            self.phone_submit_btn,
            self.auth_error_label 
        ], horizontal_alignment="center", alignment="center")

        # --- UI NHẬP OTP ---
        self.otp_input = ft.TextField(label="Login Code (OTP)", bgcolor="#080808", border_color="#333333", color="#00f2ff", focused_border_color="#00f2ff")
        self.password_input = ft.TextField(label="2FA Password (If any)", password=True, bgcolor="#080808", border_color="#333333", color="#00f2ff", focused_border_color="#00f2ff")
        self.otp_submit_btn = ft.ElevatedButton("VERIFY & LAUNCH CORE", bgcolor="#ff8800", color="white", on_click=self.handle_otp_submit)
        self.otp_error_label = ft.Text("", color="red", size=11)

        self.otp_view = ft.Column([
            ft.Text("SECURITY VERIFICATION", size=20, weight="bold", color="#ff8800"),
            ft.Text("Check your Telegram app for the login code.", size=12, color="#666666"),
            ft.Container(height=20),
            self.otp_input,
            self.password_input,
            ft.Container(height=10),
            self.otp_submit_btn,
            self.otp_error_label 
        ], horizontal_alignment="center", alignment="center", visible=False)

        # Xóa loading và thay bằng form đăng nhập
        self.page.controls.clear()
        self.login_container = ft.Container(
            content=ft.Column([self.phone_view, self.otp_view], alignment="center"),
            padding=30, expand=True, alignment=ft.Alignment(0,0)
        )
        self.page.add(self.login_container)
        self.page.update()

    # --- LOGIC ĐĂNG NHẬP MULTI-USER ---
    async def connect_client(self, session_str=""):
        if not self.client:
            self.client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
        if not self.client.is_connected():
            await self.client.connect()

    async def check_existing_session(self, saved_session):
        try:
            await self.connect_client(saved_session)
            if await self.client.is_user_authorized():
                self.show_dashboard_ui() 
            else:
                if hasattr(self.page, "client_storage"):
                    await self.page.client_storage.remove_async("kealix_cloud_session")
                self.show_login_ui()
        except:
            if hasattr(self.page, "client_storage"):
                await self.page.client_storage.remove_async("kealix_cloud_session")
            self.show_login_ui()

    def handle_phone_submit(self, e):
        self.phone = self.phone_input.value.strip()
        if not self.phone:
            self.auth_error_label.value = "Phone number is required!"
            self.page.update()
            return
            
        self.phone_submit_btn.text = "SENDING..."
        self.phone_submit_btn.disabled = True
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
            self.auth_error_label.value = f"Error: {ex}"
            self.phone_submit_btn.text = "SEND OTP"
            self.phone_submit_btn.disabled = False
        self.page.update()

    def handle_otp_submit(self, e):
        otp = self.otp_input.value.strip()
        pwd = self.password_input.value.strip()
        
        if not otp:
            self.otp_error_label.value = "OTP is required!"
            self.page.update()
            return
            
        self.otp_submit_btn.text = "VERIFYING..."
        self.otp_submit_btn.disabled = True
        self.page.update()
        asyncio.create_task(self.verify_login(otp, pwd))

    async def verify_login(self, otp, pwd):
        try:
            await self.client.sign_in(phone=self.phone, code=otp, phone_code_hash=self.phone_code_hash)
            if hasattr(self.page, "client_storage"):
                await self.page.client_storage.set_async("kealix_cloud_session", self.client.session.save())
            self.show_dashboard_ui()
        except errors.SessionPasswordNeededError:
            if not pwd:
                self.otp_error_label.value = "2FA Password is required!"
                self.otp_submit_btn.text = "VERIFY & LAUNCH CORE"
                self.otp_submit_btn.disabled = False
            else:
                try:
                    await self.client.sign_in(password=pwd)
                    if hasattr(self.page, "client_storage"):
                        await self.page.client_storage.set_async("kealix_cloud_session", self.client.session.save())
                    self.show_dashboard_ui()
                except Exception as ex2fa:
                    self.otp_error_label.value = f"2FA Error: {ex2fa}"
                    self.otp_submit_btn.text = "VERIFY & LAUNCH CORE"
                    self.otp_submit_btn.disabled = False
        except Exception as ex:
            self.otp_error_label.value = f"Login Error: {ex}"
            self.otp_submit_btn.text = "VERIFY & LAUNCH CORE"
            self.otp_submit_btn.disabled = False
        self.page.update()


    # ==========================================
    # LUỒNG 2: GIAO DIỆN DASHBOARD CHÍNH
    # ==========================================
    def show_dashboard_ui(self):
        self.page.controls.clear() # Dọn sạch màn hình cũ
        
        header = ft.Row([
            ft.Text("KAELIX", size=22, weight="bold", color="#ffffff"),
            ft.Text("CORE", size=22, weight="w300", color="#00f2ff"),
        ], alignment="center")

        self.power_symbol = ft.Text("⏻", size=60, color="#222222", weight="bold")
        self.power_btn = ft.Container(
            content=self.power_symbol,
            width=140, height=140, border_radius=70,
            bgcolor="#050505", border=ft.border.all(3, "#111111"),
            alignment=ft.Alignment(0, 0), 
            on_click=self.toggle_system,
            animate=300 
        )
        
        self.status_label = ft.Text("SYSTEM STANDBY", size=11, color="#444444", weight="bold")

        self.schedule_input = ft.TextField(
            label="Nhập giờ (Ví dụ: 08:00-12:00, 13:00-17:30)", 
            value="08:00-17:30",
            border_color="#333333", text_size=12, height=50,
            bgcolor="#080808", focused_border_color="#00f2ff",
            color="#00f2ff"
        )
        
        self.setup_panel = ft.Container(
            content=ft.Column([
                ft.Text("AUTO-PILOT SCHEDULER", size=10, color="#00f2ff"),
                self.schedule_input
            ], alignment="center"),
            height=0, opacity=0,
            animate=400,
            padding=ft.padding.only(top=10, bottom=10)
        )

        self.is_setup_open = False
        self.setup_icon = ft.Text("▼", size=10, color="#666666")
        
        self.setup_toggle_btn = ft.Container(
            content=ft.Row([
                ft.Text("⚙️ SETUP", size=10, color="#666666", weight="bold"),
                self.setup_icon 
            ], alignment="center", spacing=5),
            width=100, height=30, border_radius=15,
            bgcolor="#0a0a0a", border=ft.border.all(1, "#222222"),
            on_click=self.toggle_setup_menu,
            animate=200
        )

        self.console = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        log_panel = ft.Container(
            content=self.console,
            height=150, bgcolor="#030303", border_radius=10, 
            padding=10, border=ft.border.all(1, "#111111")
        )

        self.monitor_bars = []
        for i in range(self.chart_points):
            bar = ft.Container(
                width=5, height=15, 
                bgcolor="#00f2ff", border_radius=1, opacity=0.2, animate=50
            )
            self.monitor_bars.append(bar)
        
        monitor_panel = ft.Container(
            content=ft.Row(self.monitor_bars, spacing=1, vertical_alignment="end"),
            height=80, bgcolor="#030303", border_radius=10, 
            padding=10, border=ft.border.all(1, "#111111"),
            alignment=ft.Alignment(0, 1)
        )

        # Đẩy quá trình đăng xuất vào luồng Async
        self.logout_btn = ft.TextButton("LOG OUT & WIPE DATA", icon="logout", icon_color="red", on_click=lambda e: asyncio.create_task(self.process_logout()))

        self.page.add(
            ft.Column([
                header,
                ft.Container(height=10), 
                ft.Column([
                    self.power_btn,
                    ft.Container(height=10),
                    self.status_label,
                    ft.Container(height=10),
                    self.setup_toggle_btn,
                    self.setup_panel 
                ], horizontal_alignment="center"),
                ft.Container(height=10), 
                ft.Text("LIVE TELEMETRY", size=9, color="#666666"),
                log_panel,
                monitor_panel,
                self.logout_btn
            ], horizontal_alignment="center")
        )
        self.page.update()

    async def process_logout(self):
        """Xóa session khỏi trình duyệt một cách an toàn"""
        self.running = False
        if hasattr(self.page, "client_storage"):
            await self.page.client_storage.remove_async("kealix_cloud_session")
        if self.client: 
            await self.client.disconnect()
            self.client = None
        self.show_login_ui()

    def toggle_setup_menu(self, e):
        self.is_setup_open = not self.is_setup_open
        if self.is_setup_open:
            self.setup_panel.height = 80
            self.setup_panel.opacity = 1
            self.setup_icon.value = "▲"
            self.setup_toggle_btn.border = ft.border.all(1, "#00f2ff")
        else:
            self.setup_panel.height = 0
            self.setup_panel.opacity = 0
            self.setup_icon.value = "▼"
            self.setup_toggle_btn.border = ft.border.all(1, "#222222")
        self.page.update()

    async def animate_vital_signs(self):
        while self.running:
            self.tick += 0.5
            base_wave = math.sin(self.tick) * 5 + 20
            spike = 0
            if 3.0 < (self.tick % 8) < 3.3: spike = random.randint(30, 50)
            current_val = base_wave + spike

            self.pulse_data.pop(0)
            self.pulse_data.append(current_val)

            for i in range(self.chart_points):
                h = self.pulse_data[i]
                bar = self.monitor_bars[i]
                bar.height = h
                bar.bgcolor = "#ffffff" if h > 40 else "#00f2ff"
                bar.opacity = 1.0 if h > 40 else 0.3

            self.page.update()
            await asyncio.sleep(0.04) 

    def add_log(self, text, color="#00f2ff"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.console.controls.append(
            ft.Text(f"[{now}] > {text}", color=color, size=10, font_family="Consolas")
        )
        self.page.update()

    def toggle_system(self, e):
        self.running = not self.running
        if self.running:
            self.power_symbol.value = "⚡" 
            self.power_symbol.color = "#ff8800" 
            self.power_btn.bgcolor = "#00f2ff" 
            self.power_btn.border = ft.border.all(4, "#ffffff") 
            self.power_btn.scale = 1.05 
            
            self.status_label.value = "LINK ACTIVE - STEALTH MODE ON"
            self.status_label.color = "#00f2ff"
            
            if self.is_setup_open: self.toggle_setup_menu(None) 
            
            asyncio.create_task(self.main_loop())
            asyncio.create_task(self.animate_vital_signs())
            self.add_log("CORE INITIALIZED. SECURING CONNECTION...")
        else:
            self.power_symbol.value = "⏻" 
            self.power_symbol.color = "#222222" 
            self.power_btn.bgcolor = "#050505"
            self.power_btn.border = ft.border.all(3, "#111111")
            self.power_btn.scale = 1.0 
            
            self.status_label.value = "SYSTEM STANDBY"
            self.status_label.color = "#444444"
            self.pulse_data = [15] * self.chart_points
            self.add_log("SYSTEM OFFLINE.", "red")
            
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
                    self.add_log(f"Pulse transmitted. Network Stable.")
                else:
                    self.add_log("Outside schedule. Deep Sleep...", "#444444")
                
                await asyncio.sleep(random.randint(45, 75)) 
        except Exception as ex:
            if self.running:
                self.add_log(f"FATAL ERROR: {ex}", "red")
            self.running = False
            self.page.update()

async def main(page: ft.Page):
    page.title = "Kaelix Matrix Cloud"
    page.bgcolor = "#000000"
    page.padding = 20
    page.theme_mode = "dark"
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center" 
    
    try:
        page.window.width = 430
        page.window.height = 750
        page.window.resizable = False
        page.window.maximizable = False
    except:
        pass

    CyberPulseApp(page)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)