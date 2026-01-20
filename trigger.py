import cv2
import numpy as np
import mss
import time
import win32api, win32con
import keyboard
from ultralytics import YOLO
from collections import deque
import ctypes
import random
import threading
import os

# ================= 參數設定 (預設值) =================
class Config:
    def __init__(self):
        self.MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CS2.engine')
        self.SCREEN_WIDTH = 3440
        self.SCREEN_HEIGHT = 1440
        self.DETECTION_SIZE = 640
        
        # 平滑移動
        self.SMOOTHING_FACTOR = 0.3
        self.MIN_MOVE_THRESHOLD = 2
        self.MAX_MOVE_SPEED = 80
        self.MOUSE_JITTER = 0  # 新增：滑鼠抖動大小
        
        # 目標追蹤
        self.TARGET_HISTORY_SIZE = 3
        self.PREDICTION_WEIGHT = 0.4
        
        # 瞄準設定
        self.CONF_THRESHOLD = 0.5
        self.IOU_THRESHOLD = 0.5
        self.MAX_LOCK_DISTANCE = 280
        self.FOV_SIZE = 640  # 新增：可調整的 FOV (對應 DETECTION_SIZE)
        
        # Trigger Bot
        self.ENABLE_TRIGGER_BOT = False
        self.TRIGGER_RADIUS = 10
        self.TRIGGER_DELAY_MS = 0.1
        self.TRIGGER_KEY = "c"  # 改為字串以便 GUI 設定，內部再轉換
        
        # 點射控制
        self.BURST_MODE = True
        self.BURST_SHOTS = 3
        self.BURST_INTERVAL_MS = 250
        self.SHOT_DURATION_MS = 50
        
        # 後坐力 (RCS)
        self.RECOIL_COMPENSATION = True
        self.RECOIL_STRENGTH = 6
        
        # 瞄準偏移與部位選擇
        self.HEAD_AIM_OFFSET = 0.0      # 0.0 = 中心
        self.BODY_AIM_OFFSET = 0.02     # 0.02 = 接近頂部 (頸部)
        
        # 部位選擇: "HEAD", "NECK", "CHEST", "STOMACH"
        self.TARGET_PART = "HEAD" 
        
        # 效能與顯示
        self.TARGET_FPS = 300
        self.SKIP_FRAME_VISUALIZATION = True
        self.ENABLE_PERFORMANCE_MONITORING = False
        self.REDUCE_DEBUG_OUTPUT = True
        
        # 熱鍵
        self.AIM_TOGGLE_KEY = 'x'
        self.TRIGGER_TOGGLE_KEY = 'c'
        self.EXIT_KEY = 'q'

# 全域設定實例
cfg = Config()

# class 定義
CLASS_ENEMY = 0
CLASS_HEAD = 1

