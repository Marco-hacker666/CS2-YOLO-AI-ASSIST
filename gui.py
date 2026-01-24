# 完整版 AI 瞄準系統 GUI - 帶自動優化
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys

# ==================== 配置類別 ====================
class Config:
    def __init__(self):
        # 模型設定
        self.MODEL_PATH = r'D:\AI\CS2.pt'
        
        # 螢幕設定
        self.SCREEN_WIDTH = 3440
        self.SCREEN_HEIGHT = 1440
        self.DETECTION_SIZE = 640
        
        # 瞄準設定
        self.AIM_ENABLED = True
        self.AIM_HEIGHT = 0.0  # 0.0=頭, 0.5=胸, 1.0=腰
        self.SMOOTHING_FACTOR = 0.85
        self.MAX_MOVE_SPEED = 300
        self.MOUSE_JITTER = 0.3
        self.MAX_LOCK_DISTANCE = 300
        
        # Trigger Bot
        self.ENABLE_TRIGGER_BOT = False
        self.TRIGGER_DELAY_MS = 500
        self.TRIGGER_RADIUS = 10
        
        # 壓槍
        self.RECOIL_COMPENSATION = True
        self.RECOIL_STRENGTH = 3
        
        # 快捷鍵
        self.AIM_TOGGLE_KEY = 'x'
        self.TRIGGER_TOGGLE_KEY = 'c'
        self.EXIT_KEY = 'q'
        
        # 視覺
        self.SKIP_FRAME_VISUALIZATION = False
        self.REDUCE_DEBUG_OUTPUT = True
        self.SHOW_FOV_CIRCLE = True
        
        # 效能
        self.TARGET_FPS = 300
        
    def save(self, filepath='config.json'):
        config_dict = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                config_dict[key] = value
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=4, ensure_ascii=False)
    
    def load(self, filepath='config.json'):
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
                for key, value in config_dict.items():
                    if hasattr(self, key):
                        setattr(self, key, value)

# 全局配置
cfg = Config()

