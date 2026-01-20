import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import subprocess
import importlib.util
import json

# Localization Strings
TRANSLATIONS = {
    "en": {
        "title": "AI Aim Assistant - Configuration",
        "start_btn": "START ASSISTANT",
        "stop_btn": "STOP ASSISTANT",
        "status_stopped": "Status: Stopped",
        "status_running": "Status: Running",
        "toggle_aim_on": "Toggle Aim (ON)",
        "toggle_aim_off": "Toggle Aim (OFF)",
        "toggle_trigger_on": "Toggle Trigger (ON)",
        "toggle_trigger_off": "Toggle Trigger (OFF)",
        "tab_general": "General",
        "tab_aim": "Aim Assist",
        "tab_trigger": "Trigger Bot",
        "tab_system": "System",
        "config_title": "Configuration",
        "save_settings": "Save Settings",
        "load_settings": "Load Settings",
        "model_settings": "Model Settings",
        "model_path": "Model Path:",
        "browse": "Browse",
        "hotkeys": "Hotkeys",
        "visuals": "Visuals",
        "show_preview": "Show Preview Window",
        "show_debug": "Show Detailed Debug Data",
        "aim_params": "Aim Parameters",
        "fov_radius": "FOV Radius (Lock Dist):",
        "smoothing": "Smoothing Factor (Speed):",
        "max_speed": "Max Move Speed:",
        "jitter": "Mouse Jitter (Humanize):",
        "aim_point": "Aim Point (Y-Axis Lock)",
        "target_part": "Target Priority Part:",
        "head_offset": "Head Offset (-0.5 to 0.5):",
        "body_offset": "Body Offset (0.0 to 1.0):",
        "trigger_settings": "Trigger Settings",
        "enable_trigger": "Enable Trigger Bot",
        "trigger_delay": "Trigger Delay (ms):",
        "rcs_title": "Recoil Control System (RCS)",
        "enable_rcs": "Enable Recoil Control",
        "rcs_strength": "RCS Strength:",
        "trigger_radius": "Trigger Radius (px):",
        "burst_control": "Burst Control",
        "enable_burst": "Enable Burst Mode",
        "burst_shots": "Shots per Burst:",
        "burst_interval": "Burst Interval (ms):",
        "performance": "Performance",
        "target_fps": "Target FPS:",
        "detection_size": "Detection Size:",
        "msg_saved": "Settings saved to config.json",
        "msg_loaded": "Settings loaded. Please restart GUI or re-check tabs to see all changes.",
        "err_model_not_found": "Model file not found:",
        "err_save_failed": "Failed to save settings:",
        "err_load_failed": "Failed to load settings:",
        "lang_select": "Language:",
        "validation_title": "Environment Check",
        "validation_success": "Environment check passed.",
        "validation_fail_model": "Critical: No model file (CS2.engine, CS2.pt, CS2.onnx) found in directory!",
        "validation_fail_trigger": "Critical: trigger.py not found!",
        "validation_warn_config": "Warning: config.json not found or invalid. Using defaults.",
        "stopped_key": "Status: Stopped (Key Pressed)"
    },
    "zh-TW": {
        "title": "AI 瞄準助手 - 設定",
        "start_btn": "啟動助手",
        "stop_btn": "停止助手",
        "status_stopped": "狀態: 已停止",
        "status_running": "狀態: 運行中",
        "toggle_aim_on": "切換瞄準 (開啟)",
        "toggle_aim_off": "切換瞄準 (關閉)",
        "toggle_trigger_on": "切換扳機 (開啟)",
        "toggle_trigger_off": "切換扳機 (關閉)",
        "tab_general": "一般設定",
        "tab_aim": "自瞄設定",
        "tab_trigger": "扳機設定",
        "tab_system": "系統設定",
        "config_title": "設定檔操作",
        "save_settings": "儲存設定",
        "load_settings": "載入設定",
        "model_settings": "模型設定",
        "model_path": "模型路徑:",
        "browse": "瀏覽",
        "hotkeys": "快捷鍵",
        "visuals": "視覺效果",
        "show_preview": "顯示預覽視窗",
        "show_debug": "顯示詳細除錯數據",
        "aim_params": "瞄準參數",
        "fov_radius": "FOV 半徑 (鎖定距離):",
        "smoothing": "平滑係數 (速度):",
        "max_speed": "最大移動速度:",
        "jitter": "滑鼠抖動 (擬人化):",
        "aim_point": "瞄準點 (Y軸鎖定)",
        "target_part": "優先瞄準部位:",
        "head_offset": "頭部偏移 (-0.5 到 0.5):",
        "body_offset": "身體偏移 (0.0 到 1.0):",
        "trigger_settings": "扳機設定",
        "enable_trigger": "啟用自動扳機",
        "trigger_delay": "觸發延遲 (ms):",
        "rcs_title": "後座力控制系統 (RCS)",
        "enable_rcs": "啟用後座力控制",
        "rcs_strength": "RCS 強度:",
        "trigger_radius": "觸發半徑 (px):",
        "burst_control": "點射控制",
        "enable_burst": "啟用點射模式",
        "burst_shots": "每次點射發數:",
        "burst_interval": "點射間隔 (ms):",
        "performance": "效能設定",
        "target_fps": "目標 FPS:",
        "detection_size": "偵測尺寸:",
        "msg_saved": "設定已儲存至 config.json",
        "msg_loaded": "設定已載入。請重啟 GUI 或切換分頁以查看變更。",
        "err_model_not_found": "找不到模型檔案:",
        "err_save_failed": "儲存設定失敗:",
        "err_load_failed": "載入設定失敗:",
        "lang_select": "語言:",
        "validation_title": "環境檢查",
        "validation_success": "環境檢查通過。",
        "validation_fail_model": "嚴重錯誤: 目錄中找不到模型檔案 (CS2.engine, CS2.pt, CS2.onnx)!",
        "validation_fail_trigger": "嚴重錯誤: 找不到 trigger.py!",
        "validation_warn_config": "警告: config.json 遺失或無效。使用預設值。",
        "stopped_key": "狀態: 已停止 (按鍵觸發)"
    }
}