# ================= Trigger Bot 控制器 =================
class TriggerBot:
    def __init__(self):
        self.last_trigger_time = 0
        self.is_firing = False
        self.target_locked_time = None
        
        # 點射狀態
        self.current_burst_count = 0
        self.burst_start_time = 0
        self.in_burst = False
        self.last_shot_time = 0
        self.shots_fired_in_burst = 0
        
    def check_and_fire(self, detected_objects, center_f, enable_trigger):
        """檢查準心範圍內是否有目標，並自動開火（帶點射控制）"""
        if not enable_trigger:
            self.release()
            self.reset_burst()
            self.target_locked_time = None
            return False
        
        current_time = time.time()
        
        # 檢查準心範圍內是否有目標
        target_in_crosshair = False
        for obj in detected_objects:
            tx, ty = obj['target']
            dist_from_center = np.hypot(tx - center_f, ty - center_f)
            
            if dist_from_center <= cfg.TRIGGER_RADIUS:
                target_in_crosshair = True
                break
        
        if not target_in_crosshair:
            self.release()
            self.reset_burst()
            self.target_locked_time = None
            return False
        
        # 目標在準心內，檢查反應延遲
        if self.target_locked_time is None:
            self.target_locked_time = current_time
            
        if current_time - self.target_locked_time < (cfg.TRIGGER_DELAY_MS / 1000.0):
            return False
        
        # 點射模式
        if cfg.BURST_MODE:
            return self._burst_fire(current_time)
        else:
            # 持續開火模式 (預設 100ms 間隔)
            if current_time - self.last_trigger_time >= 0.1:
                self.fire()
                self.last_trigger_time = current_time
                return True
            return False
    
    def _burst_fire(self, current_time):
        """點射邏輯：發射 N 發 → 停止 → 等待 → 重複"""
        burst_interval = cfg.BURST_INTERVAL_MS / 1000.0
        shot_duration = cfg.SHOT_DURATION_MS / 1000.0
        
        # 如果沒有在點射中，且距離上次點射足夠久
        if not self.in_burst:
            if current_time - self.burst_start_time >= burst_interval:
                # 開始新的點射
                self.in_burst = True
                self.current_burst_count = 0
                self.burst_start_time = current_time
                self.shots_fired_in_burst = 0
        
        # 在點射中
        if self.in_burst:
            # 檢查是否已經發射足夠的子彈
            if self.current_burst_count < cfg.BURST_SHOTS:
                # 按住開火鍵一小段時間
                if current_time - self.last_shot_time >= (shot_duration / cfg.BURST_SHOTS):
                    self.fire()
                    self.current_burst_count += 1
                    self.shots_fired_in_burst += 1
                    self.last_shot_time = current_time
                    
                    # 後坐力補償
                    if cfg.RECOIL_COMPENSATION:
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
            # 使用 Config 中的 RCS 強度
            compensation_y = int(cfg.RECOIL_STRENGTH * self.shots_fired_in_burst * 0.8)
            
            # X 軸補償 (隨機左右輕微抖動，模擬人類控制)
            compensation_x = 0
            if cfg.MOUSE_JITTER > 0:
                compensation_x = random.randint(-int(cfg.RECOIL_STRENGTH/2), int(cfg.RECOIL_STRENGTH/2))

            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, compensation_x, compensation_y, 0, 0)
    
    def fire(self):
        """按下開火鍵"""
        if not self.is_firing:
            # 使用 cfg.TRIGGER_KEY 判斷按鍵 (如果是滑鼠左鍵)
            # 這裡簡化處理，假設 Trigger Bot 都是用左鍵開火模擬
            # 如果需要自訂 Trigger Key 觸發模擬按鍵，需要更複雜的對應
            # 暫時維持左鍵點擊
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
    def __init__(self):
        self.current_target = None
        self.velocity_x = 0
        self.velocity_y = 0
        
        # 目標位置歷史（用於預測）
        self.target_history = deque(maxlen=cfg.TARGET_HISTORY_SIZE)
        
    def update(self, target_x, target_y, mouse_x, mouse_y):
        """
        使用指數平滑 + 速度限制 + 預測 + 隨機抖動
        """
        # 更新歷史長度（如果設定改變）
        if self.target_history.maxlen != cfg.TARGET_HISTORY_SIZE:
            self.target_history = deque(list(self.target_history), maxlen=cfg.TARGET_HISTORY_SIZE)
            
        # 記錄目標歷史
        self.target_history.append((target_x, target_y))
        
        # 預測目標移動
        predicted_x, predicted_y = self._predict_target_position(target_x, target_y)
        
        # 計算誤差
        error_x = predicted_x - mouse_x
        error_y = predicted_y - mouse_y
        distance = np.hypot(error_x, error_y)
        
        # 小於閾值不移動（減少抖動）
        if distance < cfg.MIN_MOVE_THRESHOLD:
            return 0, 0
        
        # 動態平滑因子（距離越遠，反應越快）
        dynamic_smoothing = cfg.SMOOTHING_FACTOR
        if distance > 100:
            dynamic_smoothing = min(cfg.SMOOTHING_FACTOR * 1.5, 0.5)  # 遠距離加速
        elif distance < 20:
            dynamic_smoothing = max(cfg.SMOOTHING_FACTOR * 0.7, 0.1)  # 近距離減速
        
        # 指數平滑速度
        self.velocity_x = self.velocity_x * (1 - dynamic_smoothing) + error_x * dynamic_smoothing
        self.velocity_y = self.velocity_y * (1 - dynamic_smoothing) + error_y * dynamic_smoothing
        
        # 限制最大速度
        speed = np.hypot(self.velocity_x, self.velocity_y)
        if speed > cfg.MAX_MOVE_SPEED:
            scale = cfg.MAX_MOVE_SPEED / speed
            self.velocity_x *= scale
            self.velocity_y *= scale
            
        # 加入隨機抖動 (Jitter)
        final_x = int(self.velocity_x)
        final_y = int(self.velocity_y)
        
        if cfg.MOUSE_JITTER > 0:
            jitter_x = random.randint(-cfg.MOUSE_JITTER, cfg.MOUSE_JITTER)
            jitter_y = random.randint(-cfg.MOUSE_JITTER, cfg.MOUSE_JITTER)
            final_x += jitter_x
            final_y += jitter_y
        
        return final_x, final_y
    
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
        predicted_x = current_x + avg_vx * cfg.PREDICTION_WEIGHT
        predicted_y = current_y + avg_vy * cfg.PREDICTION_WEIGHT
        
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
    """計算瞄準點 (解決腳部問題，支援部位選擇)"""
    tx = (x1 + x2) / 2
    box_height = y2 - y1
    
    # 根據 TARGET_PART 調整優先級和偏移
    # 預設行為
    priority = 1
    aim_type = "BODY"
    
    # 計算 Y 座標
    if cls == CLASS_HEAD:
        # 如果檢測到頭部
        if cfg.TARGET_PART in ["HEAD", "NECK"]:
            # 瞄準頭部中心或微調
            ty = y1 + box_height * (0.5 + cfg.HEAD_AIM_OFFSET)
            priority = 2 # 最高優先
            aim_type = "HEAD"
        else:
            # 雖然有頭，但我們想瞄準身體 (例如 Chest)
            # 這通常不常見，因為 Head 框很小，如果想瞄準身體應該用 Body 框
            # 但如果只有 Head 框可用...
            ty = y2 + box_height * 0.5 # 往下瞄一點 (假設下面有身體)
            priority = 1
            aim_type = "HEAD(AS_BODY)"
            
    else: # CLASS_ENEMY (Body)
        # 根據部位選擇計算 offset
        # y1 是頂部, y2 是底部
        
        target_offset = 0.2 # 預設 Chest/Upper Body
        
        if cfg.TARGET_PART == "HEAD":
            target_offset = 0.08 # 嘗試瞄準頭部位置 (Box 頂端)
            priority = 1 # 如果有真正的 Head Class，那個會是 2
        elif cfg.TARGET_PART == "NECK":
            target_offset = 0.12 # 頸部
        elif cfg.TARGET_PART == "CHEST":
            target_offset = 0.25 # 胸口
        elif cfg.TARGET_PART == "STOMACH":
            target_offset = 0.5  # 腹部/中心
            
        # 應用微調
        final_offset = target_offset + cfg.BODY_AIM_OFFSET
        ty = y1 + box_height * final_offset
        aim_type = "BODY"

    # 計算距離準心的距離
    dist = np.hypot(tx - center_f, ty - center_f)
    
    # 🔥 除錯輸出（可選）
    if debug and not cfg.REDUCE_DEBUG_OUTPUT:
        print(f"[{aim_type}] cls={cls} | part={cfg.TARGET_PART} | aim=({int(tx)},{int(ty)}) | dist={int(dist)} | priority={priority}")
    
    return tx, ty, priority, dist

