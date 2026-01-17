# ⚡ YOLO Real-time Vision Framework (Universal Version)
### ⚡ YOLO 即時視覺辨識架構 (通用加速版)

[English](#english) | [中文說明](#中文說明)

---

<a name="english"></a>
## 🌐 English Description

A high-speed real-time object detection framework optimized for NVIDIA GPUs (especially RTX 40/50 series). This project focuses on **stability**, **smooth tracking**, and **minimal CPU overhead** using YOLOv8 and TensorRT.

### 🚀 Key Features
* **Universal Capture Engine**: Supports multi-mode screen capture (MSS/Win32) for maximum compatibility across different Windows environments.
* **PID Stabilization**: Implements Proportional-Integral-Derivative (PID) control logic to eliminate cursor jitter and "overshooting."
* **TensorRT Ready**: Optimized for `.engine` models, achieving consistent sub-5ms inference times.
* **Smart ROI**: Only processes a specific Region of Interest (ROI) to save GPU resources for the actual game.

### ⚙️ Setup
1.  **Dependencies**:
    ```bash
    pip install ultralytics mss opencv-python pywin32 keyboard numpy wheel
    ```
    ```bash
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
    ```
    Change your pytorch for your GPU!
2.  **Model**: Place your `best.engine` or `best.pt` in the root directory.
3.  **Run**: Execute `python main.py` with Administrative privileges.

---
##Rember to Install Pytorch to your computer
<a name="中文說明"></a>
## 🇹🇼 中文說明

本專案是一個針對 NVIDIA GPU (特別是 RTX 40/50 系列) 優化的即時目標偵測架構。核心開發重點在於**操作穩定性**、**平滑追蹤**以及**極低的 CPU 佔用率**。

### 🚀 核心優勢
* **通用擷取引擎**: 支援 MSS/Win32 等多種擷取方式，確保在不同 Windows 版本與遊戲環境下都能穩定運作。
* **PID 穩定演算法**: 引入 PID 控制邏輯，有效解決準心跳動與「過度修正」問題，提供絲滑的吸附感。
* **TensorRT 深度優化**: 專為 `.engine` 格式設計，確保在 3440x1440px 等高解析度下仍能保持極低延遲。
* **局部區域偵測**: 僅針對螢幕中心區域進行擷取 (ROI)，節省 GPU 效能以維持遊戲幀率。

### ⚙️ 安裝與使用
1.  **安裝必要套件**:
    ```bash
    pip install ultralytics mss opencv-python pywin32 keyboard numpy
    ```
2.  **模型準備**: 將你的 `best.engine` 模型檔案放入專案根目錄。
3.  **啟動**: 以**管理員權限**執行 `python main.py`。

---

## 🎮 Controls / 操作方式
| Key / 按鍵 | Action / 功能 |
| :--- | :--- |
| **Hold [X]** | Toggle Tracking / 按住開啟瞄準輔助 |
| **Press [C]** | Toggle TriggerBot / 切換自動開火模式 |
| **Press [Q]** | Emergency Exit / 安全退出程式 |

## 📊 Performance Benchmark / 效能表現
*Tested on RTX 5080 @ 21:9 Ultrawide*
* **Inference**: ~1.5ms - 2.5ms
* **Capture**: ~3ms (MSS Optimized)
* **Overall Latency**: Ultra-low input lag

## ⚠️ Disclaimer / 免責聲明
This project is for **technical research and educational purposes** only. It demonstrates the application of PID controllers and AI inference in real-time environments. The author does not condone or support any use in competitive online gaming.
本專案僅供**技術研究與教育用途**，旨在展示 PID 控制器與 AI 推理在即時環境中的應用。作者不鼓勵、亦不支援任何違反遊戲公平性的行為。

## 📄 License
[MIT License](LICENSE)
