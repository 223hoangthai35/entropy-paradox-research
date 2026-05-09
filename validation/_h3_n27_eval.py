"""One-shot script: evaluate H3 on n=27 panel using frozen H2 outputs."""
import json
import numpy as np
import sys
from scipy.stats import spearmanr

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

with open(r'E:\projects\research\project\validation\results_v2\n27_experiment\h2_eta_squared_n27.json', 'r', encoding='utf-8') as f:
    h2_n27 = json.load(f)
with open(r'E:\projects\research\project\validation\results_v2\n27_experiment\h1_dml_cpcv_n27.json', 'r', encoding='utf-8') as f:
    h1_n27 = json.load(f)

rps_n27 = h2_n27['rps_point_estimates']

rows_n27 = []
for m, mdata in h2_n27['per_market'].items():
    filt = mdata['filtered']
    raw = mdata['raw']
    p_tra_filt = filt['n_per_regime']['Transitional'] / filt['N_obs']
    p_tra_raw = raw['n_per_regime']['Transitional'] / raw['N_obs']
    tier = h1_n27['results'][m]['tier_rank']
    cat = h1_n27['results'][m]['category']
    rows_n27.append({
        'name': m, 'category': cat, 'tier': tier,
        'rps': float(rps_n27[m]),
        'p_tra_filt': p_tra_filt, 'p_tra_raw': p_tra_raw
    })


def h3_verdict(p_tra, category):
    if category == 'Frontier':
        if p_tra > 0.55: return 'PASS'
        elif p_tra < 0.45: return 'REJECT'
        else: return 'Dead zone'
    elif category == 'Developed':
        if p_tra < 0.50: return 'PASS'
        elif p_tra > 0.60: return 'REJECT'
        else: return 'Dead zone'
    else:
        return 'n/a'


print("=" * 100)
print("H3 EVALUATION ON n=27 PANEL")
print("=" * 100)
print(f"\n{'Market':<10} {'Category':<15} {'Tier':<5} {'RPS':>6} {'p_tra(filt)':>12} {'H3 verdict':<25}")
print("-" * 90)
for r in sorted(rows_n27, key=lambda x: (x['tier'], -x['p_tra_filt'])):
    v = h3_verdict(r['p_tra_filt'], r['category'])
    flag = " [REJECT]" if v == 'REJECT' else ""
    print(f"{r['name']:<10} {r['category']:<15} {r['tier']:<5} {r['rps']:>6.3f} {r['p_tra_filt']:>12.3f}  {v:<25}{flag}")

print("\n" + "=" * 100)
print("Spearman tests for H3 continuous on n=27")
print("=" * 100)
p_tra_filt = np.array([r['p_tra_filt'] for r in rows_n27])
p_tra_raw = np.array([r['p_tra_raw'] for r in rows_n27])
tier_arr = np.array([r['tier'] for r in rows_n27])
rps_arr = np.array([r['rps'] for r in rows_n27])

print(f"\n{'Predictor':<20} {'rho(p_tra_filt)':>17} {'p':>8} {'rho(p_tra_raw)':>17} {'p':>8}")
print("-" * 75)
for name, arr in [('RPS', rps_arr), ('Tier (MSCI)', tier_arr)]:
    rho_f, p_f = spearmanr(p_tra_filt, arr)
    rho_r, p_r = spearmanr(p_tra_raw, arr)
    print(f"{name:<20} {rho_f:>+17.4f} {p_f:>8.4f} {rho_r:>+17.4f} {p_r:>8.4f}")

print("\n" + "=" * 100)
print("Per-tier p_tra summary at n=27")
print("=" * 100)
print(f"\n{'Tier':<18} {'n':<3} {'Mean p_tra(filt)':>17} {'Min':>7} {'Max':>7} {'PASS':>5} {'REJECT':>7} {'DZ':>4}")
print("-" * 80)
for t in [4, 3, 2, 1]:
    cat_name = {4: 'Frontier', 3: 'Asian Emerging', 2: 'Crypto', 1: 'Developed'}[t]
    cat_full = {4: 'Frontier', 3: 'Emerging', 2: 'Crypto', 1: 'Developed'}[t]
    sub_p = [r['p_tra_filt'] for r in rows_n27 if r['tier'] == t]
    sub_v = [h3_verdict(r['p_tra_filt'], r['category']) for r in rows_n27 if r['tier'] == t]
    n_pass = sum(1 for v in sub_v if v == 'PASS')
    n_rej = sum(1 for v in sub_v if v == 'REJECT')
    n_dz = sum(1 for v in sub_v if v == 'Dead zone')
    print(f"{cat_name:<18} {len(sub_p):<3} {np.mean(sub_p):>17.3f} {np.min(sub_p):>7.3f} {np.max(sub_p):>7.3f} {n_pass:>5} {n_rej:>7} {n_dz:>4}")