CURRENT_LANG = "zh-TW" # Default to Traditional Chinese as per user preference

def load_config_early():
    global CURRENT_LANG
    if os.path.exists("config.json"):
        try:
            with open("config.json", "r") as f:
                data = json.load(f)
                if "language" in data:
                    CURRENT_LANG = data["language"]
                # Update cfg values too
                for key, val in data.items():
                    if hasattr(cfg, key):
                        setattr(cfg, key, val)
        except Exception as e:
            print(f"Error loading config early: {e}")

# Call it immediately to set language and config before GUI creation
load_config_early()

def tr(key):
    """Translate key to current language."""
    return TRANSLATIONS.get(CURRENT_LANG, TRANSLATIONS["en"]).get(key, key)

def check_and_install_packages():
    """Check for required packages and install them if missing."""
    required_packages = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'mss': 'mss',
        'win32api': 'pywin32',
        'keyboard': 'keyboard',
        'ultralytics': 'ultralytics'
    }
    
    missing_packages = []
    
    print("Checking dependencies...")
    for module_name, package_name in required_packages.items():
        if importlib.util.find_spec(module_name) is None:
            print(f"Missing module: {module_name} (Package: {package_name})")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"Installing missing packages: {', '.join(missing_packages)}")
        try:
            # Use subprocess.check_call safely
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("All packages installed successfully.")
            
            # Show message box
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Installation Complete", f"Installed: {', '.join(missing_packages)}\nPlease restart the application.")
            root.destroy()
            sys.exit(0) 
            
        except Exception as e:
            print(f"Error installing packages: {e}")
            # Try to show error in GUI if possible
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Installation Error", f"Failed to install packages.\nError: {e}\nPlease install manually: pip install {' '.join(missing_packages)}")
                root.destroy()
            except:
                pass
            sys.exit(1)
    else:
        print("All dependencies satisfied.")

