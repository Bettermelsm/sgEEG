"""
Step 2b: Advanced EEG Analysis - LTP6 SD Rat (SCI-grade extensions)
Date: 2026-10-05
Requires: step1_extract.py outputs in extracted/ (same batch dir as step2_analysis.py)

New dimensions over step2:
  1. Stimulus artifact removal (±5 ms window interpolation around each stim)
  2. Trial-level QC (predefined rejection: |amp| > 5x baseline std, or flat trial)
  3. fPSP slope quantification (10-90% rising-phase linear fit) - LTP gold standard
  4. Morlet wavelet time-frequency (pure scipy/numpy, no pywt) + stim-locked ERSP
  5. Coefficient-of-variation (CV) analysis - synaptic release probability proxy
  6. Paired statistics: baseline vs post-window, effect size (Cohen's d)

Output: plots_adv/*.png + _advanced_summary.txt
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import signal as sp_signal
import os, json, warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

BASE = r"D:\01SG_FILES\006DEV\Process\SG20260417DEV01_EEG\Process\20260630"
EXT_DIR = os.path.join(BASE, "extracted")
OUT_DIR = os.path.join(BASE, "plots_adv")
os.makedirs(OUT_DIR, exist_ok=True)

FS = 1000

BANDS = {
    'Delta':  (1,  4),
    'Theta':  (4,  8),
    'Alpha':  (8,  14),
    'Beta':   (14, 30),
    'Gamma':  (30, 100),
}

# ============================================================
# CORE HELPERS (shared with step2, self-contained copy)
# ============================================================

def load_csv(csv_name):
    path = os.path.join(EXT_DIR, csv_name)
    if not os.path.exists(path):
        return None, None
    df = pd.read_csv(path)
    return df.iloc[:, 0].values, df.iloc[:, 1].values

def bandpass(sig, lo, hi, fs=FS, order=4):
    nyq = fs / 2
    lo, hi = max(lo, 0.5), min(hi, nyq * 0.99)
    b, a = sp_signal.butter(order, [lo / nyq, hi / nyq], btype='band')
    return sp_signal.filtfilt(b, a, sig)

def find_stim_events(sig, t, n_sigma=5, min_interval_s=0.3):
    sig_abs = np.abs(sig - np.mean(sig))
    thresh = n_sigma * np.std(sig_abs)
    above = np.where(sig_abs > thresh)[0]
    if len(above) == 0:
        return np.array([])
    events = [above[0]]
    for idx in above[1:]:
        if t[idx] - t[events[-1]] > min_interval_s:
            events.append(idx)
    return t[np.array(events)]

def remove_stim_artifact(sig, t, stims, half_win_s=0.005):
    """Linear interpolation across ±half_win around each stim onset."""
    sig_clean = sig.copy()
    hw = int(half_win_s * FS)
    for st in stims:
        i0 = np.searchsorted(t, st)
        a, b = i0 - hw, i0 + hw
        a, b = max(a, 0), min(b, len(sig) - 1)
        if b <= a + 1:
            continue
        sig_clean[a:b] = np.interp(t[a:b], [t[a], t[b]], [sig[a], sig[b]])
    return sig_clean

def morlet_cwt(sig, freqs, fs=FS, n_cycles=7):
    """Morlet CWT via FFT convolution (pure numpy). Returns [n_freqs, n_samples] complex."""
    sig = sig - np.mean(sig)
    n = len(sig)
    out = np.zeros((len(freqs), n), dtype=complex)
    # pad enough for linear convolution with the longest wavelet (~4s at min freq)
    n_fft = int(2 ** np.ceil(np.log2(n + int(8 * n_cycles / (2 * np.pi * freqs.min()) * fs))))
    sig_fft = np.fft.fft(sig, n_fft)
    for i, f in enumerate(freqs):
        sigma = n_cycles / (2 * np.pi * f)
        t_w = np.arange(-3.5 * sigma, 3.5 * sigma + 1 / fs, 1 / fs)
        w = np.exp(2j * np.pi * f * t_w) * np.exp(-t_w ** 2 / (2 * sigma ** 2))
        w /= np.sqrt(sigma * np.sqrt(np.pi))       # unit energy
        w_fft = np.fft.fft(w, n_fft)               # complex wavelet -> full complex FFT
        conv = np.fft.ifft(sig_fft * w_fft)[: n + len(w) - 1]   # linear part (no wraparound since n_fft padded)
        seg = conv[len(w) // 2: len(w) // 2 + n]
        out[i, :len(seg)] = seg
    return out

def fpsp_slope(avg, t, st_search=(0.002, 0.020), rise=(0.1, 0.9)):
    """
    10-90% rising-phase linear fit on averaged evoked response.
    Returns (slope_uV_per_ms, r2, (t10, t90)) or None if no valid response.
    avg: baseline-subtracted, artifact-free averaged EP (V); t: seconds.
    """
    i1, i2 = int(st_search[0] * FS), int(st_search[1] * FS)
    if i2 >= len(avg):
        return None
    seg = avg[i1:i2]
    if np.all(np.diff(seg) <= 0) or np.max(np.abs(seg)) < 1e-13:
        return None
    peak_i = np.argmax(np.abs(seg))
    peak_t, peak_v = t[i1 + peak_i], seg[peak_i]
    v10, v90 = peak_v * rise[0], peak_v * rise[1]
    if peak_v > 0:
        i_lo = np.argmax(seg[:peak_i + 1] >= v10) if np.any(seg[:peak_i + 1] >= v10) else None
        i_hi = peak_i - np.argmax(seg[:peak_i + 1][::-1] >= v90) if np.any(seg[:peak_i + 1] >= v90) else None
    else:
        i_lo = np.argmax(seg[:peak_i + 1] <= v10) if np.any(seg[:peak_i + 1] <= v10) else None
        i_hi = peak_i - np.argmax(seg[:peak_i + 1][::-1] <= v90) if np.any(seg[:peak_i + 1] <= v90) else None
    if i_lo is None or i_hi is None or i_hi <= i_lo:
        return None
    ts, vs = t[i1 + i_lo: i1 + i_hi + 1], seg[i_lo: i_hi + 1]
    if len(ts) < 3:
        return None
    p = np.polyfit(ts * 1000, vs * 1e6, 1)          # uV per ms
    pred = np.polyval(p, ts * 1000)
    ss_res = np.sum((vs * 1e6 - pred) ** 2)
    ss_tot = np.sum((vs * 1e6 - np.mean(vs * 1e6)) ** 2) + 1e-20
    return p[0], 1 - ss_res / ss_tot, (ts[0], ts[-1])

def cohens_d(x, y):
    nx, ny = len(x), len(y)
    s = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / (nx + ny - 2))
    return (np.mean(x) - np.mean(y)) / (s + 1e-20)

# ============================================================
# RECORD CONFIG (mirrors step2 RECORDS, same csv naming)
# ============================================================

RAT_MAP = {'LTP6_8_SD': 'rat8', 'LTP6_8_SD2': 'rat8_s2', 'LTP6_29_SD': 'rat29'}

RECORDS = {
    'r8_rec03':  dict(file='LTP6_8_SD',  rat='Rat8',    rec=3, ch_eeg=1, ch_stim=3, color='#1565C0'),
    'r8_rec05':  dict(file='LTP6_8_SD',  rat='Rat8',    rec=5, ch_eeg=1, ch_stim=3, color='#1A237E'),
    'r8_rec07':  dict(file='LTP6_8_SD',  rat='Rat8',    rec=7, ch_eeg=1, ch_stim=3, color='#3949AB'),
    'r8s2_rec02':dict(file='LTP6_8_SD2', rat='Rat8_S2', rec=2, ch_eeg=1, ch_stim=2, color='#00838F'),
    'r29_rec03': dict(file='LTP6_29_SD', rat='Rat29',   rec=3, ch_eeg=1, ch_stim=3, color='#E65100'),
    'r29_rec04': dict(file='LTP6_29_SD', rat='Rat29',   rec=4, ch_eeg=1, ch_stim=3, color='#BF360C'),
    'r29_rec06': dict(file='LTP6_29_SD', rat='Rat29',   rec=6, ch_eeg=1, ch_stim=3, color='#FF6E40'),
}

def csv_name(file_tag, rec_idx, ch_idx):
    role_map = {1: 'EEG', 2: 'Stim', 3: 'Stim'} if file_tag not in ['LTP6_8_SD', 'LTP6_29_SD'] \
        else {1: 'EEG', 2: 'Ch2', 3: 'Stim'}
    return f"{RAT_MAP[file_tag]}_rec{rec_idx:02d}_ch{ch_idx}_{role_map[ch_idx]}_{file_tag}.csv"

# ============================================================
# LOAD + PREPROCESS ALL RECORDS
# ============================================================

PRE_WIN, POST_WIN = 0.5, 2.0
summary_lines = ["LTP6 SD Rat - Advanced Analysis Summary (step2b)", f"Date: 2026-10-05", ""]

for key, rec in RECORDS.items():
    t, sig = load_csv(csv_name(rec['file'], rec['rec'], rec['ch_eeg']))
    ts, ss = load_csv(csv_name(rec['file'], rec['rec'], rec['ch_stim']))
    if t is None or ts is None:
        rec['loaded'] = False
        print(f"[SKIP] {key}: csv missing")
        continue
    rec.update(t=t, sig=sig, loaded=True)
    rec['stims'] = find_stim_events(ss, ts, n_sigma=5, min_interval_s=0.3)
    # artifact removal on 1-100 Hz filtered signal
    sig_bp = bandpass(sig, 1, 100)
    rec['sig_clean'] = remove_stim_artifact(sig_bp, t, rec['stims'])
    print(f"{key}: {t[-1]:.0f}s, {len(rec['stims'])} stims")

loaded = {k: v for k, v in RECORDS.items() if v.get('loaded')}

# ============================================================
# FIG A1: Trial QC + artifact-removed evoked averages per record
# ============================================================

print("\nFig A1: QC + cleaned evoked potentials...")

# QC: collect per-trial peak amplitude; reject |peak| > 5x baseline std
qc_stats = {}
for key, rec in loaded.items():
    t, sig = rec['t'], rec['sig_clean']
    stims = rec['stims']
    bl_mask = t < (stims[0] - 1) if len(stims) else t < 5
    bl_std = np.std(sig[bl_mask]) if bl_mask.any() else np.std(sig)
    trials, kept = [], []
    for st in stims:
        m = (t >= st - PRE_WIN) & (t <= st + POST_WIN)
        target = int((PRE_WIN + POST_WIN) * FS)
        if m.sum() < target:
            continue
        seg = sig[m][:target]
        pre_i = int(PRE_WIN * FS)
        peak = np.max(np.abs(seg[pre_i:])) if len(seg) > pre_i else np.max(np.abs(seg))
        trials.append((st, seg, peak))
    for st, seg, peak in trials:
        if peak <= 5 * bl_std and np.std(seg) > 0.01 * bl_std:   # not huge artifact, not flat
            kept.append((st, seg))
    qc_stats[key] = dict(n_total=len(trials), n_kept=len(kept), bl_std=bl_std)
    rec['trials'] = kept

n = len(loaded)
ncol = 4
nrow = (n + ncol - 1) // ncol
fig, axes = plt.subplots(nrow, ncol, figsize=(20, 4 * nrow))
axes_f = np.array(axes).flatten()

for i, (key, rec) in enumerate(loaded.items()):
    ax = axes_f[i]
    t_ep = np.linspace(-PRE_WIN, POST_WIN, int((PRE_WIN + POST_WIN) * FS))
    segs = np.array([s for _, s in rec['trials']])
    if len(segs) < 2:
        ax.text(0.5, 0.5, 'insufficient', transform=ax.transAxes, ha='center'); continue
    avg = np.mean(segs, axis=0)
    sem = np.std(segs, 0) / np.sqrt(len(segs))
    for s in segs[:20]:
        ax.plot(t_ep, s, lw=0.1, color=rec['color'], alpha=0.15)
    ax.plot(t_ep, avg, lw=2, color=rec['color'], label=f'mean (n={len(segs)}/{qc_stats[key]["n_total"]})')
    ax.fill_between(t_ep, avg - sem, avg + sem, alpha=0.2, color=rec['color'])
    ax.axvline(0, color='red', ls='--', lw=1.5)
    q = qc_stats[key]
    ax.set_title(f"{rec['rat']} R{rec['rec']} | kept {q['n_kept']}/{q['n_total']}\n"
                 f"(rej: >5σ or flat)", fontsize=9)
    ax.set_xlabel('Time (s)'); ax.set_ylabel('uV (1-100Hz, artifact-removed)')
    ax.legend(fontsize=7); ax.grid(alpha=0.2)

for j in range(len(loaded), len(axes_f)):
    axes_f[j].set_visible(False)
fig.suptitle('A1: Artifact-Removed, QC-Filtered Stimulus-Locked Averages', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'A1_qc_evoked_averages.png'), bbox_inches='tight')
plt.close()

# ============================================================
# FIG A2: fPSP slope per trial (LTP gold standard)
# ============================================================

print("Fig A2: fPSP slope analysis...")
valid = {k: r for k, r in loaded.items() if len(r.get('trials', [])) >= 5}
fig, axes = plt.subplots(2, 4, figsize=(22, 10))
axes_f = np.array(axes).flatten()
slope_table = []

for i, (key, rec) in enumerate(valid.items()):
    ax = axes_f[i]
    t_ep = np.linspace(-PRE_WIN, POST_WIN, int((PRE_WIN + POST_WIN) * FS))
    slopes, t_stims = [], []
    for st, seg in rec['trials']:
        r = fpsp_slope(seg, t_ep)
        if r is not None:
            slopes.append(r[0]); t_stims.append(st)
    if len(slopes) < 5:
        ax.text(0.5, 0.5, 'no valid fPSP', transform=ax.transAxes, ha='center')
        ax.set_title(f"{rec['rat']} R{rec['rec']}", fontsize=9)
        continue
    slopes = np.array(slopes)
    # orient sign to dominant direction, then MAD-based outlier rejection
    slopes = slopes * np.sign(np.median(slopes) or 1)
    med = np.median(slopes)
    mad = np.median(np.abs(slopes - med)) + 1e-12
    keep = np.abs(slopes - med) < 3 * mad * 1.4826
    if keep.sum() < 5:
        keep = np.ones_like(keep, dtype=bool)
    n_rej = int((~keep).sum())
    slopes, t_stims = slopes[keep], np.array(t_stims)[keep]
    base = np.median(slopes[:max(3, len(slopes) // 5)])
    norm = slopes / (base if base != 0 else 1)
    ax.plot(norm, 'o-', ms=3, lw=1, color=rec['color'])
    ax.axhline(1.0, color='gray', ls='--')
    # split-half comparison
    half = len(norm) // 2
    d = cohens_d(norm[half:], norm[:half])
    trend = '↑LTP' if np.mean(norm[half:]) > 1.1 else ('↓LTD' if np.mean(norm[half:]) < 0.9 else '≈')
    ax.set_title(f"{rec['rat']} R{rec['rec']} | {trend} d={d:.2f} (rej {n_rej})\n"
                 f"slope {np.median(slopes):.1f} [MAD-robust] uV/ms", fontsize=9)
    slope_table.append((key, rec['rat'], rec['rec'], len(slopes), np.median(slopes), np.std(slopes),
                        np.mean(norm[:half]), np.mean(norm[half:]), d, trend))
    ax.set_xlabel('Trial #'); ax.set_ylabel('Slope (norm. to baseline median)')
    ax.grid(alpha=0.25)

for j in range(len(valid), len(axes_f)):
    axes_f[j].set_visible(False)
fig.suptitle('A2: fPSP Slope (10-90% rising fit) Per Trial - LTP Gold Standard', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'A2_fpsp_slope.png'), bbox_inches='tight')
plt.close()

summary_lines.append("== A2 fPSP slope ==")
summary_lines.append(f"{'key':<12}{'rat':<8}{'R':<4}{'n':<5}{'slope uV/ms':<16}{'first-half':<12}{'second-half':<13}{'d':<7}{'trend'}")
for row in slope_table:
    summary_lines.append(f"{row[0]:<12}{row[1]:<8}{row[2]:<4}{row[3]:<5}"
                         f"{row[4]:.2f} +/- {row[5]:.2f}       {row[6]:<12.2f}{row[7]:<13.2f}{row[8]:<7.2f}{row[9]}")

# ============================================================
# FIG A3: Morlet wavelet TF + stim-locked ERSP (major records)
# ============================================================

print("Fig A3: wavelet TF + ERSP...")
freqs = np.logspace(np.log10(2), np.log10(100), 40)
major = ['r8_rec07', 'r8s2_rec02', 'r29_rec04', 'r29_rec06']

fig, axes = plt.subplots(2, len(major), figsize=(6 * len(major), 9))
for col, key in enumerate(major):
    rec = loaded[key]
    t, sig = rec['t'], rec['sig_clean']
    c = morlet_cwt(sig, freqs)
    power = np.abs(c) ** 2

    # 3a: full TF plot
    ax = axes[0, col]
    im = ax.pcolormesh(t, freqs, 10 * np.log10(power + 1e-20), shading='auto', cmap='viridis')
    for st in rec['stims'][:60]:
        ax.axvline(st, color='red', lw=0.4, alpha=0.5)
    ax.set_yscale('log')
    ax.set_title(f"{rec['rat']} R{rec['rec']} - Wavelet TF", fontsize=10)
    ax.set_xlabel('Time (s)'); ax.set_ylabel('Freq (Hz)')
    plt.colorbar(im, ax=ax, label='dB')

    # 3b: ERSP - stim-locked mean power change vs 1s pre-stim baseline
    ax = axes[1, col]
    stims = rec['stims']
    win_t = np.arange(-1.0, 2.0, 1 / FS)
    ersp = np.zeros((len(freqs), len(win_t)))
    used = 0
    for st in stims:
        i0 = np.searchsorted(t, st + win_t[0])
        i1 = i0 + len(win_t)
        if i0 < 0 or i1 > len(t):
            continue
        seg_p = 10 * np.log10(power[:, i0:i1] + 1e-20)
        ersp += seg_p; used += 1
    if used:
        ersp /= used
        base_m = ersp[:, win_t < 0].mean(axis=1, keepdims=True)
        im2 = ax.pcolormesh(win_t, freqs, ersp - base_m, shading='auto', cmap='RdBu_r',
                            vmin=-6, vmax=6)
        ax.axvline(0, color='black', lw=1.5)
        ax.set_yscale('log')
        ax.set_title(f"ERSP (n={used} stims, vs pre-stim)", fontsize=10)
        ax.set_xlabel('Time from stim (s)'); ax.set_ylabel('Freq (Hz)')
        plt.colorbar(im2, ax=ax, label='dB change')

fig.suptitle('A3: Morlet Wavelet Time-Frequency + Stimulus-Locked ERSP', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'A3_wavelet_ersp.png'), bbox_inches='tight')
plt.close()

# ============================================================
# FIG A4: CV analysis (synaptic release probability proxy)
# ============================================================

print("Fig A4: CV analysis...")
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

ax = axes[0]
for key, rec in valid.items():
    t_ep = np.linspace(-PRE_WIN, POST_WIN, int((PRE_WIN + POST_WIN) * FS))
    amps = [np.max(np.abs(seg[int(PRE_WIN * FS):])) for _, seg in rec['trials']]
    if len(amps) < 8:
        continue
    amps = np.array(amps)
    # sliding window CV
    w = max(5, len(amps) // 5)
    cv_t, cv_v, amp_v = [], [], []
    for i in range(0, len(amps) - w + 1, w):
        seg = amps[i:i + w]
        cv_t.append(i + w / 2); cv_v.append(np.std(seg, ddof=1) / (np.mean(seg) + 1e-20))
        amp_v.append(np.mean(seg))
    ax.plot(cv_t, cv_v, 'o-', ms=4, lw=1, color=rec['color'], label=f"{rec['rat']} R{rec['rec']}")
ax.set_xlabel('Trial # (window center)')
ax.set_ylabel('CV of EP amplitude (sliding window)')
ax.set_title('CV Time Course - release probability proxy')
ax.legend(fontsize=8); ax.grid(alpha=0.25)

ax = axes[1]
for key, rec in valid.items():
    t_ep = np.linspace(-PRE_WIN, POST_WIN, int((PRE_WIN + POST_WIN) * FS))
    amps = np.array([np.max(np.abs(seg[int(PRE_WIN * FS):])) for _, seg in rec['trials']])
    if len(amps) < 8:
        continue
    m, s = amps.mean(), amps.std(ddof=1)
    cv = s / (m + 1e-20)
    ax.scatter(1 / cv ** 2, m, s=60, color=rec['color'], alpha=0.8)
    ax.annotate(f"{rec['rat']} R{rec['rec']}", (1 / cv ** 2, m), fontsize=7,
                xytext=(4, 4), textcoords='offset points')
ax.set_xlabel('CV$^{-2}$ (∝ release sites × P)')
ax.set_ylabel('Mean EP amplitude')
ax.set_title('CV$^{-2}$ vs Amplitude - synaptic locus inference')
ax.grid(alpha=0.25)

fig.suptitle('A4: Coefficient of Variation Analysis', fontweight='bold')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'A4_cv_analysis.png'), bbox_inches='tight')
plt.close()

# ============================================================
# FIG A5: Band power pre/post with paired stats (effect size)
# ============================================================

print("Fig A5: band power pre/post paired stats...")
fig, ax = plt.subplots(figsize=(12, 6))
x, labels = [], []
w = 0.8 / len(BANDS)
for bi, (bname, (lo, hi)) in enumerate(BANDS.items()):
    first_half, second_half = [], []
    for key, rec in valid.items():
        t, sig = rec['t'], rec['sig_clean']
        mid = t[len(t) // 2]
        f, psd = sp_signal.welch(sig[t < mid], FS, nperseg=min(4096, (t < mid).sum()))
        mask = (f >= lo) & (f <= hi)
        p1 = np.trapezoid(psd[mask], f[mask])
        f, psd = sp_signal.welch(sig[t >= mid], FS, nperseg=min(4096, (t >= mid).sum()))
        p2 = np.trapezoid(psd[mask], f[mask])
        first_half.append(p1); second_half.append(p2)
    d = cohens_d(np.array(second_half), np.array(first_half))
    x.append(bi)
    ax.bar(bi - w / 2, np.mean(first_half), w * 0.9, color='gray', alpha=0.7)
    ax.bar(bi + w / 2, np.mean(second_half), w * 0.9, color='#1565C0', alpha=0.85)
    ax.text(bi, max(np.mean(first_half), np.mean(second_half)), f"d={d:.2f}",
            ha='center', va='bottom', fontsize=9, fontweight='bold')
labels = list(BANDS.keys())
ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels)
ax.legend(['First half (≈baseline)', 'Second half'], fontsize=9)
ax.set_ylabel('Band power (PSD integral)')
ax.set_title(f'A5: Band Power First vs Second Half Across Records (n={len(valid)}, Cohen\'s d)', fontweight='bold')
ax.grid(alpha=0.2, axis='y')
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, 'A5_band_prepost_stats.png'), bbox_inches='tight')
plt.close()

summary_lines += ["", "== A5 band power first vs second half (per-record Welch) ==",
                  f"Records used: {len(valid)} | effect size = Cohen's d (second vs first half)"]

# ============================================================
# SAVE SUMMARY
# ============================================================

summary_lines += ["", "Output figures:",
    "  A1_qc_evoked_averages.png   - artifact-removed QC-filtered EP averages",
    "  A2_fpsp_slope.png           - fPSP slope per trial, split-half Cohen's d",
    "  A3_wavelet_ersp.png         - Morlet TF + stim-locked ERSP",
    "  A4_cv_analysis.png          - CV time course + CV^-2 vs amplitude",
    "  A5_band_prepost_stats.png   - band power pre/post with effect sizes"]

with open(os.path.join(OUT_DIR, "_advanced_summary.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(summary_lines))

print("\n" + "\n".join(summary_lines))
print(f"\n✓ Advanced analysis complete → {OUT_DIR}")
