import cv2
import numpy as np
import mss
import time
import win32api, win32con
import keyboard
from ultralytics import YOLO
from collections import deque
import ctypes

# ================= 參數設定 =================
MODEL_PATH = r'D:\AI\CS2.engine'  # 🔥 使用 TensorRT engine
# 如果是 .pt 模型會自動轉換，也可以直接用 .engine

SCREEN_WIDTH = 3440
SCREEN_HEIGHT = 1440
DETECTION_SIZE = 640  # 🔥 改回你原本的 928 (更大視野，但慢 50%)

# 平滑移動參數（取代 PID）
SMOOTHING_FACTOR = 0.3  # 稍微提高反應速度
MIN_MOVE_THRESHOLD = 2
MAX_MOVE_SPEED = 80     # 提高最大速度

# 目標追蹤
TARGET_HISTORY_SIZE = 3  # 🔥 減少到 3 (降低延遲)
PREDICTION_WEIGHT = 0.4  # 增加預測權重

# 瞄準設定
CONF_THRESHOLD = 0.5     # 🔥 降低到 0.5 (更靈敏，但可能誤判)
IOU_THRESHOLD = 0.5      # 🔥 NMS IoU 閾值
MAX_LOCK_DISTANCE = 280  # 稍微增加鎖定範圍

# Trigger Bot 設定
ENABLE_TRIGGER_BOT = False  # 🔥 True = 啟用自動開火
TRIGGER_RADIUS = 15         # 🔥 準心內此半徑內有目標就開火（像素）
TRIGGER_DELAY_MS = 5       # 🔥 延遲開火時間（毫秒），更人性化
TRIGGER_KEY = win32con.VK_LBUTTON  # 🔥 左鍵開火（可改成其他鍵）

# 🔥 點射控制（防止連發失控）
BURST_MODE = True           # True = 點射模式, False = 持續開火
BURST_SHOTS = 2             # 每次點射發射數（建議 3-5）
BURST_INTERVAL_MS = 200      # 每次點射間隔（毫秒）
SHOT_DURATION_MS = 80       # 單次射擊持續時間（毫秒，控制射速）

# 🔥 後坐力補償（實驗性）
RECOIL_COMPENSATION = True  # True = 啟用下壓補償
RECOIL_STRENGTH = 4          # 每發子彈的下壓像素（需根據武器調整）

# 瞄準偏移
HEAD_AIM_OFFSET = 0.0
BODY_AIM_OFFSET = 0.05   # 微調到 x%

# class 定義
CLASS_ENEMY = 0
CLASS_HEAD = 1

# 效能優化
TARGET_FPS = 300         # 🔥 極限幀率
FRAME_TIME = 1 / TARGET_FPS
SKIP_FRAME_VISUALIZATION = True  # 🔥 True = 不顯示視窗 (再提升 30% FPS)
ENABLE_PERFORMANCE_MONITORING = True  # 🔥 顯示詳細效能分析
REDUCE_DEBUG_OUTPUT = True  # 🔥 減少 print 輸出