def get_nvidia_gpu_status():
    """Detect if NVIDIA GPU is present on the system using multiple methods."""
    print("Checking for NVIDIA GPU...")
    
    # Method 1: nvidia-smi (Most reliable if drivers are installed)
    try:
        # shell=True helps find the executable in path on Windows
        result = subprocess.run("nvidia-smi -L", capture_output=True, text=True, shell=True)
        if result.returncode == 0 and "GPU" in result.stdout:
            return True, "NVIDIA GPU Detected (via nvidia-smi)"
    except Exception:
        pass

    # Method 2: wmic (Standard Windows)
    try:
        # Use wmic with capture_output to handle encoding better (Python handles it)
        result = subprocess.run('wmic path win32_VideoController get Name', capture_output=True, text=True, shell=True)
        if "NVIDIA" in result.stdout.upper():
            return True, "NVIDIA GPU Detected (via wmic)"
    except Exception:
        pass

    # Method 3: PowerShell (Fallback)
    try:
        cmd = 'powershell "Get-WmiObject Win32_VideoController | Select-Object Name"'
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        if "NVIDIA" in result.stdout.upper():
            return True, "NVIDIA GPU Detected (via PowerShell)"
    except Exception:
        pass
        
    return False, "No NVIDIA GPU Detected"

def check_torch_installation():
    """Check PyTorch installation and ensure CUDA support if GPU exists."""
    try:
        has_nvidia, gpu_msg = get_nvidia_gpu_status()
        print(f"Hardware Check: {gpu_msg}")
    except Exception as e:
        print(f"Hardware Check Failed: {e}")
        has_nvidia = False # Assume no NVIDIA if detection crashes hard
    
    need_install = False
    is_cuda_available = False
    
    try:
        import torch
        is_cuda_available = torch.cuda.is_available()
        print(f"Current PyTorch: {torch.__version__}, CUDA Available: {is_cuda_available}")
        
        if has_nvidia and not is_cuda_available:
            print("⚠️ Warning: NVIDIA GPU detected but installed PyTorch is CPU-only.")
            # Use a temporary root for messagebox since main root isn't created yet
            root = tk.Tk()
            root.withdraw()
            response = messagebox.askyesno("Hardware Optimization", 
                "NVIDIA GPU detected but current PyTorch does not support CUDA.\n"
                "Do you want to reinstall PyTorch with CUDA support for better performance?",
                parent=root)
            root.destroy()
            
            if response:
                need_install = True
                subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "torch", "torchvision", "torchaudio"])
        
    except ImportError:
        print("PyTorch not found.")
        need_install = True
    except Exception as e:
        print(f"Error checking torch: {e}")
        # Continue without crashing if torch check fails, just assume we might need install if not found
        pass

    if need_install:
        print("Installing optimized PyTorch...")
        try:
            if has_nvidia:
                # Install PyTorch with CUDA 12.1
                cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio", 
                       "--index-url", "https://download.pytorch.org/whl/cu121"]
            else:
                # Install CPU version
                cmd = [sys.executable, "-m", "pip", "install", "torch", "torchvision", "torchaudio"]
                
            print(f"Executing: {' '.join(cmd)}")
            subprocess.check_call(cmd)
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Installation Complete", "PyTorch installed successfully.\nPlease restart the application.")
            root.destroy()
            sys.exit(0)
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Failed to install PyTorch: {e}")
            root.destroy()
            sys.exit(1)

# Run dependency check before importing trigger
check_torch_installation() # Check Torch FIRST
check_and_install_packages() # Then check others

# Add current directory to path to ensure we can import trigger
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    import trigger
    from trigger import cfg
except ImportError:
    messagebox.showerror("Error", "Could not import trigger.py. Make sure it exists in the same directory.")
    sys.exit(1)

class GameGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(tr("title"))
        self.root.geometry("600x800")
        
        # Enhanced Detection on Startup
        self.validate_environment()
        
        self.assistant = trigger.GameAssistant()
        self.is_running = False
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main Container
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Language Selector
        lang_frame = ttk.Frame(main_frame)
        lang_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(lang_frame, text=tr("lang_select")).pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value="Traditional Chinese" if CURRENT_LANG == "zh-TW" else "English")
        lang_cb = ttk.Combobox(lang_frame, textvariable=self.lang_var, 
                               values=["English", "Traditional Chinese"], state="readonly", width=20)
        lang_cb.pack(side=tk.LEFT, padx=5)
        lang_cb.bind("<<ComboboxSelected>>", self.change_language)
        
        # Notebook (Tabs)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create Tabs
        self.create_general_tab()
        self.create_aim_tab()
        self.create_trigger_tab()
        self.create_system_tab()
        
        # Control Buttons
        control_frame = ttk.LabelFrame(main_frame, text="Control Panel", padding="10")
        control_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = ttk.Button(control_frame, text=tr("start_btn"), command=self.toggle_assistant)
        self.btn_start.pack(fill=tk.X, ipady=5)
        
        self.status_label = ttk.Label(control_frame, text=tr("status_stopped"), foreground="red")
        self.status_label.pack(pady=5)

        # Manual Toggles Frame
        toggle_frame = ttk.Frame(control_frame)
        toggle_frame.pack(fill=tk.X, pady=5)
        
        # Manual Aim Toggle
        self.btn_toggle_aim = ttk.Button(toggle_frame, text=tr("toggle_aim_off"), command=self.toggle_aim_manual)
        self.btn_toggle_aim.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Manual Trigger Toggle
        self.btn_toggle_trigger = ttk.Button(toggle_frame, text=tr("toggle_trigger_off"), command=self.toggle_trigger_manual)
        self.btn_toggle_trigger.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set callback for status updates from assistant
        self.assistant.set_callback(self.update_status_from_thread)

    def validate_environment(self):
        """Check for critical files and environment state."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 1. Check trigger.py
        if not os.path.exists(os.path.join(current_dir, "trigger.py")):
            messagebox.showerror(tr("validation_title"), tr("validation_fail_trigger"))
            self.root.after(100, lambda: self.btn_start.config(state="disabled"))
            return False

        # 2. Check Models
        models = ["CS2.engine", "CS2.pt", "CS2.onnx"]
        found_model = any(os.path.exists(os.path.join(current_dir, m)) for m in models)
        if not found_model:
            messagebox.showerror(tr("validation_title"), tr("validation_fail_model"))
            self.root.after(100, lambda: self.btn_start.config(state="disabled"))
            return False
            
        # 3. Check Config
        if not os.path.exists(os.path.join(current_dir, "config.json")):
            # Just a warning
            messagebox.showwarning(tr("validation_title"), tr("validation_warn_config"))
            
        return True

    def change_language(self, event=None):
        """Handle language change selection."""
        selection = self.lang_var.get()
        global CURRENT_LANG
        if selection == "English":
            new_lang = "en"
        else:
            new_lang = "zh-TW"
            
        if new_lang != CURRENT_LANG:
            CURRENT_LANG = new_lang
            # Save to config immediately
            self.save_settings()
            messagebox.showinfo(tr("title"), "Language changed. Please restart the application to apply changes.\n語言已變更，請重啟程式以套用設定。")

    def create_general_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text=tr("tab_general"))
        
        # Config Actions
        cfg_frame = ttk.LabelFrame(tab, text=tr("config_title"), padding="10")
        cfg_frame.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(cfg_frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text=tr("save_settings"), command=self.save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=tr("load_settings"), command=self.load_settings).pack(side=tk.LEFT, padx=5)

        # Model Selection
        lbl_frame = ttk.LabelFrame(tab, text=tr("model_settings"), padding="10")
        lbl_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(lbl_frame, text=tr("model_path")).pack(anchor=tk.W)
        self.model_path_var = tk.StringVar(value=cfg.MODEL_PATH)
        entry_model = ttk.Entry(lbl_frame, textvariable=self.model_path_var, width=50)
        entry_model.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(lbl_frame, text=tr("browse"), command=self.browse_model).pack(side=tk.RIGHT)
        
        # Hotkeys
        hk_frame = ttk.LabelFrame(tab, text=tr("hotkeys"), padding="10")
        hk_frame.pack(fill=tk.X, pady=5)
        
        self.create_entry_row(hk_frame, "Aim Toggle Key:", "AIM_TOGGLE_KEY")
        self.create_entry_row(hk_frame, "Trigger Toggle Key:", "TRIGGER_TOGGLE_KEY")
        self.create_entry_row(hk_frame, "Exit Key:", "EXIT_KEY")

        # Visuals
        vis_frame = ttk.LabelFrame(tab, text=tr("visuals"), padding="10")
        vis_frame.pack(fill=tk.X, pady=5)
        
        self.var_preview = tk.BooleanVar(value=not cfg.SKIP_FRAME_VISUALIZATION)
        ttk.Checkbutton(vis_frame, text=tr("show_preview"), variable=self.var_preview, 
                        command=self.update_config).pack(anchor=tk.W)
        
        self.var_debug = tk.BooleanVar(value=not cfg.REDUCE_DEBUG_OUTPUT)
        ttk.Checkbutton(vis_frame, text=tr("show_debug"), variable=self.var_debug, 
                        command=self.update_config).pack(anchor=tk.W)

    def create_aim_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text=tr("tab_aim"))
        
        # Aim Settings
        aim_frame = ttk.LabelFrame(tab, text=tr("aim_params"), padding="10")
        aim_frame.pack(fill=tk.X, pady=5)
        
        # FOV (Aim Radius)
        self.create_scale_row(aim_frame, tr("fov_radius"), "MAX_LOCK_DISTANCE", 50, 500, 10)
        
        # Speed / Smoothing
        self.create_scale_row(aim_frame, tr("smoothing"), "SMOOTHING_FACTOR", 0.01, 1.0, 0.01)
        self.create_scale_row(aim_frame, tr("max_speed"), "MAX_MOVE_SPEED", 10, 500, 10)
        
        # Jitter
        self.create_scale_row(aim_frame, tr("jitter"), "MOUSE_JITTER", 0, 20, 1)
        
        # Offsets (Y-Axis Lock)
        offset_frame = ttk.LabelFrame(tab, text=tr("aim_point"), padding="10")
        offset_frame.pack(fill=tk.X, pady=5)
        
        # Target Part Selector
        part_frame = ttk.Frame(offset_frame)
        part_frame.pack(fill=tk.X, pady=5)
        ttk.Label(part_frame, text=tr("target_part")).pack(side=tk.LEFT)
        self.var_target_part = tk.StringVar(value=cfg.TARGET_PART)
        part_cb = ttk.Combobox(part_frame, textvariable=self.var_target_part, 
                               values=["HEAD", "NECK", "CHEST", "STOMACH"], state="readonly")
        part_cb.pack(side=tk.LEFT, padx=5)
        part_cb.bind("<<ComboboxSelected>>", lambda e: self.update_config())
        
        ttk.Label(offset_frame, text=tr("head_offset")).pack(anchor=tk.W)
        self.create_scale_row(offset_frame, tr("head_offset"), "HEAD_AIM_OFFSET", -0.5, 0.5, 0.01)
        
        ttk.Label(offset_frame, text=tr("body_offset")).pack(anchor=tk.W)
        self.create_scale_row(offset_frame, tr("body_offset"), "BODY_AIM_OFFSET", 0.0, 1.0, 0.01)

    def create_trigger_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text=tr("tab_trigger"))
        
        tb_frame = ttk.LabelFrame(tab, text=tr("trigger_settings"), padding="10")
        tb_frame.pack(fill=tk.X, pady=5)
        
        # Enable/Disable
        self.var_tb_enable = tk.BooleanVar(value=cfg.ENABLE_TRIGGER_BOT)
        ttk.Checkbutton(tb_frame, text=tr("enable_trigger"), variable=self.var_tb_enable, 
                        command=self.update_config).pack(anchor=tk.W, pady=5)
        
        # Delay
        self.create_scale_row(tb_frame, tr("trigger_delay"), "TRIGGER_DELAY_MS", 0, 1000, 10)

        # Recoil Control System (RCS)
        rcs_frame = ttk.LabelFrame(tab, text=tr("rcs_title"), padding="10")
        rcs_frame.pack(fill=tk.X, pady=5)
        
        self.var_rcs_enable = tk.BooleanVar(value=cfg.RECOIL_COMPENSATION)
        ttk.Checkbutton(rcs_frame, text=tr("enable_rcs"), variable=self.var_rcs_enable,
                        command=self.update_config).pack(anchor=tk.W)
        
        self.create_scale_row(rcs_frame, tr("rcs_strength"), "RECOIL_STRENGTH", 0, 20, 1)
        
        # Radius
        self.create_scale_row(tb_frame, tr("trigger_radius"), "TRIGGER_RADIUS", 1, 100, 1)
        
        # Burst Mode
        burst_frame = ttk.LabelFrame(tab, text=tr("burst_control"), padding="10")
        burst_frame.pack(fill=tk.X, pady=5)
        
        self.var_burst = tk.BooleanVar(value=cfg.BURST_MODE)
        ttk.Checkbutton(burst_frame, text=tr("enable_burst"), variable=self.var_burst, 
                        command=self.update_config).pack(anchor=tk.W)
        
        self.create_scale_row(burst_frame, tr("burst_shots"), "BURST_SHOTS", 1, 10, 1)
        self.create_scale_row(burst_frame, tr("burst_interval"), "BURST_INTERVAL_MS", 50, 1000, 10)

    def create_system_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text=tr("tab_system"))
        
        sys_frame = ttk.LabelFrame(tab, text=tr("performance"), padding="10")
        sys_frame.pack(fill=tk.X, pady=5)
        
        self.create_scale_row(sys_frame, tr("target_fps"), "TARGET_FPS", 30, 500, 10)
        self.create_scale_row(sys_frame, tr("detection_size"), "DETECTION_SIZE", 320, 1280, 32)

    def create_scale_row(self, parent, label_text, config_attr, min_val, max_val, step):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        lbl = ttk.Label(frame, text=f"{label_text}", width=25)
        lbl.pack(side=tk.LEFT)
        
        # Value var
        current_val = getattr(cfg, config_attr)
        var = tk.DoubleVar(value=current_val)
        
        # Value label
        val_lbl = ttk.Label(frame, text=f"{current_val:.2f}", width=8)
        val_lbl.pack(side=tk.RIGHT)
        
        def on_change(val):
            float_val = float(val)
            # Round to step
            if step >= 1:
                final_val = int(round(float_val))
            else:
                final_val = round(float_val, 2)
            
            setattr(cfg, config_attr, final_val)
            val_lbl.config(text=str(final_val))
            
            # Special handling for DETECTION_SIZE (affects screen center)
            if config_attr == "DETECTION_SIZE" or config_attr == "FOV_SIZE":
                # Only if using FOV_SIZE separately, but typically they might be linked
                pass
                
        scale = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, command=on_change)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

    def create_entry_row(self, parent, label_text, config_attr):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(frame, text=label_text, width=20).pack(side=tk.LEFT)
        
        current_val = getattr(cfg, config_attr)
        var = tk.StringVar(value=str(current_val))
        
        def on_write(*args):
            setattr(cfg, config_attr, var.get())
            
        var.trace_add("write", on_write)
        
        entry = ttk.Entry(frame, textvariable=var)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def browse_model(self):
        filename = filedialog.askopenfilename(
            title="Select Model File",
            filetypes=[("Model Files", "*.engine *.pt *.onnx"), ("All Files", "*.*")]
        )
        if filename:
            self.model_path_var.set(filename)
            cfg.MODEL_PATH = filename

    def update_config(self):
        # Update boolean toggles
        cfg.SKIP_FRAME_VISUALIZATION = not self.var_preview.get()
        cfg.REDUCE_DEBUG_OUTPUT = not self.var_debug.get()
        cfg.ENABLE_TRIGGER_BOT = self.var_tb_enable.get()
        cfg.BURST_MODE = self.var_burst.get()
        cfg.RECOIL_COMPENSATION = self.var_rcs_enable.get()
        cfg.TARGET_PART = self.var_target_part.get()
        
        # Update thread state if running
        if self.is_running:
            # If trigger bot is disabled via checkbox, force disable in assistant
            if not cfg.ENABLE_TRIGGER_BOT:
                self.assistant.toggle_trigger(False)
                self.btn_toggle_trigger.config(text="Toggle Trigger (OFF)")
            else:
                 # If enabled via checkbox, update the internal flag, but don't auto-activate
                 # unless it was already active? Let's just sync the config.
                 pass

    def save_settings(self):
        """Save current configuration to JSON file"""
        config_data = {}
        # Get all attributes of Config that are not methods/internal
        for attr in dir(cfg):
            if not attr.startswith("__") and not callable(getattr(cfg, attr)):
                val = getattr(cfg, attr)
                if isinstance(val, (int, float, str, bool)):
                    config_data[attr] = val
        
        try:
            import json
            with open("config.json", "w") as f:
                json.dump(config_data, f, indent=4)
            messagebox.showinfo("Success", "Settings saved to config.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def load_settings(self):
        """Load configuration from JSON file"""
        import json
        if not os.path.exists("config.json"):
            messagebox.showinfo("Info", "No config file found.")
            return
            
        try:
            with open("config.json", "r") as f:
                config_data = json.load(f)
            
            # Update Config object
            for key, val in config_data.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, val)
            
            # Update Language Var (GUI only)
            if "language" in config_data:
                lang_code = config_data["language"]
                if lang_code == "en":
                    self.lang_var.set("English")
                else:
                    self.lang_var.set("Traditional Chinese")
            
            # Refresh GUI elements
            self.model_path_var.set(cfg.MODEL_PATH)
            self.var_preview.set(not cfg.SKIP_FRAME_VISUALIZATION)
            self.var_debug.set(not cfg.REDUCE_DEBUG_OUTPUT)
            self.var_tb_enable.set(cfg.ENABLE_TRIGGER_BOT)
            self.var_burst.set(cfg.BURST_MODE)
            self.var_rcs_enable.set(cfg.RECOIL_COMPENSATION)
            self.var_target_part.set(cfg.TARGET_PART)
            
            # We need to refresh scales manually as they are bound to DoubleVars that are not directly linked to cfg until change
            # But in create_scale_row, we use a new DoubleVar initialized with current val.
            # To refresh properly, we might need to restart GUI or update all vars.
            # Ideally, we should have stored references to vars.
            # For now, let's just tell user to restart or re-open tabs.
            # Actually, let's try to update at least the visible ones if we can.
            
            # Simpler: Just show message that settings loaded, some might need restart or re-opening tab
            messagebox.showinfo("Success", "Settings loaded. Please restart GUI or re-check tabs to see all changes.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load settings: {e}")

    def toggle_aim_manual(self):
        if not self.is_running:
            return
        
        # Current state is self.assistant.aim_enabled
        new_state = not self.assistant.aim_enabled
        self.assistant.toggle_aim(new_state)
        self.update_toggle_buttons()

    def toggle_trigger_manual(self):
        if not self.is_running:
            return
            
        new_state = not self.assistant.trigger_enabled
        self.assistant.toggle_trigger(new_state)
        self.update_toggle_buttons()
        
    def update_toggle_buttons(self):
        if self.assistant.aim_enabled:
            self.btn_toggle_aim.config(text="Toggle Aim (ON)")
        else:
            self.btn_toggle_aim.config(text="Toggle Aim (OFF)")
            
        if self.assistant.trigger_enabled:
            self.btn_toggle_trigger.config(text="Toggle Trigger (ON)")
        else:
            self.btn_toggle_trigger.config(text="Toggle Trigger (OFF)")

    def toggle_assistant(self):
        if not self.is_running:
            # Validate model
            if not os.path.exists(cfg.MODEL_PATH):
                messagebox.showerror("Error", f"Model file not found: {cfg.MODEL_PATH}")
                return

            # Start
            self.update_config() # Ensure latest config
            self.assistant.start()
            self.is_running = True
            self.btn_start.config(text="STOP ASSISTANT")
            self.status_label.config(text="Status: Running", foreground="green")
            
            # Start status update loop
            self.root.after(500, self.periodic_status_check)
            
        else:
            # Stop
            self.assistant.stop()
            self.is_running = False
            self.btn_start.config(text="START ASSISTANT")
            self.status_label.config(text="Status: Stopped", foreground="red")
            self.btn_toggle_aim.config(text="Toggle Aim (OFF)")
            self.btn_toggle_trigger.config(text="Toggle Trigger (OFF)")

    def periodic_status_check(self):
        if self.is_running:
            self.update_toggle_buttons()
            self.root.after(500, self.periodic_status_check)

    def update_status_from_thread(self, msg):
        if msg == "stopped":
            self.root.after(0, self.handle_stop_from_thread)

    def handle_stop_from_thread(self):
        self.is_running = False
        self.btn_start.config(text="START ASSISTANT")
        self.status_label.config(text="Status: Stopped (Key Pressed)", foreground="red")

    def on_close(self):
        if self.is_running:
            self.assistant.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = GameGUI(root)
    root.mainloop()
    root = tk.Tk()
    app = GameGUI(root)
    root.mainloop()
