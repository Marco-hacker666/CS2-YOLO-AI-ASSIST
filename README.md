# CS2-YOLO-AI-ASSIST
# ⚡ YOLO Real-time Vision Assistant (High Performance)
### ⚡ YOLO 即時視覺輔助系統 (高性能版)

[English](#english) | [中文說明](#中文說明)

---

<a name="english"></a>
## 🌐 English Description

This project is a high-performance, low-latency object detection and aiming assistance framework. It demonstrates the integration of **YOLOv8/TensorRT**, **DXCam**, and **Win32API** to achieve sub-5ms latency in real-time computer vision tasks.

### 🚀 Key Features
* **Ultra-Low Latency Capture**: Powered by [DXCam](https://github.com/ra1nty/DXCam) (Desktop Duplication API).
* **TensorRT Acceleration**: Supports `.engine` format for maximum GPU inference speed (FP16).
* **PID/Smooth Control**: Advanced smoothing algorithms for human-like cursor movement.
* **Optimized Pipeline**: Zero-copy RGB data flow from capture to inference.

### ⚙️ Installation
1.  **Install dependencies**:
    ```bash
    pip install ultralytics dxcam opencv-python pywin32 keyboard numpy
    ```
2.  **Export Model to TensorRT**:
    ```bash
    yolo export model=your_model.pt format=engine device=0 half=True
    ```
3.  **Run**: `python main.py`

---

<a name="中文說明"></a>
## 🇹🇼 中文說明

本專案是一個針對高性能、低延遲目標偵測與瞄準輔助的技術架構。主要展示如何整合 **YOLOv8/TensorRT**、**DXCam** 與 **Win32API**，在即時電腦視覺任務中實現低於 5ms 的極低延遲。

### 🚀 核心優勢
* **極速螢幕擷取**: 使用 [DXCam](https://github.com/ra1nty/DXCam) (Windows 桌面重複 API)，遠快於 MSS 或 OpenCV。
* **TensorRT 硬體加速**: 支援 `.engine` 模型格式，充分發揮 NVIDIA GPU 的 FP16 推理性能。
* **平滑軌跡控制**: 內建平滑演算法，模擬真實人類滑鼠移動軌跡，降低「非人感」。
* **效能優化工作流**: 擷取後的 RGB 數據直接餵入 AI 模型，減少記憶體複製與色彩空間轉換的開銷。

### ⚙️ 安裝環境
1.  **安裝必要套件**:
    ```bash
    pip install ultralytics dxcam opencv-python pywin32 keyboard numpy
    ```
2.  **轉換模型至 TensorRT (推薦)**:
    ```bash
    yolo export model=your_model.pt format=engine device=0 half=True
    ```
3.  **啟動程式**: 執行 `python main.py`

---

## 📊 Performance Benchmark / 效能基準
Tested on **RTX 5080** @ 3440 x 1440:

| Stage / 階段 | Latency / 延遲 | Status |
| :--- | :--- | :--- |
| **Capture / 擷取** | ~1.2 ms | ✅ |
| **Inference / 推理** | ~1.8 ms | ✅ |
| **Total / 總延遲** | **< 4 ms** | 🚀 |

## 🎮 Controls / 操作方式
* **Hold [X]**: Activate Aim Assist / 按住 [X] 開啟瞄準輔助
* **Press [Q]**: Quit / 按 [Q] 安全退出系統

## ⚠️ Disclaimer / 免責聲明
This software is for **educational and research purposes only**. The author is not responsible for any bans or legal issues caused by using this in online games.
本軟體僅供**教育與學術研究用途**（例如測試電腦視覺延遲、人機互動等）。作者不承擔任何因在線上遊戲中使用此軟體而導致的封號或法律責任。

## 📄 License
[MIT License](LICENSE)a ez aim bot