# ================= Trigger Bot 控制器 =================
class TriggerBot:
    def __init__(self, radius, delay_ms, trigger_key, burst_mode=True, 
                 burst_shots=3, burst_interval_ms=80, shot_duration_ms=60,
                 recoil_comp=False, recoil_strength=2):
        self.radius = radius
        self.delay = delay_ms / 1000.0
        self.trigger_key = trigger_key
        self.last_trigger_time = 0
        self.is_firing = False
        
        # 點射控制
        self.burst_mode = burst_mode
        self.burst_shots = burst_shots
        self.burst_interval = burst_interval_ms / 1000.0
        self.shot_duration = shot_duration_ms / 1000.0
        
        # 點射狀態
        self.current_burst_count = 0
        self.burst_start_time = 0
        self.in_burst = False
        self.last_shot_time = 0
        
        # 後坐力補償
        self.recoil_comp = recoil_comp
        self.recoil_strength = recoil_strength
        self.shots_fired_in_burst = 0
        
    def check_and_fire(self, detected_objects, center_f, enable_trigger):
        """檢查準心範圍內是否有目標，並自動開火（帶點射控制）"""
        if not enable_trigger:
            self.release()
            self.reset_burst()
            return False
        
        current_time = time.time()
        
        # 檢查準心範圍內是否有目標
        target_in_crosshair = False
        for obj in detected_objects:
            tx, ty = obj['target']
            dist_from_center = np.hypot(tx - center_f, ty - center_f)
            
            if dist_from_center <= self.radius:
                target_in_crosshair = True
                break
        
        if not target_in_crosshair:
            self.release()
            self.reset_burst()
            return False
        
        # 點射模式
        if self.burst_mode:
            return self._burst_fire(current_time)
        else:
            # 持續開火模式
            if current_time - self.last_trigger_time >= self.delay:
                self.fire()
                self.last_trigger_time = current_time
                return True
            return False
    
    def _burst_fire(self, current_time):
        """點射邏輯：發射 N 發 → 停止 → 等待 → 重複"""
        # 如果沒有在點射中，且距離上次點射足夠久
        if not self.in_burst:
            if current_time - self.burst_start_time >= self.burst_interval:
                # 開始新的點射
                self.in_burst = True
                self.current_burst_count = 0
                self.burst_start_time = current_time
                self.shots_fired_in_burst = 0
        
        # 在點射中
        if self.in_burst:
            # 檢查是否已經發射足夠的子彈
            if self.current_burst_count < self.burst_shots:
                # 按住開火鍵一小段時間
                if current_time - self.last_shot_time >= (self.shot_duration / self.burst_shots):
                    self.fire()
                    self.current_burst_count += 1
                    self.shots_fired_in_burst += 1
                    self.last_shot_time = current_time
                    
                    # 後坐力補償
                    if self.recoil_comp:
                        self._compensate_recoil()
                    
                    return True
            else:
                # 點射完成，釋放並等待下次
                self.release()
                self.in_burst = False
                return False
        
        return False
    
    def _compensate_recoil(self):
        """後坐力補償：向下微調滑鼠"""
        if self.shots_fired_in_burst > 0:
            # 後坐力隨著射擊次數增加
            compensation = int(self.recoil_strength * self.shots_fired_in_burst * 0.8)
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, compensation, 0, 0)
    
    def fire(self):
        """按下開火鍵"""
        if not self.is_firing:
            ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            self.is_firing = True
    
    def release(self):
        """釋放開火鍵"""
        if self.is_firing:
            ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            self.is_firing = False
    
    def reset_burst(self):
        """重置點射狀態"""
        self.in_burst = False
        self.current_burst_count = 0
        self.shots_fired_in_burst = 0
    
    def force_release(self):
        """強制釋放（用於關閉輔助時）"""
        self.release()
        self.reset_burst()

# ================= 平滑移動控制器 =================
class SmoothAimController:
    def __init__(self, smoothing=0.25, max_speed=40, min_threshold=2):
        self.smoothing = smoothing
        self.max_speed = max_speed
        self.min_threshold = min_threshold
        self.current_target = None
        self.velocity_x = 0
        self.velocity_y = 0
        
        # 目標位置歷史（用於預測）
        self.target_history = deque(maxlen=TARGET_HISTORY_SIZE)
        
    def update(self, target_x, target_y, mouse_x, mouse_y):
        """
        使用指數平滑 + 速度限制 + 預測
        """
        # 記錄目標歷史
        self.target_history.append((target_x, target_y))
        
        # 預測目標移動
        predicted_x, predicted_y = self._predict_target_position(target_x, target_y)
        
        # 計算誤差
        error_x = predicted_x - mouse_x
        error_y = predicted_y - mouse_y
        distance = np.hypot(error_x, error_y)
        
        # 小於閾值不移動（減少抖動）
        if distance < self.min_threshold:
            return 0, 0
        
        # 動態平滑因子（距離越遠，反應越快）
        dynamic_smoothing = self.smoothing
        if distance > 100:
            dynamic_smoothing = min(self.smoothing * 1.5, 0.5)  # 遠距離加速
        elif distance < 20:
            dynamic_smoothing = max(self.smoothing * 0.7, 0.1)  # 近距離減速
        
        # 指數平滑速度
        self.velocity_x = self.velocity_x * (1 - dynamic_smoothing) + error_x * dynamic_smoothing
        self.velocity_y = self.velocity_y * (1 - dynamic_smoothing) + error_y * dynamic_smoothing
        
        # 限制最大速度
        speed = np.hypot(self.velocity_x, self.velocity_y)
        if speed > self.max_speed:
            scale = self.max_speed / speed
            self.velocity_x *= scale
            self.velocity_y *= scale
        
        return int(self.velocity_x), int(self.velocity_y)
    
    def _predict_target_position(self, current_x, current_y):
        """預測目標下一幀位置（線性外推）"""
        if len(self.target_history) < 2:
            return current_x, current_y
        
        # 計算平均速度
        positions = list(self.target_history)
        velocities_x = [positions[i][0] - positions[i-1][0] for i in range(1, len(positions))]
        velocities_y = [positions[i][1] - positions[i-1][1] for i in range(1, len(positions))]
        
        avg_vx = np.mean(velocities_x) if velocities_x else 0
        avg_vy = np.mean(velocities_y) if velocities_y else 0
        
        # 預測位置
        predicted_x = current_x + avg_vx * PREDICTION_WEIGHT
        predicted_y = current_y + avg_vy * PREDICTION_WEIGHT
        
        return predicted_x, predicted_y
    
    def reset(self):
        self.velocity_x = 0
        self.velocity_y = 0
        self.target_history.clear()

