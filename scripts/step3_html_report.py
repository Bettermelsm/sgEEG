"""
Generate self-contained HTML report for LTP6 SD Rat EEG (2026-06-30)
All images embedded as base64, no external dependencies.
"""

import base64
import os
import json
from pathlib import Path
from datetime import datetime

BASE = r"D:\01SG_FILES\006DEV\Process\SG20260417DEV01_EEG\Process\20260630"
PLOT_DIR = os.path.join(BASE, "plots")
EXT_DIR  = os.path.join(BASE, "extracted")
OUT_HTML = os.path.join(BASE, "SGA20260417DEV01_LTP6_report.html")

def img_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def img_tag(fname, alt="", width="100%"):
    path = os.path.join(PLOT_DIR, fname)
    if not os.path.exists(path):
        return f'<p style="color:gray;">[图片未找到: {fname}]</p>'
    b64 = img_b64(path)
    return f'<img src="data:image/png;base64,{b64}" alt="{alt}" style="width:{width};border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.18);margin:12px 0;">'

# Load metadata
meta_path = os.path.join(EXT_DIR, "_metadata.json")
with open(meta_path, encoding="utf-8") as f:
    meta = json.load(f)

# Load summary text
summ_path = os.path.join(PLOT_DIR, "_analysis_summary.txt")
with open(summ_path, encoding="utf-8") as f:
    summary_txt = f.read()

now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

# ── Build section helpers ────────────────────────────────────────────────────
def section(title, anchor, content, level=1):
    tag = f"h{level}"
    return f"""
    <div class="section" id="{anchor}">
      <{tag} class="sec-title lv{level}">{title}</{tag}>
      {content}
    </div>"""

def card(content, cls=""):
    return f'<div class="card {cls}">{content}</div>'

def table_html(headers, rows, caption=""):
    ths = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows
    )
    cap = f"<caption>{caption}</caption>" if caption else ""
    return f"<div class='tbl-wrap'><table>{cap}<thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table></div>"

def callout(kind, text):
    icons = {"info":"ℹ️","warning":"⚠️","danger":"🔴","tip":"💡"}
    return f'<div class="callout callout-{kind}"><span class="callout-icon">{icons.get(kind,"📌")}</span> {text}</div>'

def fig_block(fname, caption, width="100%"):
    return f"""
    <figure>
      {img_tag(fname, caption, width)}
      <figcaption>{caption}</figcaption>
    </figure>"""

