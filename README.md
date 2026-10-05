# sgEEG — LabChart .adicht 电生理三步分析管线

从 LabChart / PowerLab `.adicht` 文件到自包含 HTML 报告的完整电生理分析流程。

```
step1_extract.py      .adicht → extracted/*.csv + _metadata.json   (adi-reader)
step2_analysis.py     → plots/01-08*.png + _analysis_summary.txt
step3_html_report.py  → 自包含 HTML 报告（图片 base64 内嵌）
```

## 功能

- EEG/EMG 提取：多文件、多 record、多通道，逐 record 采样率/单位
- 频段分解：Delta/Theta/Alpha/Beta/Gamma（1–100 Hz）
- Welch 功率谱密度、RMS 包络、频段功率时间 course
- 刺激检测（marker 通道阈值法）、刺激锁定诱发电位叠加平均（±SEM）
- LTP/LTD 分析：各试次 post/pre RMS 比值 + 趋势判定
- 跨动物/跨批次对比
- 8 张标准图 + 定量文本汇总 + 单文件 HTML 报告
- **进阶（step2b）**：刺激伪迹去除、trial 质控、fPSP 斜率（10–90% 拟合 + MAD 稳健剔除）、
  Morlet 小波时频 + 刺激锁定 ERSP、CV 突触释放概率分析、Cohen's d 效应量

## 安装

```bash
pip install adi-reader numpy pandas scipy matplotlib
```

## 使用

见 [SKILL.md](SKILL.md)（含 11 条踩坑清单与已验证批次）。每次使用：新建批次目录，
拷入 `scripts/` 三个脚本 + 原始 `.adicht`，改头部路径配置后顺序执行。

## 来源

源自 SG20260417DEV01 项目实战（SD 大鼠海马 LTP、C57 小鼠 EEG/EMG 分级刺激），
已验证 3 个批次。

## License

MIT