# ================= 貝茲曲線平滑（備選方案）=================
class BezierAimController:
    """使用貝茲曲線實現超平滑移動"""
    def __init__(self, duration_ms=100):
        self.duration = duration_ms / 1000.0  # 轉換為秒
        self.start_pos = None
        self.target_pos = None
        self.start_time = None
        self.is_moving = False
        
    def start_move(self, current_x, current_y, target_x, target_y):
        self.start_pos = (current_x, current_y)
        self.target_pos = (target_x, target_y)
        self.start_time = time.time()
        self.is_moving = True
        
    def update(self):
        if not self.is_moving:
            return 0, 0
        
        elapsed = time.time() - self.start_time
        t = min(elapsed / self.duration, 1.0)  # 0 到 1
        
        if t >= 1.0:
            self.is_moving = False
            return 0, 0
        
        # 使用緩動函數（easeOutCubic）
        eased_t = 1 - pow(1 - t, 3)
        
        # 計算當前應該在的位置
        current_x = self.start_pos[0] + (self.target_pos[0] - self.start_pos[0]) * eased_t
        current_y = self.start_pos[1] + (self.target_pos[1] - self.start_pos[1]) * eased_t
        
        # 計算需要移動的量（與上一幀的差異）
        if not hasattr(self, 'last_pos'):
            self.last_pos = self.start_pos
        
        move_x = current_x - self.last_pos[0]
        move_y = current_y - self.last_pos[1]
        self.last_pos = (current_x, current_y)
        
        return int(move_x), int(move_y)

# ================= 工具函式 =================
def get_mouse_pos():
    return win32api.GetCursorPos()

def calculate_aim_point(cls, x1, y1, x2, y2, center_f, debug=False):
    """計算瞄準點 (解決腳部問題)"""
    tx = (x1 + x2) / 2
    box_height = y2 - y1
    box_width = x2 - x1
    
    if cls == CLASS_HEAD:
        # 頭部：直接瞄準中心
        ty = y1 + box_height * (0.5 + HEAD_AIM_OFFSET)
        priority = 2
        aim_type = "HEAD"
    else:
        # 身體：瞄準上方 18% (頸部/胸口位置)
        ty = y1 + box_height * BODY_AIM_OFFSET
        priority = 1
        aim_type = "BODY"
    
    # 計算距離準心的距離
    dist = np.hypot(tx - center_f, ty - center_f)
    
    # 🔥 除錯輸出（可選）
    if debug and not REDUCE_DEBUG_OUTPUT:
        print(f"[{aim_type}] cls={cls} | box=({int(x1)},{int(y1)},{int(x2)},{int(y2)}) | "
              f"aim=({int(tx)},{int(ty)}) | dist={int(dist)} | priority={priority}")
    
    return tx, ty, priority, dist