# ── Inject all logo (optional) ───────────────────────────────────────────────
logo_path = r"D:\01SG_FILES\002Company_files\Logo\watermark.jpg"
logo_tag = ""
if os.path.exists(logo_path):
    logo_b64 = img_b64(logo_path)
    logo_tag = f'<img src="data:image/jpeg;base64,{logo_b64}" class="logo" alt="Sengene Logo">'

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
:root {
  --primary:   #1a237e;
  --accent:    #3949ab;
  --accent2:   #e65100;
  --bg:        #f5f6fa;
  --card-bg:   #ffffff;
  --text:      #222;
  --muted:     #666;
  --border:    #dde2f0;
  --radius:    10px;
  --shadow:    0 2px 14px rgba(26,35,126,.10);
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.7;
  font-size: 15px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* ── layout ── */
.wrapper { display: flex; min-height: 100vh; }
nav {
  width: 240px; min-width: 220px; max-width: 260px;
  background: var(--primary);
  color: #c5cae9;
  padding: 28px 0 40px;
  position: sticky; top: 0; height: 100vh; overflow-y: auto;
  flex-shrink: 0;
}
nav .nav-title {
  font-size: 13px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: #9fa8da;
  padding: 0 22px 10px; margin-bottom: 6px;
  border-bottom: 1px solid rgba(255,255,255,.1);
}
nav a {
  display: block; padding: 7px 22px; color: #c5cae9;
  font-size: 13.5px; border-left: 3px solid transparent;
  transition: all .2s;
}
nav a:hover, nav a.active {
  background: rgba(255,255,255,.08);
  border-left-color: #7986cb;
  color: #fff; text-decoration: none;
}
nav a.sub { padding-left: 36px; font-size: 12.5px; opacity: .85; }

main {
  flex: 1; padding: 36px 44px 60px;
  max-width: 1100px;
  overflow-x: hidden;
}

/* ── header ── */
header {
  background: linear-gradient(135deg, var(--primary) 0%, #283593 60%, #3949ab 100%);
  color: #fff;
  padding: 36px 44px 30px;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 16px;
}
header .logo { height: 52px; border-radius: 6px; }
.header-text h1 { font-size: 26px; font-weight: 700; letter-spacing: .01em; }
.header-text .subtitle { font-size: 13.5px; opacity: .8; margin-top: 4px; }
.header-meta { font-size: 12.5px; opacity: .75; margin-top: 8px; }

/* ── section ── */
.section { margin-bottom: 44px; }
.sec-title.lv1 {
  font-size: 20px; font-weight: 700; color: var(--primary);
  border-left: 5px solid var(--accent); padding-left: 14px;
  margin: 32px 0 16px;
}
.sec-title.lv2 {
  font-size: 16px; font-weight: 600; color: #37474f;
  margin: 22px 0 10px; padding-left: 4px;
  border-bottom: 1px dashed var(--border); padding-bottom: 4px;
}
.sec-title.lv3 {
  font-size: 14.5px; font-weight: 600; color: var(--accent);
  margin: 16px 0 8px;
}

/* ── card ── */
.card {
  background: var(--card-bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px 26px;
  margin-bottom: 22px;
  border: 1px solid var(--border);
}
.card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; margin-bottom: 22px; }
.metric-card {
  background: var(--card-bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 18px 20px;
  border-top: 4px solid var(--accent);
  text-align: center;
}
.metric-card.orange { border-top-color: var(--accent2); }
.metric-card.green  { border-top-color: #2e7d32; }
.metric-card.teal   { border-top-color: #00695c; }
.metric-val { font-size: 30px; font-weight: 800; color: var(--primary); }
.metric-card.orange .metric-val { color: var(--accent2); }
.metric-card.green  .metric-val { color: #2e7d32; }
.metric-card.teal   .metric-val { color: #00695c; }
.metric-label { font-size: 12px; color: var(--muted); margin-top: 4px; }

/* ── table ── */
.tbl-wrap { overflow-x: auto; margin: 14px 0; border-radius: 8px; box-shadow: var(--shadow); }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; background: var(--card-bg); }
caption { caption-side: top; text-align: left; font-weight: 600; color: var(--muted); font-size: 13px; padding: 8px 12px; }
th { background: var(--primary); color: #fff; padding: 10px 14px; font-weight: 600; text-align: left; white-space: nowrap; }
td { padding: 8px 14px; border-bottom: 1px solid var(--border); }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f0f4ff; }
td.num { font-family: 'Consolas', monospace; text-align: right; }
td.warn { color: #c62828; font-weight: 600; }
td.good { color: #2e7d32; font-weight: 600; }

/* ── figure ── */
figure { margin: 18px 0; }
figure img { display: block; }
figcaption {
  font-size: 12.5px; color: var(--muted);
  text-align: center; margin-top: 6px; font-style: italic;
}

/* ── callout ── */
.callout {
  border-radius: 8px; padding: 12px 18px; margin: 14px 0;
  font-size: 13.5px; display: flex; align-items: flex-start; gap: 10px;
}
.callout-icon { font-size: 18px; flex-shrink: 0; margin-top: 1px; }
.callout-info    { background: #e8eaf6; border-left: 4px solid #3949ab; }
.callout-warning { background: #fff8e1; border-left: 4px solid #f57f17; }
.callout-danger  { background: #fce4ec; border-left: 4px solid #c62828; }
.callout-tip     { background: #e8f5e9; border-left: 4px solid #2e7d32; }

/* ── code ── */
pre {
  background: #263238; color: #cfd8dc;
  border-radius: 8px; padding: 16px 18px;
  font-size: 12.5px; overflow-x: auto; margin: 14px 0;
  font-family: 'Consolas', 'Fira Code', monospace;
}
code { font-family: 'Consolas', 'Fira Code', monospace; font-size: 13px;
  background: #eef0f8; border-radius: 4px; padding: 1px 5px; color: var(--accent2); }

/* ── badge ── */
.badge {
  display: inline-block; font-size: 11.5px; font-weight: 700;
  border-radius: 4px; padding: 2px 8px; margin-left: 6px; vertical-align: middle;
}
.badge-blue   { background:#e8eaf6; color:#3949ab; }
.badge-orange { background:#fff3e0; color:#e65100; }
.badge-red    { background:#fce4ec; color:#c62828; }
.badge-green  { background:#e8f5e9; color:#2e7d32; }

/* ── footer ── */
footer {
  margin-top: 48px; padding: 20px 0;
  border-top: 1px solid var(--border);
  font-size: 12px; color: var(--muted); text-align: center;
}

/* ── responsive ── */
@media (max-width: 768px) {
  nav { display: none; }
  main { padding: 20px 16px 40px; }
  header { padding: 20px 16px; }
}
"""

# ── JS (smooth scroll + active nav) ─────────────────────────────────────────
JS = """
document.addEventListener('DOMContentLoaded', function() {
  const links = document.querySelectorAll('nav a');
  const sections = document.querySelectorAll('.section[id]');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) {
        links.forEach(l => l.classList.remove('active'));
        const active = document.querySelector(`nav a[href="#${e.target.id}"]`);
        if (active) active.classList.add('active');
      }
    });
  }, { threshold: 0.25 });
  sections.forEach(s => observer.observe(s));
  links.forEach(l => l.addEventListener('click', function(e) {
    const href = this.getAttribute('href');
    if (href && href.startsWith('#')) {
      e.preventDefault();
      const target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }));
});
"""

# ── Build HTML sections ──────────────────────────────────────────────────────

# Section 0: metrics
metrics_html = """
<div class="card-grid">
  <div class="metric-card">
    <div class="metric-val">3</div>
    <div class="metric-label">数据文件 (.adicht)</div>
  </div>
  <div class="metric-card">
    <div class="metric-val">13</div>
    <div class="metric-label">记录段 (Records)</div>
  </div>
  <div class="metric-card green">
    <div class="metric-val">38.6<span style="font-size:18px;font-weight:400"> 分钟</span></div>
    <div class="metric-label">总记录时长</div>
  </div>
  <div class="metric-card orange">
    <div class="metric-val">701</div>
    <div class="metric-label">检测到总刺激次数</div>
  </div>
  <div class="metric-card teal">
    <div class="metric-val">1000 <span style="font-size:16px;font-weight:400">Hz</span></div>
    <div class="metric-label">采样率</div>
  </div>
  <div class="metric-card">
    <div class="metric-val">42</div>
    <div class="metric-label">导出 CSV 文件</div>
  </div>
</div>
"""

# Section 1: Background
sec1 = f"""
{metrics_html}
<div class="card">
  <h3 class="sec-title lv3">实验信息</h3>
  {table_html(
    ["项目","内容"],
    [
      ["实验动物","SD大鼠 × 2只 (Rat8, Rat29)"],
      ["动物状态","麻醉 (isoflurane/pentobarbital)"],
      ["实验日期","2026年6月30日"],
      ["采集设备","PowerLab + FE231 Bio Amp + FE180 Stimulus Isolator"],
      ["采样率","1000 Hz（所有通道）"],
      ["信号类型","EEGi（颅内侵入式脑电）"],
      ["实验目的","Long-Term Potentiation/Depression (LTP/LTD) 诱导"],
      ["分析工具","Python 3.12 + adi-reader 0.1.15 + scipy/matplotlib"],
    ]
  )}
</div>
<div class="card">
  <h3 class="sec-title lv3">数据文件</h3>
  {table_html(
    ["文件名","大鼠","通道数","记录段","总时长","主要刺激模式"],
    [
      ["LTP6_8 SD.adicht","Rat8","3","7","814.6 s","TBS (~3.2 Hz 簇发)"],
      ["LTP6_8 SD2.adicht","Rat8-S2","2","2","361.1 s","间隔 2–9 s"],
      ["LTP6_29 SD.adicht","Rat29","3","6","1140.4 s","LFS 1 Hz"],
    ]
  )}
</div>
"""

# Section 2: Overview
sec2 = f"""
{callout("info","下图将三只动物的全部记录段按时间顺序拼接显示。红色竖线为检测到的刺激事件，灰色竖线为 record 分隔符。")}
{fig_block("01_overview_timeline.png", "图1. 所有记录段 EEG 时间线总览（三行分别对应 Rat8、Rat8-S2、Rat29）")}
<div class="card">
  <h3 class="sec-title lv3">各记录段详情</h3>
  {table_html(
    ["记录键","大鼠","Rec#","时长(s)","检测刺激数","EEG RMS","说明"],
    [
      ["r8_rec01","Rat8","1","10.7","0","78.5","⚠️ 信号削顶 (±102 mV)"],
      ["r8_rec02","Rat8","2","6.3","0","58.0","⚠️ 信号削顶"],
      ["r8_rec03","Rat8","3","208.4","0","47.7","⚠️ 信号削顶，可能为基线段"],
      ["r8_rec04","Rat8","4","44.3","4","49.7","刺激起步，量程已调整"],
      ["r8_rec05","Rat8","5","163.3","36","15.7","TBS 探测期"],
      ["r8_rec06","Rat8","6","46.7","12","14.6","TBS 持续"],
      ["r8_rec07","Rat8","7","334.8","24","20.6","TBS 主记录"],
      ["r8s2_rec01","Rat8-S2","1","85.2","8","27.9","低频探测"],
      ["r8s2_rec02","Rat8-S2","2","275.9","100","16.0","✅ 高质量 LTP 诱导"],
      ["r29_rec03","Rat29","3","195.2","65","8.4","1 Hz LFS 开始"],
      ["r29_rec04","Rat29","4","523.8","360","15.3","✅ 主要 LTD 诱导 (1 Hz × 360次)"],
      ["r29_rec05","Rat29","5","75.1","61","10.3","LFS 持续"],
      ["r29_rec06","Rat29","6","341.6","73","8.7","刺激后恢复期"],
    ]
  )}
</div>
{callout("danger","Rat8 Rec1–3 的 EEG 幅度恒定在 ±102 mV（ADC 上限），信号被截断（clipping）。这些记录段应标记为无效数据，不纳入主分析。建议核实实验记录本，确认这三段是否为设备调试段。")}
"""

# Section 3: Stimulus
sec3 = f"""
<div class="card">
  <h3 class="sec-title lv3">Rat8 — Theta-Burst Stimulation (TBS)</h3>
  {table_html(
    ["记录","刺激数","平均间隔 (s)","中位间隔 (s)","解读"],
    [
      ["Rec4","4","0.31","0.31","短暂试探"],
      ["Rec5","36","3.36","0.31","阈值探测，含快速簇"],
      ["Rec6","12","3.05","0.31","簇发持续"],
      ["Rec7","24","7.30","0.31","长间隔主记录"],
    ]
  )}
  {callout("tip","中位间隔 0.31 s（≈3.2 Hz）是 Theta-Burst 的 burst 内频率，而平均间隔更长反映了 burst 之间的停歇间隔。TBS 是诱导皮层 <b>LTP（长时程增益）</b> 最常用的高效方案。")}
</div>
<div class="card">
  <h3 class="sec-title lv3">Rat8-S2 — 间隔变化刺激</h3>
  {table_html(
    ["记录","刺激数","平均间隔 (s)","说明"],
    [
      ["Rec1","8","8.99","低频探测期"],
      ["Rec2","100","2.21","高频重复 LTP 诱导（2s 间隔）"],
    ]
  )}
</div>
<div class="card">
  <h3 class="sec-title lv3">Rat29 — Low-Frequency Stimulation (LFS, 1 Hz)</h3>
  {table_html(
    ["记录","刺激数","平均间隔 (s)","中位间隔 (s)","解读"],
    [
      ["Rec3","65","1.29","1.00","1 Hz LFS 起始"],
      ["Rec4","360","0.99","1.00","主要诱导期（523 s，8.7 分钟）"],
      ["Rec5","61","1.25","1.00","LFS 持续"],
      ["Rec6","73","4.60","1.00","间隔延长，观察恢复"],
    ]
  )}
  {callout("warning","1 Hz 低频刺激（LFS）是诱导突触 <b>LTD（长时程抑制）</b> 的标准方案，而非 LTP。Rat29 Rec4（360次，523秒）可能是在评估 <b>homosynaptic LTD</b>，而非 LTP。请结合实验设计文档确认实验意图。")}
</div>
"""

# Section 4: Signal quality
sec4 = f"""
{fig_block("04_key_records_detail.png", "图4. 关键长记录详细分析（Raw 原始信号 / RMS 包络 / PSD 功率谱，逐行对应 Rat8 Rec3、Rat8 Rec7、Rat29 Rec4、Rat29 Rec6）")}
<div class="card">
  <h3 class="sec-title lv3">信号质量评估</h3>
  {table_html(
    ["动物","信号范围","截断?","量程单位","评估"],
    [
      ["Rat8 Rec1-3","±102 mV（恒定）","是 ⚠️","mV","ADC 上限，数据无效"],
      ["Rat8 Rec4-7","−142 ~ +116 uV","轻微","uV","量程已调整，质量良好"],
      ["Rat8-S2 Rec2","±51 uV","否","uV","✅ 优质"],
      ["Rat29 Rec3-6","±30 ~ ±102 uV","偶发","uV","✅ 总体质量优"],
    ]
  )}
</div>
"""

# Section 5: PSD
sec5 = f"""
{fig_block("02_PSD_comparison.png", "图2. 功率谱密度对比（Welch 法，1-100 Hz 带通滤波后）。左：全频段，右：0-50 Hz 缩放视图")}
{callout("info","麻醉状态下 SD 大鼠 EEG 预期表现：<b>Delta (1–4 Hz) 功率占主导（>50%）</b>，与异氟烷/戊巴比妥麻醉的典型脑电模式一致。Gamma 功率最低符合预期。")}
"""

# Section 6: Band power
sec6 = f"""
{fig_block("03_band_power_profile.png", "图3. 各记录段 EEG 频段功率分布（柱状图）及平均频段能量占比（饼图）")}
{fig_block("07_band_time_course.png", "图7. 关键记录的各频段功率时序（Delta / Theta / Alpha / Beta / Gamma，红色竖线为刺激事件）")}
"""

# Section 7: Evoked potentials
sec7 = f"""
{callout("info","刺激锁定平均（Stimulus-Locked Averaging）：以每次刺激时刻为 t=0，取前 500 ms / 后 2 s 时间窗，将 1-100 Hz 带通滤波后的 EEG 叠加平均。灰色细线为单次试次，彩色粗线为均值，色带为 ±SEM。")}
{fig_block("05_evoked_potentials.png", "图5. 各记录段刺激锁定诱发电位均值。红色虚线为刺激时刻 (t=0)，n 为有效试次数")}
<div class="card">
  <h3 class="sec-title lv3">各记录有效试次数</h3>
  {table_html(
    ["记录","大鼠","刺激数","有效试次","备注"],
    [
      ["Rec5","Rat8","36","~36","TBS 诱导期"],
      ["Rec6","Rat8","12","~12","TBS"],
      ["Rec7","Rat8","24","~24","TBS 主记录"],
      ["Rec2","Rat8-S2","100","~100","最佳 Rat8 试次量"],
      ["Rec3","Rat29","65","~65","1 Hz LFS"],
      ["Rec4","Rat29","360","~360","✅ 最多试次，统计效力最强"],
      ["Rec5","Rat29","61","~61","LFS 持续"],
      ["Rec6","Rat29","73","~73","恢复期观察"],
    ]
  )}
</div>
"""

# Section 8: LTP analysis
sec8 = f"""
{callout("info","LTP 分析：以第一次刺激前的 EEG RMS 为基线，计算每次刺激后 2s 内 RMS 与基线的比值。比值 >1 表示兴奋性增强（LTP 趋势），<1 表示抑制增强（LTD 趋势）。移动平均窗口 = 5 次。")}
{fig_block("06_LTP_analysis.png", "图6. 各记录刺激前后 RMS 比值（Post/Pre）随试次的变化。灰色虚线 = 基线（比值=1）")}
"""

# Section 9: Cross-animal comparison
sec9 = f"""
{fig_block("08_cross_animal_comparison.png", "图8. Rat8 vs Rat29 跨动物对比（PSD / 频段功率分布 / 幅度分布 / 各记录刺激数统计）")}
"""

# Section 10: Conclusion
sec10 = f"""
<div class="card">
  <h3 class="sec-title lv3">主要结论</h3>
  <ol style="line-height:2;padding-left:20px;font-size:14px;">
    <li><b>采样率满足要求：</b>全部文件均以 1000 Hz 采样，覆盖 0–500 Hz 奈奎斯特频率，EEG 常用频段（Delta–Gamma）均可分析。</li>
    <li><b>Rat8 刺激方案（TBS）：</b>簇内间隔 ~0.31 s（3.2 Hz），与 Theta-Burst Stimulation 特征一致，为 LTP 诱导的有效方案。有效记录 Rec5–7（Rat8）及 Rec2（Rat8-S2）。</li>
    <li><b>Rat29 刺激方案（1 Hz LFS）：</b>Rec4 是本次实验数据量最大的记录（360次，8.7分钟），符合标准 LTD 诱导协议。Rec3→4→5→6 构成完整的诱导时程（基线→诱导→早期表达→晚期）。</li>
    <li><b>信号质量：</b>Rat8 Rec1–3 存在 ADC 截断，建议排除。Rat29 所有记录及 Rat8 Rec4–7 信号质量良好。</li>
    <li><b>频谱特征：</b>Delta 频段（1–4 Hz）功率主导，符合麻醉 SD 大鼠 EEG 预期，Gamma 成分最低。</li>
    <li><b>诱发电位：</b>Rat29 Rec4（n=360）提供最高统计效力的诱发电位均值，建议作为主要分析对象。</li>
  </ol>
</div>
<div class="card">
  <h3 class="sec-title lv3">后续建议</h3>
  {table_html(
    ["优先级","建议","目标记录"],
    [
      ["🔴 高","确认 Rat8 Rec1-3 是调试段还是有效数据，排除截断记录","r8_rec01–03"],
      ["🔴 高","提取 Rat29 Rec4 的 fEPSP（场兴奋性突触后电位）峰幅随试次变化，确认 LTD 是否形成","r29_rec04"],
      ["🟡 中","比较 Rat29 Rec3→4→5→6 各阶段基线 EEG 功率，评估 LTD 的表达时程","r29_rec03–06"],
      ["🟡 中","分析 Rat8-S2 Rec2（100次，2s间隔）的诱发电位幅度变化，确认 LTP 成立","r8s2_rec02"],
      ["🟢 低","制作 Spectrogram（短时傅里叶变换）观察频率成分随时间的动态变化","全部主记录"],
      ["🟢 低","将本次 LTP6 数据与 SDtest（5月12–13日）对比，评估实验一致性","跨批次"],
    ]
  )}
</div>
"""

# Section 11: File index
sec11 = f"""
<div class="card">
  <h3 class="sec-title lv3">分析输出文件</h3>
  {table_html(
    ["文件","类型","描述"],
    [
      ["step1_extract.py","Python 脚本","adicht → CSV 数据提取"],
      ["step2_analysis.py","Python 脚本","完整 EEG 分析（8 张图）"],
      ["extracted/ (42 CSV)","数据文件","按动物/记录/通道导出的原始数据"],
      ["plots/01_overview_timeline.png","图像","所有记录段时间线总览"],
      ["plots/02_PSD_comparison.png","图像","功率谱密度对比"],
      ["plots/03_band_power_profile.png","图像","频段功率分布"],
      ["plots/04_key_records_detail.png","图像","关键记录 Raw/RMS/PSD 三联图"],
      ["plots/05_evoked_potentials.png","图像","刺激锁定诱发电位"],
      ["plots/06_LTP_analysis.png","图像","刺激前后 RMS 比值"],
      ["plots/07_band_time_course.png","图像","频段功率时间序列"],
      ["plots/08_cross_animal_comparison.png","图像","跨动物对比"],
      ["SGA20260417DEV01_LTP6_report.html","报告","本 HTML 报告（自含式）"],
    ]
  )}
</div>
<div class="card">
  <h3 class="sec-title lv3">定量摘要（原始输出）</h3>
  <pre>{summary_txt}</pre>
</div>
"""

# ── NAV ──────────────────────────────────────────────────────────────────────
NAV = """
<div class="nav-title">目录</div>
<a href="#s0">实验背景</a>
<a href="#s1">数据总览</a>
<a href="#s2">刺激参数分析</a>
<a href="#s3">信号质量评估</a>
<a href="#s4" class="sub">功率谱密度</a>
<a href="#s5" class="sub">频段功率</a>
<a href="#s6">诱发电位</a>
<a href="#s7">LTP/LTD 分析</a>
<a href="#s8">跨动物对比</a>
<a href="#s9">结论与建议</a>
<a href="#s10">文件索引</a>
"""

# ── Assemble HTML ─────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SGA20260417DEV01 LTP6 EEG 分析报告 — 广州三基因科技</title>
<meta name="description" content="SD大鼠 LTP/LTD EEG 颅内电生理分析报告，2026年6月30日，三基因科技">
<style>{CSS}</style>
</head>
<body>
<div class="wrapper">
  <nav id="sidenav">
    {NAV}
  </nav>
  <div style="flex:1;display:flex;flex-direction:column;min-width:0;">
    <header>
      <div class="header-text">
        <h1>SD大鼠 LTP/LTD 脑电分析报告</h1>
        <div class="subtitle">Long-Term Potentiation / Depression — EEGi 颅内电生理</div>
        <div class="header-meta">
          项目编号：SGA20260417DEV01 &nbsp;|&nbsp;
          实验日期：2026-06-30 &nbsp;|&nbsp;
          报告生成：{now_str} &nbsp;|&nbsp;
          广州三基因科技有限公司
        </div>
      </div>
      {logo_tag}
    </header>
    <main>
      <p style="color:#b71c1c;font-size:13px;margin-bottom:6px;">
        如您对此实验报告有异议，请务必于 <b>30 个工作日</b>内联系项目经理或发送邮件至
        <a href="mailto:info@sengene.top">info@sengene.top</a>。
      </p>

      {section("实验背景与设计", "s0", sec1)}
      {section("数据总览与记录段详情", "s1", sec2)}
      {section("刺激参数分析", "s2", sec3)}
      {section("信号质量评估", "s3", sec4)}
      {section("功率谱密度分析 (PSD)", "s4", sec5, level=2)}
      {section("EEG 频段功率分析", "s5", sec6, level=2)}
      {section("诱发电位分析 (Evoked Potential)", "s6", sec7)}
      {section("LTP / LTD 效应分析", "s7", sec8)}
      {section("跨动物比较 (Rat8 vs Rat29)", "s8", sec9)}
      {section("结论与后续建议", "s9", sec10)}
      {section("数据文件索引", "s10", sec11)}

      <footer>
        <p>广州三基因科技有限公司 &nbsp;|&nbsp; 项目编号 SGA20260417DEV01 &nbsp;|&nbsp;
        生成时间 {now_str} &nbsp;|&nbsp; 本报告由 Antigravity (AGY) 自动生成</p>
        <p style="margin-top:4px;opacity:.7;">
          Python 3.12 · adi-reader 0.1.15 · scipy {'{scipy_ver}'} · matplotlib {'{mpl_ver}'}
        </p>
      </footer>
    </main>
  </div>
</div>
<script>{JS}</script>
</body>
</html>"""

# fill version placeholders
try:
    import scipy, matplotlib
    html = html.replace("{scipy_ver}", scipy.__version__).replace("{mpl_ver}", matplotlib.__version__)
except:
    html = html.replace("{scipy_ver}", "?").replace("{mpl_ver}", "?")

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(OUT_HTML) / 1024
print(f"HTML report generated: {OUT_HTML}")
print(f"File size: {size_kb:.0f} KB ({size_kb/1024:.1f} MB)")
print("Done!")