# Frontier-only subpanel
print("\n" + "=" * 100)
print("Frontier-only subpanel test (n=8 at n=27): Spearman within-tier")
print("=" * 100)
front_rows = [r for r in rows_n27 if r['tier'] == 4]
front_p = np.array([r['p_tra_filt'] for r in front_rows])
front_rps = np.array([r['rps'] for r in front_rows])
print(f"\nFrontier markets (n=8 at n=27 panel):")
for r in sorted(front_rows, key=lambda x: x['rps']):
    print(f"  RPS={r['rps']:.3f}  {r['name']:<10} p_tra={r['p_tra_filt']:.3f}  {h3_verdict(r['p_tra_filt'], 'Frontier')}")

if len(front_p) > 2:
    rho, p = spearmanr(front_p, front_rps)
    print(f"\nWithin-Frontier ρ(p_tra, RPS) = {rho:+.4f}, p = {p:.4f}, n = {len(front_p)}")

# Comparison with n=8 main
print("\n" + "=" * 100)
print("DIRECT COMPARISON: H3 at n=8 (BVB) vs H3 at n=27")
print("=" * 100)
p_tra_n8 = np.array([0.451, 0.369, 0.535, 0.558, 0.452, 0.433, 0.352, 0.376])
tier_n8 = np.array([4, 4, 3, 3, 2, 1, 1, 1])
rps_n8 = np.array([0.90, 0.225, 0.45, 0.40, 0.55, 0.275, 0.20, 0.18])

print(f"\n{'Test':<35} {'n=8 result':>15} {'n=27 result':>15} {'Stable?':<10}")
print("-" * 80)

# RPS Spearman
rho_rps_8, p_rps_8 = spearmanr(p_tra_n8, rps_n8)
rho_rps_27, p_rps_27 = spearmanr(p_tra_filt, rps_arr)
stable_rps = "YES" if abs(rho_rps_8 - rho_rps_27) < 0.2 else "NO"
print(f"{'rho(p_tra, RPS)':<35} {rho_rps_8:>+15.3f} {rho_rps_27:>+15.3f} {stable_rps:<10}")

# Tier Spearman
rho_tier_8, p_tier_8 = spearmanr(p_tra_n8, tier_n8)
rho_tier_27, p_tier_27 = spearmanr(p_tra_filt, tier_arr)
stable_tier = "YES" if abs(rho_tier_8 - rho_tier_27) < 0.2 else "NO"
print(f"{'rho(p_tra, tier)':<35} {rho_tier_8:>+15.3f} {rho_tier_27:>+15.3f} {stable_tier:<10}")

# Frontier verdicts
def count_frontier_pass(p_tra_arr, tier_arr):
    front_idx = tier_arr == 4
    front_p = p_tra_arr[front_idx]
    pass_n = sum(1 for p in front_p if p > 0.55)
    fail_n = sum(1 for p in front_p if p < 0.45)
    dz_n = len(front_p) - pass_n - fail_n
    return pass_n, fail_n, dz_n, len(front_p)

p_n8, f_n8, dz_n8, total_n8 = count_frontier_pass(p_tra_n8, tier_n8)
p_n27, f_n27, dz_n27, total_n27 = count_frontier_pass(p_tra_filt, tier_arr)
print(f"{'Frontier PASS / FAIL / DZ':<35} {f'{p_n8}/{f_n8}/{dz_n8} (n={total_n8})':>15} {f'{p_n27}/{f_n27}/{dz_n27} (n={total_n27})':>15}")

# Developed verdicts
def count_developed_pass(p_tra_arr, tier_arr):
    dev_idx = tier_arr == 1
    dev_p = p_tra_arr[dev_idx]
    pass_n = sum(1 for p in dev_p if p < 0.50)
    fail_n = sum(1 for p in dev_p if p > 0.60)
    dz_n = len(dev_p) - pass_n - fail_n
    return pass_n, fail_n, dz_n, len(dev_p)

dp_n8, df_n8, ddz_n8, dtotal_n8 = count_developed_pass(p_tra_n8, tier_n8)
dp_n27, df_n27, ddz_n27, dtotal_n27 = count_developed_pass(p_tra_filt, tier_arr)
print(f"{'Developed PASS / FAIL / DZ':<35} {f'{dp_n8}/{df_n8}/{ddz_n8} (n={dtotal_n8})':>15} {f'{dp_n27}/{df_n27}/{ddz_n27} (n={dtotal_n27})':>15}")
