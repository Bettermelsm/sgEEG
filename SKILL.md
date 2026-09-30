---
name: sgEEG
description: >-
  LabChart .adicht 神经电生理（EEG/EMG/LTP）三步分析管线：adi-reader 提取 CSV →
  频段分解/PSD/诱发电位/LTP 前后对比分析 → 自包含 HTML 报告。
  源自 SG20260417DEV01（SD 大鼠海马 LTP + C57 小鼠 EEG/EMG）实战批次。
  当用户提到 LabChart、adicht、ADInstruments、EEG/EMG 分析、LTP、诱发电位、
  频段功率（Delta/Theta/Alpha/Beta/Gamma）、电生理数据处理时触发。
license: Internal
compatibility: Windows / Python 3.10+；adi-reader、numpy、pandas、scipy、matplotlib
metadata:
  version: "1.0.0"
  status: "STABLE"
  owner: "sea"
  created: "2026-09-30"
  last_updated: "2026-09-30"
  risk_level: "low"
  visibility: "internal"
  triggers: "LabChart, adicht, ADInstruments, EEG, EMG, LTP, 诱发电位, 电生理, 频段功率, PSD"
  platforms: "claude-code"
  locales: "zh-CN"
  dependencies: "adi-reader, numpy, pandas, scipy, matplotlib"
---

# sgEEG — LabChart .adicht 电生理三步分析管线

## 适用场景

- 手里有 LabChart / PowerLab 导出的 `.adicht` 文件，需要提取和可视化
- EEG / EMG 信号分析：频段功率、PSD、RMS 包络
- 刺激诱发实验：诱发电位叠加平均、LTP/LTD 前后对比
- 需要产出可直接交付的自包含 HTML 报告

## 管线总览（三步，顺序执行）

```
step1_extract.py      .adicht → extracted/*.csv + _metadata.json   (adi-reader)
        ↓
step2_analysis.py     extracted/ → plots/*.png + _analysis_summary.txt
        ↓
step3_html_report.py  plots/ + extracted/_metadata.json → 自包含 HTML 报告
```

脚本存放在 `scripts/`，**每次使用时复制到新的批次目录再改配置**（原始脚本中
`BASE`/`DATA_DIR` 是硬编码绝对路径，这是刻意设计：每个批次目录自包含、可独立复现）。

## Step 1 — 提取（.adicht → CSV）

```bash
pip install adi-reader   # 读 LabChart adicht 格式的唯一依赖
python step1_extract.py
```

核心 API（`import adi`）：

```python
f = adi.read_file(path)
f.n_channels, f.n_records, f.channel_names
for ch_idx, ch in enumerate(f.channels):
    data = ch.get_data(rec_idx)          # rec_idx 从 1 开始！
    fs = float(ch.fs[rec_idx - 1])       # 采样率按 record 存
    units = ch.units[rec_idx - 1]
```

要点：
- 输出命名 `{rat_id}_rec{NN}_ch{N}_{角色}_{file_tag}.csv`，两列：`Time_s` + 通道列
- 通道角色按位置推断：3 通道文件 Ch1=EEG / Ch2=备用 / Ch3=Stim marker；2 通道文件 Ch1=EEG / Ch2=Stim —— **换设备后必须核对**
- `_metadata.json` 记录每个 record/通道的 fs、时长、单位、min/max/mean/std，step3 报告会读它
- 空 record（fs≤0 或数据为空）跳过并打印，不中断

## Step 2 — 分析（8 张标准图 + 定量汇总）

先改脚本头部的 `BASE`（批次目录）和 `RECORDS` 字典（每条记录声明：
file / rat / rec / ch_eeg / ch_stim / desc / color），然后运行。

标准分析内容（图 01–08）：

| 图 | 内容 | 关键函数 |
|---|---|---|
| 01 | 全部 record 拼接时间线总览 + 刺激标记竖线 | `find_stim_events` |
| 02 | Welch PSD 对比（全谱 0–100 Hz + 0–50 Hz 放大，semilogy） | `compute_psd` |
| 03 | 各 record 频段功率占比（分组柱状 + 平均饼图） | `band_power_profile` |
| 04 | 长记录三联图：原始 / RMS 包络 / PSD | `rms_envelope` |
| 05 | 刺激锁定诱发电位叠加平均（-0.5~+2.0s，单试次淡显 + 均值 ± SEM） | 见 `# FIGURE 5` |
| 06 | LTP 分析：各试次 post/pre RMS 比值 + 滑动平均，前半 vs 后半判 ↑LTP/↓LTD/≈无变化 | `compute_snr` |
| 07 | 五频段功率时间 course（分频段带通 + 1s RMS 包络） | `bandpass` + `rms_envelope` |
| 08 | 跨动物对比：PSD 叠加 / 频段占比柱状 / 幅值分布直方 / 刺激数汇总 | — |

标准频段定义（`BANDS` 字典）：

```python
Delta 1-4 Hz | Theta 4-8 Hz | Alpha 8-14 Hz | Beta 14-30 Hz | Gamma 30-100 Hz
```