# ================= 遊戲助手類別 =================
class GameAssistant:
    def __init__(self):
        self.running = False
        self.thread = None
        self.model = None
        self.aim_controller = SmoothAimController()
        self.trigger_bot = TriggerBot()
        self.status_callback = None  # 用於 GUI 更新狀態
        
        # 狀態控制
        self.aim_enabled = False
        self.trigger_enabled = cfg.ENABLE_TRIGGER_BOT

    def set_callback(self, callback):
        self.status_callback = callback
        
    def toggle_aim(self, state=None):
        if state is not None:
            self.aim_enabled = state
        else:
            self.aim_enabled = not self.aim_enabled
        print(f"輔助瞄準: {'🟢 開啟' if self.aim_enabled else '🔴 關閉'}")
        if not self.aim_enabled:
            self.aim_controller.reset()

    def toggle_trigger(self, state=None):
        if state is not None:
            self.trigger_enabled = state
        else:
            self.trigger_enabled = not self.trigger_enabled
        print(f"Trigger Bot: {'🟢 開啟' if self.trigger_enabled else '🔴 關閉'}")
        if not self.trigger_enabled:
            self.trigger_bot.force_release()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None

    def _run_loop(self):
        print("=" * 60)
        print(f"✅ 平滑瞄準系統 v3.0 (GUI版)")
        
        # 載入模型並啟用 GPU
        import torch
        import os
        
        # 檢查模型格式
        MODEL_PATH = cfg.MODEL_PATH
        model_ext = os.path.splitext(MODEL_PATH)[1]
        
        print(f"\n🔍 正在載入模型: {MODEL_PATH}")
        
        try:
            if model_ext == '.engine':
                print(f"🔥 載入 TensorRT Engine")
                self.model = YOLO(MODEL_PATH, task='detect')
                device = 'cuda:0'
                using_tensorrt = True
            elif model_ext == '.pt':
                print(f"📦 載入 PyTorch 模型")
                self.model = YOLO(MODEL_PATH, task='detect')
                using_tensorrt = False
                
                # 嘗試轉換為 TensorRT
                if torch.cuda.is_available():
                    engine_path = MODEL_PATH.replace('.pt', '.engine')
                    if not os.path.exists(engine_path):
                        print("🔧 建議轉換為 TensorRT Engine 以獲得最佳效能")
                
                device = 'cuda:0' if torch.cuda.is_available() else 'cpu'
                print(f"🖥️  使用裝置: {device.upper()}")
            else:
                print(f"❌ 不支援的模型格式: {model_ext}")
                self.running = False
                return
            
            # 只有當不是 engine 且有裝置可用時才移動模型
            # engine 通常由 ultralytics 自動處理，不需要手動 .to()
            if model_ext != '.engine':
                self.model.to(device)
                
        except Exception as e:
            print(f"❌ 模型載入失敗: {e}")
            self.running = False
            return

        sct = mss.mss()

        # 初始變數
        # active = False (已改為 self.aim_enabled)
        # trigger_active = cfg.ENABLE_TRIGGER_BOT (已改為 self.trigger_enabled)
        frame_count = 0
        fps_update_time = time.time()
        fps_display = 0
        
        # 追蹤統計
        lock_duration = 0
        last_target = None
        total_shots = 0
        
        print("\n⏳ 系統就緒，循環開始...\n")

        while self.running:
            loop_start = time.time()
            
            # 更新參數
            center_f = cfg.DETECTION_SIZE // 2
            screen_cx = cfg.SCREEN_WIDTH // 2
            screen_cy = cfg.SCREEN_HEIGHT // 2
            monitor_roi = {
                "top": int(screen_cy - center_f),
                "left": int(screen_cx - center_f),
                "width": cfg.DETECTION_SIZE,
                "height": cfg.DETECTION_SIZE
            }
            
            # 熱鍵檢測 (使用 cfg 中的熱鍵設定)
            if keyboard.is_pressed(cfg.AIM_TOGGLE_KEY):
                self.toggle_aim()
                time.sleep(0.3)
            
            if keyboard.is_pressed(cfg.TRIGGER_TOGGLE_KEY):
                self.toggle_trigger()
                time.sleep(0.3)

            if keyboard.is_pressed(cfg.EXIT_KEY):
                self.trigger_bot.force_release()
                print("\n👋 程式結束")
                self.running = False
                if self.status_callback:
                    self.status_callback("stopped")
                break

            # 擷取畫面
            sct_img = sct.grab(monitor_roi)
            frame = np.ascontiguousarray(cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR))
            
            # YOLO 推理
            results = self.model.predict(
                frame, 
                imgsz=cfg.DETECTION_SIZE, 
                conf=cfg.CONF_THRESHOLD, 
                iou=cfg.IOU_THRESHOLD,
                verbose=False, 
                half=True,
                device=device,
                max_det=15,
                agnostic_nms=True,
                classes=[CLASS_ENEMY, CLASS_HEAD]
            )
            
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

                    if dist < cfg.MAX_LOCK_DISTANCE:
                        if priority > best_priority or (priority == best_priority and dist < min_dist):
                            best_priority = priority
                            min_dist = dist
                            best_target = (tx, ty)
            
            # 平滑移動控制
            if self.aim_enabled and best_target:
                tx, ty = best_target
                mouse_x, mouse_y = get_mouse_pos()

                # 轉換到螢幕座標
                target_screen_x = monitor_roi["left"] + tx
                target_screen_y = monitor_roi["top"] + ty

                # 獲取平滑移動量
                move_x, move_y = self.aim_controller.update(
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
                self.aim_controller.reset()
                lock_duration = 0
                last_target = None
            
            # Trigger Bot 自動開火
            fired = self.trigger_bot.check_and_fire(detected_objects, center_f, self.trigger_enabled)
            if fired:
                total_shots += 1

            # FPS 計算
            frame_count += 1
            if frame_count >= 30:
                current_time = time.time()
                fps_display = int(frame_count / (current_time - fps_update_time))
                fps_update_time = current_time
                frame_count = 0

            # 視覺化
            if not cfg.SKIP_FRAME_VISUALIZATION:
                for obj in detected_objects:
                    x1, y1, x2, y2 = obj['box']
                    tx, ty = obj['target']
                    
                    color = (0, 0, 255) if obj['cls'] == CLASS_HEAD else (0, 255, 0)
                    thickness = 3 if obj['target'] == best_target else 2
                    
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness)
                    cv2.circle(frame, (int(tx), int(ty)), 4, color, -1)
                
                # 狀態資訊
                aim_text = "AIM:ON" if self.aim_enabled else "AIM:OFF"
                tb_text = "TB:ON" if self.trigger_enabled else "TB:OFF"
                cv2.putText(frame, f"FPS: {fps_display} | {aim_text} | {tb_text}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

                cv2.imshow("Preview", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
            else:
                # 確保關閉視窗
                try:
                    if cv2.getWindowProperty("Preview", 0) >= 0:
                        cv2.destroyWindow("Preview")
                except:
                    pass

            # 幀率限制
            elapsed = time.time() - loop_start
            target_frame_time = 1 / cfg.TARGET_FPS
            if elapsed < target_frame_time:
                time.sleep(target_frame_time - elapsed)

        # 結束清理
        cv2.destroyAllWindows()
        print("停止運行。")

# 為了向下相容，保留一個 main
def main():
    assistant = GameAssistant()
    assistant.start()
    while assistant.running:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            assistant.stop()
            break

if __name__ == "__main__":
    main()