import glob
import json
import os
import re
import shutil
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# 打包（PyInstaller 冻结）运行时，基准目录取 exe 所在目录；否则取脚本所在目录
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
MEDIA_DIR = os.path.join(SRC_DIR, "media")
ICON_PATH = os.path.join(SRC_DIR, "icon.ico")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CONFIG_PATH = os.path.join(SRC_DIR, "config.json")

NAV_BG = "#e6e6e6"
NAV_FG = "#333333"
BTN_BG = "#d0d0d0"
BTN_BG_ACTIVE = "#c0c0c0"
BTN_FG = "#333333"

SUB_NAV_BG = "#e6e6e6"
SUB_NAV_FG = "#333333"
SUB_NAV_ACTIVE = "#d0d0d0"
MAIN_BG = "#f0f0f0"


class FlierZedApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.load_config()
        self.title(self.getText("window_title"))
        self.geometry("1024x768")
        self.state("zoomed")  # 程序运行后窗口最大化显示
        self.set_icon()
        self.ensure_output_dir()

        self.current_project = None  # 当前打开的项目文件夹路径
        self.current_page = None  # 当前页面标识
        self.current_item = None

        self.create_widgets()
        self.bind_all("<Control-s>", self.global_save)  # Ctrl+S 全局保存
        self.show_no_project()

    def load_config(self):
        """读取 config.json，初始化语言配置"""
        self.config = self._read_json(CONFIG_PATH)
        if not self.config:
            self.config = {"version": "v1.0.0", "language": "CN", "lang_text": {}}
        self.language = self.config.get("language", "CN")

    def getText(self, key):
        """根据当前语言返回 config.json lang_text 中的文案；缺少时回退 CN，仍无则返回键名"""
        lang_map = self.config.get("lang_text", {}).get(self.language, {})
        if key in lang_map:
            return lang_map[key]
        cn = self.config.get("lang_text", {}).get("CN", {})
        return cn.get(key, key)

    def set_icon(self):
        """添加窗口图标"""
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass

    def update_title(self):
        """更新窗口标题，打开项目时在标题后附加项目文件夹路径"""
        base = self.getText("window_title")
        if self.current_project:
            self.title(f"{base} - {self.current_project}")
        else:
            self.title(base)

    def switch_language(self, lang_key):
        """切换语言：更新 config.json 并重建界面"""
        if lang_key == self.language:
            return
        self.config["language"] = lang_key
        self.language = lang_key
        self._write_json(CONFIG_PATH, self.config)

        project = self.current_project
        page = self.current_page
        # 重建整个界面
        for w in self.winfo_children():
            w.destroy()
        self.current_project = project
        self.create_widgets()
        self.update_title()
        if self.current_project:
            self.show_project()
            if page and page != "items":
                self.show_page(page)
        else:
            self.show_no_project()

    def global_save(self, _event=None):
        """Ctrl+S 全局保存：未打开项目时不做任何反应；已选中物品时先提交右侧编辑区改动"""
        if not self.current_project:
            return
        if self.current_page == "items" and self.current_item:
            # 仅在物品页且有选中物品时，提交当前物品编辑区的改动
            self.save_item_detail()
        else:
            self.refresh_generated_files()
            messagebox.showinfo(self.getText("title_save"), self.getText("saved"))

    def ensure_output_dir(self):
        """判断当前目录下有没有 output 文件夹，没有则创建"""
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)

    def create_widgets(self):
        # 导航栏按钮样式
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Nav.TButton",
            background=BTN_BG,
            foreground=BTN_FG,
            bordercolor=NAV_BG,
            lightcolor=NAV_BG,
            darkcolor=NAV_BG,
            relief="flat",
        )
        style.map(
            "Nav.TButton",
            background=[("active", BTN_BG_ACTIVE), ("pressed", BTN_BG_ACTIVE)],
            foreground=[("active", NAV_FG), ("pressed", NAV_FG)],
        )

        # 顶部导航栏
        self.nav_bar = tk.Frame(self, bg=NAV_BG, height=48)
        self.nav_bar.pack(side="top", fill="x")
        self.nav_bar.pack_propagate(False)

        # 导航栏左侧两个按钮
        self.btn_new = ttk.Button(self.nav_bar, text=self.getText("new_project"), style="Nav.TButton", command=self.new_project)
        self.btn_new.pack(side="left", padx=3, pady=4)

        self.btn_open = ttk.Button(self.nav_bar, text=self.getText("open_project"), style="Nav.TButton", command=self.open_project)
        self.btn_open.pack(side="left", padx=3, pady=4)

        self.btn_open_folder = ttk.Button(self.nav_bar, text=self.getText("open_folder"), style="Nav.TButton", command=self.open_project_folder)
        self.btn_open_folder.pack(side="left", padx=3, pady=4)

        self.btn_settings = ttk.Button(self.nav_bar, text=self.getText("settings"), style="Nav.TButton", command=self.show_settings)
        self.btn_settings.pack(side="left", padx=3, pady=4)

        # 主显示区域
        self.main_area = tk.Frame(self, bg=MAIN_BG)
        self.main_area.pack(side="top", fill="both", expand=True)

        # 次级导航栏（打开项目后显示）
        self.sub_nav = tk.Frame(self.main_area, bg=SUB_NAV_BG, height=40)
        self.sub_nav.pack_propagate(False)

        style.configure(
            "SubNav.TButton",
            background=SUB_NAV_BG,
            foreground=SUB_NAV_FG,
            bordercolor=SUB_NAV_BG,
            lightcolor=SUB_NAV_BG,
            darkcolor=SUB_NAV_BG,
            relief="flat",
        )
        style.map(
            "SubNav.TButton",
            background=[("active", SUB_NAV_ACTIVE), ("pressed", SUB_NAV_ACTIVE)],
            foreground=[("active", SUB_NAV_FG), ("pressed", SUB_NAV_FG)],
        )

        # 选中态样式（当前页面按钮高亮）
        style.configure(
            "SubNavSel.TButton",
            background="#ffffff",
            foreground=SUB_NAV_FG,
            bordercolor=SUB_NAV_ACTIVE,
            lightcolor=SUB_NAV_ACTIVE,
            darkcolor=SUB_NAV_ACTIVE,
            relief="solid",
        )
        style.map(
            "SubNavSel.TButton",
            background=[("active", "#ffffff"), ("pressed", "#ffffff")],
            foreground=[("active", SUB_NAV_FG), ("pressed", SUB_NAV_FG)],
        )

        self.btn_items = ttk.Button(self.sub_nav, text=self.getText("page_items"), style="SubNav.TButton", command=lambda: self.show_page("items"))
        self.btn_items.pack(side="left", padx=3, pady=3)

        self.btn_images = ttk.Button(self.sub_nav, text=self.getText("page_images"), style="SubNav.TButton", command=lambda: self.show_page("images"))
        self.btn_images.pack(side="left", padx=3, pady=3)

        self.btn_icon = ttk.Button(self.sub_nav, text=self.getText("page_icons"), style="SubNav.TButton", command=lambda: self.show_page("icons"))
        self.btn_icon.pack(side="left", padx=3, pady=3)

        self.btn_refresh = ttk.Button(self.sub_nav, text=self.getText("page_refresh"), style="SubNav.TButton", command=lambda: self.show_page("refresh"))
        self.btn_refresh.pack(side="left", padx=3, pady=3)

        self._nav_buttons = {
            "items": self.btn_items,
            "images": self.btn_images,
            "icons": self.btn_icon,
            "refresh": self.btn_refresh,
        }

        # 页面容器
        self.page_container = tk.Frame(self.main_area, bg=MAIN_BG)

        self.current_page = None  # 当前显示的子页面
        self.no_project_label = None  # "请打开项目"提示标签

    def clear_main_area(self):
        """清空主显示区域中除次级导航栏和页面容器外的临时内容"""
        for widget in self.main_area.winfo_children():
            if widget in (self.sub_nav, self.page_container):
                continue
            widget.destroy()

    def show_no_project(self):
        """显示未打开项目的界面"""
        self.sub_nav.pack_forget()
        self.page_container.pack_forget()
        self.clear_main_area()
        self.no_project_label = tk.Label(
            self.main_area, text=self.getText("no_project"), bg=MAIN_BG, fg="#888888",
        )
        self.no_project_label.pack(expand=True)

    def show_project(self):
        """显示已打开项目的界面，默认展示物品页面"""
        if not self.current_project:
            self.show_no_project()
            return

        self.clear_main_area()
        if self.no_project_label is not None:
            self.no_project_label.destroy()
            self.no_project_label = None

        self.sub_nav.pack(side="top", fill="x")
        self.page_container.pack(side="top", fill="both", expand=True)
        self.show_page("items")  # 默认显示物品页面

    # ---- 子页面 ----

    def clear_page_container(self):
        """清空页面容器"""
        for widget in self.page_container.winfo_children():
            widget.destroy()

    def show_page(self, page):
        """切换主显示区域页面：items / images / icons / refresh"""
        self.clear_page_container()
        self.current_page = page
        self.update_sub_nav_state(page)
        if page == "items":
            self.show_items_page()
        elif page == "images":
            self.show_images_page()
        elif page == "icons":
            self.show_icon_page()
        elif page == "refresh":
            self.show_refresh_page()

    def update_sub_nav_state(self, page):
        """更新次级导航栏按钮的选中态"""
        for key, btn in self._nav_buttons.items():
            btn.configure(style="SubNavSel.TButton" if key == page else "SubNav.TButton")

    def show_items_page(self):
        """物品页面"""
        self.clear_page_container()

        # 左侧列表区域
        left_frame = tk.Frame(self.page_container, bg=MAIN_BG)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        # 物品列表（Treeview）
        tree_frame = tk.Frame(left_frame, bg=MAIN_BG)
        tree_frame.pack(side="top", fill="both", expand=True)

        self.items_tree = ttk.Treeview(tree_frame, columns=("name",), show="headings", height=15)
        self.items_tree.heading("name", text=self.getText("list_items"))
        self.items_tree.column("name", width=220, anchor="w")
        self.items_tree.pack(side="left", fill="y")
        self.items_tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # 物品数据：tree iid -> {id, name, icon, weight, image, remark}
        self.items_data = {}
        self.current_item = None  # 当前选中物品的 iid

        # 每次打开物品界面，从 Items.txt 读取物品列表（并从 FlierData.lua 补充图片、备注）
        self.load_items_from_files()
        for key, data in self.items_data.items():
            self.items_tree.insert("", "end", iid=key, values=(data["name"],))

        # 列表下方按钮
        btn_frame = tk.Frame(left_frame, bg=MAIN_BG)
        btn_frame.pack(side="top", fill="x", pady=(6, 0))

        self.btn_add_item = ttk.Button(btn_frame, text=self.getText("btn_add"), command=self.add_item)
        self.btn_add_item.pack(side="left", padx=3)

        self.btn_del_item = ttk.Button(btn_frame, text=self.getText("btn_del"), command=self.delete_item)
        self.btn_del_item.pack(side="right", padx=3)

        # ---- 中间区域：当前物品属性编辑 ----
        self.build_item_detail_area(left_frame)

    def build_item_detail_area(self, left_frame):
        """中间区域：上方为物品基本属性（除ID外可编辑），下方为刷新分布，底部为保存按钮。
        未选中物品时不显示表单，只显示"请先选择物品"占位"""
        right_frame = tk.Frame(self.page_container, bg=MAIN_BG)
        right_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)

        # 占位提示（未选中时显示，覆盖整个中间区域）
        self.detail_placeholder = tk.Label(right_frame, text=self.getText("select_item_first"),
                                           bg=MAIN_BG, fg="#888888")
        self.detail_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # 编辑表单（选中时显示的整个区域）
        form = tk.Frame(right_frame, bg=MAIN_BG)
        self.detail_form = form

        # ---- 基本属性区 ----
        prop_title = tk.Label(form, text=self.getText("basic_attrs"), bg=MAIN_BG, fg="#333333")
        prop_title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # ID（只读）
        tk.Label(form, text=self.getText("field_id"), bg=MAIN_BG).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=3)
        self.detail_id_var = tk.StringVar()
        tk.Entry(form, textvariable=self.detail_id_var, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(0, 10), pady=3)

        # 物品名（可编辑）
        tk.Label(form, text=self.getText("field_name"), bg=MAIN_BG).grid(row=2, column=0, sticky="w", padx=(0, 10), pady=3)
        self.detail_name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.detail_name_var).grid(
            row=2, column=1, sticky="ew", padx=(0, 10), pady=3)

        # 图标（可编辑，下拉列表）
        tk.Label(form, text=self.getText("field_icon"), bg=MAIN_BG).grid(row=3, column=0, sticky="w", padx=(0, 10), pady=3)
        self.detail_icon_var = tk.StringVar()
        self.detail_icon_combo = ttk.Combobox(form, textvariable=self.detail_icon_var,
                                              state="readonly")
        self.detail_icon_combo["values"] = self.get_icon_images()
        self.detail_icon_combo.grid(row=3, column=1, sticky="ew", padx=(0, 10), pady=3)

        # 重量（可编辑，数字）
        tk.Label(form, text=self.getText("field_weight"), bg=MAIN_BG).grid(row=4, column=0, sticky="w", padx=(0, 10), pady=3)
        self.detail_weight_var = tk.StringVar()
        tk.Entry(form, textvariable=self.detail_weight_var).grid(
            row=4, column=1, sticky="ew", padx=(0, 10), pady=3)

        form.columnconfigure(1, weight=1)

        # ---- 分割线 ----
        sep = ttk.Separator(form, orient="horizontal")
        sep.grid(row=5, column=0, columnspan=2, sticky="ew", pady=10)

        # ---- 图片 / 备注区域 ----
        other_title = tk.Label(form, text=self.getText("other_info"), bg=MAIN_BG, fg="#333333")
        other_title.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # 图片（下拉菜单，读取 textures 目录下所有 png）
        tk.Label(form, text=self.getText("field_flier_image"), bg=MAIN_BG).grid(row=7, column=0, sticky="nw", padx=(0, 10), pady=3)
        self.detail_image_var = tk.StringVar()
        self.detail_image_combo = ttk.Combobox(form, textvariable=self.detail_image_var,
                                               state="readonly")
        self.detail_image_combo["values"] = self.get_images_no_prefix()
        self.detail_image_combo.grid(row=7, column=1, sticky="ew", padx=(0, 10), pady=3)

        # 备注（带内部滚动条）
        tk.Label(form, text=self.getText("field_flier_note"), bg=MAIN_BG).grid(row=8, column=0, sticky="nw", padx=(0, 10), pady=3)
        remark_frame = tk.Frame(form, bg=MAIN_BG)
        remark_frame.grid(row=8, column=1, sticky="ew", padx=(0, 10), pady=3)
        remark_frame.columnconfigure(0, weight=1)
        self.detail_remark_text = tk.Text(remark_frame, width=40, height=6, wrap="word")
        self.detail_remark_scroll = ttk.Scrollbar(remark_frame, orient="vertical",
                                                  command=self.detail_remark_text.yview)
        self.detail_remark_text.configure(yscrollcommand=self.detail_remark_scroll.set)
        self.detail_remark_text.grid(row=0, column=0, sticky="nsew")
        self.detail_remark_scroll.grid(row=0, column=1, sticky="ns")

        # ---- 备注下方分割线 ----
        sep2 = ttk.Separator(form, orient="horizontal")
        sep2.grid(row=9, column=0, columnspan=2, sticky="ew", pady=8)

        # ---- 刷新分布区域 ----
        tk.Label(form, text=self.getText("dist_title"), bg=MAIN_BG, fg="#333333").grid(
            row=11, column=0, columnspan=2, sticky="w", pady=(0, 4))

        dist_frame = tk.Frame(form, bg=MAIN_BG)
        dist_frame.grid(row=12, column=0, columnspan=2, sticky="ew", padx=(0, 10), pady=3)
        dist_frame.columnconfigure(0, weight=1)
        self.dist_tree = ttk.Treeview(dist_frame, columns=("container", "chance"), show="headings", height=5)
        self.dist_tree.heading("container", text=self.getText("edit_containers"))
        self.dist_tree.heading("chance", text=self.getText("edit_chance"))
        self.dist_tree.column("container", width=240, anchor="w")
        self.dist_tree.column("chance", width=80, anchor="center")
        self.dist_scroll = ttk.Scrollbar(dist_frame, orient="vertical", command=self.dist_tree.yview)
        self.dist_tree.configure(yscrollcommand=self.dist_scroll.set)
        self.dist_tree.grid(row=0, column=0, sticky="nsew")
        self.dist_scroll.grid(row=0, column=1, sticky="ns")

        ttk.Button(form, text=self.getText("add_container"), command=self.open_add_container).grid(
            row=13, column=0, sticky="w", padx=(0, 10), pady=4)

        # ---- 保存按钮（位于"刷新分布"信息区域下方）----
        sep4 = ttk.Separator(form, orient="horizontal")
        sep4.grid(row=14, column=0, columnspan=2, sticky="ew", pady=8)

        ttk.Button(form, text=self.getText("btn_save"), command=self.save_item_detail).grid(
            row=15, column=0, sticky="w", padx=(0, 10), pady=4)

        # 底部留白，让上方内容保持在上部
        form.rowconfigure(16, weight=1)

        # 默认未选中物品：隐藏表单，仅显示占位
        self.detail_form.place_forget()

    def add_item(self):
        """点击"新增"：打开新增物品子窗口（模态，父窗口锁定）"""
        win = tk.Toplevel(self)
        win.title(self.getText("add_item_title"))
        win.configure(bg="#ffffff")
        win.transient(self)  # 依附主窗口
        win.resizable(False, False)
        win.grab_set()  # 锁定父窗口
        win.focus_set()

        # 居中显示
        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        # ---- 表单区域（提示文本在上，输入框在下）----
        form_frame = tk.Frame(win, bg="#ffffff")
        form_frame.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        id_var = tk.StringVar()
        name_var = tk.StringVar()
        icon_var = tk.StringVar()
        weight_var = tk.StringVar(value="0.05")

        # 输入校验函数
        def validate_id(new_text):
            """ID 只能输入英文、数字和下划线"""
            return re.fullmatch(r"[A-Za-z0-9_]*", new_text) is not None

        def validate_weight(new_text):
            """重量只能输入数字和小数点"""
            return re.fullmatch(r"\d*\.?\d*", new_text) is not None

        row = 0

        # ID（英文数字下划线）
        tk.Label(form_frame, text=self.getText("id_label"), bg="#ffffff", anchor="w").grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))
        row += 1
        id_entry = ttk.Entry(form_frame, textvariable=id_var, width=30,
                             validate="key", validatecommand=(win.register(validate_id), "%P"))
        id_entry.grid(row=row, column=0, sticky="w", padx=5, pady=(0, 5))
        row += 1

        # 物品名（DisplayName）
        tk.Label(form_frame, text=self.getText("name_label"), bg="#ffffff", anchor="w").grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))
        row += 1
        name_entry = ttk.Entry(form_frame, textvariable=name_var, width=30)
        name_entry.grid(row=row, column=0, sticky="w", padx=5, pady=(0, 5))
        row += 1

        # 图标（Icon，下拉列表，只能选择，不可编辑）
        tk.Label(form_frame, text=self.getText("icon_label"), bg="#ffffff", anchor="w").grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))
        row += 1
        icon_combo = ttk.Combobox(form_frame, textvariable=icon_var, width=28, state="readonly")
        icon_combo["values"] = self.get_icon_images()
        icon_combo.grid(row=row, column=0, sticky="w", padx=5, pady=(0, 5))
        row += 1

        # 重量（Weight，数字，不能小于0）
        tk.Label(form_frame, text=self.getText("weight_label"), bg="#ffffff", anchor="w").grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))
        row += 1
        weight_entry = ttk.Entry(form_frame, textvariable=weight_var, width=30,
                                 validate="key", validatecommand=(win.register(validate_weight), "%P"))
        weight_entry.grid(row=row, column=0, sticky="w", padx=5, pady=(0, 5))
        row += 1

        id_entry.focus_set()

        # ---- 确定 / 取消按钮（确定靠左，取消靠右）----
        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        def on_ok():
            item_id = id_var.get().strip()
            item_name = name_var.get().strip()
            item_icon = icon_var.get().strip()
            item_weight = weight_var.get().strip()

            if not item_id:
                messagebox.showwarning(self.getText("title_info"), self.getText("id_empty"), parent=win)
                return
            # 物品ID重名判断
            for got in self.items_data.values():
                if got["id"] == item_id:
                    messagebox.showwarning(self.getText("title_info"), self.getText("id_exists").format(item_id), parent=win)
                    return
            if not item_name:
                messagebox.showwarning(self.getText("title_info"), self.getText("name_empty"), parent=win)
                return
            if not item_weight:
                item_weight = "0"
            try:
                weight = float(item_weight)
            except ValueError:
                messagebox.showwarning(self.getText("title_info"), self.getText("weight_num"), parent=win)
                return
            if weight < 0:
                messagebox.showwarning(self.getText("title_info"), self.getText("weight_neg"), parent=win)
                return

            # TODO: 后续根据模板生成物品代码
            iid = self.items_tree.insert("", "end", values=(item_name,))
            self.items_data[iid] = {
                "id": item_id,
                "name": item_name,
                "icon": item_icon,
                "weight": item_weight,
                "image": "",
                "remark": "",
                "containers": {},
            }
            self.refresh_generated_files()
            win.destroy()

        def on_cancel():
            win.destroy()

        ttk.Button(btn_frame, text=self.getText("btn_ok"), command=on_ok).pack(side="left", padx=3)
        ttk.Button(btn_frame, text=self.getText("btn_cancel"), command=on_cancel).pack(side="right", padx=3)

    def delete_item(self):
        """点击"删除"：删除选中的物品"""
        selected = self.items_tree.selection()
        if not selected:
            messagebox.showwarning(self.getText("title_delete"), self.getText("del_select_item"))
            return
        for item in selected:
            self.items_data.pop(item, None)
            self.items_tree.delete(item)
            if item == self.current_item:
                self.current_item = None
                self.clear_item_detail()
        self.refresh_generated_files()

    def get_texture_files(self, require_item_prefix):
        """读取当前项目 media/textures 目录下 png 图片文件名，文件名符合要求。
        require_item_prefix=True 只取以 Item_ 开头的；False 只取无 Item_ 前缀的"""
        if not self.current_project:
            return []
        result = []
        for f in self.get_texture_files_all(require_item_prefix):
            base = os.path.splitext(f)[0]
            if re.fullmatch(r"[A-Za-z0-9_]+", base):
                result.append(f)
        return result

    def get_texture_files_all(self, require_item_prefix):
        """返回匹配前缀分类的所有 png（含不符合命名要求的），用于列表中展示以便重命名"""
        if not self.current_project:
            return []
        tex_dir = os.path.join(self.current_project, "media", "textures")
        if not os.path.isdir(tex_dir):
            return []
        result = []
        for f in sorted(os.listdir(tex_dir)):
            if not f.lower().endswith(".png"):
                continue
            base = os.path.splitext(f)[0]
            if base.startswith("Item_") == require_item_prefix:
                result.append(f)
        return result

    def get_icon_images(self):
        """图标：只显示以 Item_ 前缀命名且文件名符合要求的 png"""
        return self.get_texture_files(True)

    def get_images_no_prefix(self):
        """图片：只显示无 Item_ 前缀且文件名符合要求的 png"""
        return self.get_texture_files(False)

    def load_items_from_files(self):
        """每次打开物品界面时，从 Items.txt 读取物品列表，并从 FlierData.lua 补充图片、备注"""
        self.items_data = {}
        if not self.current_project:
            return
        txt_path = self._find_project_file(os.path.join("media", "scripts"), "*Items.txt")
        if not txt_path or not os.path.isfile(txt_path):
            return
        bindings = self.load_flier_data_bindings()
        containers = self.load_item_containers_in_file()
        with open(txt_path, encoding="utf-8") as f:
            content = f.read()
        idx = 0
        for m in re.finditer(r"item\s+([A-Za-z0-9_]+)\s*\{(.*?)\}", content, re.S):
            key = str(idx)
            idx += 1
            item_id = m.group(1)
            block = m.group(2)
            bind = bindings.get(item_id, {})
            self.items_data[key] = {
                "id": item_id,
                "name": self._extract_kv(block, "DisplayName"),
                "icon": self._item_value_to_icon(self._extract_kv(block, "Icon")),
                "weight": self._extract_kv(block, "Weight"),
                "image": bind.get("image", ""),
                "remark": bind.get("note", ""),
                "containers": containers.get(item_id, {}),
            }

    def load_flier_data_bindings(self):
        """解析项目内 FlierData.lua，返回 {物品ID: {image, note}}"""
        result = {}
        if not self.current_project:
            return result
        data_path = self._find_project_file(os.path.join("media", "lua", "client"), "*FlierData.lua")
        if not data_path or not os.path.isfile(data_path):
            return result
        with open(data_path, encoding="utf-8") as f:
            content = f.read()
        for m in re.finditer(r'\["Base\.([^"]+)"\]\s*=\s*\{(.*?)\}', content, re.S):
            item_id = m.group(1)
            block = m.group(2)
            img = re.search(r"'image'\s*=\s*\"([^\"]*)\"|image\s*=\s*\"([^\"]*)\"", block)
            note_match = re.search(r"'note'\s*=\s*\"([^\"]*)\"|note\s*=\s*\"([^\"]*)\"", block)
            note_val = (note_match.group(1) or note_match.group(2) or "") if note_match else ""
            raw_img = (img.group(1) or img.group(2) or "") if img else ""
            # 只保留文件名，去掉可能累积的 media/textures/ 路径前缀
            image = os.path.basename(raw_img.strip().rstrip("/\\")) if raw_img.strip() else ""
            result[item_id] = {
                "image": image,
                "note": self._resolve_note_text(item_id, note_val),
            }
        return result

    def _resolve_note_text(self, item_id, note_val):
        """若 FlierData 的 note 是 IGUI_{id}_Note 键，则从翻译文件取回真实文本"""
        key = f"IGUI_{item_id}_Note"
        if note_val == key:
            cn_data = self._read_json(self._translate_file("CN", "IG_UI.json"))
            if key in cn_data:
                return cn_data[key]
        return note_val

    def _extract_kv(self, block, key):
        """从 item 块中提取某个键的值（如 DisplayName 等），找不到返回空串"""
        m = re.search(rf"{key}\s*=\s*([^,\n]+)", block)
        return m.group(1).strip() if m else ""

    def on_item_select(self, _event=None):
        """点击物品列表项后，把右边物品信息编辑区域填充上具体信息"""
        selected = self.items_tree.selection()
        if not selected:
            self.show_detail_placeholder()
            return
        iid = selected[0]
        data = self.items_data.get(iid)
        if not data:
            return
        self.current_item = iid
        self.detail_id_var.set(data.get("id", ""))
        self.detail_name_var.set(data.get("name", ""))
        self.detail_icon_var.set(data.get("icon", ""))
        self.detail_weight_var.set(data.get("weight", ""))
        self.detail_image_var.set(data.get("image", ""))
        self.detail_remark_text.delete("1.0", "end")
        remark = data.get("remark", "").replace("<BR>", "\n")
        self.detail_remark_text.insert("1.0", remark)
        self.hide_detail_placeholder()
        self.refresh_dist_tree(iid)

    def show_detail_placeholder(self):
        """未选中物品：隐藏编辑表单，只显示"请先选择物品"占位"""
        if hasattr(self, "detail_placeholder"):
            self.detail_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        if hasattr(self, "detail_form"):
            self.detail_form.place_forget()

    def hide_detail_placeholder(self):
        """选中物品：隐藏占位，显示编辑表单"""
        if hasattr(self, "detail_placeholder"):
            self.detail_placeholder.place_forget()
        if hasattr(self, "detail_form"):
            self.detail_form.place(relx=0, rely=0, relwidth=1, relheight=1, anchor="nw")

    def refresh_dist_tree(self, iid):
        """刷新当前物品的刷新分布列表（容器列显示容器名）"""
        if not hasattr(self, "dist_tree"):
            return
        self.dist_tree.delete(*self.dist_tree.get_children())
        name_map = {c["ID"]: c["name"] for c in self._get_container_candidates()}
        data = self.items_data.get(iid) or {}
        for cid, chance in (data.get("containers") or {}).items():
            self.dist_tree.insert("", "end", values=(name_map.get(cid, cid), chance))

    def clear_item_detail(self):
        """清空右侧物品信息编辑区域"""
        if not hasattr(self, "detail_id_var"):
            return
        self.detail_id_var.set("")
        self.detail_name_var.set("")
        self.detail_icon_var.set("")
        self.detail_weight_var.set("")
        self.detail_image_var.set("")
        self.detail_remark_text.delete("1.0", "end")
        self.show_detail_placeholder()
        if hasattr(self, "dist_tree"):
            self.dist_tree.delete(*self.dist_tree.get_children())

    # ---- 刷新分布（容器）相关 ----
    def _get_container_candidates(self):
        """读取 src/containers.json，返回容器候选列表 [{"name","ID"}]"""
        path = os.path.join(SRC_DIR, "containers.json")
        data = self._read_json(path)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict) and d.get("ID")]
        return []

    def load_item_containers_in_file(self):
        """解析项目 Distribution.lua，返回 {物品ID: {容器ID: 几率}}"""
        result = {}
        if not self.current_project:
            return result
        path = self._find_project_file(
            os.path.join("media", "lua", "server", "Items"), "*Distribution.lua"
        )
        if not path or not os.path.isfile(path):
            return result
        with open(path, encoding="utf-8") as f:
            content = f.read()
        entry_re = re.compile(
            r'table\.insert\(ProceduralDistributions\.list\["([^"]+)"\]\.items,\s*"Base\.([^"]+)"\s*\);\s*'
            r'table\.insert\(ProceduralDistributions\.list\["([^"]+)"\]\.items,\s*\{?(\d+)\}?\s*\);', re.S)
        for m in entry_re.finditer(content):
            cid, item_id, row_cid, chance = m.group(1), m.group(2), m.group(3), m.group(4)
            if cid != row_cid:
                continue
            result.setdefault(item_id, {})[cid] = int(chance)
        return result

    def open_add_container(self):
        """弹子窗口：为当前物品添加刷新分布的容器与几率"""
        if not self.current_item:
            messagebox.showwarning(self.getText("title_info"), self.getText("save_select_first"))
            return
        data = self.items_data[self.current_item]
        candidates = self._get_container_candidates()
        used = set((data.get("containers") or {}).keys())
        available = [c for c in candidates if c["ID"] not in used]

        win = tk.Toplevel(self)
        win.title(self.getText("add_container_title"))
        win.configure(bg="#ffffff")
        win.transient(self)
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        form = tk.Frame(win, bg="#ffffff")
        form.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # 容器（下拉，排除当前物品已使用的容器）
        tk.Label(form, text=self.getText("container_label"), bg="#ffffff", anchor="w").grid(
            row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        cont_var = tk.StringVar()
        cont_combo = ttk.Combobox(form, textvariable=cont_var, width=42, state="readonly")
        cont_combo["values"] = [c["name"] for c in available]
        cont_combo.grid(row=1, column=0, sticky="w", padx=5, pady=(0, 5))

        # 几率（整数 1-100）
        tk.Label(form, text=self.getText("chance_label"), bg="#ffffff", anchor="w").grid(
            row=2, column=0, sticky="w", padx=5, pady=(5, 0))

        def validate_chance(new_text):
            return re.fullmatch(r"\d{0,3}", new_text) is not None

        chance_var = tk.StringVar()
        chance_entry = ttk.Entry(form, textvariable=chance_var, width=12,
                                 validate="key", validatecommand=(win.register(validate_chance), "%P"))
        chance_entry.grid(row=3, column=0, sticky="w", padx=5, pady=(0, 5))

        def on_ok():
            sel = cont_combo.current()
            if sel < 0:
                messagebox.showwarning(self.getText("title_info"), self.getText("need_select_container"), parent=win)
                return
            try:
                chance = int(chance_var.get())
            except ValueError:
                messagebox.showwarning(self.getText("title_info"), self.getText("chance_int"), parent=win)
                return
            if chance < 1 or chance > 100:
                messagebox.showwarning(self.getText("title_info"), self.getText("chance_range"), parent=win)
                return
            data.setdefault("containers", {})[available[sel]["ID"]] = chance
            self.refresh_generated_files()
            win.destroy()
            if self.current_item:
                self.refresh_dist_tree(self.current_item)

        def on_cancel():
            win.destroy()

        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text=self.getText("btn_ok"), command=on_ok).pack(side="left", padx=3)
        ttk.Button(btn_frame, text=self.getText("btn_cancel"), command=on_cancel).pack(side="right", padx=3)

    # ---- 生成物品脚本与 FlierData ----
    def _find_project_file(self, rel_dir, pattern):
        """在当前项目目录下按 glob 模式查找文件，返回第一个匹配路径（无则 None）"""
        folder = os.path.join(self.current_project, rel_dir)
        if not os.path.isdir(folder):
            return None
        files = glob.glob(os.path.join(folder, pattern))
        return files[0] if files else None

    def _icon_to_item_value(self, name):
        """把内部完整图标文件名（如 Item_aaa.png）转为 Items.txt 中 Icon 的值（aaa，无前缀无后缀）"""
        base = os.path.splitext((name or ""))[0]
        if base.startswith("Item_"):
            base = base[5:]
        return base

    def _item_value_to_icon(self, value):
        """把 Items.txt 读到的 Icon 值（无前缀无后缀，如 aaa）还原为内部完整文件名（如 Item_aaa.png）"""
        value = (value or "").strip()
        if not value or not self.current_project:
            return value
        base = value if value.startswith("Item_") else "Item_" + value
        candidate = os.path.join(self.current_project, "media", "textures", base + ".png")
        if os.path.isfile(candidate):
            return base + ".png"
        return value

    def generate_items_txt(self):
        """根据物品数据生成 Items.txt（物品脚本，参考模板第一段代码）"""
        if not self.current_project:
            return
        txt_path = self._find_project_file(os.path.join("media", "scripts"), "*Items.txt")
        if not txt_path:
            return

        lines = ["module Base"]
        lines.append("{")
        for data in self.items_data.values():
            lines.append(f"\titem {data.get('id', '')}")
            lines.append("\t{")
            lines.append("\t\tItemType = base:normal,")
            lines.append(f"\t\tDisplayName = {data.get('name', '')},")
            lines.append(f"\t\tIcon = {self._icon_to_item_value(data.get('icon', ''))},")
            lines.append(f"\t\tWeight = {data.get('weight', '0')},")
            lines.append("\t}")
        lines.append("}")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _png_size(self, path):
        """读取 PNG 图片尺寸，返回 (width, height)；解析失败返回 None"""
        try:
            with open(path, "rb") as f:
                header = f.read(24)
            if header[:8] != b"\x89PNG\r\n\x1a\n":
                return None
            return (int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big"))
        except Exception:
            return None

    def generate_flier_data(self):
        """生成 FlierData.lua（物品与图片、备注的绑定关系，参考模板第三段代码）"""
        if not self.current_project:
            return
        data_path = self._find_project_file(os.path.join("media", "lua", "client"), "*FlierData.lua")
        if not data_path:
            return

        lines = ["FlierData = {"]
        for data in self.items_data.values():
            item_id = data.get("id", "")
            image = data.get("image", "").strip()
            image_value = f"media/textures/{image}" if image else ""
            note_key = f"IGUI_{item_id}_Note"
            # 读取图片真实宽高，供游戏内创建窗口时按比例显示（避免竖屏图片被放大超出屏幕）
            width = height = 0
            if image:
                size = self._png_size(os.path.join(self.current_project, "media", "textures", image))
                if size:
                    width, height = size
            lines.append(f"\t[\"Base.{item_id}\"] = {{")
            lines.append(f"\t\timage = \"{image_value}\",")
            lines.append(f"\t\twidth = {width},")
            lines.append(f"\t\theight = {height},")
            lines.append(f"\t\tnote = \"{note_key}\"")
            lines.append("\t},")
        lines.append("}")

        with open(data_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _read_json(self, filepath):
        """读取 json 文件，不存在或解析失败返回空字典"""
        if not filepath or not os.path.isfile(filepath):
            return {}
        try:
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_json(self, filepath, data):
        """把字典写回 json 文件"""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _translate_file(self, lang, filename):
        """返回翻译文件路径：项目/media/lua/shared/Translate/{lang}/{filename}"""
        return os.path.join(
            self.current_project, "media", "lua", "shared", "Translate", lang, filename
        )

    def generate_translate_files(self):
        """生成翻译文件：
        - ItemName.json：写入 "Base.{物品ID}":"{物品名}"
        - IG_UI.json：写入 "IGUI_{物品ID}_Note":"{传单备注}"（保留原有默认项）
        对 CN 与 EN 两个语言目录都写入"""
        if not self.current_project:
            return
        for lang in ("CN", "EN"):
            lang_dir = os.path.join(
                self.current_project, "media", "lua", "shared", "Translate", lang
            )
            if not os.path.isdir(lang_dir):
                continue
            item_name_path = os.path.join(lang_dir, "ItemName.json")
            ig_ui_path = os.path.join(lang_dir, "IG_UI.json")
            item_name_data = self._read_json(item_name_path)
            ig_ui_data = self._read_json(ig_ui_path)
            for data in self.items_data.values():
                item_id = data.get("id", "")
                item_name_data[f"Base.{item_id}"] = data.get("name", "")
                ig_ui_data[f"IGUI_{item_id}_Note"] = data.get("remark", "").replace("\n", "<BR>")
            self._write_json(item_name_path, item_name_data)
            self._write_json(ig_ui_path, ig_ui_data)

    def generate_distribution_lua(self):
        """生成 Distribution.lua：为每个物品的容器写入刷新分布代码（参考模板）"""
        if not self.current_project:
            return
        path = self._find_project_file(
            os.path.join("media", "lua", "server", "Items"), "*Distribution.lua"
        )
        if not path:
            return

        lines = ["require \"Items/ProceduralDistributions\"", ""]
        for data in self.items_data.values():
            item_id = data.get("id", "")
            for cid, chance in (data.get("containers") or {}).items():
                lines.append(f"table.insert(ProceduralDistributions.list[\"{cid}\"].items, \"Base.{item_id}\");")
                lines.append(f"table.insert(ProceduralDistributions.list[\"{cid}\"].items, {chance});")
                lines.append("")

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def refresh_generated_files(self):
        """增删、保存物品后重新生成 Items.txt、FlierData.lua、翻译文件与 Distribution.lua"""
        self.generate_items_txt()
        self.generate_flier_data()
        self.generate_translate_files()
        self.generate_distribution_lua()

    def save_item_detail(self):
        """保存当前物品的编辑信息到对应文件"""
        if not self.current_item:
            messagebox.showwarning(self.getText("title_save"), self.getText("save_select_first"))
            return
        data = self.items_data[self.current_item]
        data["name"] = self.detail_name_var.get().strip()
        data["icon"] = self.detail_icon_var.get().strip()
        data["weight"] = self.detail_weight_var.get().strip()
        data["image"] = self.detail_image_var.get().strip()
        data["remark"] = self.detail_remark_text.get("1.0", "end").strip()
        # 同步更新列表显示名
        self.items_tree.item(self.current_item, values=(data["name"],))
        self.refresh_generated_files()
        messagebox.showinfo(self.getText("title_save"), self.getText("saved_item"))

    def show_images_page(self):
        """图片页面：左侧图片列表，右侧画布缩略图预览（仅无 Item_ 前缀的图片）"""
        self.show_texture_page("images")

    def show_icon_page(self):
        """图标页面：左侧图标列表，右侧画布缩略图预览（仅 Item_ 前缀的图标）"""
        self.show_texture_page("icons")

    def _invalid_texture_names(self, require_item_prefix):
        """识别该分类下文件名不符合要求的 png（用于显示提示）"""
        tex_dir = os.path.join(self.current_project, "media", "textures")
        invalid = []
        if os.path.isdir(tex_dir):
            for f in os.listdir(tex_dir):
                if not f.lower().endswith(".png"):
                    continue
                base = os.path.splitext(f)[0]
                if base.startswith("Item_") != require_item_prefix:
                    continue
                if re.fullmatch(r"[A-Za-z0-9_]+", base) is None:
                    invalid.append(f)
        return invalid

    def show_texture_page(self, mode):
        """图片/图标共用的列表 + 画布页面。mode: 'images' 或 'icons'"""
        self.clear_page_container()
        self.image_page_mode = mode

        is_icon = (mode == "icons")
        heading = self.getText("list_icons") if is_icon else self.getText("list_images")
        file_list = self.get_texture_files_all(is_icon)

        # ---- 非法文件名提示（有非法则显示，否则隐藏）----
        if self._invalid_texture_names(is_icon):
            tk.Label(
                self.page_container,
                text=self.getText("invalid_name_warning"),
                bg="#000000", fg="#ff0000", font=("", 11, "bold"),
            ).pack(side="top", fill="x", padx=10, pady=(10, 0))

        # ---- 左侧列表 ----
        left_frame = tk.Frame(self.page_container, bg=MAIN_BG)
        left_frame.pack(side="left", fill="y", padx=10, pady=10)

        tree_frame = tk.Frame(left_frame, bg=MAIN_BG)
        tree_frame.pack(side="top", fill="both", expand=True)

        self.images_tree = ttk.Treeview(tree_frame, columns=("name",), show="headings", height=15)
        self.images_tree.heading("name", text=heading)
        self.images_tree.column("name", width=220, anchor="w")
        self.images_tree.pack(side="left", fill="y")
        self.images_tree.bind("<Button-3>", self.image_list_right_click)
        self._image_menu = None  # 右键菜单引用

        self.image_list = file_list
        for name in file_list:
            self.images_tree.insert("", "end", iid=name, values=(name,))

        # 列表下方按钮
        btn_frame = tk.Frame(left_frame, bg=MAIN_BG)
        btn_frame.pack(side="top", fill="x", pady=(6, 0))
        ttk.Button(btn_frame, text=self.getText("btn_add"), command=self.add_image).pack(side="left", padx=3)
        ttk.Button(btn_frame, text=self.getText("btn_del"), command=self.delete_image).pack(side="right", padx=3)

        # ---- 右侧大画布缩略图 ----
        self.build_image_canvas()

    def build_image_canvas(self):
        """中间区域：滚动画布，展示当前分类所有图片的缩小预览图，可点击查看大图"""
        canvas_frame = tk.Frame(self.page_container, bg=MAIN_BG)
        canvas_frame.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.img_canvas = tk.Canvas(canvas_frame, bg=MAIN_BG, highlightthickness=0)
        xbar = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.img_canvas.xview)
        ybar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.img_canvas.yview)
        self.img_canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)

        self.img_canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")

        inner = tk.Frame(self.img_canvas, bg=MAIN_BG)
        self._img_inner = inner
        self._img_window = self.img_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: self.img_canvas.configure(scrollregion=self.img_canvas.bbox("all")))

        def _fit_width(e):
            self.img_canvas.itemconfigure(self._img_window, width=e.width)
        self.img_canvas.bind("<Configure>", _fit_width)

        # 缩略图
        self.image_page_photos = []  # 保持引用防止被回收
        for i, name in enumerate(self.image_list):
            thumb = self._make_thumbnail(name)
            if thumb is None:
                continue
            self.image_page_photos.append(thumb)
            lbl = tk.Label(inner, image=thumb, bg=MAIN_BG, cursor="hand2", bd=1, relief="solid")
            name_lbl = tk.Label(inner, text=name, bg=MAIN_BG, fg="#555555")
            row = i // 4
            col = i % 4
            lbl.grid(row=row * 2, column=col, padx=6, pady=(6, 2))
            name_lbl.grid(row=row * 2 + 1, column=col, pady=(0, 6))
            lbl.bind("<Button-1>", lambda e, n=name: self.show_full_image(n))

    def _make_thumbnail(self, name):
        """生成某张图片的缩略图 PhotoImage，最大边约 120px"""
        path = os.path.join(self.current_project, "media", "textures", name)
        if not os.path.isfile(path):
            return None
        try:
            img = tk.PhotoImage(file=path)
        except Exception:
            return None
        w, h = img.width(), img.height()
        if w <= 0 or h <= 0:
            return None
        max_s = 120
        factor = max(int(max(w / max_s, h / max_s)), 1)
        if factor > 1:
            img = img.subsample(factor, factor)
        return img

    def show_full_image(self, name):
        """点击缩略图：打开子窗口显示完整大图"""
        path = os.path.join(self.current_project, "media", "textures", name)
        if not os.path.isfile(path):
            return
        win = tk.Toplevel(self)
        win.title(name)
        win.transient(self)
        try:
            img = tk.PhotoImage(file=path)
        except Exception as e:
            messagebox.showerror(self.getText("preview"), f"{e}")
            win.destroy()
            return

        # 图片过大时缩小，保证能展示出全部内容
        w, h = img.width(), img.height()
        if w > 0 and h > 0:
            max_w = self.winfo_screenwidth() - 120
            max_h = self.winfo_screenheight() - 120
            factor = max(int(max(w / max_w, h / max_h)), 1)
            if factor > 1:
                img = img.subsample(factor, factor)

        win._img = img  # 保持引用
        tk.Label(win, image=img).pack()

    def add_image(self):
        """新增图片/图标：文件选择器选择 png 复制到 textures 目录，图标模式无 Item_ 前缀时自动加前缀；重名则失败"""
        if not self.current_project:
            return
        is_icon = (self.image_page_mode == "icons")
        title = self.getText("select_icon") if is_icon else self.getText("select_image")
        path = filedialog.askopenfilename(title=title, filetypes=[(self.getText("image_filter"), "*.png")])
        if not path:
            return
        tex_dir = os.path.join(self.current_project, "media", "textures")
        if not os.path.isdir(tex_dir):
            os.makedirs(tex_dir)
        base, ext = os.path.splitext(os.path.basename(path))
        # 图标：若所选文件名尚无 Item_ 前缀则补上；已有则不重复添加
        if is_icon and not base.startswith("Item_"):
            base = "Item_" + base
        new_name = base + ext
        dst = os.path.join(tex_dir, new_name)
        # 重名判断：已存在则添加失败并提示
        if os.path.exists(dst):
            messagebox.showwarning(self.getText("title_add"), self.getText("add_dup").format(new_name), parent=self)
            return
        shutil.copy2(path, dst)
        self.show_texture_page(self.image_page_mode)

    def delete_image(self):
        """删除图片/图标：删除选中的 png 文件"""
        selected = self.images_tree.selection()
        if not selected:
            messagebox.showwarning(self.getText("title_delete"), self.getText("del_select_image"))
            return
        if not messagebox.askyesno(self.getText("title_delete"), self.getText("del_confirm")):
            return
        tex_dir = os.path.join(self.current_project, "media", "textures")
        for name in selected:
            p = os.path.join(tex_dir, name)
            try:
                if os.path.isfile(p):
                    os.remove(p)
            except Exception as e:
                messagebox.showerror(self.getText("title_delete"), self.getText("del_fail").format(name, e))
        self.show_texture_page(self.image_page_mode)

    def image_list_right_click(self, event):
        """图片列表右键菜单"""
        iid = self.images_tree.identify_row(event.y)
        if not iid:
            return
        self.images_tree.selection_set(iid)
        self.images_tree.focus(iid)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label=self.getText("rename_title"), command=lambda: self.rename_image(iid))
        self._image_menu = menu  # 保持引用防止被回收
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def rename_image(self, iid):
        """重命名图片/图标：弹出模态子窗口输入新名称"""
        tex_dir = os.path.join(self.current_project, "media", "textures")
        src = os.path.join(tex_dir, iid)
        if not os.path.isfile(src):
            return

        win = tk.Toplevel(self)
        win.title(self.getText("rename_title"))
        win.configure(bg="#ffffff")
        win.transient(self)
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        old_base = os.path.splitext(iid)[0]

        form = tk.Frame(win, bg="#ffffff")
        form.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        tk.Label(form, text=self.getText("label_name"), bg="#ffffff", anchor="w").pack(side="top", fill="x", pady=(0, 4))

        name_var = tk.StringVar(value=old_base)
        entry = ttk.Entry(form, textvariable=name_var, width=30)
        entry.pack(side="top", fill="x")
        entry.focus_set()
        entry.select_range(0, "end")

        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        def on_ok():
            new_base = name_var.get().strip()
            if not new_base:
                messagebox.showwarning(self.getText("title_info"), self.getText("rename_empty"), parent=win)
                return
            if not re.fullmatch(r"[A-Za-z0-9_]+", new_base):
                messagebox.showwarning(self.getText("title_info"), self.getText("rename_invalid"), parent=win)
                return
            new_name = new_base + ".png"
            dst = os.path.join(tex_dir, new_name)
            if new_name != iid and os.path.exists(dst):
                messagebox.showwarning(self.getText("title_info"), self.getText("rename_exists"), parent=win)
                return
            try:
                os.rename(src, dst)
            except Exception as e:
                messagebox.showerror(self.getText("title_info"), self.getText("rename_fail"), parent=win)
                return
            win.destroy()
            self.show_texture_page(self.image_page_mode)

        def on_cancel():
            win.destroy()

        ttk.Button(btn_frame, text=self.getText("btn_ok"), command=on_ok).pack(side="left", padx=3)
        ttk.Button(btn_frame, text=self.getText("btn_cancel"), command=on_cancel).pack(side="right", padx=3)

    def show_refresh_page(self):
        """刷新页面"""
        label = tk.Label(self.page_container, text=self.getText("page_refresh"), bg=MAIN_BG, fg="#333333")
        label.pack(expand=True)

    def new_project(self):
        """新建项目：在 output 下创建 {日期}_{时间} 文件夹，并复制 src/media 到其中"""
        if self.current_project:
            if not messagebox.askyesno(self.getText("new_project"), self.getText("new_project_confirm")):
                return

        date_str = datetime.now().strftime("%Y%m%d")
        time_str = datetime.now().strftime("%H%M%S")
        project_name = f"{date_str}_{time_str}"
        project_dir = os.path.join(OUTPUT_DIR, project_name)

        try:
            os.makedirs(project_dir)
            shutil.copytree(MEDIA_DIR, os.path.join(project_dir, "media"))

            # 重命名项目内的 Flier.lua 为 {日期_时间}Flier.lua
            flier_src = os.path.join(project_dir, "media", "lua", "client", "Flier.lua")
            flier_dst = os.path.join(project_dir, "media", "lua", "client", f"{project_name}Flier.lua")
            if os.path.exists(flier_src):
                os.rename(flier_src, flier_dst)
                # 在 Flier.lua 开头导入 {日期_时间}FlierData.lua（不带后缀）
                require_line = f'require "{project_name}FlierData"\n'
                with open(flier_dst, "r", encoding="utf-8") as f:
                    content = f.read()
                with open(flier_dst, "w", encoding="utf-8") as f:
                    f.write(require_line + content)

            # 重命名项目内的 FlierData.lua 为 {日期_时间}FlierData.lua
            data_src = os.path.join(project_dir, "media", "lua", "client", "FlierData.lua")
            data_dst = os.path.join(project_dir, "media", "lua", "client", f"{project_name}FlierData.lua")
            if os.path.exists(data_src):
                os.rename(data_src, data_dst)

            # 重命名项目内的 Items.txt 为 {日期_时间}Items.txt
            items_src = os.path.join(project_dir, "media", "scripts", "Items.txt")
            items_dst = os.path.join(project_dir, "media", "scripts", f"{project_name}Items.txt")
            if os.path.exists(items_src):
                os.rename(items_src, items_dst)

            # 重命名项目内的 Distribution.lua 为 {日期_时间}Distribution.lua
            dist_src = os.path.join(project_dir, "media", "lua", "server", "Items", "Distribution.lua")
            dist_dst = os.path.join(project_dir, "media", "lua", "server", "Items", f"{project_name}Distribution.lua")
            if os.path.exists(dist_src):
                os.rename(dist_src, dist_dst)
        except Exception as e:
            messagebox.showerror(self.getText("new_project_fail"), f"{e}")
            return

        self.current_project = project_dir
        self.update_title()
        messagebox.showinfo(self.getText("new_project"), self.getText("project_created").format(project_dir))
        self.show_project()

    def open_project(self):
        """打开项目：选择 output 下的一个项目文件夹"""
        project_dir = filedialog.askdirectory(
            initialdir=OUTPUT_DIR, title=self.getText("open_project")
        )
        if project_dir:
            self.current_project = project_dir
            self.update_title()
            self.show_project()

    def open_project_folder(self):
        """打开文件夹：在文件资源管理器中打开当前项目所在文件夹"""
        if not self.current_project:
            messagebox.showwarning(self.getText("title_open"), self.getText("open_folder_no_project"))
            return
        try:
            os.startfile(self.current_project)
        except Exception as e:
            messagebox.showerror(self.getText("title_open"), self.getText("open_folder_fail").format(e))

    def show_settings(self):
        """设置：弹出模态子窗口，显示当前游戏版本和语言选择"""
        version = self.config.get("version", self.getText("game_version"))

        win = tk.Toplevel(self)
        win.title(self.getText("settings_title"))
        win.configure(bg="#ffffff")
        win.transient(self)
        win.resizable(False, False)
        win.grab_set()
        win.focus_set()

        win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - win.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        form = tk.Frame(win, bg="#ffffff")
        form.pack(side="top", fill="both", expand=True, padx=20, pady=20)

        # 语言选择下拉菜单（lang_text 字典下的所有键）
        tk.Label(form, text=self.getText("language"), bg="#ffffff", anchor="w").pack(side="top", fill="x", pady=(0, 4))
        lang_var = tk.StringVar(value=self.language)
        lang_combo = ttk.Combobox(form, textvariable=lang_var, state="readonly")
        lang_vals = list(self.config.get("lang_text", {}).keys())
        lang_combo["values"] = lang_vals
        if self.language in lang_vals:
            lang_combo.current(lang_vals.index(self.language))
        lang_combo.pack(side="top", fill="x", pady=(0, 10))

        # 版本号显示
        tk.Label(form, text=self.getText("game_version"), bg="#ffffff", anchor="w").pack(side="top", fill="x", pady=(0, 4))
        tk.Label(form, text=version, bg="#ffffff", anchor="w", font=("", 12, "bold")).pack(side="top", fill="x")

        def on_switch():
            new_lang = lang_var.get()
            if new_lang:
                win.destroy()
                self.switch_language(new_lang)

        btn_frame = tk.Frame(win, bg="#ffffff")
        btn_frame.pack(side="bottom", fill="x", padx=20, pady=12)
        tk.Button(btn_frame, text=self.getText("btn_ok"), command=on_switch).pack(side="left")
        tk.Button(btn_frame, text=self.getText("btn_close"), command=win.destroy).pack(side="right")


if __name__ == "__main__":
    app = FlierZedApp()
    app.mainloop()