核心信号处理函数（可直接复用）：

```python
def bandpass(sig, lo, hi, fs, order=4):        # Butterworth 带通 + filtfilt（零相移）
    nyq = fs / 2
    lo, hi = max(lo, 0.5), min(hi, nyq * 0.99)  # 防 Nyquist 越界
    b, a = sp_signal.butter(order, [lo/nyq, hi/nyq], btype='band')
    return sp_signal.filtfilt(b, a, sig)

def rms_envelope(sig, window_ms, fs):           # 均匀滤波 RMS 包络
def find_stim_events(sig, t, n_sigma=5, min_interval_s=0.3)  # marker 通道阈值检测
def compute_psd(sig, fs, nperseg=min(4096, len(sig)))        # Welch
def band_power(sig, lo, hi, fs)                 # PSD 区间梯形积分
def compute_snr(sig, stims, t, pre_win=1.0, post_win=2.0)    # 各试次 post/pre RMS 比
```

输出：`plots/01..08*.png`（150 dpi）+ `_analysis_summary.txt`（每 record 的
时长/刺激数/RMS/Delta%/Beta% + 刺激间隔统计）。

## Step 3 — HTML 报告（自包含）

读取 `plots/` 全部图片 + `_metadata.json` + `_analysis_summary.txt`，
图片 base64 内嵌成**单文件 HTML**（`SGA{项目号}_{批次}_report.html`），无外部依赖，
可直接发邮件/存档。改脚本尾部 `OUT_HTML` 命名即可。

另有 Rmd 变体（`SGA*_report.Rmd` → HTML），需要叙述性结论时用 Rmd；纯图表汇总用 step3。

## 踩坑清单（务必先读）

1. **rec_idx 从 1 开始**（`ch.get_data(1)` 是第一个 record），但 `ch.fs`/`ch.units` 数组是 **0-indexed**，必须 `ch.fs[rec_idx - 1]`
2. **fs 和单位按 record 存**，同一个文件不同 record 采样率可能不同（实战见过 100/200/1000 Hz 混存），逐 record 读取，不要全局假设
3. **marker 通道角色不要猜**：实战中 stim marker 在 Ch3（3 通道文件）也在 Ch2（2 通道文件），step1 提取完先打印 `_metadata.json` 核对通道数与单位（V = marker，mV/uV = 信号）
4. **单位不统一**（uV vs mV 混存）：画 PSD/直方对比前先统一 ×1000，否则曲线差 3 个数量级
5. **短 record（<5s）跳过频段分析**：nperseg 不足会导致 Welch 失真甚至 NaN，脚本已做时长过滤和 NaN 守卫
6. **marker 检测参数**：`n_sigma=5, min_interval_s=0.3` 是防误检/防重复检的实战值；刺激过密（<0.3s 间隔）时调低 `min_interval_s`
7. **filtfilt 前先防 Nyquist 越界**：hi 必须 < fs/2×0.99，否则 scipy 报错
8. **matplotlib 中文**：`font.sans-serif = ['SimHei', 'Microsoft YaHei']` + `axes.unicode_minus = False`，且用 `Agg` 后端（无 GUI 环境）
9. **诱发电位对齐**：片段截取要求 ≥90% 目标长度（`mask.sum() >= target_len*0.9`），防止 record 末尾刺激产生截断 trial 拉偏均值
10. **LABChart 文件名带空格**（如 `LTP6_29 SD.adicht`）：Windows 下没问题，但传 Linux 服务器前建议重命名去空格
11. **EMG 通道**：采样率往往远低于 EEG（实战 100 Hz vs 1000 Hz），跨通道对齐用各自的时间轴，不要用样本索引

## 已验证批次

| 批次 | 物种/实验 | 位置 |
|---|---|---|
| 20260630 LTP6 | SD 大鼠海马 LTP（3 文件 15 records，1000 Hz） | `D:\01SG_FILES\006DEV\Process\SG20260417DEV01_EEG\Process\20260630` |
| C57test | C57 小鼠 EEG/EMG + 分级刺激（轻触/夹尾/针刺） | 同上 `\Process\C57test` |
| SDtest | SD 大鼠 EEG/EMG（2026-05-12） | 同上 `\Process\SDtest` |

单文件简化版（提取+分析一体）见 `C57test\analysis.py`，快速探索时可用。

## 快速上手清单

1. 新建批次目录，拷入 `scripts/` 三个脚本 + `.adicht` 原始文件
2. 改 `step1_extract.py`：`DATA_DIR` + `files` 列表（文件名/rat_id/file_tag）
3. 跑 step1 → 检查 `extracted/_metadata.json` 确认通道角色和采样率
4. 改 `step2_analysis.py`：`BASE` + `RECORDS`（每条记录的通道号和配色）；fs 全局不一致时改 `FS` 或按 record 传入
5. 跑 step2 → 看 8 张图 + summary
6. 改 `step3_html_report.py` 的 `OUT_HTML` → 跑出交付 HTML
