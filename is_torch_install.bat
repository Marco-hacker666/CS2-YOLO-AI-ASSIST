python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

---

## 📊 預期效能提升

| 設定 | FPS (預估) |
|------|-----------|
| CPU | 10-20 FPS ❌ |
| GPU (FP32) | 60-100 FPS ✅ |
| GPU (FP16) | 120-200 FPS 🔥 |

---

運行腳本後會顯示：
```
✅ GPU 已啟用: NVIDIA GeForce RTX 5080
📊 VRAM: 49.0 GB