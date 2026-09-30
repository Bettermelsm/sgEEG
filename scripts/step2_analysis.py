"""
Step 2: Full EEG Analysis - LTP6 SD Rat (2026-06-30)
Files: LTP6_8 SD.adicht (rat8), LTP6_8 SD2.adicht (rat8_s2), LTP6_29 SD.adicht (rat29)
Sampling rate: 1000 Hz (all files)
Experiment: Long-Term Potentiation (LTP) via brain stimulation

Analysis includes:
  - Raw signal overview for all records
  - Stimulus detection from marker channels
  - EEG frequency band decomposition (Delta/Theta/Alpha/Beta/Gamma)
  - Power spectral density (Welch)
  - Evoked potential averaging (peri-stimulus)
  - LTP: pre/post stimulation amplitude comparison
  - Cross-rat comparison
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import pandas as pd
import numpy as np
from scipy import signal as sp_signal
from scipy.ndimage import uniform_filter1d
import os
import json
import warnings
warnings.filterwarnings('ignore')

# Chinese font support
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

BASE = r"D:\01SG_FILES\006DEV\Process\SG20260417DEV01_EEG\Process\20260630"
EXT_DIR = os.path.join(BASE, "extracted")
OUT_DIR = os.path.join(BASE, "plots")
os.makedirs(OUT_DIR, exist_ok=True)

FS = 1000   # 1000 Hz

# ============================================================
# EEG FREQUENCY BANDS
# ============================================================
BANDS = {
    'Delta (1-4 Hz)':  (1,  4,  '#1565C0'),
    'Theta (4-8 Hz)':  (4,  8,  '#2E7D32'),
    'Alpha (8-14 Hz)': (8,  14, '#F57F17'),
    'Beta (14-30 Hz)': (14, 30, '#B71C1C'),
    'Gamma (30-100 Hz)':(30,100, '#6A1B9A'),
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_csv(csv_name):
    """Load a CSV file from the extracted folder."""
    path = os.path.join(EXT_DIR, csv_name)
    if not os.path.exists(path):
        return None, None, None
    df = pd.read_csv(path)
    t = df.iloc[:, 0].values
    sig = df.iloc[:, 1].values
    col = df.columns[1]
    return t, sig, col

def bandpass(sig, lo, hi, fs=FS, order=4):
    nyq = fs / 2
    lo = max(lo, 0.5)
    hi = min(hi, nyq * 0.99)
    b, a = sp_signal.butter(order, [lo / nyq, hi / nyq], btype='band')
    return sp_signal.filtfilt(b, a, sig)

def rms_envelope(sig, window_ms=200, fs=FS):
    w = max(1, int(window_ms / 1000 * fs))
    return np.sqrt(uniform_filter1d(sig ** 2, w, mode='nearest'))

def find_stim_events(sig, t, n_sigma=5, min_interval_s=0.3):
    """Detect stimulus pulses from marker channel."""
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

def compute_psd(sig, fs=FS, nperseg=None):
    if nperseg is None:
        nperseg = min(4096, len(sig))
    f, psd = sp_signal.welch(sig, fs=fs, nperseg=nperseg)
    return f, psd

def band_power(sig, lo, hi, fs=FS):
    f, psd = compute_psd(sig, fs)
    mask = (f >= lo) & (f <= hi)
    return np.trapz(psd[mask], f[mask])

def compute_snr(sig, stims, t, pre_win=1.0, post_win=2.0):
    """Compute post/pre stimulus RMS ratio for each trial."""
    bl_mask = t < (stims[0] - 1) if len(stims) > 0 else t < 5
    bl_rms = np.sqrt(np.mean(sig[bl_mask] ** 2)) if bl_mask.any() else 1.0
    ratios = []
    for st in stims:
        post = (t >= st) & (t < st + post_win)
        if post.any():
            ratios.append(np.sqrt(np.mean(sig[post] ** 2)) / max(bl_rms, 1e-10))
    return np.array(ratios), bl_rms

# ============================================================
# DEFINE ALL RECORDS TO ANALYZE
# ============================================================
# Format: key -> {file_tag, rat_id, rec, ch_eeg, ch_stim, desc, color}

RECORDS = {
    # Rat8 - LTP6_8 SD.adicht (7 records, Ch3 is stim marker V)
    'r8_rec01': dict(file='LTP6_8_SD', rat='Rat8', rec=1, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec1 (10.8s, init)', color='#1976D2'),
    'r8_rec02': dict(file='LTP6_8_SD', rat='Rat8', rec=2, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec2 (6.3s)', color='#1565C0'),
    'r8_rec03': dict(file='LTP6_8_SD', rat='Rat8', rec=3, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec3 (208s, baseline+stim)', color='#0D47A1'),
    'r8_rec04': dict(file='LTP6_8_SD', rat='Rat8', rec=4, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec4 (44.3s)', color='#0D47A1'),
    'r8_rec05': dict(file='LTP6_8_SD', rat='Rat8', rec=5, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec5 (163s, long)', color='#1A237E'),
    'r8_rec06': dict(file='LTP6_8_SD', rat='Rat8', rec=6, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec6 (46.7s)', color='#283593'),
    'r8_rec07': dict(file='LTP6_8_SD', rat='Rat8', rec=7, ch_eeg=1, ch_stim=3,
                     desc='Rat8 Rec7 (334.8s, main)', color='#3949AB'),

    # Rat8 session 2 - LTP6_8 SD2.adicht (2 records, Ch2 is stim marker)
    'r8s2_rec01': dict(file='LTP6_8_SD2', rat='Rat8_S2', rec=1, ch_eeg=1, ch_stim=2,
                       desc='Rat8-S2 Rec1 (85s)', color='#00838F'),
    'r8s2_rec02': dict(file='LTP6_8_SD2', rat='Rat8_S2', rec=2, ch_eeg=1, ch_stim=2,
                       desc='Rat8-S2 Rec2 (275s, main)', color='#006064'),

    # Rat29 - LTP6_29 SD.adicht (6 records, Ch3 is stim marker V)
    'r29_rec03': dict(file='LTP6_29_SD', rat='Rat29', rec=3, ch_eeg=1, ch_stim=3,
                      desc='Rat29 Rec3 (195s)', color='#E65100'),
    'r29_rec04': dict(file='LTP6_29_SD', rat='Rat29', rec=4, ch_eeg=1, ch_stim=3,
                      desc='Rat29 Rec4 (523s, main)', color='#BF360C'),
    'r29_rec05': dict(file='LTP6_29_SD', rat='Rat29', rec=5, ch_eeg=1, ch_stim=3,
                      desc='Rat29 Rec5 (75s)', color='#DD2C00'),
    'r29_rec06': dict(file='LTP6_29_SD', rat='Rat29', rec=6, ch_eeg=1, ch_stim=3,
                      desc='Rat29 Rec6 (341s, post)', color='#FF6E40'),
}

def csv_name(file_tag, rec_idx, ch_idx):
    rat_map = {'LTP6_8_SD': 'rat8', 'LTP6_8_SD2': 'rat8_s2', 'LTP6_29_SD': 'rat29'}
    role_map_3ch = {1: 'EEG', 2: 'Ch2', 3: 'Stim'}
    role_map_2ch = {1: 'EEG', 2: 'Stim'}
    n_chs = 3 if file_tag in ['LTP6_8_SD', 'LTP6_29_SD'] else 2
    role_map = role_map_3ch if n_chs == 3 else role_map_2ch
    role = role_map.get(ch_idx, f'ch{ch_idx}')
    rat = rat_map[file_tag]
    return f"{rat}_rec{rec_idx:02d}_ch{ch_idx}_{role}_{file_tag}.csv"

# Pre-load all signals and stims
print("Loading signals and detecting stimuli...")
for key, rec in RECORDS.items():
    t_eeg, sig_eeg, _ = load_csv(csv_name(rec['file'], rec['rec'], rec['ch_eeg']))
    t_stim, sig_stim, _ = load_csv(csv_name(rec['file'], rec['rec'], rec['ch_stim']))

    if t_eeg is None:
        rec['loaded'] = False
        continue

    rec['loaded'] = True
    rec['t'] = t_eeg
    rec['sig'] = sig_eeg
    rec['duration'] = t_eeg[-1]

    if t_stim is not None:
        stims = find_stim_events(sig_stim, t_stim, n_sigma=5, min_interval_s=0.3)
        rec['stims'] = stims
        rec['stim_sig'] = sig_stim
        rec['stim_t'] = t_stim
    else:
        rec['stims'] = np.array([])

    print(f"  {key}: {rec['duration']:.1f}s, {len(rec['stims'])} stims")

loaded = {k: v for k, v in RECORDS.items() if v.get('loaded')}
print(f"Loaded {len(loaded)}/{len(RECORDS)} records.")

# ============================================================
# FIGURE 1: Overview - All Records Timeline
# ============================================================
print("\nFig 1: Overview timeline of all records...")

all_files = [
    ('Rat8 (LTP6_8_SD)',   ['r8_rec01','r8_rec02','r8_rec03','r8_rec04','r8_rec05','r8_rec06','r8_rec07'], '#1565C0'),
    ('Rat8-S2 (LTP6_8_SD2)', ['r8s2_rec01','r8s2_rec02'], '#00838F'),
    ('Rat29 (LTP6_29_SD)', ['r29_rec03','r29_rec04','r29_rec05','r29_rec06'], '#E65100'),
]

fig, axes = plt.subplots(3, 1, figsize=(22, 12))
fig.suptitle('LTP6 SD Rat EEG - Session Overview (2026-06-30)', fontsize=16, fontweight='bold')

for ax_idx, (group_label, keys, group_color) in enumerate(all_files):
    ax = axes[ax_idx]
    x_offset = 0
    for key in keys:
        rec = RECORDS.get(key, {})
        if not rec.get('loaded'):
            continue
        t = rec['t']
        sig = rec['sig']
        t_plot = t + x_offset
        ax.plot(t_plot, sig, linewidth=0.2, color=rec['color'], alpha=0.7)

        # Mark stimuli
        for st in rec['stims']:
            ax.axvline(st + x_offset, color='red', linewidth=0.5, alpha=0.5)

        # Record separator
        ax.axvline(x_offset, color='gray', linewidth=1, linestyle=':', alpha=0.4)
        ax.text(x_offset + 0.5, ax.get_ylim()[1] * 0.85 if ax.get_ylim()[1] != 1 else 80,
                f"Rec{rec['rec']}\n{len(rec['stims'])}stims", fontsize=6, color='navy')

        x_offset += rec['duration'] + 5  # 5s gap between records

    ax.set_title(f'{group_label}: {sum(RECORDS[k].get("duration",0) for k in keys if RECORDS[k].get("loaded")):.0f}s total, '
                 f'{sum(len(RECORDS[k].get("stims",[])) for k in keys if RECORDS[k].get("loaded"))} stims',
                 fontsize=11)
    ax.set_ylabel('Amplitude (uV/mV)')
    ax.set_xlabel('Time (s, concatenated)')
    ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '01_overview_timeline.png'), bbox_inches='tight')
plt.close()
print("  Fig 1 saved.")

# ============================================================
# FIGURE 2: Power Spectral Density Comparison
# ============================================================
print("Fig 2: PSD comparison...")

# Select major records
psd_keys = [
    ('r8_rec03',    'Rat8 Rec3 (208s)'),
    ('r8_rec05',    'Rat8 Rec5 (163s)'),
    ('r8_rec07',    'Rat8 Rec7 (334s)'),
    ('r8s2_rec02',  'Rat8-S2 Rec2 (275s)'),
    ('r29_rec03',   'Rat29 Rec3 (195s)'),
    ('r29_rec04',   'Rat29 Rec4 (523s)'),
    ('r29_rec06',   'Rat29 Rec6 (341s)'),
]

fig, axes = plt.subplots(1, 2, figsize=(20, 8))
fig.suptitle('LTP6 SD Rat - Power Spectral Density (Welch)', fontsize=16, fontweight='bold')

ax_full = axes[0]
ax_zoom = axes[1]

for key, label in psd_keys:
    rec = RECORDS.get(key, {})
    if not rec.get('loaded'):
        continue
    sig = rec['sig']
    # Convert to consistent uV if needed
    if 'mV' in str(RECORDS[key].get('desc', '')):
        sig_plot = sig * 1000
    else:
        sig_plot = sig.copy()

    # Bandpass 1-100 Hz for clean PSD
    sig_bp = bandpass(sig_plot, 1, 100)
    f, psd = compute_psd(sig_bp)

    ax_full.semilogy(f, psd, linewidth=1.5, color=rec['color'], alpha=0.8, label=f"{label}")
    ax_zoom.semilogy(f[f <= 50], psd[f <= 50], linewidth=1.5, color=rec['color'], alpha=0.8, label=f"{label}")

# Band boundary lines
for ax in [ax_full, ax_zoom]:
    for freq, bname in [(4, 'θ'), (8, 'α'), (14, 'β'), (30, 'γ')]:
        ax.axvline(freq, color='gray', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.text(freq + 0.3, ax.get_ylim()[0] * 10 if ax.get_ylim()[0] != 0 else 1e-4,
                bname, fontsize=9, color='gray', va='bottom')

ax_full.set_xlim(0, 100)
ax_full.set_title('Full Spectrum (0-100 Hz)', fontsize=12)
ax_full.set_xlabel('Frequency (Hz)')
ax_full.set_ylabel('PSD')
ax_full.legend(fontsize=8, loc='upper right')
ax_full.grid(True, alpha=0.3)

ax_zoom.set_xlim(0, 50)
ax_zoom.set_title('Zoomed (0-50 Hz)', fontsize=12)
ax_zoom.set_xlabel('Frequency (Hz)')
ax_zoom.set_ylabel('PSD')
ax_zoom.legend(fontsize=8, loc='upper right')
ax_zoom.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '02_PSD_comparison.png'), bbox_inches='tight')
plt.close()
print("  Fig 2 saved.")

# ============================================================
# FIGURE 3: Frequency Band Power per Record (Rat8 & Rat29)
# ============================================================
print("Fig 3: Band power analysis...")

def band_power_profile(sig, fs=FS):
    result = {}
    for bname, (lo, hi, _) in BANDS.items():
        try:
            result[bname] = band_power(sig, lo, hi, fs)
        except:
            result[bname] = 0
    return result

fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.suptitle('LTP6 SD Rat - EEG Band Power Profile per Record', fontsize=16, fontweight='bold')

band_names = list(BANDS.keys())
band_colors = [v[2] for v in BANDS.values()]

rat_groups = [
    ('Rat8 (LTP6_8_SD)',   ['r8_rec01','r8_rec02','r8_rec03','r8_rec04','r8_rec05','r8_rec06','r8_rec07'], axes[0,0], axes[0,1]),
    ('Rat8-S2 + Rat29',    ['r8s2_rec01','r8s2_rec02','r29_rec03','r29_rec04','r29_rec05','r29_rec06'], axes[1,0], axes[1,1]),
]

for group_label, keys, ax_bar, ax_pie in rat_groups:
    valid_keys = [k for k in keys if RECORDS[k].get('loaded')]
    if not valid_keys:
        continue

    rec_labels = []
    band_matrix = []  # shape: [n_recs, n_bands]

    for key in valid_keys:
        rec = RECORDS[key]
        # Skip very short records (< 5s) - insufficient for band analysis
        if rec.get('duration', 0) < 5:
            continue
        sig = rec['sig'].copy()
        profile = band_power_profile(sig)
        vals = [profile[b] for b in band_names]
        # Guard against NaN
        if any(np.isnan(v) or not np.isfinite(v) for v in vals):
            continue
        band_matrix.append(vals)
        rec_labels.append(f"Rec{rec['rec']}\n({rec['duration']:.0f}s)")

    if len(band_matrix) == 0:
        ax_bar.text(0.5, 0.5, 'No valid records', transform=ax_bar.transAxes, ha='center')
        ax_pie.text(0.5, 0.5, 'No valid records', transform=ax_pie.transAxes, ha='center')
        continue

    band_matrix = np.array(band_matrix)  # [n_recs, n_bands]

    # Normalized (% of total)
    row_sums = band_matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1e-10
    band_norm = band_matrix / row_sums

    x = np.arange(len(rec_labels))
    width = 0.15

    for b_idx, (bname, color) in enumerate(zip(band_names, band_colors)):
        short_name = bname.split('(')[0].strip()
        ax_bar.bar(x + b_idx * width, band_norm[:, b_idx] * 100,
                   width, label=short_name, color=color, alpha=0.8)

    ax_bar.set_title(f'{group_label} - Band Power (% of total)', fontsize=11)
    ax_bar.set_xticks(x + width * 2)
    ax_bar.set_xticklabels(rec_labels, fontsize=8)
    ax_bar.set_ylabel('% Power')
    ax_bar.legend(fontsize=8, loc='upper right')
    ax_bar.grid(True, alpha=0.2, axis='y')

    # Pie chart: average band distribution
    avg_power = band_matrix.mean(axis=0)
    # Guard against NaN/zero in pie
    avg_power = np.nan_to_num(avg_power, nan=0.0)
    if avg_power.sum() > 0:
        ax_pie.pie(avg_power, labels=[b.split('(')[0].strip() for b in band_names],
                   colors=band_colors, autopct='%1.1f%%', startangle=90,
                   textprops={'fontsize': 9})
    else:
        ax_pie.text(0.5, 0.5, 'Zero power', transform=ax_pie.transAxes, ha='center')
    ax_pie.set_title(f'{group_label} - Avg Band Distribution', fontsize=11)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '03_band_power_profile.png'), bbox_inches='tight')
plt.close()
print("  Fig 3 saved.")

# ============================================================
# FIGURE 4: Detailed EEG for Key Long Records
# ============================================================
print("Fig 4: Detailed EEG for key records...")

key_detail = [
    ('r8_rec03',   'Rat8 Rec3 (208s)'),
    ('r8_rec07',   'Rat8 Rec7 (334s)'),
    ('r29_rec04',  'Rat29 Rec4 (523s)'),
    ('r29_rec06',  'Rat29 Rec6 (341s)'),
]

fig, axes = plt.subplots(len(key_detail), 3, figsize=(24, 4 * len(key_detail)))
fig.suptitle('LTP6 SD Rat - Key Record Detail (Raw / RMS / PSD)', fontsize=15, fontweight='bold')

for row, (key, label) in enumerate(key_detail):
    rec = RECORDS.get(key, {})
    if not rec.get('loaded'):
        continue

    t, sig = rec['t'], rec['sig']
    stims = rec['stims']
    color = rec['color']

    # --- Raw signal ---
    ax = axes[row, 0]
    ax.plot(t, sig, linewidth=0.2, color=color, alpha=0.7)
    for st in stims[:50]:
        ax.axvline(st, color='red', linewidth=0.6, linestyle='--', alpha=0.5)
    ax.set_title(f'{label} - Raw EEG ({len(stims)} stims)', fontsize=10)
    ax.set_ylabel('Amplitude')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.2)

    # --- RMS envelope ---
    ax = axes[row, 1]
    rms = rms_envelope(sig, 500)
    ax.plot(t, rms, linewidth=0.7, color=color)
    ax.fill_between(t, 0, rms, alpha=0.25, color=color)
    for st in stims[:50]:
        ax.axvline(st, color='blue', linewidth=0.6, linestyle='--', alpha=0.4)
    ax.set_title(f'{label} - RMS Envelope', fontsize=10)
    ax.set_ylabel('RMS')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.2)

    # --- PSD ---
    ax = axes[row, 2]
    sig_bp = bandpass(sig, 1, 100)
    f, psd = compute_psd(sig_bp)
    ax.semilogy(f[f <= 100], psd[f <= 100], linewidth=1.5, color=color)
    for freq, bname in [(4,'θ'), (8,'α'), (14,'β'), (30,'γ')]:
        ax.axvline(freq, color='gray', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.text(freq + 0.2, psd.max() * 0.3, bname, fontsize=8, color='gray')
    ax.set_title(f'{label} - PSD (1-100 Hz)', fontsize=10)
    ax.set_xlabel('Frequency (Hz)')
    ax.set_ylabel('PSD')
    ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '04_key_records_detail.png'), bbox_inches='tight')
plt.close()
print("  Fig 4 saved.")

# ============================================================
# FIGURE 5: Evoked Potentials (Stimulus-locked averaging)
# ============================================================
print("Fig 5: Evoked potentials...")

ep_keys = [k for k, v in RECORDS.items()
           if v.get('loaded') and len(v.get('stims', [])) >= 3]

n_ep = len(ep_keys)
n_cols = 3
n_rows = (n_ep + n_cols - 1) // n_cols

fig, axes = plt.subplots(n_rows, n_cols, figsize=(21, 5 * n_rows))
fig.suptitle('LTP6 SD Rat - Stimulus-Locked Evoked Potentials', fontsize=15, fontweight='bold')
axes_flat = axes.flatten() if n_rows > 1 else [axes] if n_cols == 1 else list(axes)

PRE_WIN = 0.5
POST_WIN = 2.0
target_len = int((PRE_WIN + POST_WIN) * FS)

for idx, key in enumerate(ep_keys):
    ax = axes_flat[idx]
    rec = RECORDS[key]
    t, sig = rec['t'], rec['sig']
    stims = rec['stims']
    color = rec['color']

    # Bandpass EEG
    sig_bp = bandpass(sig, 1, 100)

    segments = []
    for st in stims:
        mask = (t >= st - PRE_WIN) & (t <= st + POST_WIN)
        if mask.sum() >= int(target_len * 0.9):
            seg = sig_bp[mask]
            if len(seg) >= target_len:
                segments.append(seg[:target_len])

    if len(segments) < 2:
        ax.text(0.5, 0.5, f'Insufficient trials\n(n={len(segments)})',
                transform=ax.transAxes, ha='center', fontsize=11, color='gray')
        ax.set_title(f"{rec['rat']} Rec{rec['rec']}\n0 trials", fontsize=9)
        continue

    segs = np.array(segments)
    avg = np.mean(segs, axis=0)
    sem = np.std(segs, axis=0) / np.sqrt(len(segs))
    t_ep = np.linspace(-PRE_WIN, POST_WIN, len(avg))

    # Individual trials (faint)
    for s in segs[:20]:
        ax.plot(t_ep, s, linewidth=0.15, color=color, alpha=0.15)

    # Average + SEM shading
    ax.plot(t_ep, avg, linewidth=2, color=color, alpha=0.95,
            label=f'Mean (n={len(segs)})')
    ax.fill_between(t_ep, avg - sem, avg + sem, alpha=0.2, color=color)
    ax.axvline(0, color='red', linewidth=2, linestyle='--', alpha=0.8, label='Stim')
    ax.axhline(0, color='gray', linewidth=0.5, alpha=0.4)

    ax.set_title(f"{rec['rat']} Rec{rec['rec']}\nn={len(segs)} trials, {len(stims)} stims",
                 fontsize=9)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude (filtered)')
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-PRE_WIN, POST_WIN)

# Hide unused axes
for idx in range(n_ep, len(axes_flat)):
    axes_flat[idx].set_visible(False)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '05_evoked_potentials.png'), bbox_inches='tight')
plt.close()
print("  Fig 5 saved.")

# ============================================================
# FIGURE 6: LTP Analysis - Pre vs Post Stimulation
# ============================================================
print("Fig 6: LTP pre/post analysis...")

ltp_keys = [
    ('r8_rec03',  'Rat8 Rec3'),
    ('r8_rec05',  'Rat8 Rec5'),
    ('r8_rec07',  'Rat8 Rec7'),
    ('r8s2_rec02','Rat8-S2 Rec2'),
    ('r29_rec04', 'Rat29 Rec4'),
    ('r29_rec06', 'Rat29 Rec6'),
]

fig, axes = plt.subplots(2, 3, figsize=(21, 12))
fig.suptitle('LTP6 SD Rat - Pre/Post Stimulation RMS Ratio (LTP Analysis)', fontsize=15, fontweight='bold')
axes_flat2 = axes.flatten()

for idx, (key, label) in enumerate(ltp_keys):
    ax = axes_flat2[idx]
    rec = RECORDS.get(key, {})
    if not rec.get('loaded') or len(rec.get('stims', [])) < 3:
        ax.text(0.5, 0.5, 'Insufficient data', transform=ax.transAxes, ha='center', fontsize=12, color='gray')
        ax.set_title(label, fontsize=10)
        continue

    t, sig = rec['t'], rec['sig']
    stims = rec['stims']
    color = rec['color']

    ratios, bl_rms = compute_snr(sig, stims, t, pre_win=1.0, post_win=2.0)

    # Plot individual trial ratios
    ax.scatter(range(len(ratios)), ratios, s=15, color=color, alpha=0.6, zorder=3)

    # Moving average
    if len(ratios) > 5:
        window = min(5, len(ratios) // 3)
        ma = np.convolve(ratios, np.ones(window) / window, mode='valid')
        x_ma = np.arange(window // 2, window // 2 + len(ma))
        ax.plot(x_ma, ma, linewidth=2.5, color=color, alpha=0.9, label=f'MA({window})')

    ax.axhline(1.0, color='gray', linestyle='--', linewidth=1.5, alpha=0.6, label='Baseline')

    # Statistical annotation
    if len(ratios) > 1:
        pre_half = ratios[:len(ratios)//2]
        post_half = ratios[len(ratios)//2:]
        trend = "↑ LTP" if np.mean(post_half) > np.mean(pre_half) * 1.1 else \
                "↓ LTD" if np.mean(post_half) < np.mean(pre_half) * 0.9 else "≈ No change"
        ax.set_xlabel(f'Trial # | {trend}')
    else:
        ax.set_xlabel('Trial #')

    ax.set_title(f'{label}\n{len(ratios)} trials, baseline RMS={bl_rms:.2f}', fontsize=10)
    ax.set_ylabel('Post/Pre RMS ratio')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '06_LTP_analysis.png'), bbox_inches='tight')
plt.close()
print("  Fig 6 saved.")

# ============================================================
# FIGURE 7: Band Power Time Course (spectrogram-style)
# ============================================================
print("Fig 7: Band power time course for major records...")

major_recs = [
    ('r8_rec03',  'Rat8 Rec3 (208s)'),
    ('r8_rec07',  'Rat8 Rec7 (334s)'),
    ('r29_rec04', 'Rat29 Rec4 (523s)'),
]

fig, axes = plt.subplots(len(major_recs), len(BANDS), figsize=(24, 4 * len(major_recs)))
fig.suptitle('LTP6 SD Rat - EEG Band Power Time Course', fontsize=15, fontweight='bold')

for row, (key, title_prefix) in enumerate(major_recs):
    rec = RECORDS.get(key, {})
    if not rec.get('loaded'):
        continue
    t, sig = rec['t'], rec['sig']
    stims = rec['stims']

    for col, (band_name, (lo, hi, bcolor)) in enumerate(BANDS.items()):
        ax = axes[row, col]
        sig_band = bandpass(sig, lo, hi)
        rms_band = rms_envelope(sig_band, window_ms=1000)

        ax.plot(t, rms_band, linewidth=0.5, color=bcolor, alpha=0.9)
        ax.fill_between(t, 0, rms_band, alpha=0.2, color=bcolor)
        for st in stims[:30]:
            ax.axvline(st, color='red', linewidth=0.4, alpha=0.35)

        short_band = band_name.split('(')[0].strip()
        ax.set_title(f'{title_prefix}\n{short_band}', fontsize=8)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Band RMS')
        ax.grid(True, alpha=0.2)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '07_band_time_course.png'), bbox_inches='tight')
plt.close()
print("  Fig 7 saved.")

# ============================================================
# FIGURE 8: Rat8 vs Rat29 Cross-Animal Comparison
# ============================================================
print("Fig 8: Cross-animal comparison...")

fig, axes = plt.subplots(2, 2, figsize=(20, 12))
fig.suptitle('LTP6 SD Rat - Cross-Animal Comparison (Rat8 vs Rat29)', fontsize=15, fontweight='bold')

# 8a: PSD overlay
ax = axes[0, 0]
compare_pairs = [
    ('r8_rec07',  'Rat8 Rec7 (334s)', '#1976D2'),
    ('r8s2_rec02','Rat8-S2 Rec2 (275s)', '#00ACC1'),
    ('r29_rec04', 'Rat29 Rec4 (523s)', '#E64A19'),
    ('r29_rec06', 'Rat29 Rec6 (341s)', '#FF7043'),
]
for key, label, color in compare_pairs:
    rec = RECORDS.get(key, {})
    if not rec.get('loaded'):
        continue
    sig_bp = bandpass(rec['sig'], 1, 100)
    f, psd = compute_psd(sig_bp)
    ax.semilogy(f[f <= 60], psd[f <= 60], linewidth=2, color=color, alpha=0.85, label=label)
for freq, bname in [(4,'θ'),(8,'α'),(14,'β'),(30,'γ')]:
    ax.axvline(freq, color='gray', linewidth=0.5, linestyle=':', alpha=0.5)
ax.set_title('PSD Comparison (1-60 Hz)', fontsize=11)
ax.set_xlabel('Frequency (Hz)')
ax.set_ylabel('PSD')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# 8b: Band power radar-style bar
ax = axes[0, 1]
rat8_keys = ['r8_rec05', 'r8_rec07', 'r8s2_rec02']
rat29_keys = ['r29_rec04', 'r29_rec06']
short_bands = [b.split('(')[0].strip() for b in BANDS.keys()]

def avg_band_pct(keys):
    all_profiles = []
    for k in keys:
        r = RECORDS.get(k, {})
        if not r.get('loaded'):
            continue
        profile = band_power_profile(r['sig'])
        total = sum(profile.values()) + 1e-10
        all_profiles.append([profile[b] / total for b in BANDS.keys()])
    if not all_profiles:
        return [0] * len(BANDS)
    return np.mean(all_profiles, axis=0)

rat8_pct = avg_band_pct(rat8_keys)
rat29_pct = avg_band_pct(rat29_keys)
x = np.arange(len(short_bands))
width = 0.35
bars1 = ax.bar(x - width/2, [v*100 for v in rat8_pct], width, label='Rat8', color='#1976D2', alpha=0.8)
bars2 = ax.bar(x + width/2, [v*100 for v in rat29_pct], width, label='Rat29', color='#E64A19', alpha=0.8)
ax.set_xticks(x)
ax.set_xticklabels(short_bands, fontsize=9)
ax.set_title('Band Power Distribution Comparison', fontsize=11)
ax.set_ylabel('% Power')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.25, axis='y')

# 8c: Amplitude distribution
ax = axes[1, 0]
for key, label, color in compare_pairs:
    rec = RECORDS.get(key, {})
    if not rec.get('loaded'):
        continue
    sig_bp = bandpass(rec['sig'], 1, 100)
    ax.hist(sig_bp, bins=120, density=True, alpha=0.35, color=color, label=label)
ax.set_title('Amplitude Distribution (1-100 Hz bandpass)', fontsize=11)
ax.set_xlabel('Amplitude')
ax.set_ylabel('Density')
ax.legend(fontsize=9)
ax.grid(True, alpha=0.25)

# 8d: Stimulus count and duration summary
ax = axes[1, 1]
summary_keys = list(loaded.keys())
summary_stims = [len(RECORDS[k].get('stims', [])) for k in summary_keys]
summary_dur = [RECORDS[k].get('duration', 0) for k in summary_keys]
summary_labels = [f"{RECORDS[k]['rat']}\nRec{RECORDS[k]['rec']}" for k in summary_keys]

x = np.arange(len(summary_keys))
color_list = [RECORDS[k]['color'] for k in summary_keys]
bars = ax.bar(x, summary_stims, color=color_list, alpha=0.8, edgecolor='white', linewidth=0.5)
for bar, dur in zip(bars, summary_dur):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f'{dur:.0f}s', ha='center', va='bottom', fontsize=6, rotation=45)
ax.set_xticks(x)
ax.set_xticklabels(summary_labels, fontsize=7)
ax.set_title('Stimulus Count per Record', fontsize=11)
ax.set_ylabel('Number of Stimuli')
ax.grid(True, alpha=0.25, axis='y')

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, '08_cross_animal_comparison.png'), bbox_inches='tight')
plt.close()
print("  Fig 8 saved.")

# ============================================================
# QUANTITATIVE SUMMARY
# ============================================================
print("\n" + "=" * 70)
print("QUANTITATIVE ANALYSIS SUMMARY - LTP6 SD RAT (2026-06-30)")
print("=" * 70)

summary_lines = [
    "LTP6 SD Rat EEG Analysis Summary",
    "Date: 2026-06-30",
    f"Sampling rate: {FS} Hz",
    f"Records analyzed: {len(loaded)}",
    "",
    f"{'Record':<18} {'Rat':<10} {'Duration':>10} {'Stims':>8} {'EEG_RMS':>10} {'Delta%':>8} {'Beta%':>8}",
    "-" * 80,
]

print(f"\n{'Record':<18} {'Rat':<10} {'Duration':>10} {'Stims':>8} {'EEG_RMS':>10} {'Delta%':>8} {'Beta%':>8}")
print("-" * 75)

for key in sorted(loaded.keys()):
    rec = RECORDS[key]
    t, sig = rec['t'], rec['sig']
    stims = rec['stims']

    rms_val = np.sqrt(np.mean(sig ** 2))
    profile = band_power_profile(sig)
    total_p = sum(profile.values()) + 1e-10
    delta_pct = profile['Delta (1-4 Hz)'] / total_p * 100
    beta_pct = profile['Beta (14-30 Hz)'] / total_p * 100

    line = (f"{key:<18} {rec['rat']:<10} {rec['duration']:>10.1f} {len(stims):>8} "
            f"{rms_val:>10.3f} {delta_pct:>8.1f} {beta_pct:>8.1f}")
    print(line)
    summary_lines.append(line)

    if len(stims) > 1:
        intervals = np.diff(stims)
        print(f"  -> Stim intervals: mean={np.mean(intervals):.2f}s, "
              f"median={np.median(intervals):.2f}s, std={np.std(intervals):.2f}s")
        summary_lines.append(f"  -> Stim intervals: mean={np.mean(intervals):.2f}s, "
                             f"median={np.median(intervals):.2f}s")

summary_lines += [
    "",
    "Output Figures:",
    "  01_overview_timeline.png     - All records concatenated",
    "  02_PSD_comparison.png        - Power spectral density",
    "  03_band_power_profile.png    - EEG band power per record",
    "  04_key_records_detail.png    - Raw/RMS/PSD for long records",
    "  05_evoked_potentials.png     - Stimulus-locked averaging",
    "  06_LTP_analysis.png          - Pre/post stimulation ratio",
    "  07_band_time_course.png      - Band power over time",
    "  08_cross_animal_comparison.png - Rat8 vs Rat29",
]

# Save text summary
summary_path = os.path.join(OUT_DIR, "_analysis_summary.txt")
with open(summary_path, "w", encoding="utf-8") as f_out:
    f_out.write("\n".join(summary_lines))

print(f"\nSummary saved: {summary_path}")
print(f"\nOutput files in: {OUT_DIR}")
for fn in sorted(os.listdir(OUT_DIR)):
    if fn.endswith('.png'):
        size_kb = os.path.getsize(os.path.join(OUT_DIR, fn)) / 1024
        print(f"  {fn}: {size_kb:.0f} KB")

print("\n✓ Analysis complete!")