# ==================== 自動優化系統 ====================
class AutoOptimizer:
    @staticmethod
    def detect_system():
        """偵測系統規格"""
        import subprocess
        
        specs = {
            'cpu_cores': 4,
            'ram_gb': 8.0,
            'gpu_type': 'CPU',
            'gpu_name': '未偵測到',
            'has_nvidia': False
        }
        
        # CPU 核心
        try:
            specs['cpu_cores'] = os.cpu_count() or 4
        except:
            pass
        
        # RAM
        try:
            if sys.platform == 'win32':
                result = subprocess.run('wmic computersystem get TotalPhysicalMemory', 
                                       capture_output=True, text=True, shell=True)
                for line in result.stdout.splitlines():
                    if line.strip().isdigit():
                        specs['ram_gb'] = round(int(line.strip()) / (1024**3), 1)
                        break
        except:
            pass
        
        # GPU
        try:
            # NVIDIA
            result = subprocess.run('nvidia-smi -L', capture_output=True, text=True, shell=True)
            if result.returncode == 0 and 'GPU' in result.stdout:
                specs['has_nvidia'] = True
                specs['gpu_type'] = 'NVIDIA'
                # 提取 GPU 名稱
                for line in result.stdout.splitlines():
                    if 'GPU' in line:
                        specs['gpu_name'] = line.split(':')[1].strip() if ':' in line else 'NVIDIA GPU'
                        break
        except:
            pass
        
        # 如果沒偵測到 NVIDIA，嘗試偵測其他 GPU
        if not specs['has_nvidia']:
            try:
                result = subprocess.run('wmic path win32_VideoController get Name', 
                                       capture_output=True, text=True, shell=True)
                for line in result.stdout.splitlines():
                    line = line.strip()
                    if line and 'Name' not in line:
                        specs['gpu_name'] = line
                        if 'AMD' in line.upper() or 'RADEON' in line.upper():
                            specs['gpu_type'] = 'AMD'
                        elif 'INTEL' in line.upper():
                            specs['gpu_type'] = 'Intel'
                        break
            except:
                pass
        
        return specs
    
    @staticmethod
    def calculate_performance_tier(specs):
        """計算效能等級"""
        score = 0
        
        # CPU 評分（0-30）
        if specs['cpu_cores'] >= 12:
            score += 30
        elif specs['cpu_cores'] >= 8:
            score += 25
        elif specs['cpu_cores'] >= 6:
            score += 20
        elif specs['cpu_cores'] >= 4:
            score += 15
        else:
            score += 10
        
        # RAM 評分（0-30）
        if specs['ram_gb'] >= 32:
            score += 30
        elif specs['ram_gb'] >= 16:
            score += 25
        elif specs['ram_gb'] >= 12:
            score += 20
        elif specs['ram_gb'] >= 8:
            score += 15
        else:
            score += 10
        
        # GPU 評分（0-40）
        if specs['has_nvidia']:
            gpu_name = specs['gpu_name'].upper()
            if '4090' in gpu_name or '4080' in gpu_name:
                score += 40
            elif '4070' in gpu_name or '4060' in gpu_name or '3090' in gpu_name or '3080' in gpu_name:
                score += 35
            elif '3070' in gpu_name or '3060' in gpu_name or '2080' in gpu_name:
                score += 30
            elif '2070' in gpu_name or '2060' in gpu_name or '1660' in gpu_name:
                score += 25
            else:
                score += 20
        elif specs['gpu_type'] == 'AMD':
            score += 25
        elif specs['gpu_type'] == 'Intel':
            score += 15
        else:
            score += 5
        
        # 等級判定
        if score >= 85:
            return '極致', score
        elif score >= 70:
            return '高階', score
        elif score >= 50:
            return '中階', score
        elif score >= 30:
            return '入門', score
        else:
            return '低階', score
    
    @staticmethod
    def apply_optimal_settings(tier, specs):
        """根據效能等級應用最佳設定"""
        if tier == '極致':
            cfg.DETECTION_SIZE = 928
            cfg.TARGET_FPS = 300
            cfg.MAX_MOVE_SPEED = 350
            cfg.SMOOTHING_FACTOR = 0.9
            cfg.SKIP_FRAME_VISUALIZATION = True
        
        elif tier == '高階':
            cfg.DETECTION_SIZE = 640
            cfg.TARGET_FPS = 240
            cfg.MAX_MOVE_SPEED = 300
            cfg.SMOOTHING_FACTOR = 0.85
            cfg.SKIP_FRAME_VISUALIZATION = True
        
        elif tier == '中階':
            cfg.DETECTION_SIZE = 640
            cfg.TARGET_FPS = 144
            cfg.MAX_MOVE_SPEED = 250
            cfg.SMOOTHING_FACTOR = 0.7
            cfg.SKIP_FRAME_VISUALIZATION = True
        
        elif tier == '入門':
            cfg.DETECTION_SIZE = 480
            cfg.TARGET_FPS = 100
            cfg.MAX_MOVE_SPEED = 200
            cfg.SMOOTHING_FACTOR = 0.6
            cfg.SKIP_FRAME_VISUALIZATION = True
        
        else:  # 低階
            cfg.DETECTION_SIZE = 480
            cfg.TARGET_FPS = 60
            cfg.MAX_MOVE_SPEED = 150
            cfg.SMOOTHING_FACTOR = 0.5
            cfg.SKIP_FRAME_VISUALIZATION = True