# ================= 主程式 =================
def main():
    print("=" * 60)
    print(f"✅ 平滑瞄準系統 v3.0 (TensorRT 優化版)")
    print(f"📺 解析度: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    print(f"🎯 偵測區域: {DETECTION_SIZE}x{DETECTION_SIZE}")
    print(f"⚙️  平滑度: {SMOOTHING_FACTOR} | 最大速度: {MAX_MOVE_SPEED}px/frame")
    print(f"🔮 預測權重: {PREDICTION_WEIGHT}")
    print(f"⚡ 目標 FPS: {TARGET_FPS}")
    if ENABLE_TRIGGER_BOT:
        mode = "點射" if BURST_MODE else "連發"
        print(f"🔫 Trigger Bot: 啟用 | 模式={mode} | 半徑={TRIGGER_RADIUS}px | 延遲={TRIGGER_DELAY_MS}ms")
        if BURST_MODE:
            print(f"   ├─ 點射: {BURST_SHOTS}發/次 | 間隔={BURST_INTERVAL_MS}ms")
        if RECOIL_COMPENSATION:
            print(f"   └─ 後坐力補償: 強度={RECOIL_STRENGTH}px/發")
    print("=" * 60)
    print("🎮 控制說明:")
    print("   [X] 開/關輔助瞄準 (Aimbot)")
    print("   [C] 開/關自動開火 (Trigger Bot) - 可獨立使用")
    print("   [Q] 退出程式")
    print("💡 提示: Trigger Bot 可以單獨開啟，不需要 Aimbot")
    print("=" * 60)

    # 載入模型並啟用 GPU
    import torch
    import os
    
    # 檢查模型格式
    model_ext = os.path.splitext(MODEL_PATH)[1]
    
    print(f"\n🔍 正在載入模型...")
    
    if model_ext == '.engine':
        print(f"🔥 載入 TensorRT Engine: {MODEL_PATH}")
        model = YOLO(MODEL_PATH, task='detect')
        device = 'cuda:0'
        using_tensorrt = True
    elif model_ext == '.pt':
        print(f"📦 載入 PyTorch 模型: {MODEL_PATH}")
        model = YOLO(MODEL_PATH, task='detect')
        using_tensorrt = False
        
        # 嘗試轉換為 TensorRT (第一次會較慢)
        if torch.cuda.is_available():
            print("🔧 正在轉換為 TensorRT Engine (首次需要 1-2 分鐘)...")
            try:
                # 匯出為 TensorRT
                engine_path = MODEL_PATH.replace('.pt', '.engine')
                if not os.path.exists(engine_path):
                    model.export(format='engine', device=0, half=True, imgsz=DETECTION_SIZE)
                    print(f"✅ TensorRT Engine 已生成: {engine_path}")
                    print("💡 下次請直接使用 .engine 檔案以獲得最佳效能")
                else:
                    print(f"💡 發現已存在的 Engine: {engine_path}")
                    print("   建議直接使用 .engine 檔案")
            except Exception as e:
                print(f"⚠️  TensorRT 轉換失敗，使用 GPU 直接推理: {e}")
        
        device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
    else:
        print(f"❌ 不支援的模型格式: {model_ext}")
        return
    
    # 檢查 CUDA
    if torch.cuda.is_available():
        print(f"✅ GPU 已啟用: {torch.cuda.get_device_name(0)}")
        print(f"📊 VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        print(f"🔥 CUDA 版本: {torch.version.cuda}")
    else:
        print("❌ 警告: 未偵測到 CUDA，使用 CPU (FPS 會很慢！)")
        print("💡 請安裝: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")
        device = 'cpu'
    
    if device != 'cpu' and model_ext != '.engine':
        model.to(device)
    
    print(f"🤖 模型類別: {model.names}")
    print(f"📍 使用設備: {device}")
    print(f"⚡ TensorRT: {'✅ 已啟用' if using_tensorrt or model_ext == '.engine' else '❌ 未啟用'}")
    print("=" * 60)

    sct = mss.mss()

    center_f = DETECTION_SIZE // 2
    screen_cx = SCREEN_WIDTH // 2
    screen_cy = SCREEN_HEIGHT // 2
    monitor_roi = {
        "top": int(screen_cy - center_f),
        "left": int(screen_cx - center_f),
        "width": DETECTION_SIZE,
        "height": DETECTION_SIZE
    }

    # 使用平滑控制器
    aim_controller = SmoothAimController(
        smoothing=SMOOTHING_FACTOR,
        max_speed=MAX_MOVE_SPEED,
        min_threshold=MIN_MOVE_THRESHOLD
    )
    
    # Trigger Bot 控制器
    trigger_bot = TriggerBot(
        radius=TRIGGER_RADIUS,
        delay_ms=TRIGGER_DELAY_MS,
        trigger_key=TRIGGER_KEY,
        burst_mode=BURST_MODE,
        burst_shots=BURST_SHOTS,
        burst_interval_ms=BURST_INTERVAL_MS,
        shot_duration_ms=SHOT_DURATION_MS,
        recoil_comp=RECOIL_COMPENSATION,
        recoil_strength=RECOIL_STRENGTH
    )

    active = False
    trigger_active = ENABLE_TRIGGER_BOT  # Trigger Bot 獨立開關
    prev_time = time.time()
    frame_count = 0
    fps_update_time = time.time()
    fps_display = 0

    # 追蹤統計
    lock_duration = 0
    last_target = None
    total_shots = 0  # 統計開火次數
    
    # 🔥 效能監控
    perf_timers = {
        'capture': [],
        'inference': [],
        'processing': [],
        'visualization': [],
        'total': []
    }

    print("\n⏳ 系統就緒，等待指令...\n")

    while True:
        loop_start = time.time()
        
        # ⏱️ 計時開始
        perf_capture_start = time.time()

        # 熱鍵檢測
        if keyboard.is_pressed('x'):
            active = not active
            status = "🟢 開啟" if active else "🔴 關閉"
            print(f"\n{'='*60}")
            print(f"輔助瞄準: {status}")
            print(f"{'='*60}\n")
            aim_controller.reset()
            if not active:
                trigger_bot.force_release()  # 關閉時釋放開火鍵
            time.sleep(0.3)
        
        if keyboard.is_pressed('c'):
            trigger_active = not trigger_active
            status = "🟢 開啟" if trigger_active else "🔴 關閉"
            print(f"\n{'='*60}")
            print(f"Trigger Bot: {status}")
            print(f"{'='*60}\n")
            trigger_bot.force_release()  # 切換時釋放開火鍵
            time.sleep(0.3)

        if keyboard.is_pressed('q'):
            trigger_bot.force_release()  # 退出前釋放
            print("\n👋 程式結束")
            break

        # 擷取畫面
        sct_img = sct.grab(monitor_roi)
        frame = np.ascontiguousarray(cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR))
        
        perf_capture_time = time.time() - perf_capture_start
        
        # ⏱️ 推理計時
        perf_inference_start = time.time()

        # YOLO 推理（TensorRT 極速模式）
        results = model.predict(
            frame, 
            imgsz=DETECTION_SIZE, 
            conf=CONF_THRESHOLD, 
            iou=IOU_THRESHOLD,      # 🔥 NMS IoU 閾值
            verbose=False, 
            half=True,              # FP16
            device=device,
            max_det=15,             # 🔥 最多偵測 15 個目標
            agnostic_nms=True,      # 更快的 NMS
            classes=[CLASS_ENEMY, CLASS_HEAD]  # 🔥 只偵測指定類別
        )
        
        perf_inference_time = time.time() - perf_inference_start
        
        # ⏱️ 處理計時
        perf_processing_start = time.time()

        # 尋找最佳目標
        best_target = None
        best_priority = -1
        min_dist = float('inf')
        detected_objects = []

        for r in results:
            if r.boxes is None:
                continue
            
            for box in r.boxes:
                cls = int(box.cls[0])
                if cls not in (CLASS_ENEMY, CLASS_HEAD):
                    continue

                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])

                tx, ty, priority, dist = calculate_aim_point(cls, x1, y1, x2, y2, center_f, debug=False)

                detected_objects.append({
                    'cls': cls,
                    'conf': conf,
                    'dist': dist,
                    'box': (x1, y1, x2, y2),
                    'target': (tx, ty),
                    'priority': priority
                })

                if dist < MAX_LOCK_DISTANCE:
                    if priority > best_priority or (priority == best_priority and dist < min_dist):
                        best_priority = priority
                        min_dist = dist
                        best_target = (tx, ty)
        
        perf_processing_time = time.time() - perf_processing_start
        
        # ⏱️ 視覺化計時
        perf_visualization_start = time.time()

        # 平滑移動控制
        if active and best_target:
            tx, ty = best_target
            mouse_x, mouse_y = get_mouse_pos()

            # 轉換到螢幕座標
            target_screen_x = monitor_roi["left"] + tx
            target_screen_y = monitor_roi["top"] + ty

            # 🔥 除錯：顯示當前鎖定的目標類型
            locked_obj = next((obj for obj in detected_objects if obj['target'] == best_target), None)
            if locked_obj and not REDUCE_DEBUG_OUTPUT:
                target_type = "HEAD" if locked_obj['cls'] == CLASS_HEAD else "BODY"
                print(f"🎯 鎖定: {target_type} | 距離={int(locked_obj['dist'])}px | 優先級={locked_obj['priority']}")

            # 獲取平滑移動量
            move_x, move_y = aim_controller.update(
                target_screen_x, 
                target_screen_y, 
                mouse_x, 
                mouse_y
            )

            # 執行移動
            if abs(move_x) > 0 or abs(move_y) > 0:
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)

            # 追蹤鎖定時長
            if last_target == best_target:
                lock_duration += 1
            else:
                lock_duration = 0
            last_target = best_target

        else:
            aim_controller.reset()
            lock_duration = 0
            last_target = None
        
        # Trigger Bot 自動開火（獨立運作，不需要 aimbot 開啟）
        fired = trigger_bot.check_and_fire(detected_objects, center_f, trigger_active)
        if fired:
            total_shots += 1

        # FPS 計算
        frame_count += 1
        if frame_count >= 30:
            current_time = time.time()
            fps_display = int(frame_count / (current_time - fps_update_time))
            fps_update_time = current_time
            frame_count = 0
            
            # 🔥 效能分析（每 30 幀顯示一次）
            if ENABLE_PERFORMANCE_MONITORING and perf_timers['total']:
                avg_capture = np.mean(perf_timers['capture'][-30:]) * 1000
                avg_inference = np.mean(perf_timers['inference'][-30:]) * 1000
                avg_processing = np.mean(perf_timers['processing'][-30:]) * 1000
                avg_viz = np.mean(perf_timers['visualization'][-30:]) * 1000
                avg_total = np.mean(perf_timers['total'][-30:]) * 1000
                
                print(f"\n📊 效能分析 (平均耗時 ms):")
                print(f"   螢幕擷取: {avg_capture:.1f}ms")
                print(f"   YOLO 推理: {avg_inference:.1f}ms ⚡")
                print(f"   目標處理: {avg_processing:.1f}ms")
                print(f"   視覺化: {avg_viz:.1f}ms")
                print(f"   總計: {avg_total:.1f}ms → 理論最大FPS: {1000/avg_total:.0f}\n")
                
                # 瓶頸診斷
                bottleneck = max([
                    ('擷取', avg_capture),
                    ('推理', avg_inference),
                    ('處理', avg_processing),
                    ('視覺化', avg_viz)
                ], key=lambda x: x[1])
                
                if bottleneck[1] > 10:
                    print(f"⚠️  瓶頸: {bottleneck[0]} ({bottleneck[1]:.1f}ms)")
                    if bottleneck[0] == '推理':
                        print("   建議: 確認是否使用 TensorRT Engine")
                    elif bottleneck[0] == '視覺化':
                        print("   建議: 設定 SKIP_FRAME_VISUALIZATION = True")
                    elif bottleneck[0] == '擷取':
                        print("   建議: 降低 DETECTION_SIZE")

        # 視覺化（可選擇性關閉以提升 FPS）
        if not SKIP_FRAME_VISUALIZATION:
            for obj in detected_objects:
                x1, y1, x2, y2 = obj['box']
                tx, ty = obj['target']
                
                color = (0, 0, 255) if obj['cls'] == CLASS_HEAD else (0, 255, 0)
                thickness = 3 if obj['target'] == best_target else 2
                
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
                cv2.circle(frame, (int(tx), int(ty)), 4, color, -1)
                
                label = f"{'HEAD' if obj['cls'] == CLASS_HEAD else 'BODY'} {obj['dist']:.0f}px"
                cv2.putText(frame, label, (int(x1), int(y1) - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 繪製移動軌跡（顯示預測）
            if best_target and len(aim_controller.target_history) > 1:
                points = list(aim_controller.target_history)
                for i in range(len(points) - 1):
                    pt1 = (int(points[i][0] - monitor_roi["left"]), 
                           int(points[i][1] - monitor_roi["top"]))
                    pt2 = (int(points[i+1][0] - monitor_roi["left"]), 
                           int(points[i+1][1] - monitor_roi["top"]))
                    cv2.line(frame, pt1, pt2, (255, 255, 0), 1)

            # 狀態資訊
            aim_color = (0, 255, 0) if active else (0, 0, 255)
            aim_text = "AIM:ON" if active else "AIM:OFF"
            
            trigger_color = (0, 255, 0) if trigger_active else (128, 128, 128)
            trigger_text = "TB:ON" if trigger_active else "TB:OFF"
            
            cv2.putText(frame, f"FPS: {fps_display} | {aim_text} | {trigger_text}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, aim_color, 2)
            
            cv2.putText(frame, f"Targets: {len(detected_objects)} | Lock: {lock_duration}f | Shots: {total_shots}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # 顯示點射狀態
            if trigger_active and trigger_bot.burst_mode:
                burst_info = f"Burst: {trigger_bot.current_burst_count}/{trigger_bot.burst_shots}"
                cv2.putText(frame, burst_info, (10, 90),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 2)
                
                cv2.putText(frame, f"Speed: {int(np.hypot(aim_controller.velocity_x, aim_controller.velocity_y))}px/f", 
                           (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                cv2.putText(frame, f"Speed: {int(np.hypot(aim_controller.velocity_x, aim_controller.velocity_y))}px/f", 
                           (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 準心
            cv2.circle(frame, (center_f, center_f), 5, (255, 0, 0), -1)
            cv2.circle(frame, (center_f, center_f), MAX_LOCK_DISTANCE, (255, 255, 0), 1)
            
            # Trigger Bot 範圍（橙色圓圈）
            if trigger_active:
                cv2.circle(frame, (center_f, center_f), TRIGGER_RADIUS, (0, 165, 255), 2)

            cv2.imshow("Smooth Aim Vision", frame)
            cv2.waitKey(1)
            
            perf_visualization_time = time.time() - perf_visualization_start
        else:
            # 只在終端顯示 FPS
            if frame_count == 0:
                aim_status = "ON" if active else "OFF"
                tb_status = "ON" if trigger_active else "OFF"
                print(f"\rFPS: {fps_display} | AIM: {aim_status} | TB: {tb_status} | Targets: {len(detected_objects)} | Shots: {total_shots}", 
                      end='', flush=True)
            
            perf_visualization_time = 0  # 無視覺化

        # 🔥 記錄效能數據
        if ENABLE_PERFORMANCE_MONITORING:
            perf_timers['capture'].append(perf_capture_time)
            perf_timers['inference'].append(perf_inference_time)
            perf_timers['processing'].append(perf_processing_time)
            perf_timers['visualization'].append(perf_visualization_time)
            perf_timers['total'].append(time.time() - loop_start)
            
            # 只保留最近 100 幀的數據
            for key in perf_timers:
                if len(perf_timers[key]) > 100:
                    perf_timers[key] = perf_timers[key][-100:]

        # 幀率限制（根據是否顯示視窗調整）
        if not SKIP_FRAME_VISUALIZATION:
            elapsed = time.time() - loop_start
            sleep_time = FRAME_TIME - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
        # 如果關閉視窗，盡可能跑滿 CPU (無限制)

    if not SKIP_FRAME_VISUALIZATION:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()