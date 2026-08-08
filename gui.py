import os
import re
import threading
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox

# UI Styling Defaults
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LapdoctorGUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("LapDoctor - Smart System Health Assistant")
        self.geometry("1100x750")
        self.minsize(1000, 680)

        # Theme Palettes: same layout/design language, only the surface &
        # text tones swap between Dark/Light. Accent + status colors are kept
        # brand-consistent across both themes on purpose.
        self.PALETTES = {
            "Dark": {
                "bg": "#121214", "card": "#1E1E22", "sidebar": "#18181B",
                "surface2": "#27272A", "surface3": "#20202A", "hover2": "#3F3F46",
                "text": "#F4F4F5", "muted": "#A1A1AA", "muted2": "#52525B",
            },
            "Light": {
                "bg": "#F1F5F9", "card": "#FFFFFF", "sidebar": "#E4E4E7",
                "surface2": "#E5E7EB", "surface3": "#ECECF1", "hover2": "#D4D4D8",
                "text": "#18181B", "muted": "#52525B", "muted2": "#71717A",
            },
        }
        self.current_theme = "Dark"

        # Color Palette (populated from PALETTES; kept as plain attributes so
        # every existing widget-creation call site is unchanged)
        self.BG_DARK = self.PALETTES["Dark"]["bg"]
        self.CARD_BG = self.PALETTES["Dark"]["card"]
        self.SIDEBAR_BG = self.PALETTES["Dark"]["sidebar"]
        self.PRIMARY_ACCENT = "#38BDF8"  # Cyan/Blue - constant brand accent
        self.TEXT_COLOR = self.PALETTES["Dark"]["text"]
        self.TEXT_MUTED = self.PALETTES["Dark"]["muted"]

        self.configure(fg_color=self.BG_DARK)

        # App State
        self.is_scanning = False
        self.stop_requested = False
        self.detected_items = []
        self.analysis_summary = {"reasons": [], "total_safe_size": 0}
        self.live_stats = {"cpu": 0, "ram": 0, "disk": 0, "storage": 0}
        self.scan_stop_event = threading.Event()
        self.scan_progress = 0

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Build Layout
        self.create_sidebar()
        self.create_main_container()

        # Load Core Modules
        self.load_backend_modules()
        self.init_history_db()

        # Active Page Tracking
        self.show_page("dashboard")

        # Hardware Monitoring Thread
        self.monitoring = True
        threading.Thread(target=self.update_system_stats, daemon=True).start()

    def load_backend_modules(self):
        try:
            from core import app_analyzer, cleanup, duplicate, large_files, old_files, system_monitor
            self.app_analyzer = app_analyzer
            self.cleanup = cleanup
            self.duplicate = duplicate
            self.large_files = large_files
            self.old_files = old_files
            self.system_monitor = system_monitor
        except ImportError:
            self.app_analyzer = None
            self.cleanup = None
            self.duplicate = None
            self.large_files = None
            self.old_files = None
            self.system_monitor = None

    def init_history_db(self):
        db_path = os.path.join(os.path.dirname(__file__), "lapdoctor_cache.db")
        self.history_db_path = db_path
        try:
            import sqlite3
            self.history_conn = sqlite3.connect(db_path, check_same_thread=False)
            self.history_conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_type TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    deleted_files TEXT,
                    deleted_count INTEGER DEFAULT 0,
                    deleted_size_mb REAL DEFAULT 0,
                    note TEXT
                )
                """
            )
            self.history_conn.commit()
        except Exception as exc:
            self.log_text = None
            self.history_conn = None
            self.history_error = str(exc)

    def record_scan(self, scan_type, target_path, status, deleted_files=None, deleted_count=0, deleted_size_mb=0.0, note=""):
        if not getattr(self, "history_conn", None):
            return
        try:
            import sqlite3
            scanned_at = time.strftime("%Y-%m-%d %H:%M:%S")
            self.history_conn.execute(
                """
                INSERT INTO scan_history (scan_type, target_path, scanned_at, status, deleted_files, deleted_count, deleted_size_mb, note)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (scan_type, target_path, scanned_at, status, "|".join(deleted_files or []), deleted_count, deleted_size_mb, note),
            )
            self.history_conn.commit()
        except Exception as exc:
            self.log(f"[History Error]: {exc}")

    def refresh_history_page(self):
        if not getattr(self, "history_conn", None):
            return
        try:
            rows = self.history_conn.execute(
                """
                SELECT id, scan_type, target_path, scanned_at, status, deleted_count, deleted_files, deleted_size_mb
                FROM scan_history
                ORDER BY id DESC
                """
            ).fetchall()
            if getattr(self, "history_txt", None):
                self.history_txt.delete("1.0", "end")
                if not rows:
                    self.history_txt.insert("end", "[System Initialized]: No scan history available yet.\n")
                    if hasattr(self, "last_scan_label"):
                        self.last_scan_label.configure(text="Last scanned: none")
                    if hasattr(self, "last_deleted_label"):
                        self.last_deleted_label.configure(text="Last deleted: none")
                    return

                latest_scan = rows[0]
                scan_type, target_path, scanned_at, status = latest_scan[1], latest_scan[2], latest_scan[3], latest_scan[4]
                if hasattr(self, "last_scan_label"):
                    self.last_scan_label.configure(
                        text=f"Last scanned: {scan_type.upper()} on {target_path} at {scanned_at} ({status})"
                    )

                last_deleted = next((row for row in rows if row[4] == "deleted"), None)
                if last_deleted and hasattr(self, "last_deleted_label"):
                    deleted_files = last_deleted[6] or ""
                    deleted_count = last_deleted[5]
                    deleted_size_mb = last_deleted[7] or 0
                    self.last_deleted_label.configure(
                        text=f"Last deleted: {deleted_count} files | {deleted_size_mb:.2f} MB | {deleted_files}"
                    )
                elif hasattr(self, "last_deleted_label"):
                    self.last_deleted_label.configure(text="Last deleted: none")

                self.history_txt.insert("end", "Scan & Cleanup History\n")
                for row in rows:
                    scan_type, target_path, scanned_at, status, deleted_count, deleted_files = row[1], row[2], row[3], row[4], row[5], row[6]
                    deleted = deleted_files or ""
                    self.history_txt.insert(
                        "end",
                        f"[{scanned_at}] Scan Type: {scan_type.upper()} | Target: {target_path} | Status: {status} | Deleted: {deleted_count} | Files: {deleted}\n",
                    )
        except Exception as exc:
            if getattr(self, "history_txt", None):
                self.history_txt.insert("end", f"[History Load Error]: {exc}\n")

    # -------------------------------------------------------------
    # Navigation & Layout
    # -------------------------------------------------------------
    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0, fg_color=self.SIDEBAR_BG
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(fill="x", padx=15, pady=(20, 25))

        ctk.CTkLabel(
            brand_frame,
            text="🩺 LapDoctor",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.TEXT_COLOR,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            brand_frame,
            text="Smart System Health Assistant",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            anchor="w",
        ).pack(fill="x")

        self.nav_btns = {}
        nav_items = [
            ("dashboard", "🩺  Dashboard"),
            ("ai_assistant", "🤖  AI Assistant"),
            ("scan", "🔍  Storage Scan"),
            ("history", "📜  Scan History"),
            ("settings", "⚙️  Settings"),
        ]

        for page_id, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                fg_color="transparent",
                text_color=self.TEXT_MUTED,
                hover_color="#27272A",
                height=40,
                command=lambda p=page_id: self.show_page(p),
            )
            btn.pack(fill="x", padx=10, pady=4)
            self.nav_btns[page_id] = btn

    def create_main_container(self):
        self.main_container = ctk.CTkFrame(
            self, corner_radius=0, fg_color=self.BG_DARK
        )
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)
        self.main_container.grid_rowconfigure(1, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.create_header_bar()

        self.pages = {}
        self.create_dashboard_page()
        self.create_ai_assistant_page()
        self.create_scan_page()
        self.create_history_page()
        self.create_settings_page()

    def create_header_bar(self):
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        self.page_title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.TEXT_COLOR,
        )
        self.page_title.pack(side="left")

        privacy_btn = ctk.CTkButton(
            header_frame,
            text="🔒 Privacy Protected",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#064E3B",
            text_color="#34D399",
            hover_color="#047857",
            height=30,
            command=self.show_privacy_modal,
        )
        privacy_btn.pack(side="right")

    def show_page(self, page_id):
        for pid, frame in self.pages.items():
            frame.grid_forget()
            self.nav_btns[pid].configure(
                fg_color="transparent", text_color=self.TEXT_MUTED
            )

        self.pages[page_id].grid(row=1, column=0, sticky="nsew")
        self.nav_btns[page_id].configure(
            fg_color="#27272A", text_color=self.PRIMARY_ACCENT
        )

        if page_id == "history":
            self.refresh_history_page()

        titles = {
            "dashboard": "System Health Dashboard",
            "ai_assistant": "Real-Time AI Assistant",
            "scan": "Storage Scanner & Analysis",
            "history": "Scan & Activity History",
            "settings": "System Settings",
        }
        self.page_title.configure(text=titles.get(page_id, "LapDoctor"))

    # -------------------------------------------------------------
    # Dashboard Implementation
    # -------------------------------------------------------------
    def create_dashboard_page(self):
        page = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self.pages["dashboard"] = page
        page.grid_columnconfigure((0, 1), weight=1)

        health_card = ctk.CTkFrame(page, fg_color=self.CARD_BG, corner_radius=12)
        health_card.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        ctk.CTkLabel(
            health_card,
            text="System Health Status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=20, pady=(15, 0))

        self.health_score_lbl = ctk.CTkLabel(
            health_card,
            text="-- / 100",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.health_score_lbl.pack(anchor="w", padx=20)

        self.health_status_badge = ctk.CTkLabel(
            health_card,
            text="CALCULATING...",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.health_status_badge.pack(anchor="w", padx=20, pady=(0, 15))

        stats_frame = ctk.CTkFrame(page, fg_color="transparent")
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=0, pady=10)
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_widgets = {}
        metrics = [
            ("CPU", "cpu", "18%"),
            ("RAM", "ram", "62%"),
            ("Disk Activity", "disk", "4%"),
            ("Storage Usage", "storage", "68%"),
        ]

        for idx, (label, key, default_val) in enumerate(metrics):
            card = ctk.CTkFrame(stats_frame, fg_color=self.CARD_BG, corner_radius=10)
            card.grid(row=0, column=idx, sticky="ew", padx=5, pady=5)

            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=self.TEXT_MUTED,
            ).pack(anchor="w", padx=12, pady=(10, 2))

            val_lbl = ctk.CTkLabel(
                card,
                text=default_val,
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=self.TEXT_COLOR,
            )
            val_lbl.pack(anchor="w", padx=12, pady=(0, 10))
            self.stat_widgets[key] = val_lbl

        # Storage Analysis Card
        rec_card = ctk.CTkFrame(page, fg_color=self.CARD_BG, corner_radius=12)
        rec_card.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=10)

        ctk.CTkLabel(
            rec_card,
            text="💡 Storage Analysis Summary",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.PRIMARY_ACCENT,
        ).pack(anchor="w", padx=20, pady=(15, 5))

        self.reclaim_txt = ctk.CTkLabel(
            rec_card,
            text="Run a scan to analyze why your storage is full.",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#F59E0B",
        )
        self.reclaim_txt.pack(anchor="w", padx=20, pady=(0, 10))

        btn_review = ctk.CTkButton(
            rec_card,
            text="Start Scan & Deep Analysis",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            command=lambda: self.show_page("scan"),
        )
        btn_review.pack(anchor="w", padx=20, pady=(0, 20))

    # -------------------------------------------------------------
    # Real-Time AI Assistant Implementation
    # -------------------------------------------------------------
    def create_ai_assistant_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["ai_assistant"] = page
        page.grid_rowconfigure(1, weight=1)
        page.grid_columnconfigure(0, weight=1)

        ai_header = ctk.CTkFrame(page, fg_color=self.CARD_BG, corner_radius=10)
        ai_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            ai_header,
            text="🤖 LapDoctor AI Diagnosis & Assistant",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.PRIMARY_ACCENT,
        ).pack(side="left", padx=15, pady=10)

        chips_frame = ctk.CTkFrame(ai_header, fg_color="transparent")
        chips_frame.pack(side="right", padx=10)

        quick_prompts = [
            ("⚡ High RAM Query", "Why is my RAM usage high?"),
            ("🐢 Laptop Slow", "Why is my laptop slow?"),
            ("🧹 Storage Reasons", "Why is my storage full?"),
        ]

        for label, query_text in quick_prompts:
            btn = ctk.CTkButton(
                chips_frame,
                text=label,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#27272A",
                text_color=self.TEXT_COLOR,
                hover_color="#3F3F46",
                height=26,
                command=lambda q=query_text: self.send_ai_query(q),
            )
            btn.pack(side="left", padx=4)

        self.chat_frame = ctk.CTkScrollableFrame(page, fg_color=self.CARD_BG)
        self.chat_frame.grid(row=1, column=0, sticky="nsew")

        input_frame = ctk.CTkFrame(page, fg_color="transparent")
        input_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.ai_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Ask AI: 'Why is my laptop slow?', 'How to free RAM?', 'Why storage is full?'...",
            font=ctk.CTkFont(size=13),
            height=40,
        )
        self.ai_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.ai_entry.bind("<Return>", lambda event: self.send_ai_query())

        send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            width=90,
            height=40,
            command=self.send_ai_query,
        )
        send_btn.pack(side="right")

        self.add_chat_message(
            "AI Assistant",
            "Hello! I am your LapDoctor AI. Ask me anything like 'Why is my laptop slow?', 'Why is my RAM high?', or 'Why is my storage full?'",
            is_user=False,
        )

    def send_ai_query(self, preset_query=None):
        query = preset_query or self.ai_entry.get().strip()
        if not query:
            return

        if not preset_query:
            self.ai_entry.delete(0, "end")

        self.add_chat_message("You", query, is_user=True)
        threading.Thread(
            target=self.generate_ai_response, args=(query,), daemon=True
        ).start()

    def add_chat_message(self, sender, text, is_user=False):
        bubble_bg = "#27272A" if is_user else "#18181B"
        border_col = self.PRIMARY_ACCENT if not is_user else "#52525B"

        msg_card = ctk.CTkFrame(
            self.chat_frame,
            fg_color=bubble_bg,
            border_width=1,
            border_color=border_col,
            corner_radius=10,
        )
        msg_card.pack(
            fill="x",
            padx=10,
            pady=6,
            anchor="e" if is_user else "w",
        )

        header = ctk.CTkLabel(
            msg_card,
            text=sender,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.PRIMARY_ACCENT if not is_user else "#A1A1AA",
        )
        header.pack(anchor="w", padx=12, pady=(8, 2))

        body = ctk.CTkLabel(
            msg_card,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=self.TEXT_COLOR,
            justify="left",
            wraplength=680,
        )
        body.pack(anchor="w", padx=12, pady=(0, 8))

    def generate_ai_response(self, query):
        time.sleep(0.3)
        q = query.lower().strip()

        cpu_val = self.live_stats.get("cpu", 18)
        ram_val = self.live_stats.get("ram", 62)
        disk_val = self.live_stats.get("disk", 4)

        # --- INTENT GUARDRAIL ---
        # List of allowed tech keywords
        tech_keywords = [
            "slow", "lag", "hang", "speed", "laptop", "pc", "computer", "lap",
            "ram", "memory", "storage", "disk", "full", "space", "scan",
            "clean", "temp", "heat", "fan", "cpu", "hi", "hello", "hey", "help",
            "greetings", "vanakkam"
        ]
        
        is_valid_tech_query = any(keyword in q for keyword in tech_keywords)

        if not is_valid_tech_query:
            response = (
                "⚠️ **Invalid Question**: I am LapDoctor AI, specialized strictly in laptop health and diagnostics.\n\n"
                "Please ask me about **slowness, RAM usage, disk storage, CPU load, or thermal issues**!"
            )
        else:
            # 1. Greetings
            if any(w in q for w in ["hi", "hello", "hey", "greetings", "vanakkam"]):
                response = (
                    f"👋 **Hello! How can I assist you with your laptop today?**\n\n"
                    f"📊 **Live System Snapshot**:\n"
                    f"• CPU Load: {cpu_val}%\n"
                    f"• RAM Usage: {ram_val}%\n"
                    f"• Disk Activity: {disk_val}%\n\n"
                    f"You can ask me questions like:\n"
                    f"• \"Why is my laptop slow?\"\n"
                    f"• \"Why is my RAM usage high?\"\n"
                    f"• \"Why is my storage full?\""
                )

            # 2. Slowness / Lag / Performance Queries
            elif any(w in q for w in ["slow", "lag", "hang", "freeze", "performance", "speed", "lap", "laptop"]):
                reasons = []
                if ram_val > 70:
                    reasons.append(f"• **High RAM Usage ({ram_val}%)**: Browser tabs or background apps are taking up heavy memory.")
                if cpu_val > 60:
                    reasons.append(f"• **High CPU Load ({cpu_val}%)**: Background processes are consuming processing power.")
                
                if not reasons:
                    reasons.append(f"• **CPU ({cpu_val}%) and RAM ({ram_val}%) are stable**, but disk fragmentation, startup programs, or accumulated junk files are delaying file reads.")

                reasons_str = "\n".join(reasons)

                response = (
                    f"🐢 **Laptop Slowness Diagnostic**:\n\n"
                    f"**Current Findings**:\n{reasons_str}\n\n"
                    f"🛠️ **Recommended Steps to Fix**:\n"
                    f"1. **Clear Storage Junk**: Go to **Storage Scan** and run a scan to free cache & duplicates.\n"
                    f"2. **Disable Startup Apps**: Press `Ctrl + Shift + Esc` -> Startup Apps -> Disable unnecessary apps.\n"
                    f"3. **Check Thermal Vents**: Ensure fans are clean to avoid CPU thermal throttling."
                )

            # 3. Storage / Disk Full Queries
            elif any(w in q for w in ["full", "storage", "disk", "space", "clean", "junk"]):
                if not self.analysis_summary["reasons"]:
                    response = (
                        "💾 **Storage Diagnostics**:\n\n"
                        "No scan data available yet. Please open the **Storage Scan** tab and run a scan first!\n"
                        "Once completed, I will analyze the exact reasons (large files, duplicates, cache) and recommend safe items to clean with your explicit permission."
                    )
                else:
                    reasons_str = "\n".join([f"• {r}" for r in self.analysis_summary["reasons"]])
                    response = (
                        f"🔍 **Storage Analysis Results**:\n\n"
                        f"{reasons_str}\n\n"
                        f"💡 **Recommended Action**:\n"
                        f"Go to **Storage Scan -> Recommended Files**, review the safe items, and click **'Approve & Clean Selected Files'**."
                    )

            # 4. High RAM / Memory Queries
            elif any(w in q for w in ["ram", "memory"]):
                response = (
                    f"⚡ **RAM Analysis (Current Usage: {ram_val}%)**:\n\n"
                    f"• Web browsers (Chrome/Edge) with multiple tabs consume significant RAM.\n"
                    f"• Active background services stay loaded in memory.\n\n"
                    f"💡 **Optimization Tips**:\n"
                    f"1. Close inactive browser tabs.\n"
                    f"2. Go to **Storage Scan -> App Caches** to clear application caches."
                )

            # 5. Heating / Fan Queries
            elif any(w in q for w in ["heat", "hot", "fan", "temp", "thermal"]):
                response = (
                    f"🔥 **Thermal & Temperature Diagnostic**:\n\n"
                    f"Current CPU Load: {cpu_val}%\n"
                    f"• High CPU load generates heat, triggering cooling fans.\n"
                    f"• Ensure laptop vents are elevated and not blocked by soft surfaces."
                )

            # 6. Fallback Catch-All (For valid tech queries that don't match exactly)
            else:
                response = (
                    f"🤖 **LapDoctor Diagnostic Engine**:\n\n"
                    f"I processed your query: *\"{query}\"*\n\n"
                    f"📊 Current Metrics: CPU: {cpu_val}% | RAM: {ram_val}% | Disk: {disk_val}%\n\n"
                    f"Try asking:\n"
                    f"• \"Why is my laptop slow?\"\n"
                    f"• \"Why is RAM high?\"\n"
                    f"• \"Why is my storage full?\""
                )

        self.after(0, lambda: self.add_chat_message("AI Assistant", response, is_user=False))

    # -------------------------------------------------------------
    # Storage Scanner & Recommended Files Page
    # -------------------------------------------------------------
    def create_scan_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.pages["scan"] = page
        page.grid_rowconfigure(2, weight=1)
        page.grid_columnconfigure(0, weight=1)

        ctrl_card = ctk.CTkFrame(page, fg_color=self.CARD_BG, corner_radius=10)
        ctrl_card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        path_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(
            path_frame,
            text="Target Path:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Select Directory...")
        self.path_entry.insert(0, os.path.expanduser(r"~\Downloads"))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        browse_btn = ctk.CTkButton(
            path_frame, text="Browse", width=80, fg_color="#27272A", command=self.browse_folder
        )
        browse_btn.pack(side="right")

        mode_frame = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        mode_frame.pack(fill="x", padx=15, pady=(0, 12))

        self.scan_type = ctk.StringVar(value="duplicates")
        modes = [
            ("Duplicates", "duplicates"),
            ("Large Files (>50MB)", "large"),
            ("Old Files", "old"),
            ("App Caches", "apps"),
        ]

        for text, m_id in modes:
            rb = ctk.CTkRadioButton(
                mode_frame,
                text=text,
                value=m_id,
                variable=self.scan_type,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color=self.PRIMARY_ACCENT,
            )
            rb.pack(side="left", padx=(0, 15))

        self.scan_btn = ctk.CTkButton(
            mode_frame,
            text="START SCAN & ANALYZE",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            command=self.toggle_scan,
        )
        self.scan_btn.pack(side="right")

        self.analysis_card = ctk.CTkFrame(page, fg_color=self.CARD_BG, corner_radius=10)
        self.analysis_card.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.analysis_title = ctk.CTkLabel(
            self.analysis_card,
            text="🔍 Storage Analysis: Awaiting Scan...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.PRIMARY_ACCENT,
        )
        self.analysis_title.pack(anchor="w", padx=15, pady=10)

        self.scan_status = ctk.CTkLabel(
            self.analysis_card,
            text="Idle",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.scan_status.pack(anchor="w", padx=15, pady=(0, 4))

        self.scan_progress_bar = ctk.CTkProgressBar(
            self.analysis_card,
            width=280,
            height=12,
            mode="determinate",
            progress_color="#29f281",
        )
        self.scan_progress_bar.set(0)
        self.scan_progress_bar.pack(anchor="w", padx=15, pady=(0, 4))

        self.scan_progress_label = ctk.CTkLabel(
            self.analysis_card,
            text="Scan progress: 0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.scan_progress_label.pack(anchor="w", padx=15, pady=(0, 12))

        self.tabview = ctk.CTkTabview(
            page, segmented_button_selected_color=self.PRIMARY_ACCENT
        )
        self.tabview.grid(row=2, column=0, sticky="nsew")

        self.tab_files = self.tabview.add("Recommended Files to Clean (User Approval Required)")
        self.tab_console = self.tabview.add("Scan Log Console")

        self.tab_files.grid_rowconfigure(1, weight=1)
        self.tab_files.grid_columnconfigure(0, weight=1)

        action_bar = ctk.CTkFrame(self.tab_files, fg_color="transparent")
        action_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ctk.CTkButton(
            action_bar, text="Select All Safe", width=110, fg_color="#27272A", command=self.select_all
        ).pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            action_bar, text="Deselect All", width=90, fg_color="#27272A", command=self.deselect_all
        ).pack(side="left")

        self.clean_btn = ctk.CTkButton(
            action_bar,
            text="⚠️ Approve & Clean Selected Files",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=self.run_cleanup,
        )
        self.clean_btn.pack(side="right")

        self.scroll_files = ctk.CTkScrollableFrame(self.tab_files, fg_color=self.CARD_BG)
        self.scroll_files.grid(row=1, column=0, sticky="nsew")

        self.tab_console.grid_rowconfigure(0, weight=1)
        self.tab_console.grid_columnconfigure(0, weight=1)

        self.log_text = ctk.CTkTextbox(
            self.tab_console,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=self.CARD_BG,
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")

    # -------------------------------------------------------------
    # Risk Classification & File Recommendation Generator
    # -------------------------------------------------------------
    def classify_risk(self, file_path):
        clean_p = file_path.lower()
        ext = os.path.splitext(clean_p)[1]

        if "windows" in clean_p or "system32" in clean_p or ext in [".dll", ".sys", ".ini", ".dat"]:
            return "🔴 DO NOT REMOVE (System File)", "#EF4444", False

        elif ext in [".tmp", ".log", ".chk", ".old", ".dmp", ".bak"]:
            return "🟢 SAFE TO CLEAN", "#22C55E", True

        else:
            return "🟡 REVIEW BEFORE DELETE", "#F59E0B", False

    def add_file_item(self, file_path):
        clean_path = os.path.normpath(file_path.strip())
        file_name = os.path.basename(clean_path) or clean_path

        risk_label, risk_color, is_safe = self.classify_risk(clean_path)

        try:
            sz_mb = os.path.getsize(clean_path) / (1024 * 1024) if os.path.exists(clean_path) else 0.0
        except Exception:
            sz_mb = 0.0

        item_frame = ctk.CTkFrame(self.scroll_files, fg_color="#18181B")
        item_frame.pack(fill="x", padx=5, pady=4)

        var = ctk.BooleanVar(value=is_safe)

        chk = ctk.CTkCheckBox(
            item_frame,
            text=f"{file_name} ({sz_mb:.1f} MB)",
            variable=var,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.TEXT_COLOR,
            fg_color=self.PRIMARY_ACCENT,
        )
        chk.pack(side="left", padx=(10, 5), pady=8)

        badge = ctk.CTkLabel(
            item_frame,
            text=risk_label,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=risk_color,
        )
        badge.pack(side="left", padx=10)

        path_label = ctk.CTkLabel(
            item_frame,
            text=f"({clean_path})",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
        )
        path_label.pack(side="left", padx=(0, 10))

        self.detected_items.append(
            {"path": clean_path, "var": var, "frame": item_frame, "size": sz_mb, "safe": is_safe}
        )

    # -------------------------------------------------------------
    # Post-Scan Storage Analysis Logic
    # -------------------------------------------------------------
    def analyze_storage_reasons(self, found_paths):
        reasons = []
        total_safe_bytes = 0
        mode = self.scan_type.get()
        selected_count = len(found_paths)

        if mode == "duplicates":
            reasons.append(f"Found {selected_count} file items in the duplicate scan scope.")
        elif mode == "large":
            reasons.append(f"Found {selected_count} large-file candidates in the selected path.")
        elif mode == "old":
            reasons.append(f"Found {selected_count} stale-file candidates in the selected path.")
        elif mode == "apps":
            reasons.append(f"Found {selected_count} cache/app-location entries in the system cache scope.")

        if not reasons:
            reasons.append("Storage is healthy with minimal removable junk in this directory.")

        for item in self.detected_items:
            if item["safe"]:
                total_safe_bytes += item["size"]

        self.analysis_summary["reasons"] = reasons
        self.analysis_summary["total_safe_size"] = total_safe_bytes

        summary_msg = f"🔍 Storage Analysis: Found {selected_count} total files. Reasons: " + " | ".join(reasons)
        self.analysis_title.configure(text=summary_msg)

        # Reflect the same real result on the Dashboard card, which previously
        # kept showing its static "Run a scan..." placeholder forever.
        if hasattr(self, "reclaim_txt"):
            if selected_count > 0:
                mb = total_safe_bytes
                dash_msg = (
                    f"{selected_count} items found ({mode} scan) — "
                    f"~{mb:.1f} MB safely reclaimable. Review in Storage Scan."
                )
                self.reclaim_txt.configure(text=dash_msg, text_color="#F59E0B")
            else:
                self.reclaim_txt.configure(
                    text=f"Last {mode} scan found nothing to clean. Storage looks healthy.",
                    text_color="#22C55E",
                )

    # -------------------------------------------------------------
    # History & Settings Pages
    # -------------------------------------------------------------
    def create_history_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color=self.CARD_BG)
        self.pages["history"] = page
        page.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            page,
            text="Scan & Cleanup History Log",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=15)

        summary = ctk.CTkFrame(page, fg_color="#20202A", corner_radius=10)
        summary.pack(fill="x", padx=20, pady=(0, 12))

        self.last_scan_label = ctk.CTkLabel(
            summary,
            text="Last scanned: none",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.TEXT_COLOR,
        )
        self.last_scan_label.pack(anchor="w", padx=15, pady=(10, 3))

        self.last_deleted_label = ctk.CTkLabel(
            summary,
            text="Last deleted: none",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.TEXT_COLOR,
        )
        self.last_deleted_label.pack(anchor="w", padx=15, pady=(3, 10))

        self.history_txt = ctk.CTkTextbox(
            page,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#121214",
        )
        self.history_txt.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.history_txt.insert(
            "end", "[System Initialized]: Waiting for user-approved cleanup tasks.\n"
        )

    def create_settings_page(self):
        page = ctk.CTkFrame(self.main_container, fg_color=self.CARD_BG)
        self.pages["settings"] = page

        ctk.CTkLabel(
            page, text="Preferences", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=15)

        theme_frame = ctk.CTkFrame(page, fg_color="transparent")
        theme_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            theme_frame,
            text="Appearance Theme Mode:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(side="left", padx=(0, 10))

        theme_menu = ctk.CTkOptionMenu(
            theme_frame,
            values=["Dark", "Light"],
            command=self.apply_theme,
            fg_color="#27272A",
            button_color="#3F3F46",
        )
        theme_menu.set(self.current_theme)
        theme_menu.pack(side="left")
        self.theme_menu = theme_menu

        self.theme_status_lbl = ctk.CTkLabel(
            theme_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
        )
        self.theme_status_lbl.pack(side="left", padx=(12, 0))

        exclude_frame = ctk.CTkFrame(page, fg_color="transparent")
        exclude_frame.pack(fill="x", padx=20, pady=10)

        self.skip_system_dirs_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            exclude_frame,
            text="Exclude Windows / Program Files / recycle bin from scans (recommended)",
            variable=self.skip_system_dirs_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.PRIMARY_ACCENT,
        ).pack(anchor="w")

        ctk.CTkLabel(
            exclude_frame,
            text="Keeps scans of broad paths (e.g. a whole drive) fast and responsive by\nskipping locked/system-owned folders that rarely contain real duplicates or junk.",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

    # -------------------------------------------------------------
    # Theme Engine
    # -------------------------------------------------------------
    def apply_theme(self, mode):
        """Actually applies the selected theme.

        Rather than requiring every widget-creation call site to be rewritten,
        this walks the live widget tree and swaps any color that matches the
        *previous* palette for its equivalent tone in the *new* palette. Status
        colors (red/green/amber badges) and the brand accent are intentionally
        left untouched, so the layout/design stays exactly the same -- only the
        light/dark surface & text tones change.
        """
        if mode not in self.PALETTES or mode == self.current_theme:
            return

        old_palette = self.PALETTES[self.current_theme]
        new_palette = self.PALETTES[mode]
        color_map = {
            old_palette[key]: new_palette[key]
            for key in old_palette
            if old_palette[key] != new_palette[key]
        }

        self.current_theme = mode
        ctk.set_appearance_mode(mode)

        self.BG_DARK = new_palette["bg"]
        self.CARD_BG = new_palette["card"]
        self.SIDEBAR_BG = new_palette["sidebar"]
        self.TEXT_COLOR = new_palette["text"]
        self.TEXT_MUTED = new_palette["muted"]

        self._retheme_widget(self, color_map)
        self.configure(fg_color=self.BG_DARK)

        if hasattr(self, "theme_status_lbl"):
            self.theme_status_lbl.configure(text=f"✓ {mode} theme applied")
        if hasattr(self, "log"):
            self.log(f"[Settings]: Appearance theme switched to {mode}.")

    def _retheme_widget(self, widget, color_map):
        for attr in ("fg_color", "text_color", "border_color", "button_color",
                     "segmented_button_fg_color", "segmented_button_unselected_color"):
            try:
                current = widget.cget(attr)
            except Exception:
                continue
            if isinstance(current, str) and current in color_map:
                try:
                    widget.configure(**{attr: color_map[current]})
                except Exception:
                    pass

        try:
            children = widget.winfo_children()
        except Exception:
            children = []
        for child in children:
            self._retheme_widget(child, color_map)

    def show_privacy_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Privacy Status")
        modal.geometry("420x280")
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text="🔒 Privacy Protection Guarantees",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#34D399",
        ).pack(anchor="w", padx=20, pady=(20, 10))

        points = [
            "✓ Files analyzed 100% locally on your machine",
            "✓ Zero automatic deletions without your explicit permission",
            "✓ No personal file contents stored or logged",
            "✓ Local SHA-256 duplicate verification",
        ]

        for pt in points:
            ctk.CTkLabel(
                modal, text=pt, font=ctk.CTkFont(size=12), text_color=self.TEXT_COLOR
            ).pack(anchor="w", padx=25, pady=3)

        ctk.CTkButton(
            modal, text="Close", fg_color="#27272A", command=modal.destroy
        ).pack(pady=15)

    # -------------------------------------------------------------
    # Helper & Scanner Functions
    # -------------------------------------------------------------
    def browse_folder(self):
        selected = filedialog.askdirectory()
        if selected:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected)

    def update_system_stats(self):
        while self.monitoring:
            try:
                if self.system_monitor and hasattr(self.system_monitor, "get_stats"):
                    stats = self.system_monitor.get_stats()
                    self.live_stats["cpu"] = stats.get("cpu", 0)
                    self.live_stats["ram"] = stats.get("ram_pct", 0)
                    self.live_stats["disk"] = stats.get("disk_pct", 0)
                    self.live_stats["storage"] = stats.get("storage_pct", 0)

                self.after(
                    0,
                    lambda: self._refresh_stats_ui(
                        f"{self.live_stats['cpu']}%",
                        f"{self.live_stats['ram']}%",
                        f"{self.live_stats['disk']}%",
                        f"{self.live_stats['storage']}%",
                    ),
                )
            except Exception:
                pass
            time.sleep(2)

    def _refresh_stats_ui(self, cpu, ram, disk, storage):
        self.stat_widgets["cpu"].configure(text=cpu)
        self.stat_widgets["ram"].configure(text=ram)
        self.stat_widgets["disk"].configure(text=disk)
        self.stat_widgets["storage"].configure(text=storage)
        self._update_health_score()

    def _update_health_score(self):
        """Derives a live health score from real CPU/RAM/disk/storage load
        instead of the fixed '82/100' placeholder that never changed."""
        cpu = self.live_stats.get("cpu", 0)
        ram = self.live_stats.get("ram", 0)
        storage = self.live_stats.get("storage", 0)

        # Weighted penalty model: storage pressure and RAM pressure hurt the
        # score more than a momentary CPU spike, since they affect the whole
        # system persistently rather than just the current instant.
        penalty = (cpu * 0.25) + (ram * 0.35) + (storage * 0.40)
        score = max(0, min(100, round(100 - penalty)))

        if score >= 80:
            color, label = "#22C55E", "HEALTHY"
        elif score >= 55:
            color, label = "#F59E0B", "NEEDS ATTENTION"
        else:
            color, label = "#EF4444", "CRITICAL"

        if hasattr(self, "health_score_lbl"):
            self.health_score_lbl.configure(text=f"{score} / 100", text_color=color)
        if hasattr(self, "health_status_badge"):
            self.health_status_badge.configure(text=label, text_color=color)

    def select_all(self):
        for item in self.detected_items:
            if item["safe"]:
                item["var"].set(True)

    def deselect_all(self):
        for item in self.detected_items:
            item["var"].set(False)

    def log(self, message):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _set_scan_progress_ui(self, value):
        self.scan_progress = max(0, min(100, int(value)))
        self.scan_progress_bar.set(self.scan_progress / 100.0)
        self.scan_progress_label.configure(text=f"Scan progress: {self.scan_progress}%")

    def _on_scan_progress(self, stage, done, total):
        """Real progress callback wired into core scanners (replaces the old
        fake time-based animation with the scanner's actual work)."""
        stage_labels = {
            "discover": "Discovering files",
            "prefilter": "Pre-filtering candidates",
            "hash": "Verifying duplicates",
        }
        if total:
            pct = max(0, min(99, int((done / total) * 100)))
        else:
            # Unbounded discovery stage: creep forward so the bar still shows
            # activity without pretending to know an exact percentage.
            pct = max(0, min(60, self.scan_progress + 1))

        self.scan_progress = pct
        label = stage_labels.get(stage, stage)
        detail = f"{label}: {done}" + (f" / {total}" if total else " files scanned")
        self.after(0, lambda: self._set_scan_progress_ui(self.scan_progress))
        self.after(0, lambda: self.scan_status.configure(text=detail))

    def toggle_scan(self):
        if not self.is_scanning:
            self.start_scan()
        else:
            self.stop_requested = True
            self.scan_stop_event.set()
            self.scan_status.configure(text="Stopping scan...")
            self.log("[User Action]: Stop requested. The running scan is being interrupted.")

    def start_scan(self):
        target_path = self.path_entry.get().strip()
        if not target_path:
            messagebox.showerror("Error", "Please select a valid folder path to scan!")
            return
        if not os.path.exists(target_path):
            messagebox.showerror("Error", "Selected path does not exist!")
            return

        self.is_scanning = True
        self.stop_requested = False
        self.scan_progress = 0
        self.scan_stop_event = threading.Event()
        self.scan_btn.configure(
            text="STOP SCAN", fg_color="#EF4444", hover_color="#DC2626"
        )
        self.scan_status.configure(text="Scanning now...")
        self._set_scan_progress_ui(0)

        for item in self.detected_items:
            item["frame"].destroy()
        self.detected_items.clear()

        self.log(
            f"=== Starting [{self.scan_type.get().upper()}] Scan on: {target_path} ==="
        )
        self.record_scan(self.scan_type.get(), target_path, "in_progress")
        self.run_scanner_thread(target_path)

    def run_scanner_thread(self, target_path):
        """Compatibility worker launcher for the requested UI contract."""
        threading.Thread(target=self.execute_scan, args=(target_path,), daemon=True).start()

    def execute_scan(self, path):
        mode = self.scan_type.get()
        raw_output = ""
        found_paths = []
        skip_system_dirs = getattr(self, "skip_system_dirs_var", None)
        skip_system_dirs = skip_system_dirs.get() if skip_system_dirs else True

        try:
            if mode == "duplicates" and self.duplicate:
                raw_output = str(self.duplicate.scan(
                    path, stop_event=self.scan_stop_event,
                    progress_cb=self._on_scan_progress, skip_system_dirs=skip_system_dirs,
                ))
            elif mode == "large" and self.large_files:
                raw_output = str(self.large_files.scan(
                    path, stop_event=self.scan_stop_event,
                    progress_cb=self._on_scan_progress, skip_system_dirs=skip_system_dirs,
                ))
            elif mode == "old" and self.old_files:
                raw_output = str(self.old_files.scan(
                    path, stop_event=self.scan_stop_event,
                    progress_cb=self._on_scan_progress, skip_system_dirs=skip_system_dirs,
                ))
            elif mode == "apps" and self.app_analyzer:
                raw_output = str(self.app_analyzer.scan(
                    path, stop_event=self.scan_stop_event,
                    progress_cb=self._on_scan_progress, skip_system_dirs=skip_system_dirs,
                ))

            if not self.stop_requested:
                self.log(self._summary_from_output(mode, raw_output, path))
                found_paths = self._extract_scan_paths(raw_output)
            else:
                self.log(f"[Scan Interrupted] {mode} scan stopped on: {path}")

        except Exception as e:
            self.log(f"[Scan Error]: {str(e)}")
        finally:
            self.is_scanning = False
            self.scan_stop_event.clear()
            self.after(0, lambda: self.finish_scan(list(set(found_paths))))

    def _extract_scan_paths(self, raw_output):
        output = str(raw_output or "")
        found_paths = []
        pattern = r"[a-zA-Z]:[\\/][^\n\r\"'|]+"
        matches = re.findall(pattern, output)
        for m in matches:
            p = os.path.normpath(m.split(" [LOCKED:")[0].split(" [")[0].strip())
            if os.path.exists(p):
                found_paths.append(p)
        return found_paths

    def _summary_from_output(self, mode, raw_output, path):
        output = str(raw_output).strip()
        if not output:
            return f"[{mode.upper()}] Scan completed for {path} with no report rows."

        first_line = output.splitlines()[0]
        lower = output.lower()
        if "found" in lower:
            summary = []
            for line in output.splitlines():
                if line.strip().startswith("Found ") or line.strip().startswith("Total ") or "No " in line:
                    summary.append(line.strip())
                elif "Total" in line:
                    summary.append(line.strip())
            return f"[{mode.upper()}] Scan summary for {path}: " + " | ".join(summary[:3])

        return f"[{mode.upper()}] Scan completed for {path}: {first_line}"

    def finish_scan(self, paths):
        scan_mode = self.scan_type.get()
        was_stopped = self.stop_requested
        self.stop_requested = False
        self.scan_stop_event.clear()

        self.scan_btn.configure(
            text="START SCAN & ANALYZE",
            fg_color=self.PRIMARY_ACCENT,
            hover_color="#0284C7",
        )
        self.scan_status.configure(text="Done" if not was_stopped else "Stopped")
        self.scan_progress = 100 if not was_stopped else max(0, min(100, self.scan_progress))
        self._set_scan_progress_ui(self.scan_progress)

        if was_stopped:
            self.log("\n=== Scan Stopped by User ===")
            self.record_scan(scan_mode, self.path_entry.get().strip(), "stopped")
        else:
            self.record_scan(scan_mode, self.path_entry.get().strip(), "completed")

        for p in paths:
            self.add_file_item(p)

        self.analyze_storage_reasons(paths)
        self.log("\n=== Scan & Analysis Completed ===")
        self.tabview.set("Recommended Files to Clean (User Approval Required)")
        self.refresh_history_page()

    def run_cleanup(self):
        selected_files = [
            item["path"] for item in self.detected_items if item["var"].get()
        ]

        if not selected_files:
            messagebox.showinfo("Cleanup Info", "No files were selected for removal.")
            return

        permission_granted = messagebox.askyesno(
            "User Permission Required",
            f"You are about to move {len(selected_files)} items to the Recycle Bin.\n\nDo you grant permission to clean these files?",
            icon="warning"
        )

        if permission_granted:
            try:
                if self.cleanup and hasattr(self.cleanup, "execute"):
                    res = self.cleanup.execute(selected_files)
                    self.log(str(res))
                    deleted_count = len(selected_files)
                    deleted_size_mb = sum(os.path.getsize(p) if os.path.exists(p) else 0 for p in selected_files) / (1024*1024)
                    self.record_scan(
                        self.scan_type.get(),
                        self.path_entry.get().strip(),
                        "deleted",
                        deleted_files=selected_files,
                        deleted_count=deleted_count,
                        deleted_size_mb=deleted_size_mb,
                        note="cleanup-approved",
                    )
                    self.history_txt.insert(
                        "end",
                        f"[{time.strftime('%Y-%m-%d %H:%M')}] User Approved Deletion: {len(selected_files)} items cleaned.\n",
                    )

                remaining = []
                for item in self.detected_items:
                    if item["var"].get() and not os.path.exists(item["path"]):
                        item["frame"].destroy()
                    else:
                        remaining.append(item)
                self.detected_items = remaining
                self.refresh_history_page()
                messagebox.showinfo("Success", "Selected files cleaned safely!")
            except Exception as e:
                self.log(f"[Cleanup Error]: {str(e)}")


if __name__ == "__main__":
    app = LapdoctorGUI()
    app.mainloop()