# ==================== GUI 主視窗 ====================
class AimSystemGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 瞄準系統控制面板 v4.0")
        self.root.geometry("750x900")
        self.root.resizable(False, False)
        
        # 樣式
        style = ttk.Style()
        style.theme_use('clam')
        
        # 創建 UI
        self.create_widgets()
        
        # 載入配置
        if os.path.exists('config.json'):
            cfg.load()
            self.refresh_all_values()
    
    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 頂部按鈕區
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(top_frame, text="🚀 自動優化設定", command=self.auto_optimize).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="💾 保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📁 載入配置", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🔄 重置", command=self.reset_config).pack(side=tk.LEFT, padx=5)
        
        # 分頁
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.create_main_tab()
        self.create_aim_tab()
        self.create_trigger_tab()
        self.create_visual_tab()
        self.create_advanced_tab()
        
        # 底部控制按鈕
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(bottom_frame, text="▶️ 啟動系統", command=self.start_system, 
                  ).pack(fill=tk.X, ipady=10)
    
    def create_main_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="主要設定")
        
        # 模型選擇
        model_frame = ttk.LabelFrame(tab, text="模型設定", padding="10")
        model_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(model_frame, text="模型路徑:").pack(anchor=tk.W)
        
        path_frame = ttk.Frame(model_frame)
        path_frame.pack(fill=tk.X, pady=5)
        
        self.model_var = tk.StringVar(value=cfg.MODEL_PATH)
        ttk.Entry(path_frame, textvariable=self.model_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ttk.Button(path_frame, text="瀏覽", command=self.browse_model).pack(side=tk.RIGHT)
        
        # 快捷鍵
        key_frame = ttk.LabelFrame(tab, text="快捷鍵設定", padding="10")
        key_frame.pack(fill=tk.X, pady=5)
        
        self.create_key_row(key_frame, "瞄準開關:", "AIM_TOGGLE_KEY")
        self.create_key_row(key_frame, "Trigger開關:", "TRIGGER_TOGGLE_KEY")
        self.create_key_row(key_frame, "退出程式:", "EXIT_KEY")
        
        # 系統資訊
        info_frame = ttk.LabelFrame(tab, text="系統資訊", padding="10")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.info_text = tk.Text(info_frame, height=10, state='disabled', bg='#f0f0f0')
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        ttk.Button(info_frame, text="🔍 檢測系統", command=self.show_system_info).pack(pady=5)
    
    def create_aim_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="瞄準設定")
        
        # 啟用開關
        ttk.Checkbutton(tab, text="啟用自動瞄準", 
                       variable=self.create_bool_var('AIM_ENABLED')).pack(anchor=tk.W, pady=5)
        
        # 瞄準高度
        self.create_slider(tab, "瞄準高度 (0=頭, 1=腰)", "AIM_HEIGHT", 0.0, 1.0, 0.01)
        
        # 移動速度
        self.create_slider(tab, "移動速度", "MAX_MOVE_SPEED", 50, 500, 10)
        
        # 平滑度
        self.create_slider(tab, "平滑度 (越高越快)", "SMOOTHING_FACTOR", 0.1, 1.0, 0.05)
        
        # 人類抖動
        self.create_slider(tab, "人類抖動", "MOUSE_JITTER", 0.0, 5.0, 0.1)
        
        # FOV
        self.create_slider(tab, "鎖定範圍 (FOV)", "MAX_LOCK_DISTANCE", 50, 500, 10)
    
    def create_trigger_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="Trigger Bot")
        
        # 啟用開關
        ttk.Checkbutton(tab, text="啟用 Trigger Bot", 
                       variable=self.create_bool_var('ENABLE_TRIGGER_BOT')).pack(anchor=tk.W, pady=5)
        
        # 觸發延遲
        self.create_slider(tab, "觸發延遲 (ms)", "TRIGGER_DELAY_MS", 0, 1000, 10)
        
        # 觸發半徑
        self.create_slider(tab, "觸發半徑 (px)", "TRIGGER_RADIUS", 5, 50, 1)
        
        # 壓槍設定
        rcs_frame = ttk.LabelFrame(tab, text="壓槍設定", padding="10")
        rcs_frame.pack(fill=tk.X, pady=10)
        
        ttk.Checkbutton(rcs_frame, text="啟用後坐力補償", 
                       variable=self.create_bool_var('RECOIL_COMPENSATION')).pack(anchor=tk.W)
        
        self.create_slider(rcs_frame, "壓槍強度", "RECOIL_STRENGTH", 0, 10, 1)
    
    def create_visual_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="視覺設定")
        
        vis_frame = ttk.LabelFrame(tab, text="顯示選項", padding="10")
        vis_frame.pack(fill=tk.X, pady=5)
        
        # 注意：SKIP_FRAME_VISUALIZATION 是反向的
        self.show_preview_var = tk.BooleanVar(value=not cfg.SKIP_FRAME_VISUALIZATION)
        ttk.Checkbutton(vis_frame, text="顯示預覽視窗", variable=self.show_preview_var,
                       command=lambda: setattr(cfg, 'SKIP_FRAME_VISUALIZATION', not self.show_preview_var.get())).pack(anchor=tk.W)
        
        ttk.Checkbutton(vis_frame, text="顯示 FOV 圓圈", 
                       variable=self.create_bool_var('SHOW_FOV_CIRCLE')).pack(anchor=tk.W)
        
        self.show_debug_var = tk.BooleanVar(value=not cfg.REDUCE_DEBUG_OUTPUT)
        ttk.Checkbutton(vis_frame, text="顯示詳細數據", variable=self.show_debug_var,
                       command=lambda: setattr(cfg, 'REDUCE_DEBUG_OUTPUT', not self.show_debug_var.get())).pack(anchor=tk.W)
        
        # 說明
        info_text = """
提示：
• 關閉預覽視窗可提升 30-50% FPS
• 建議調試時開啟，實戰時關閉
• 關閉後仍會在終端顯示狀態
        """
        ttk.Label(tab, text=info_text, justify='left', background='#fffacd', 
                 relief='solid', padding=10).pack(fill=tk.X, pady=10)
    
    def create_advanced_tab(self):
        tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab, text="進階設定")
        
        # 效能設定
        perf_frame = ttk.LabelFrame(tab, text="效能設定", padding="10")
        perf_frame.pack(fill=tk.X, pady=5)
        
        self.create_slider(perf_frame, "目標 FPS", "TARGET_FPS", 60, 500, 10)
        self.create_slider(perf_frame, "偵測尺寸", "DETECTION_SIZE", 320, 928, 32)
        
        # 警告
        warning_text = """
⚠️ 注意：
• 偵測尺寸越大越精準但越慢
• 建議：480=快速, 640=平衡, 928=精準
• 目標 FPS 設太高可能導致 CPU 占用過高
        """
        ttk.Label(tab, text=warning_text, justify='left', foreground='red',
                 relief='solid', padding=10).pack(fill=tk.X, pady=10)
    
    def create_slider(self, parent, label, config_attr, min_val, max_val, step):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame, text=label, width=25).pack(side=tk.LEFT)
        
        current_val = getattr(cfg, config_attr)
        var = tk.DoubleVar(value=current_val)
        
        value_label = ttk.Label(frame, text=f"{current_val:.2f}" if step < 1 else f"{int(current_val)}", width=10)
        value_label.pack(side=tk.RIGHT)
        
        def on_change(val):
            float_val = float(val)
            final_val = int(round(float_val)) if step >= 1 else round(float_val, 2)
            setattr(cfg, config_attr, final_val)
            value_label.config(text=str(final_val))
        
        scale = ttk.Scale(frame, from_=min_val, to=max_val, variable=var, command=on_change)
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 儲存引用以便後續更新
        if not hasattr(self, 'sliders'):
            self.sliders = {}
        self.sliders[config_attr] = (var, value_label, scale)
    
    def create_key_row(self, parent, label, config_attr):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame, text=label, width=15).pack(side=tk.LEFT)
        
        var = tk.StringVar(value=getattr(cfg, config_attr))
        var.trace_add("write", lambda *args: setattr(cfg, config_attr, var.get()))
        
        ttk.Entry(frame, textvariable=var, width=10).pack(side=tk.LEFT, padx=5)
    
    def create_bool_var(self, config_attr):
        var = tk.BooleanVar(value=getattr(cfg, config_attr))
        var.trace_add("write", lambda *args: setattr(cfg, config_attr, var.get()))
        return var
    
    def browse_model(self):
        filepath = filedialog.askopenfilename(
            title="選擇模型檔案",
            filetypes=[("YOLO 模型", "*.pt *.engine *.onnx"), ("所有檔案", "*.*")]
        )
        if filepath:
            self.model_var.set(filepath)
            cfg.MODEL_PATH = filepath
    
    def auto_optimize(self):
        """自動優化設定"""
        # 顯示進度
        progress_win = tk.Toplevel(self.root)
        progress_win.title("自動優化")
        progress_win.geometry("400x200")
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        ttk.Label(progress_win, text="正在偵測系統規格...", font=('Arial', 12)).pack(pady=20)
        progress_bar = ttk.Progressbar(progress_win, mode='indeterminate', length=300)
        progress_bar.pack(pady=10)
        progress_bar.start()
        
        def optimize():
            # 偵測系統
            specs = AutoOptimizer.detect_system()
            tier, score = AutoOptimizer.calculate_performance_tier(specs)
            
            # 應用設定
            AutoOptimizer.apply_optimal_settings(tier, specs)
            
            # 更新 UI
            self.root.after(0, lambda: self.refresh_all_values())
            
            # 顯示結果
            result_msg = f"""
優化完成！

系統規格：
• CPU: {specs['cpu_cores']} 核心
• RAM: {specs['ram_gb']} GB
• GPU: {specs['gpu_name']}

效能評級: {tier} ({score}/100)

已自動調整：
• 偵測尺寸: {cfg.DETECTION_SIZE}
• 目標 FPS: {cfg.TARGET_FPS}
• 移動速度: {cfg.MAX_MOVE_SPEED}
• 平滑度: {cfg.SMOOTHING_FACTOR}
            """
            
            progress_win.destroy()
            messagebox.showinfo("優化完成", result_msg)
        
        # 在後台執行
        import threading
        threading.Thread(target=optimize, daemon=True).start()
    
    def show_system_info(self):
        """顯示系統資訊"""
        specs = AutoOptimizer.detect_system()
        tier, score = AutoOptimizer.calculate_performance_tier(specs)
        
        info = f"""
系統資訊：
━━━━━━━━━━━━━━━━━━━━━
CPU 核心: {specs['cpu_cores']}
記憶體: {specs['ram_gb']} GB
GPU 類型: {specs['gpu_type']}
GPU 名稱: {specs['gpu_name']}
━━━━━━━━━━━━━━━━━━━━━
效能評級: {tier} ({score}/100)
━━━━━━━━━━━━━━━━━━━━━

建議設定：
• 偵測尺寸: {640 if tier in ['高階', '中階'] else 480}
• 目標 FPS: {300 if tier == '極致' else 240 if tier == '高階' else 144}
        """
        
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info)
        self.info_text.config(state='disabled')
    
    def refresh_all_values(self):
        """刷新所有 UI 值"""
        # 刷新滑桿
        if hasattr(self, 'sliders'):
            for attr, (var, label, scale) in self.sliders.items():
                val = getattr(cfg, attr)
                var.set(val)
                if isinstance(val, float):
                    label.config(text=f"{val:.2f}")
                else:
                    label.config(text=str(val))
        
        # 刷新其他
        self.model_var.set(cfg.MODEL_PATH)
        self.show_preview_var.set(not cfg.SKIP_FRAME_VISUALIZATION)
        self.show_debug_var.set(not cfg.REDUCE_DEBUG_OUTPUT)
    
    def save_config(self):
        cfg.save()
        messagebox.showinfo("成功", "配置已保存到 config.json")
    
    def load_config(self):
        cfg.load()
        self.refresh_all_values()
        messagebox.showinfo("成功", "配置已載入")
    
    def reset_config(self):
        if messagebox.askyesno("確認", "確定要重置為預設設定嗎？"):
            global cfg
            cfg = Config()
            self.refresh_all_values()
            messagebox.showinfo("成功", "已重置為預設設定")
    
    def start_system(self):
        """啟動主系統"""
        # 檢查模型
        if not os.path.exists(cfg.MODEL_PATH):
            messagebox.showerror("錯誤", f"找不到模型檔案:\n{cfg.MODEL_PATH}")
            return
        
        # 保存配置
        cfg.save()
        
        # 顯示資訊
        info_msg = f"""
系統啟動成功！

快捷鍵：
[{cfg.AIM_TOGGLE_KEY.upper()}] 開/關瞄準
[{cfg.TRIGGER_TOGGLE_KEY.upper()}] 開/關 Trigger
[{cfg.EXIT_KEY.upper()}] 退出

配置：
• 瞄準高度: {cfg.AIM_HEIGHT}
• 移動速度: {cfg.MAX_MOVE_SPEED}
• FOV: {cfg.MAX_LOCK_DISTANCE}
• FPS: {cfg.TARGET_FPS}
        """
        
        messagebox.showinfo("啟動成功", info_msg)
        
        # TODO: 整合實際的瞄準系統代碼
        print("系統已啟動")
        print(f"配置: {cfg.__dict__}")

# ==================== 主程式 ====================
if __name__ == "__main__":
    root = tk.Tk()
    app = AimSystemGUI(root)
    root.mainloop()
