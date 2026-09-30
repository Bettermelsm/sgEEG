"""
Step 1: Extract .adicht data to CSV
Date: 2026-06-30
Files: LTP6_29 SD.adicht, LTP6_8 SD.adicht, LTP6_8 SD2.adicht
Experiment: SD rat LTP (Long-Term Potentiation) - Brain stimulation

Uses adi-reader library to read LabChart .adicht format.
Output: extracted/ directory with CSV per channel per record.
"""

import adi
import numpy as np
import pandas as pd
import os
import json

DATA_DIR = r"D:\01SG_FILES\006DEV\Process\SG20260417DEV01_EEG\Process\20260630"
OUT_DIR = os.path.join(DATA_DIR, "extracted")
os.makedirs(OUT_DIR, exist_ok=True)

# Files to process with labels
files = [
    ("LTP6_8 SD.adicht",   "rat8",    "LTP6_8_SD"),
    ("LTP6_8 SD2.adicht",  "rat8_s2", "LTP6_8_SD2"),
    ("LTP6_29 SD.adicht",  "rat29",   "LTP6_29_SD"),
]

metadata = {}

print("=" * 70)
print("ADInstruments .adicht Extraction - LTP6 SD Rat (2026-06-30)")
print("=" * 70)

for fname, rat_id, file_tag in files:
    fpath = os.path.join(DATA_DIR, fname)
    if not os.path.exists(fpath):
        print(f"[SKIP] {fname} not found")
        continue

    print(f"\n--- Reading: {fname} ({rat_id}) ---")
    f = adi.read_file(fpath)
    print(f"  Channels: {f.n_channels}, Records: {f.n_records}")

    rec_info = {
        "filename": fname,
        "rat_id": rat_id,
        "file_tag": file_tag,
        "n_channels": f.n_channels,
        "n_records": f.n_records,
        "channel_names": f.channel_names,
        "segments": []
    }

    for rec_idx in range(1, f.n_records + 1):
        seg_info = {"rec_idx": rec_idx, "channels": []}
        print(f"  Record {rec_idx}/{f.n_records}:", end="")

        for ch_idx, ch in enumerate(f.channels):
            try:
                data = ch.get_data(rec_idx)
                fs = float(ch.fs[rec_idx - 1])
                if fs <= 0 or len(data) == 0:
                    print(f" Ch{ch_idx+1}[empty]", end="")
                    continue

                duration = len(data) / fs
                # Build time array starting from 0
                t = np.arange(len(data)) / fs
                units = ch.units[rec_idx - 1] if rec_idx - 1 < len(ch.units) else "?"

                # Determine channel role from units and position
                # Ch1 = EEG signal (mV/uV), Ch2 = possibly EMG or reference, Ch3 = stim marker (V)
                if ch_idx == 0:
                    ch_role = "EEG"
                elif ch_idx == 1 and f.n_channels == 2:
                    ch_role = "Stim"
                elif ch_idx == 1:
                    ch_role = "Ch2"
                else:
                    ch_role = "Stim"

                csv_name = f"{rat_id}_rec{rec_idx:02d}_ch{ch_idx+1}_{ch_role}_{file_tag}.csv"
                csv_path = os.path.join(OUT_DIR, csv_name)

                ch_label = f"Ch{ch_idx+1}_{ch_role}_{units}"
                df = pd.DataFrame({"Time_s": t, ch_label: data})
                df.to_csv(csv_path, index=False)

                seg_info["channels"].append({
                    "ch_idx": ch_idx + 1,
                    "ch_role": ch_role,
                    "fs_hz": fs,
                    "duration_s": round(duration, 3),
                    "n_samples": len(data),
                    "units": units,
                    "signal_min": float(np.min(data)),
                    "signal_max": float(np.max(data)),
                    "signal_mean": float(np.mean(data)),
                    "signal_std": float(np.std(data)),
                    "csv_file": csv_name
                })
                print(f" Ch{ch_idx+1}({units},{fs:.0f}Hz,{duration:.1f}s)", end="")
            except Exception as e:
                print(f" Ch{ch_idx+1}[ERR:{e}]", end="")

        print()
        rec_info["segments"].append(seg_info)

    metadata[file_tag] = rec_info

# Save metadata
meta_path = os.path.join(OUT_DIR, "_metadata.json")
with open(meta_path, "w", encoding="utf-8") as f_out:
    json.dump(metadata, f_out, ensure_ascii=False, indent=2)

print(f"\n{'='*70}")
print("EXTRACTION SUMMARY")
print(f"{'='*70}")
for key, info in metadata.items():
    total_dur = sum(ch['duration_s'] for seg in info['segments'] for ch in seg['channels'] if ch['ch_idx'] == 1)
    print(f"\n{info['filename']} ({info['rat_id']})")
    print(f"  {info['n_records']} records, {info['n_channels']} channels, total EEG dur={total_dur:.1f}s")
    for seg in info["segments"]:
        for ch in seg["channels"]:
            print(f"  Rec{seg['rec_idx']:02d} Ch{ch['ch_idx']} [{ch['ch_role']}] "
                  f"fs={ch['fs_hz']:.0f}Hz  dur={ch['duration_s']:.1f}s  "
                  f"range=[{ch['signal_min']:.3f},{ch['signal_max']:.3f}]{ch['units']}")

n_csvs = len([f for f in os.listdir(OUT_DIR) if f.endswith('.csv')])
print(f"\nExtracted {n_csvs} CSV files → {OUT_DIR}")
print("Metadata saved → _metadata.json")
print("Done!")
