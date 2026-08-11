import os
import re
import io
import time
import platform
import threading
import contextlib
from turtle import title
import customtkinter as ctk
import psutil

from tkinter import filedialog, messagebox


# ============================================================
# CUSTOMTKINTER DEFAULT SETTINGS
# ============================================================

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# ============================================================
# LAPDOCTOR GUI
# ============================================================

class LapdoctorGUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        # --------------------------------------------------------
        # WINDOW
        # --------------------------------------------------------
        self.title("LapDoctor - Smart System Health Assistant")
        self.geometry("1250x800")
        self.minsize(1100, 700)

        # --------------------------------------------------------
        # COLOR PALETTE
        # --------------------------------------------------------
        self.BG_DARK = "#121214"
        self.CARD_BG = "#1E1E22"
        self.SIDEBAR_BG = "#18181B"

        self.PRIMARY_ACCENT = "#38BDF8"

        self.TEXT_COLOR = "#F4F4F5"
        self.TEXT_MUTED = "#A1A1AA"

        self.SUCCESS = "#22C55E"
        self.WARNING = "#F59E0B"
        self.DANGER = "#EF4444"

        self.configure(fg_color=self.BG_DARK)

        # --------------------------------------------------------
        # APPLICATION STATE
        # --------------------------------------------------------
        self.is_scanning = False
        self.stop_requested = False

        self.detected_items = []
        self.scan_history = []
        self.analysis_summary = {
            "reasons": [],
            "total_safe_size": 0
        }

        self.live_stats = {
            "cpu": 0,
            "ram": 0,
            "disk": 0,
            "storage": 0,
            "health": 100
        }

        self.monitoring = True
        self.history_records = []
        self._last_smart_alert_ts = 0.0
        self.scan_logs = {"duplicates": "", "large": "", "old": "", "apps": ""}
        self.ai_chat_history = []
        

        # --------------------------------------------------------
        # GRID
        # --------------------------------------------------------
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --------------------------------------------------------
        # BUILD UI
        # --------------------------------------------------------
        self.create_sidebar()
        self.create_main_container()

        # --------------------------------------------------------
        # LOAD BACKEND MODULES
        # --------------------------------------------------------
        self.load_backend_modules()

        # --------------------------------------------------------
        # SHOW DEFAULT PAGE
        # --------------------------------------------------------
        self.show_page("dashboard")

        # --------------------------------------------------------
        # HARDWARE MONITORING
        # --------------------------------------------------------
        threading.Thread(
            target=self.update_system_stats,
            daemon=True
        ).start()

        threading.Thread(
            target=self._smart_cleaning_loop,
            daemon=True
        ).start()

        # --------------------------------------------------------
        # WINDOW CLOSE HANDLER
        # --------------------------------------------------------
        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

    # ============================================================
    # BACKEND MODULES
    # ============================================================

    def load_backend_modules(self):
        try:
            from core import (
                app_analyzer,
                cleanup,
                duplicate,
                large_files,
                old_files,
                system_monitor,
                ai_assistant
            )

            self.app_analyzer = app_analyzer
            self.cleanup = cleanup
            self.duplicate = duplicate
            self.large_files = large_files
            self.old_files = old_files
            self.system_monitor = system_monitor
            self.ai_assistant = ai_assistant

        except ImportError as e:

            self.app_analyzer = None
            self.cleanup = None
            self.duplicate = None
            self.large_files = None
            self.old_files = None
            self.system_monitor = None
            self.ai_assistant = None

            print("[Backend Warning]", e)

    # ============================================================
    # SIDEBAR
    # ============================================================

    def create_sidebar(self):

        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0,
            fg_color=self.SIDEBAR_BG
        )

        self.sidebar.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # --------------------------------------------------------
        # BRAND
        # --------------------------------------------------------

        brand_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        brand_frame.pack(
            fill="x",
            padx=15,
            pady=(20, 25)
        )

        ctk.CTkLabel(
            brand_frame,
            text="⚕ LapDoctor",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            ),
            text_color=self.TEXT_COLOR,
            anchor="w"
        ).pack(
            fill="x"
        )

        ctk.CTkLabel(
            brand_frame,
            text="Smart System Health Assistant",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            anchor="w"
        ).pack(
            fill="x",
            pady=(4, 0)
        )

        # --------------------------------------------------------
        # NAVIGATION
        # --------------------------------------------------------

        self.nav_btns = {}

        nav_items = [
            ("dashboard", "⚕  Dashboard"),
            ("ai_assistant", "🤖  AI Assistant"),
            ("scan", "🔍  Storage Scan"),
            ("history", "📜  Scan History"),
            ("settings", "⚙  Settings"),
        ]

        for page_id, label in nav_items:

            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                font=ctk.CTkFont(
                    size=13,
                    weight="bold"
                ),
                fg_color="transparent",
                text_color=self.TEXT_MUTED,
                hover_color="#27272A",
                height=42,
                command=lambda p=page_id: self.show_page(p)
            )

            btn.pack(
                fill="x",
                padx=10,
                pady=4
            )

            self.nav_btns[page_id] = btn

    # ============================================================
    # MAIN CONTAINER
    # ============================================================

    def create_main_container(self):

        self.main_container = ctk.CTkFrame(
            self,
            corner_radius=0,
            fg_color=self.BG_DARK
        )

        self.main_container.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=20,
            pady=15
        )

        self.main_container.grid_rowconfigure(
            1,
            weight=1
        )

        self.main_container.grid_columnconfigure(
            0,
            weight=1
        )

        self.create_header_bar()

        self.pages = {}

        self.create_dashboard_page()
        self.create_ai_assistant_page()
        self.create_scan_page()
        self.create_history_page()
        self.create_settings_page()

    # ============================================================
    # HEADER
    # ============================================================

    def create_header_bar(self):

        header_frame = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )

        header_frame.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 15)
        )

        self.page_title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            ),
            text_color=self.TEXT_COLOR
        )

        self.page_title.pack(
            side="left"
        )

        privacy_btn = ctk.CTkButton(
            header_frame,
            text="🔒 Privacy Protected",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            fg_color="#064E3B",
            text_color="#34D399",
            hover_color="#047857",
            height=30,
            command=self.show_privacy_modal
        )

        privacy_btn.pack(
            side="right"
        )

    # ============================================================
    # PAGE NAVIGATION
    # ============================================================

    def show_page(self, page_id):

        for pid, frame in self.pages.items():

            frame.grid_forget()

            self.nav_btns[pid].configure(
                fg_color="transparent",
                text_color=self.TEXT_MUTED
            )

        self.pages[page_id].grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        self.nav_btns[page_id].configure(
            fg_color="#27272A",
            text_color=self.PRIMARY_ACCENT
        )

        titles = {
            "dashboard": "System Health Dashboard",
            "ai_assistant": "Real-Time AI Assistant",
            "scan": "Storage Scanner & Analysis",
            "history": "Scan & Activity History",
            "settings": "System Settings"
        }

        self.page_title.configure(
            text=titles.get(
                page_id,
                "LapDoctor"
            )
        )

    # ============================================================
    # DASHBOARD
    # ============================================================

    def create_dashboard_page(self):

        page = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="transparent"
        )

        self.pages["dashboard"] = page

        page.grid_columnconfigure(
            (0, 1),
            weight=1
        )

        # --------------------------------------------------------
        # HEALTH CARD
        # --------------------------------------------------------

        health_card = ctk.CTkFrame(
            page,
            fg_color=self.CARD_BG,
            corner_radius=12
        )

        health_card.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )

        ctk.CTkLabel(
            health_card,
            text="System Health Status",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=self.TEXT_MUTED
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 0)
        )

        self.health_score_lbl = ctk.CTkLabel(
            health_card,
            text="-- / 100",
            font=ctk.CTkFont(
                size=36,
                weight="bold"
            ),
            text_color=self.SUCCESS
        )

        self.health_score_lbl.pack(
            anchor="w",
            padx=20
        )

        self.health_status_badge = ctk.CTkLabel(
            health_card,
            text="CHECKING...",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color=self.SUCCESS
        )

        self.health_status_badge.pack(
            anchor="w",
            padx=20,
            pady=(0, 15)
        )

        # --------------------------------------------------------
        # SYSTEM METRICS
        # --------------------------------------------------------

        stats_frame = ctk.CTkFrame(
            page,
            fg_color="transparent"
        )

        stats_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=0,
            pady=10
        )

        stats_frame.grid_columnconfigure(
            (0, 1, 2, 3),
            weight=1
        )

        self.stat_widgets = {}

        metrics = [
            ("CPU", "cpu", "0%"),
            ("RAM", "ram", "0%"),
            ("Disk Activity", "disk", "0%"),
            ("Storage Usage", "storage", "0%")
        ]

        for idx, (label, key, default_val) in enumerate(metrics):

            card = ctk.CTkFrame(
                stats_frame,
                fg_color=self.CARD_BG,
                corner_radius=10
            )

            card.grid(
                row=0,
                column=idx,
                sticky="ew",
                padx=5,
                pady=5
            )

            ctk.CTkLabel(
                card,
                text=label,
                font=ctk.CTkFont(size=12),
                text_color=self.TEXT_MUTED
            ).pack(
                anchor="w",
                padx=12,
                pady=(10, 2)
            )

            val_lbl = ctk.CTkLabel(
                card,
                text=default_val,
                font=ctk.CTkFont(
                    size=20,
                    weight="bold"
                ),
                text_color=self.TEXT_COLOR
            )

            val_lbl.pack(
                anchor="w",
                padx=12,
                pady=(0, 10)
            )

            self.stat_widgets[key] = val_lbl

        # --------------------------------------------------------
        # STORAGE ANALYSIS
        # --------------------------------------------------------

        rec_card = ctk.CTkFrame(
            page,
            fg_color=self.CARD_BG,
            corner_radius=12
        )

        rec_card.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=10
        )

        ctk.CTkLabel(
            rec_card,
            text="💡 Storage Analysis Summary",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            ),
            text_color=self.PRIMARY_ACCENT
        ).pack(
            anchor="w",
            padx=20,
            pady=(15, 5)
        )

        self.reclaim_txt = ctk.CTkLabel(
            rec_card,
            text="Run a scan to analyze why your storage is full.",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            ),
            text_color=self.WARNING
        )

        self.reclaim_txt.pack(
            anchor="w",
            padx=20,
            pady=(0, 10)
        )

        btn_review = ctk.CTkButton(
            rec_card,
            text="Start Scan & Deep Analysis",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            ),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            command=lambda: self.show_page("scan")
        )

        btn_review.pack(
            anchor="w",
            padx=20,
            pady=(0, 20)
        )

    # ============================================================
    # AI ASSISTANT
    # ============================================================

    def create_ai_assistant_page(self):

        page = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )

        self.pages["ai_assistant"] = page

        page.grid_rowconfigure(
            1,
            weight=1
        )

        page.grid_columnconfigure(
            0,
            weight=1
        )

        ai_header = ctk.CTkFrame(
            page,
            fg_color=self.CARD_BG,
            corner_radius=10
        )

        ai_header.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        ctk.CTkLabel(
            ai_header,
            text="🤖 LapDoctor AI Diagnosis & Assistant",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=self.PRIMARY_ACCENT
        ).pack(
            side="left",
            padx=15,
            pady=10
        )

        chips_frame = ctk.CTkFrame(
            ai_header,
            fg_color="transparent"
        )

        chips_frame.pack(
            side="right",
            padx=10
        )

        quick_prompts = [
            (
                "⚡ High RAM Query",
                "Why is my RAM usage high?"
            ),
            (
                "🐢 Laptop Slow",
                "Why is my laptop slow?"
            ),
            (
                "🧹 Storage Reasons",
                "Why is my storage full?"
            )
        ]

        for label, query_text in quick_prompts:

            btn = ctk.CTkButton(
                chips_frame,
                text=label,
                font=ctk.CTkFont(
                    size=11,
                    weight="bold"
                ),
                fg_color="#27272A",
                text_color=self.TEXT_COLOR,
                hover_color="#3F3F46",
                height=26,
                command=lambda q=query_text:
                    self.send_ai_query(q)
            )

            btn.pack(
                side="left",
                padx=4
            )

        self.chat_frame = ctk.CTkScrollableFrame(
            page,
            fg_color=self.CARD_BG
        )

        self.chat_frame.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        input_frame = ctk.CTkFrame(
            page,
            fg_color="transparent"
        )

        input_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(10, 0)
        )

        self.ai_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text=(
                "Ask AI: 'Why is my laptop slow?', "
                "'How to free RAM?', 'Why storage is full?'..."
            ),
            font=ctk.CTkFont(size=13),
            height=40
        )

        self.ai_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.ai_entry.bind(
            "<Return>",
            lambda event: self.send_ai_query()
        )

        send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            ),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            width=90,
            height=40,
            command=self.send_ai_query
        )

        send_btn.pack(
            side="right"
        )

        self.add_chat_message(
            "AI Assistant",
            (
                "Hello! I am your LapDoctor AI. "
                "Ask me anything like 'Why is my laptop slow?', "
                "'Why is my RAM high?', or "
                "'Why is my storage full?'"
            ),
            is_user=False
        )

    # ============================================================
    # AI QUERY
    # ============================================================

    def send_ai_query(self, preset_query=None):

        query = (
            preset_query
            or self.ai_entry.get().strip()
        )

        if not query:
            return

        if not preset_query:
            self.ai_entry.delete(
                0,
                "end"
            )

        self.add_chat_message(
            "You",
            query,
            is_user=True
        )

        threading.Thread(
            target=self.generate_ai_response,
            args=(query,),
            daemon=True
        ).start()

    # ============================================================
    # AI CHAT MESSAGE
    # ============================================================

    def add_chat_message(
        self,
        sender,
        text,
        is_user=False
    ):

        bubble_bg = (
            "#27272A"
            if is_user
            else "#18181B"
        )

        border_col = (
            self.PRIMARY_ACCENT
            if not is_user
            else "#52525B"
        )

        msg_card = ctk.CTkFrame(
            self.chat_frame,
            fg_color=bubble_bg,
            border_width=1,
            border_color=border_col,
            corner_radius=10
        )

        msg_card.pack(
            fill="x",
            padx=10,
            pady=6,
            anchor="e" if is_user else "w"
        )

        header = ctk.CTkLabel(
            msg_card,
            text=sender,
            font=ctk.CTkFont(
                size=11,
                weight="bold"
            ),
            text_color=(
                self.PRIMARY_ACCENT
                if not is_user
                else "#A1A1AA"
            )
        )

        header.pack(
            anchor="w",
            padx=12,
            pady=(8, 2)
        )

        body = ctk.CTkLabel(
            msg_card,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=self.TEXT_COLOR,
            justify="left",
            wraplength=800
        )

        body.pack(
            anchor="w",
            padx=12,
            pady=(0, 8)
        )

    # ============================================================
    # AI RESPONSE
    # ============================================================

    def generate_ai_response(self, query):
        """Sends the user's real question to a real Gemini model (via
        core/ai_assistant.py), with live system stats + latest scan results
        injected as context, so answers are grounded in this PC's actual
        data instead of hard-coded canned replies."""

        context = {
            "os_info": platform.platform(),
            "cpu": self.live_stats.get("cpu", "?"),
            "ram": self.live_stats.get("ram", "?"),
            "disk": self.live_stats.get("disk", "?"),
            "storage": self.live_stats.get("storage", "?"),
            "duplicates_log": self.scan_logs.get("duplicates", ""),
            "large_log": self.scan_logs.get("large", ""),
            "old_log": self.scan_logs.get("old", ""),
            "apps_log": self.scan_logs.get("apps", ""),
        }

        if self.ai_assistant:
            response = self.ai_assistant.ask(
                query, context, history=list(self.ai_chat_history)
            )
        else:
            response = (
                "AI backend module failed to load. Make sure "
                "core/ai_assistant.py is present alongside gui.py."
            )

        # Keep a bounded rolling history so follow-up questions have context
        # without the prompt growing unbounded over a long session.
        self.ai_chat_history.append({"role": "user", "content": query})
        self.ai_chat_history.append({"role": "assistant", "content": response})
        self.ai_chat_history = self.ai_chat_history[-20:]

        self.after(
            0,
            lambda: self.add_chat_message(
                "AI Assistant",
                response,
                is_user=False
            )
        )

    # ============================================================
    # STORAGE SCAN PAGE
    # ============================================================

    def create_scan_page(self):

        page = ctk.CTkFrame(
            self.main_container,
            fg_color="transparent"
        )

        self.pages["scan"] = page

        page.grid_rowconfigure(
            2,
            weight=1
        )

        page.grid_columnconfigure(
            0,
            weight=1
        )

        # ========================================================
        # CONTROL CARD
        # ========================================================

        ctrl_card = ctk.CTkFrame(
            page,
            fg_color=self.CARD_BG,
            corner_radius=10
        )

        ctrl_card.grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        # --------------------------------------------------------
        # PATH
        # --------------------------------------------------------

        path_frame = ctk.CTkFrame(
            ctrl_card,
            fg_color="transparent"
        )

        path_frame.pack(
            fill="x",
            padx=15,
            pady=10
        )

        ctk.CTkLabel(
            path_frame,
            text="Target Path:",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=(0, 10)
        )

        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="Select Directory..."
        )

        self.path_entry.insert(
            0,
            os.path.expanduser(
                r"~\Downloads"
            )
        )

        self.path_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse",
            width=80,
            fg_color="#27272A",
            hover_color="#3F3F46",
            command=self.browse_folder
        )

        browse_btn.pack(
            side="right"
        )

        # --------------------------------------------------------
        # SCAN MODES
        # --------------------------------------------------------

        mode_frame = ctk.CTkFrame(
            ctrl_card,
            fg_color="transparent"
        )

        mode_frame.pack(
            fill="x",
            padx=15,
            pady=(0, 12)
        )

        self.scan_type = ctk.StringVar(
            value="duplicates"
        )

        modes = [
            ("Duplicates", "duplicates"),
            ("Large Files (>50MB)", "large"),
            ("Old Files", "old"),
            ("App Caches", "apps")
        ]

        for text, mode_id in modes:

            rb = ctk.CTkRadioButton(
                mode_frame,
                text=text,
                value=mode_id,
                variable=self.scan_type,
                font=ctk.CTkFont(
                    size=12,
                    weight="bold"
                ),
                fg_color=self.PRIMARY_ACCENT,
                hover_color="#0284C7"
            )

            rb.pack(
                side="left",
                padx=(0, 20)
            )

        self.scan_btn = ctk.CTkButton(
            mode_frame,
            text="START SCAN & ANALYZE",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            fg_color=self.PRIMARY_ACCENT,
            text_color="#000000",
            hover_color="#0284C7",
            command=self.toggle_scan
        )

        self.scan_btn.pack(
            side="right"
        )

        # ========================================================
        # ANALYSIS CARD
        # ========================================================

        self.analysis_card = ctk.CTkFrame(
            page,
            fg_color=self.CARD_BG,
            corner_radius=10
        )

        self.analysis_card.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        self.analysis_title = ctk.CTkLabel(
            self.analysis_card,
            text="🔍 Storage Analysis: Awaiting Scan...",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            ),
            text_color=self.PRIMARY_ACCENT,
            anchor="w"
        )

        self.analysis_title.pack(
            anchor="w",
            padx=15,
            pady=10
        )

        # ========================================================
        # TAB VIEW
        # ========================================================

        self.tabview = ctk.CTkTabview(
            page,
            segmented_button_selected_color=self.PRIMARY_ACCENT,
            segmented_button_selected_hover_color="#0284C7"
        )

        self.tabview.grid(
            row=2,
            column=0,
            sticky="nsew"
        )

        # --------------------------------------------------------
        # FILE TAB
        # --------------------------------------------------------

        self.tab_files = self.tabview.add(
            "Recommended Files to Clean (User Approval Required)"
        )

        self.tab_files.grid_rowconfigure(
            1,
            weight=1
        )

        self.tab_files.grid_columnconfigure(
            0,
            weight=1
        )

        # --------------------------------------------------------
        # ACTION BAR
        # --------------------------------------------------------

        action_bar = ctk.CTkFrame(
            self.tab_files,
            fg_color="transparent"
        )

        action_bar.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=5,
            pady=(5, 5)
        )

        ctk.CTkButton(
            action_bar,
            text="Select All Safe",
            width=115,
            fg_color="#27272A",
            hover_color="#3F3F46",
            command=self.select_all
        ).pack(
            side="left",
            padx=(0, 5)
        )

        ctk.CTkButton(
            action_bar,
            text="Deselect All",
            width=100,
            fg_color="#27272A",
            hover_color="#3F3F46",
            command=self.deselect_all
        ).pack(
            side="left"
        )

        self.clean_btn = ctk.CTkButton(
            action_bar,
            text="⚠ Approve & Clean Selected Files",
            font=ctk.CTkFont(
                weight="bold"
            ),
            fg_color=self.DANGER,
            hover_color="#DC2626",
            command=self.run_cleanup
        )

        self.clean_btn.pack(
            side="right"
        )

        # ========================================================
        # SINGLE SCROLLABLE RESULT FRAME
        # ========================================================

        self.scroll_files = ctk.CTkScrollableFrame(
            self.tab_files,
            fg_color="#1E1E22",
            corner_radius=8,
            scrollbar_button_color="#52525B",
            scrollbar_button_hover_color="#71717A"
        )

        self.scroll_files.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=10,
            pady=(5, 10)
        )

        # --------------------------------------------------------
        # EMPTY STATE
        # --------------------------------------------------------

        self.empty_result_label = ctk.CTkLabel(
            self.scroll_files,
            text=(
                "No scan results yet\n\n"
                "Choose a scan type and click\n"
                "'START SCAN & ANALYZE'"
            ),
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=self.TEXT_MUTED,
            justify="center"
        )

        self.empty_result_label.pack(
            pady=100
        )

        # ========================================================
        # CONSOLE TAB
        # ========================================================

        self.tab_console = self.tabview.add(
            "Scan Log Console"
        )

        self.tab_console.grid_rowconfigure(
            0,
            weight=1
        )

        self.tab_console.grid_columnconfigure(
            0,
            weight=1
        )

        self.log_text = ctk.CTkTextbox(
            self.tab_console,
            font=ctk.CTkFont(
                family="Consolas",
                size=12
            ),
            fg_color="#121214"
        )

        self.log_text.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=8,
            pady=8
        )

    # ============================================================
    # RISK CLASSIFICATION
    # ============================================================

    def classify_risk(self, file_path):

        clean_path = file_path.lower()

        extension = os.path.splitext(
            clean_path
        )[1]

        mode = self.scan_type.get().lower()

        # --------------------------------------------------------
        # SYSTEM PROTECTION
        # --------------------------------------------------------

        system_indicators = [
            "\\windows\\",
            "\\system32\\",
            "\\program files\\",
            "\\program files (x86)\\"
        ]

        if any(
            indicator in clean_path
            for indicator in system_indicators
        ):

            return (
                "🔴 DO NOT REMOVE",
                self.DANGER,
                False
            )

        if extension in [
            ".sys",
            ".dll"
        ]:

            return (
                "🔴 DO NOT REMOVE",
                self.DANGER,
                False
            )

        # --------------------------------------------------------
        # APP CACHE
        # --------------------------------------------------------

        if "app" in mode or "cache" in mode:

            return (
                "🟢 SAFE TO CLEAN",
                self.SUCCESS,
                True
            )

        # --------------------------------------------------------
        # LARGE FILES
        # --------------------------------------------------------

        if "large" in mode:

            return (
                "🟡 LARGE FILE — REVIEW",
                self.WARNING,
                False
            )

        # --------------------------------------------------------
        # OLD FILES
        # --------------------------------------------------------

        if "old" in mode:

            safe_extensions = [
                ".tmp",
                ".temp",
                ".log",
                ".bak",
                ".old"
            ]

            if extension in safe_extensions:

                return (
                    "🟢 SAFE TO CLEAN",
                    self.SUCCESS,
                    True
                )

            return (
                "🟡 REVIEW BEFORE DELETE",
                self.WARNING,
                False
            )

        # --------------------------------------------------------
        # DUPLICATES
        # --------------------------------------------------------

        if (
            "duplicate" in mode
            or "dup" in mode
        ):

            return (
                "🟡 REVIEW BEFORE DELETE",
                self.WARNING,
                False
            )

        # --------------------------------------------------------
        # DEFAULT
        # --------------------------------------------------------

        return (
            "🟡 REVIEW BEFORE DELETE",
            self.WARNING,
            False
        )

    # ============================================================
    # ADD FILE ITEM
    # ============================================================

    def add_file_item(self, item_data):

        try:

            file_path = ""
            name = ""
            size_bytes = 0

            # ----------------------------------------------------
            # STRING
            # ----------------------------------------------------

            if isinstance(
                item_data,
                str
            ):

                file_path = item_data

            # ----------------------------------------------------
            # DICTIONARY
            # ----------------------------------------------------

            elif isinstance(
                item_data,
                dict
            ):

                file_path = item_data.get(
                    "path",
                    ""
                )

                name = item_data.get(
                    "name",
                    ""
                )

                size_bytes = item_data.get(
                    "size",
                    item_data.get(
                        "size_bytes",
                        0
                    )
                )

            # ----------------------------------------------------
            # TUPLE / LIST
            # ----------------------------------------------------

            elif isinstance(
                item_data,
                (list, tuple)
            ):

                if len(item_data) > 0:

                    file_path = str(
                        item_data[0]
                    )

            file_path = (
                os.path.normpath(file_path)
                if file_path
                else ""
            )

            # ----------------------------------------------------
            # VALIDATE PATH
            # ----------------------------------------------------

            if not file_path:

                return

            if not os.path.exists(file_path):

                return

            # ----------------------------------------------------
            # NAME
            # ----------------------------------------------------

            if not name:

                name = (
                    os.path.basename(file_path)
                    or file_path
                )

            # ----------------------------------------------------
            # SIZE
            # ----------------------------------------------------

            if not size_bytes:

                try:

                    if os.path.isfile(file_path):

                        size_bytes = os.path.getsize(
                            file_path
                        )

                    elif os.path.isdir(file_path):

                        for root, dirs, files in os.walk(
                            file_path
                        ):

                            for filename in files:

                                try:

                                    full_path = os.path.join(
                                        root,
                                        filename
                                    )

                                    size_bytes += os.path.getsize(
                                        full_path
                                    )

                                except Exception:
                                    pass

                except Exception:
                    size_bytes = 0

            size_mb = (
                size_bytes /
                (1024 * 1024)
            )

            # Ignore genuinely empty items
            if size_mb <= 0:

                return

            # ----------------------------------------------------
            # DUPLICATE UI PREVENTION
            # ----------------------------------------------------

            for existing in self.detected_items:

                if (
                    existing["path"].lower()
                    == file_path.lower()
                ):

                    return

            # ----------------------------------------------------
            # RISK
            # ----------------------------------------------------

            (
                risk_text,
                risk_color,
                is_safe
            ) = self.classify_risk(
                file_path
            )

            # ----------------------------------------------------
            # HIDE EMPTY LABEL
            # ----------------------------------------------------

            if hasattr(
                self,
                "empty_result_label"
            ):

                try:
                    self.empty_result_label.pack_forget()
                except Exception:
                    pass

            # ----------------------------------------------------
            # RESULT ROW
            # ----------------------------------------------------

            row = ctk.CTkFrame(
                self.scroll_files,
                fg_color="#18181B",
                corner_radius=7
            )

            row.pack(
                fill="x",
                padx=5,
                pady=4
            )

            row.grid_columnconfigure(
                1,
                weight=1
            )

            # ----------------------------------------------------
            # CHECKBOX
            # ----------------------------------------------------

            var = ctk.BooleanVar(
                value=is_safe
            )

            checkbox = ctk.CTkCheckBox(
                row,
                text="",
                variable=var,
                width=28,
                fg_color=self.PRIMARY_ACCENT,
                hover_color="#0284C7"
            )

            checkbox.grid(
                row=0,
                column=0,
                padx=(10, 5),
                pady=10
            )

            # ----------------------------------------------------
            # FILE NAME
            # ----------------------------------------------------

            name_label = ctk.CTkLabel(
                row,
                text=f"{name} ({size_mb:.1f} MB)",
                font=ctk.CTkFont(
                    size=13,
                    weight="bold"
                ),
                text_color=self.TEXT_COLOR,
                anchor="w"
            )

            name_label.grid(
                row=0,
                column=1,
                sticky="w",
                padx=5
            )

            # ----------------------------------------------------
            # RISK BADGE
            # ----------------------------------------------------

            badge = ctk.CTkLabel(
                row,
                text=risk_text,
                font=ctk.CTkFont(
                    size=10,
                    weight="bold"
                ),
                text_color=risk_color
            )

            badge.grid(
                row=0,
                column=2,
                padx=10
            )

            # ----------------------------------------------------
            # PATH
            # ----------------------------------------------------

            path_label = ctk.CTkLabel(
                row,
                text=file_path,
                font=ctk.CTkFont(
                    size=10
                ),
                text_color=self.TEXT_MUTED,
                anchor="w"
            )

            path_label.grid(
                row=1,
                column=1,
                columnspan=2,
                sticky="ew",
                padx=5,
                pady=(0, 8)
            )

            # ----------------------------------------------------
            # SAVE ITEM
            # ----------------------------------------------------

            self.detected_items.append(
                {
                    "path": file_path,
                    "size": size_bytes,
                    "var": var,
                    "frame": row,
                    "safe": is_safe
                }
            )

        except Exception as e:

            self.log(
                f"[UI Item Error]: {str(e)}"
            )

    # ============================================================
    # STORAGE ANALYSIS
    # ============================================================

    def analyze_storage_reasons(
        self,
        items
    ):

        try:

            reasons = []
            total_safe_bytes = 0

            mode = self.scan_type.get().lower()

            count = len(
                self.detected_items
            )

            # ----------------------------------------------------
            # SAFE SIZE
            # ----------------------------------------------------

            for item in self.detected_items:

                if item["safe"]:

                    total_safe_bytes += item["size"]

            # ----------------------------------------------------
            # DUPLICATES
            # ----------------------------------------------------

            if "duplicate" in mode:

                if count > 0:

                    reasons.append(
                        f"Found {count} duplicate files "
                        "occupying redundant disk space."
                    )

                else:

                    reasons.append(
                        "No duplicate files were found."
                    )

            # ----------------------------------------------------
            # LARGE FILES
            # ----------------------------------------------------

            elif "large" in mode:

                if count > 0:

                    reasons.append(
                        f"Found {count} large files "
                        "(>50 MB) consuming "
                        "significant storage."
                    )

                else:

                    reasons.append(
                        "No files larger than 50 MB were found."
                    )

            # ----------------------------------------------------
            # OLD FILES
            # ----------------------------------------------------

            elif "old" in mode:

                if count > 0:

                    reasons.append(
                        f"Found {count} old files that "
                        "have not been modified recently."
                    )

                else:

                    reasons.append(
                        "No old files were found."
                    )

            # ----------------------------------------------------
            # APP CACHES
            # ----------------------------------------------------

            elif (
                "app" in mode
                or "cache" in mode
            ):

                if count > 0:

                    reasons.append(
                        f"Found {count} application cache "
                        "items that may be consuming storage."
                    )

                else:

                    reasons.append(
                        "No removable application cache was found."
                    )

            # ----------------------------------------------------
            # FALLBACK
            # ----------------------------------------------------

            if not reasons:

                reasons.append(
                    "No removable storage items were found."
                )

            self.analysis_summary = {
                "reasons": reasons,
                "total_safe_size": total_safe_bytes
            }

            # ----------------------------------------------------
            # DASHBOARD UPDATE
            # ----------------------------------------------------

            if hasattr(
                self,
                "reclaim_txt"
            ):

                if total_safe_bytes > 0:

                    safe_mb = (
                        total_safe_bytes /
                        (1024 * 1024)
                    )

                    self.reclaim_txt.configure(
                        text=(
                            f"💡 {safe_mb:.1f} MB can "
                            "potentially be reclaimed "
                            "after your approval."
                        )
                    )

                else:

                    self.reclaim_txt.configure(
                        text=(
                            "No automatically safe "
                            "items detected."
                        )
                    )

        except Exception as e:

            self.log(
                f"[Analysis Error]: {str(e)}"
            )

    # ============================================================
    # CLEAR RESULTS
    # ============================================================

    def clear_detected_items(self):

        self.detected_items = []

        if hasattr(
            self,
            "scroll_files"
        ):

            for child in self.scroll_files.winfo_children():

                try:
                    child.destroy()
                except Exception:
                    pass

    # ============================================================
    # SELECT ALL SAFE
    # ============================================================

    def select_all(self):

        for item in self.detected_items:

            if item["safe"]:

                item["var"].set(True)

    # ============================================================
    # DESELECT ALL
    # ============================================================

    def deselect_all(self):

        for item in self.detected_items:

            item["var"].set(False)

    # ============================================================
    # BROWSE
    # ============================================================

    def browse_folder(self):

        selected = filedialog.askdirectory()

        if selected:

            self.path_entry.delete(
                0,
                "end"
            )

            self.path_entry.insert(
                0,
                selected
            )

    # ============================================================
    # START / STOP SCAN
    # ============================================================

    def toggle_scan(self):

        if not self.is_scanning:

            self.start_scan()

        else:

            self.stop_requested = True

            self.scan_btn.configure(
                text="STOPPING...",
                state="disabled"
            )

    # ============================================================
    # START SCAN
    # ============================================================

    def start_scan(self):

        target_path = (
            self.path_entry.get().strip()
        )

        mode = self.scan_type.get().lower()

        # --------------------------------------------------------
        # PATH VALIDATION
        # --------------------------------------------------------

        if (
            not os.path.exists(target_path)
            and "app" not in mode
        ):

            messagebox.showerror(
                "Invalid Path",
                "Selected path does not exist!"
            )

            return

        # --------------------------------------------------------
        # SCAN STATE
        # --------------------------------------------------------
        self.is_scanning = True
        self.stop_requested = False
        mode_names = {
            "duplicates": "DUPLICATES",
            "large": "LARGE",
            "old": "OLD FILES",
            "apps": "APP CACHES"
        }

        display_mode = mode_names.get(
            mode,
            mode.upper()
        )

        self.add_history_record(
            display_mode,
            target_path,
            "IN PROGRESS"
        )

        self.scan_btn.configure(
            text="STOP SCAN",
            fg_color=self.DANGER,
            hover_color="#DC2626",
            state="normal"
        )

        # --------------------------------------------------------
        # CLEAR OLD RESULTS
        # --------------------------------------------------------

        self.clear_detected_items()

        # --------------------------------------------------------
        # UPDATE ANALYSIS
        # --------------------------------------------------------

        mode_names = {
            "duplicates": "Duplicate",
            "large": "Large File",
            "old": "Old File",
            "apps": "Application Cache"
        }

        display_mode = mode_names.get(
            mode,
            mode.title()
        )

        self.analysis_title.configure(
            text=(
                f"🔍 Storage Analysis: "
                f"Scanning for {display_mode}s..."
            )
        )

        # --------------------------------------------------------
        # LOG
        # --------------------------------------------------------

        self.log(
            f"\n=== Starting "
            f"[{mode.upper()}] Scan on: "
            f"{target_path} ==="
        )

        # --------------------------------------------------------
        # BACKGROUND THREAD
        # --------------------------------------------------------

        threading.Thread(
            target=self.execute_scan,
            args=(target_path,),
            daemon=True
        ).start()

    # ============================================================
    # EXECUTE SCAN
    # ============================================================

    def execute_scan(self, path):
        mode = self.scan_type.get()
        raw_output = ""
        found_paths = []
        skip_dirs = getattr(self, "skip_system_dirs_var", None)
        skip_dirs = skip_dirs.get() if skip_dirs else True

        try:
            if mode == "duplicates" and self.duplicate:
                raw_output = self.duplicate.scan(path, skip_system_dirs=skip_dirs)

            elif mode == "large" and self.large_files:
                raw_output = self.large_files.scan(path, skip_system_dirs=skip_dirs)

            elif mode == "old" and self.old_files:
                raw_output = self.old_files.scan(path, skip_system_dirs=skip_dirs)

            elif mode == "apps" and self.app_analyzer:
                try:
                    raw_output = self.app_analyzer.scan(path)
                except TypeError:
                    raw_output = self.app_analyzer.scan()
            else:
                raw_output = ""

            if raw_output is None:
                raw_output = ""

            raw_output = str(raw_output)

            # Keep the latest raw result per scan mode so the AI Assistant
            # can answer questions using this session's real scan data.
            self.scan_logs[mode] = raw_output

            if not self.stop_requested:
                self.log(raw_output)

            if mode == "large":
                for line in raw_output.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    if (
                        "Size (MB)" in line
                        or "File Path" in line
                        or "Total Large Files" in line
                        or "Found " in line
                        or "Scan" in line
                    ):
                        continue

                    if "|" in line:
                        parts = line.split("|", 1)

                        if len(parts) == 2:
                            size_text = parts[0].strip()
                            file_path = parts[1].strip()

                            if re.search(
                                r"[\d,.]+\s*MB",
                                size_text,
                                re.IGNORECASE
                            ):
                                file_path = os.path.normpath(
                                    file_path.strip().strip('"').strip("'")
                                )

                                if os.path.isfile(file_path):
                                    found_paths.append(file_path)

            elif mode == "old":
                for line in raw_output.splitlines():
                    line = line.strip()

                    matches = re.findall(
                        r"[A-Za-z]:[\\/][^\r\n\"']+",
                        line
                    )

                    for match in matches:
                        file_path = os.path.normpath(
                            match.strip().rstrip(" |,")
                        )

                        if os.path.isfile(file_path):
                            found_paths.append(file_path)

            elif mode == "apps":
                for line in raw_output.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    if "|" in line:
                        parts = [
                            p.strip()
                            for p in line.split("|")
                        ]

                        if len(parts) >= 3:
                            category = parts[0]
                            size_text = parts[1]
                            cache_path = parts[2]

                            if (
                                "category" in category.lower()
                                or "size" in size_text.lower()
                                or "path" in cache_path.lower()
                            ):
                                continue

                            cache_path = os.path.normpath(
                                cache_path.strip().strip('"').strip("'")
                            )

                            if os.path.exists(cache_path):
                                if "0.00 mb" not in size_text.lower():
                                    found_paths.append(cache_path)

                        continue

                    matches = re.findall(
                        r"[A-Za-z]:[\\/][^\r\n\"']+",
                        line
                    )

                    for match in matches:
                        cache_path = os.path.normpath(
                            match.strip().rstrip(" |,")
                        )

                        if os.path.exists(cache_path):
                            found_paths.append(cache_path)

            elif mode == "duplicates":
                matches = re.findall(
                    r"[A-Za-z]:[\\/][^\r\n\"']+",
                    raw_output
                )

                for match in matches:
                    file_path = os.path.normpath(
                        match.strip().rstrip(" |,")
                    )

                    if os.path.isfile(file_path):
                        found_paths.append(file_path)

            unique_paths = []
            seen = set()

            for file_path in found_paths:
                file_path = os.path.normpath(file_path)
                key = os.path.normcase(file_path)

                if key in seen:
                    continue

                if mode == "apps":
                    if not os.path.exists(file_path):
                        continue
                else:
                    if not os.path.isfile(file_path):
                        continue

                seen.add(key)
                unique_paths.append(file_path)

            found_paths = unique_paths

            self.log(
                f"\n[GUI DEBUG] Extracted {len(found_paths)} item(s) "
                f"for Recommended Files."
            )

            for file_path in found_paths:
                self.log(f"[GUI DEBUG] {file_path}")

        except Exception as e:
            self.log(f"[Scan Error]: {str(e)}")

        finally:
            self.is_scanning = False

            self.after(
                0,
                lambda paths=list(found_paths):
                    self.finish_scan(paths)
        )
    # ============================================================
    # FINISH SCAN
    # ============================================================

    def finish_scan(
        self,
        items
    ):

        self.is_scanning = False

        self.scan_btn.configure(
            text="START SCAN & ANALYZE",
            fg_color=self.PRIMARY_ACCENT,
            hover_color="#0284C7",
            state="normal"
        )

        # --------------------------------------------------------
        # STOPPED
        # --------------------------------------------------------

        if self.stop_requested:

            self.analysis_title.configure(
                text=(
                    "🔍 Storage Analysis: "
                    "Scan stopped by user."
                )
            )

            self.log(
                "\n=== Scan Stopped ==="
            )

            self.tabview.set(
                "Recommended Files to Clean "
                "(User Approval Required)"
            )
            if self.history_records:

                self.history_records[0]["status"] = "COMPLETED"

                self.render_history()

            return

        # --------------------------------------------------------
        # CLEAR RESULT FRAME
        # --------------------------------------------------------

        self.clear_detected_items()

        # --------------------------------------------------------
        # ADD RESULTS
        # --------------------------------------------------------

        valid_items = []

        for item in items:

            if isinstance(
                item,
                dict
            ):

                path = item.get(
                    "path",
                    ""
                )

            else:

                path = str(item)

            if (
                path
                and os.path.exists(path)
            ):

                valid_items.append(
                    item
                )

        # --------------------------------------------------------
        # RENDER
        # --------------------------------------------------------

        for item in valid_items:

            self.add_file_item(
                item
            )

        # --------------------------------------------------------
        # ANALYZE
        # --------------------------------------------------------

        self.analyze_storage_reasons(
            valid_items
        )

        # --------------------------------------------------------
        # TOTAL
        # --------------------------------------------------------

        count = len(
            self.detected_items
        )

        total_size = sum(
            item["size"]
            for item in self.detected_items
        )

        total_mb = (
            total_size /
            (1024 * 1024)
        )

        mode = self.scan_type.get()

        # --------------------------------------------------------
        # UPDATE ANALYSIS TITLE
        # --------------------------------------------------------

        if count > 0:

            self.analysis_title.configure(
                text=(
                    f"🔍 Storage Analysis: "
                    f"Found {count} total {mode.lower()} "
                    f"items occupying "
                    f"{total_mb:.1f} MB."
                )
            )

        else:

            self.analysis_title.configure(
                text=(
                    "🔍 Storage Analysis: "
                    "No removable items found."
                )
            )

        # --------------------------------------------------------
        # EMPTY RESULT
        # --------------------------------------------------------

        if count == 0:

            self.empty_result_label = ctk.CTkLabel(
                self.scroll_files,
                text=(
                    "✓ No removable items found\n\n"
                    "Your selected location looks clean."
                ),
                font=ctk.CTkFont(
                    size=15,
                    weight="bold"
                ),
                text_color=self.SUCCESS,
                justify="center"
            )

            self.empty_result_label.pack(
                pady=100
            )

        # --------------------------------------------------------
        # LOG
        # --------------------------------------------------------

        self.log(
            "\n=== Scan & Analysis Completed ==="
        )

        self.log(
            f"Items found: {count}"
        )

        self.log(
            f"Total scanned result size: "
            f"{total_mb:.2f} MB"
        )

        # --------------------------------------------------------
        # SHOW RESULTS
        # --------------------------------------------------------

        self.tabview.set(
            "Recommended Files to Clean "
            "(User Approval Required)"
        )

    # ============================================================
    # CLEANUP
    # ============================================================

    def run_cleanup(self):

        selected_files = [
            item["path"]
            for item in self.detected_items
            if item["var"].get()
        ]

        if not selected_files:

            messagebox.showinfo(
                "Cleanup Info",
                "No files were selected for removal."
            )

            return

        # --------------------------------------------------------
        # PERMISSION
        # --------------------------------------------------------

        permission_granted = messagebox.askyesno(
            "User Permission Required",
            (
                f"You are about to move "
                f"{len(selected_files)} items "
                "to the Recycle Bin.\n\n"
                "Do you grant permission to "
                "clean these files?"
            ),
            icon="warning"
        )

        if not permission_granted:

            self.log(
                "[Cleanup] User cancelled cleanup."
            )

            return

        # --------------------------------------------------------
        # EXECUTE
        # --------------------------------------------------------

        try:

            if (
                self.cleanup
                and hasattr(
                    self.cleanup,
                    "execute"
                )
            ):

                result = self.cleanup.execute(
                    selected_files
                )

                self.log(
                    str(result)
                )

            else:

                messagebox.showerror(
                    "Cleanup Error",
                    "Cleanup module is not available."
                )

                return

            # ----------------------------------------------------
            # REMOVE DELETED ITEMS FROM UI
            # ----------------------------------------------------

            remaining = []

            cleaned_count = 0

            for item in self.detected_items:

                if (
                    item["var"].get()
                    and not os.path.exists(
                        item["path"]
                    )
                ):

                    try:
                        item["frame"].destroy()
                    except Exception:
                        pass

                    cleaned_count += 1

                else:

                    remaining.append(
                        item
                    )

            self.detected_items = remaining

            # ----------------------------------------------------
            # HISTORY
            # ----------------------------------------------------

            timestamp = time.strftime(
                "%Y-%m-%d %H:%M"
            )

            self.history_last_deleted.configure(
                text=(
                    f"Last deleted: "
                    f"{cleaned_count} item(s) cleaned at "
                    f"{timestamp}"
                )
            )

            # ----------------------------------------------------
            # UPDATE ANALYSIS
            # ----------------------------------------------------

            remaining_size = sum(
                item["size"]
                for item in self.detected_items
            )

            remaining_mb = (
                remaining_size /
                (1024 * 1024)
            )

            self.analysis_title.configure(
                text=(
                    f"✓ Cleanup completed. "
                    f"{cleaned_count} item(s) removed. "
                    f"{len(self.detected_items)} remaining."
                )
            )

            messagebox.showinfo(
                "Cleanup Successful",
                (
                    f"Successfully cleaned "
                    f"{cleaned_count} item(s).\n\n"
                    f"Remaining items: "
                    f"{len(self.detected_items)}\n"
                    f"Remaining displayed size: "
                    f"{remaining_mb:.1f} MB"
                )
            )

        except Exception as e:

            self.log(
                f"[Cleanup Error]: {str(e)}"
            )

            messagebox.showerror(
                "Cleanup Error",
                str(e)
            )

    # ============================================================
    # LOGGING
    # ============================================================

    def log(self, message):

        try:

            self.after(
                0,
                lambda m=message:
                    self._append_log(m)
            )

        except Exception:
            pass

    # ============================================================
    # APPEND LOG
    # ============================================================

    def _append_log(
        self,
        message
    ):

        if not hasattr(
            self,
            "log_text"
        ):

            return

        try:

            self.log_text.insert(
                "end",
                message + "\n"
            )

            self.log_text.see(
                "end"
            )

        except Exception:
            pass

    # ============================================================
    # HISTORY PAGE
    # ============================================================

    def create_history_page(self):

        page = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="transparent"
        )

        self.pages["history"] = page

        page.grid_columnconfigure(
            0,
            weight=1
        )

        title = ctk.CTkLabel(
            page,
            text="Scan & Cleanup History Log",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=self.TEXT_COLOR
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=15
        )

        self.history_summary = ctk.CTkFrame(
            page,
            fg_color="#1E1E22",
            corner_radius=10
        )

        self.history_summary.pack(
            fill="x",
            padx=20,
            pady=(0, 10)
        )

        self.history_last_scan = ctk.CTkLabel(
            self.history_summary,
            text="Last scanned: None",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color=self.TEXT_COLOR
        )

        self.history_last_scan.pack(
            anchor="w",
            padx=15,
            pady=(12, 5)
        )

        self.history_last_deleted = ctk.CTkLabel(
            self.history_summary,
            text="Last deleted: None",
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            text_color=self.TEXT_COLOR
        )

        self.history_last_deleted.pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

        self.history_container = ctk.CTkFrame(
            page,
            fg_color="#121214"
        )

        self.history_container.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 10)
        )

        self.history_empty = ctk.CTkLabel(
            self.history_container,
            text="No scan activity yet.",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            ),
            text_color=self.TEXT_MUTED
        )

        self.history_empty.pack(
            pady=80
        )
    def add_history_record(
        self,
        scan_type,
        path,
        status
    ):

        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        record = {
            "type": scan_type,
            "path": path,
            "time": timestamp,
            "status": status
        }

        self.history_records.insert(
            0,
            record
        )

        self.render_history()
    def render_history(self):

        for child in self.history_container.winfo_children():
            child.destroy()

        if not self.history_records:

            self.history_empty = ctk.CTkLabel(
                self.history_container,
                text="No scan activity yet.",
                font=ctk.CTkFont(
                    size=14,
                    weight="bold"
                ),
                text_color=self.TEXT_MUTED
            )

            self.history_empty.pack(
                pady=80
            )

            return

        latest = self.history_records[0]

        self.history_last_scan.configure(
            text=(
                f"Last scanned: "
                f"{latest['type']} on "
                f"{latest['path']} at "
                f"{latest['time']} "
                f"({latest['status'].lower()})"
            )
        )

        for record in self.history_records:

            card = ctk.CTkFrame(
                self.history_container,
                fg_color="#18181B",
                corner_radius=8
            )

            card.pack(
                fill="x",
                padx=8,
                pady=5
            )

            icon = ctk.CTkLabel(
                card,
                text="◈",
                font=ctk.CTkFont(
                    size=15,
                    weight="bold"
                ),
                text_color=self.TEXT_COLOR
            )

            icon.grid(
                row=0,
                column=0,
                rowspan=3,
                padx=(15, 8),
                pady=10
            )

            type_label = ctk.CTkLabel(
                card,
                text=f"{record['type'].upper()} SCAN",
                font=ctk.CTkFont(
                    size=13,
                    weight="bold"
                ),
                text_color=self.TEXT_COLOR,
                anchor="w"
            )

            type_label.grid(
                row=0,
                column=1,
                sticky="w",
                pady=(10, 2)
            )

            path_label = ctk.CTkLabel(
                card,
                text=f"⌂ {record['path']}",
                font=ctk.CTkFont(
                    size=10
                ),
                text_color=self.TEXT_MUTED,
                anchor="w"
            )

            path_label.grid(
                row=1,
                column=1,
                sticky="w",
                pady=2
            )

            time_label = ctk.CTkLabel(
                card,
                text=f"◷ {record['time']}",
                font=ctk.CTkFont(
                    size=10
                ),
                text_color=self.TEXT_MUTED,
                anchor="w"
            )

            time_label.grid(
                row=2,
                column=1,
                sticky="w",
                pady=(2, 10)
            )

            if record["status"] == "COMPLETED":

                status_color = self.SUCCESS

            else:

                status_color = self.PRIMARY_ACCENT

            status_label = ctk.CTkLabel(
                card,
                text=record["status"],
                font=ctk.CTkFont(
                    size=10,
                    weight="bold"
                ),
                text_color="#FFFFFF",
                fg_color=status_color,
                corner_radius=6,
                width=90,
                height=28
            )

            status_label.grid(
                row=0,
                column=2,
                rowspan=3,
                padx=15
            )

            card.grid_columnconfigure(
                1,
                weight=1
            )
            

    # ============================================================
    # SETTINGS
    # ============================================================

    def create_settings_page(self):

        page = ctk.CTkFrame(
            self.main_container,
            fg_color=self.CARD_BG
        )

        self.pages["settings"] = page

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # ---------------- Preferences ----------------
        ctk.CTkLabel(
            scroll,
            text="Preferences",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(15, 8))

        pref_frame = ctk.CTkFrame(scroll, fg_color="#20202A", corner_radius=10)
        pref_frame.pack(fill="x", padx=20, pady=(0, 18))

        self.skip_system_dirs_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            pref_frame,
            text="Exclude Windows / Program Files / recycle bin from scans (recommended)",
            variable=self.skip_system_dirs_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=self.PRIMARY_ACCENT,
        ).pack(anchor="w", padx=15, pady=(15, 0))

        ctk.CTkLabel(
            pref_frame,
            text="Keeps scans of broad paths (e.g. a whole drive) fast and responsive by\nskipping locked/system-owned folders that rarely contain real duplicates or junk.",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(4, 15))

        # ---------------- Smart Cleaning ----------------
        ctk.CTkLabel(
            scroll,
            text="Smart Cleaning",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(0, 8))

        smart_frame = ctk.CTkFrame(scroll, fg_color="#20202A", corner_radius=10)
        smart_frame.pack(fill="x", padx=20, pady=(0, 18))

        self.smart_cleaning_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(
            smart_frame,
            text="Alert me when junk files or browser data should be cleaned",
            variable=self.smart_cleaning_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            progress_color=self.PRIMARY_ACCENT,
            command=self._on_smart_cleaning_toggled,
        ).pack(anchor="w", padx=15, pady=(15, 0))

        ctk.CTkLabel(
            smart_frame,
            text="Runs a lightweight check in the background using your real disk usage and\nDownloads-folder junk (.tmp/.log/.bak/.old/.dmp/.chk) size, and shows a\npop-up alert when storage or junk builds up. No files are touched automatically.",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(6, 0))

        self.smart_cleaning_status_lbl = ctk.CTkLabel(
            smart_frame,
            text="Status: Off",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.smart_cleaning_status_lbl.pack(anchor="w", padx=15, pady=(8, 15))

        # ---------------- About ----------------
        ctk.CTkLabel(
            scroll,
            text="About",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=20, pady=(0, 8))

        about_frame = ctk.CTkFrame(scroll, fg_color="#20202A", corner_radius=10)
        about_frame.pack(fill="x", padx=20, pady=(0, 20))

        ctk.CTkLabel(
            about_frame,
            text="🩺 LapDoctor — Smart System Health Assistant",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=self.TEXT_COLOR,
        ).pack(anchor="w", padx=15, pady=(15, 2))

        ctk.CTkLabel(
            about_frame,
            text="Version 1.0.0",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=15)

        ctk.CTkLabel(
            about_frame,
            text="License: MIT License",
            font=ctk.CTkFont(size=12),
            text_color=self.TEXT_MUTED,
        ).pack(anchor="w", padx=15, pady=(2, 0))

        ctk.CTkLabel(
            about_frame,
            text="A local, privacy-first tool that scans your own machine for duplicate,\nlarge, stale, and cache files and lets you review and clean them safely.\nNothing is uploaded off your device.",
            font=ctk.CTkFont(size=11),
            text_color=self.TEXT_MUTED,
            justify="left",
        ).pack(anchor="w", padx=15, pady=(8, 10))

        support_row = ctk.CTkFrame(about_frame, fg_color="transparent")
        support_row.pack(anchor="w", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            support_row,
            text="Need help or found a bug?",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.TEXT_COLOR,
        ).pack(anchor="w")

        ctk.CTkLabel(
            support_row,
            text="✉  support@lapdoctor.app     •     🐙 github.com/lapdoctor/issues",
            font=ctk.CTkFont(size=11),
            text_color=self.PRIMARY_ACCENT,
        ).pack(anchor="w", pady=(4, 0))

    # -------------------------------------------------------------
    # Smart Cleaning Alerts (real, not decorative -- see _smart_cleaning_loop
    # started from __init__, and _estimate_junk_mb below)
    # -------------------------------------------------------------
    def _on_smart_cleaning_toggled(self):
        enabled = self.smart_cleaning_var.get()
        if hasattr(self, "smart_cleaning_status_lbl"):
            text = "Status: On — checking in the background" if enabled else "Status: Off"
            color = "#22C55E" if enabled else self.TEXT_MUTED
            self.smart_cleaning_status_lbl.configure(text=text, text_color=color)
        if enabled:
            self._last_smart_alert_ts = 0.0

    def _estimate_junk_mb(self, folder, max_files=20000):
        junk_ext = {".tmp", ".log", ".bak", ".old", ".dmp", ".chk", ".crdownload", ".part"}
        total = 0
        checked = 0
        try:
            for root, dirs, files in os.walk(folder):
                for f in files:
                    if os.path.splitext(f)[1].lower() in junk_ext:
                        try:
                            total += os.path.getsize(os.path.join(root, f))
                        except OSError:
                            pass
                    checked += 1
                    if checked >= max_files:
                        return total / (1024 * 1024)
        except OSError:
            pass
        return total / (1024 * 1024)

    def _smart_cleaning_loop(self):
        while self.monitoring:
            try:
                if getattr(self, "smart_cleaning_var", None) is not None and self.smart_cleaning_var.get():
                    now = time.time()
                    if now - getattr(self, "_last_smart_alert_ts", 0.0) > 900:
                        storage_pct = self.live_stats.get("storage", 0)
                        downloads = os.path.expanduser("~/Downloads")
                        junk_mb = self._estimate_junk_mb(downloads) if os.path.isdir(downloads) else 0

                        if storage_pct >= 85:
                            self._last_smart_alert_ts = now
                            self.after(0, lambda p=storage_pct: self._raise_smart_alert(
                                f"Your storage is {p:.0f}% full. Running a Duplicates or Old Files scan could free up space."
                            ))
                        elif junk_mb >= 200:
                            self._last_smart_alert_ts = now
                            self.after(0, lambda m=junk_mb: self._raise_smart_alert(
                                f"Found ~{m:.0f} MB of junk files (.tmp/.log/.bak/.old) in your Downloads folder. Consider cleaning them."
                            ))
            except Exception:
                pass
            time.sleep(60)

    def _raise_smart_alert(self, message):
        if hasattr(self, "smart_cleaning_status_lbl"):
            self.smart_cleaning_status_lbl.configure(text=f"Status: On — {message}", text_color="#F59E0B")
        messagebox.showwarning("Smart Cleaning Alert", message)

    # ============================================================
    # PRIVACY MODAL
    # ============================================================

    def show_privacy_modal(self):

        modal = ctk.CTkToplevel(
            self
        )

        modal.title(
            "Privacy Status"
        )

        modal.geometry(
            "450x300"
        )

        modal.transient(
            self
        )

        modal.grab_set()

        ctk.CTkLabel(
            modal,
            text="🔒 Privacy Protection Guarantees",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            text_color="#34D399"
        ).pack(
            anchor="w",
            padx=20,
            pady=(20, 10)
        )

        points = [
            "✓ Files analyzed locally on your machine",
            "✓ No automatic deletion without permission",
            "✓ No personal file contents stored",
            "✓ Duplicate verification can use SHA-256",
            "✓ Cleanup requires explicit user approval"
        ]

        for point in points:

            ctk.CTkLabel(
                modal,
                text=point,
                font=ctk.CTkFont(
                    size=12
                ),
                text_color=self.TEXT_COLOR
            ).pack(
                anchor="w",
                padx=25,
                pady=3
            )

        ctk.CTkButton(
            modal,
            text="Close",
            fg_color="#27272A",
            hover_color="#3F3F46",
            command=modal.destroy
        ).pack(
            pady=15
        )

    # ============================================================
    # SYSTEM MONITORING
    # ============================================================

    def update_system_stats(self):

        try:
            psutil.cpu_percent(interval=None)
            psutil.disk_io_counters()
        except Exception:
            pass

        while self.monitoring:

            try:
                cpu = psutil.cpu_percent(interval=0.5)

                ram = psutil.virtual_memory().percent

                disk = 0

                disk_io = psutil.disk_io_counters()

                if disk_io:
                    current_read = disk_io.read_bytes
                    current_write = disk_io.write_bytes

                    if hasattr(self, "_last_disk_read"):
                        read_diff = current_read - self._last_disk_read
                        write_diff = current_write - self._last_disk_write

                        activity = read_diff + write_diff
                        disk = min(100, int(activity / (1024 * 1024)))

                    self._last_disk_read = current_read
                    self._last_disk_write = current_write

                storage = psutil.disk_usage(
                    os.path.abspath(os.sep)
                ).percent

                health = self.calculate_health(
                    cpu,
                    ram,
                    disk,
                    storage
                )

                self.live_stats = {
                    "cpu": round(cpu),
                    "ram": round(ram),
                    "disk": round(disk),
                    "storage": round(storage),
                    "health": round(health)
                }

                self.after(
                    0,
                    lambda stats=self.live_stats.copy():
                        self._refresh_stats_ui(
                            stats["cpu"],
                            stats["ram"],
                            stats["disk"],
                            stats["storage"],
                            stats["health"]
                        )
                )

            except Exception as e:
                print("[Monitoring Error]", e)

            time.sleep(2)
    def calculate_health(self, cpu, ram, disk, storage):

        cpu_score = max(0, 100 - cpu)

        ram_score = max(0, 100 - ram)

        disk_score = max(0, 100 - min(disk, 100))

        storage_score = max(0, 100 - storage)

        health = (
            cpu_score * 0.25 +
            ram_score * 0.25 +
            disk_score * 0.15 +
            storage_score * 0.35
        )

        return max(0, min(100, health))
    # ============================================================
    # REFRESH SYSTEM STATS
    # ============================================================

    def _refresh_stats_ui(
        self,
        cpu,
        ram,
        disk,
        storage,
        health
    ):

        try:

            self.stat_widgets["cpu"].configure(
                text=f"{cpu}%"
            )

            self.stat_widgets["ram"].configure(
                text=f"{ram}%"
            )

            self.stat_widgets["disk"].configure(
                text=f"{disk}%"
            )

            self.stat_widgets["storage"].configure(
                text=f"{storage}%"
            )

            self.health_score_lbl.configure(
                text=f"{health} / 100"
            )

            if health >= 80:

                status = "HEALTHY"
                color = self.SUCCESS

            elif health >= 60:

                status = "GOOD"
                color = self.WARNING

            elif health >= 40:

                status = "WARNING"
                color = self.WARNING

            else:

                status = "CRITICAL"
                color = self.DANGER

            self.health_score_lbl.configure(
                text_color=color
            )

            self.health_status_badge.configure(
                text=status,
                text_color=color
            )

        except Exception as e:
            print("[UI Stats Error]", e)

    # ============================================================
    # WINDOW CLOSE
    # ============================================================

    def on_close(self):

        self.monitoring = False
        self.stop_requested = True

        self.destroy()
    


# ================================================================
# APPLICATION ENTRY POINT
# ================================================================

if __name__ == "__main__":

    app = LapdoctorGUI()

    app.mainloop()