"""H2 evaluation on n=27 panel — focus on RPS pattern verification."""
import json
import numpy as np
import sys
from scipy.stats import spearmanr, pearsonr

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

with open(r'E:\projects\research\project\validation\results_v2\n27_experiment\h2_eta_squared_n27.json', 'r', encoding='utf-8') as f:
    h2 = json.load(f)
with open(r'E:\projects\research\project\validation\results_v2\n27_experiment\h1_dml_cpcv_n27.json', 'r', encoding='utf-8') as f:
    h1 = json.load(f)

rps_n27 = h2['rps_point_estimates']
rows = []
for m, mdata in h2['per_market'].items():
    raw = mdata['raw']
    filt = mdata['filtered']
    tier = h1['results'][m]['tier_rank']
    cat = h1['results'][m]['category']
    rps = float(rps_n27[m])
    rows.append({
        'name': m, 'cat': cat, 'tier': tier, 'rps': rps,
        'H_raw': raw['H_stat'], 'H_filt': filt['H_stat'],
        'eta_raw': raw['eta_sq'], 'eta_filt': filt['eta_sq']
    })

H_raw = np.array([r['H_raw'] for r in rows])
H_filt = np.array([r['H_filt'] for r in rows])
eta_raw = np.array([r['eta_raw'] for r in rows])
eta_filt = np.array([r['eta_filt'] for r in rows])
rps = np.array([r['rps'] for r in rows])
tier = np.array([r['tier'] for r in rows])

print("=" * 100)
print("H2 EVALUATION ON n=27 PANEL — full results focused on RPS pattern verification")
print("=" * 100)

print(f"\n{'Predictor':<15} {'rho(H_raw)':>12} {'p':>8} {'rho(H_filt)':>13} {'p':>8} {'rho(eta_raw)':>14} {'p':>8} {'rho(eta_filt)':>15} {'p':>8}")
print("-" * 110)
for label, predictor in [('Tier (composite)', tier), ('RPS (1-axis)', rps)]:
    r1, p1 = spearmanr(H_raw, predictor)
    r2, p2 = spearmanr(H_filt, predictor)
    r3, p3 = spearmanr(eta_raw, predictor)
    r4, p4 = spearmanr(eta_filt, predictor)
    print(f"{label:<15} {r1:>+12.4f} {p1:>8.4f} {r2:>+13.4f} {p2:>8.4f} {r3:>+14.4f} {p3:>8.4f} {r4:>+15.4f} {p4:>8.4f}")

print("\n" + "=" * 100)
print("Per-tier breakdown (cluster sanity check)")
print("=" * 100)
print(f"\n{'Tier':<18} {'n':<3} {'mean RPS':>10} {'mean H_raw':>12} {'mean H_filt':>13} {'mean eta_filt':>15}")
print("-" * 75)
for t in [4, 3, 2, 1]:
    cat_name = {4: 'Frontier', 3: 'Asian Emerging', 2: 'Crypto', 1: 'Developed'}[t]
    sub = [r for r in rows if r['tier'] == t]
    if sub:
        print(f"{cat_name:<18} {len(sub):<3} {np.mean([r['rps'] for r in sub]):>10.3f} {np.mean([r['H_raw'] for r in sub]):>12.2f} {np.mean([r['H_filt'] for r in sub]):>13.2f} {np.mean([r['eta_filt'] for r in sub]):>15.4f}")

print("\n" + "=" * 100)
print("Within-tier ρ(H, RPS) — direct test of RPS pattern within tier")
print("=" * 100)
for t in [4, 3, 1]:
    cat_name = {4: 'Frontier', 3: 'Asian Emerging', 1: 'Developed'}[t]
    sub_idx = [i for i, r in enumerate(rows) if r['tier'] == t]
    if len(sub_idx) >= 4:
        H_sub = H_raw[sub_idx]
        H_filt_sub = H_filt[sub_idx]
        rps_sub = rps[sub_idx]
        r1, p1 = spearmanr(H_sub, rps_sub)
        r2, p2 = spearmanr(H_filt_sub, rps_sub)
        print(f"\n  {cat_name} (n={len(sub_idx)}):")
        print(f"    rho(H_raw, RPS)  = {r1:+.4f}, p = {p1:.4f}")
        print(f"    rho(H_filt, RPS) = {r2:+.4f}, p = {p2:.4f}")
        print(f"    Markets:")
        for i in sub_idx:
            r = rows[i]
            print(f"      RPS={r['rps']:.3f}  {r['name']:<10} H_raw={r['H_raw']:>7.2f}  H_filt={r['H_filt']:>7.2f}")

print("\n" + "=" * 100)
print("Sensitivity: drop high-leverage markets")
print("=" * 100)

# Drop top-2 H markets (leverage)
order_H = np.argsort(-H_raw)
top2_drop = order_H[:2]
mask = np.ones(len(rows), dtype=bool)
mask[top2_drop] = False
print(f"\nDrop top-2 H_raw markets ({rows[order_H[0]]['name']}, {rows[order_H[1]]['name']}):")
print(f"  rho(H_raw, RPS | drop top-2) = {spearmanr(H_raw[mask], rps[mask])[0]:+.4f}, p = {spearmanr(H_raw[mask], rps[mask])[1]:.4f}")
print(f"  rho(H_raw, tier | drop top-2) = {spearmanr(H_raw[mask], tier[mask])[0]:+.4f}, p = {spearmanr(H_raw[mask], tier[mask])[1]:.4f}")

# Drop bottom-2 (low H plateau)
bottom2_drop = order_H[-2:]
mask2 = np.ones(len(rows), dtype=bool)
mask2[bottom2_drop] = False
print(f"\nDrop bottom-2 H_raw markets ({rows[order_H[-2]]['name']}, {rows[order_H[-1]]['name']}):")
print(f"  rho(H_raw, RPS | drop bottom-2) = {spearmanr(H_raw[mask2], rps[mask2])[0]:+.4f}, p = {spearmanr(H_raw[mask2], rps[mask2])[1]:.4f}")
print(f"  rho(H_raw, tier | drop bottom-2) = {spearmanr(H_raw[mask2], tier[mask2])[0]:+.4f}, p = {spearmanr(H_raw[mask2], tier[mask2])[1]:.4f}")

print("\n" + "=" * 100)
print("FULL PER-MARKET TABLE sorted by RPS")
print("=" * 100)
print(f"\n{'RPS':>6} {'market':<10} {'tier':<5} {'category':<15} {'H_raw':>8} {'H_filt':>8}")
for r in sorted(rows, key=lambda x: x['rps']):
    print(f"{r['rps']:>6.3f} {r['name']:<10} {r['tier']:<5} {r['cat']:<15} {r['H_raw']:>8.2f} {r['H_filt']:>8.2f}")
