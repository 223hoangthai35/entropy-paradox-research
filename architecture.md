# Financial Entropy Agent -- Dual-Plane Architecture Blueprint

> **Muc tieu**: He thong Multi-Modal Systemic Risk Engine quan sat thi truong qua **hai mat phang 
> Unsupervised Learning doc lap** -- Price Dynamics va Liquidity Structure. Agent Orchestrator 
> (Anthropic Claude) dong vai tro **Cross-Plane Reasoning Engine**, xac nhan Price Physics 
> bang Liquidity Structure thong qua vong lap **ReAct** va **Tool Use** protocol.

---

## 1. Tong quan Kien truc -- Dual-Plane Engine

```
+-------------------------------------------------+
|             agent_orchestrator.py               |
|         Cross-Plane Reasoning Engine            |
|       (ReAct Loop + Anthropic Tool Use)         |
+-------------------------------------------------+
         /                |                \
        /                 |                 \
+-------------+   +---------------+   +---------------+
| data_skill  |   |  quant_skill  |   |   ds_skill    |
|    .py      |   |      .py      |   |     .py       |
+-------------+   +---------------+   +---------------+
| vnstock     |   | WPE, MFI      |   | Price GMM     |
| VN30 fetch  |   | Vol Shannon   |   | Volume GMM    |
| Fallback    |   | Vol SampEn    |   | Regime Map    |
+-------------+   +---------------+   +---------------+
       |                  |                   |
       v                  v                   v
 [Market Data]    [Entropy Metrics]     [Dual Labels]
       |                  |                   |
       +----------+-------+-------+-----------+
                  |               |
                  v               v
        +=================+ +=================+
        |     PLANE 1     | |     PLANE 2     |
        | Price Dynamics  | |    Liquidity    |
        | X: WPE          | | X: Shannon Ent  |
        | Y: Volatility   | | Y: Sample Ent   |
        | Physical Chaos  | | Liq. Structure  |
        +=================+ +=================+
                  \               /
                   \             /
                    v           v
             +=============================+
             |    CROSS-PLANE SYNTHESIS    |
             |-----------------------------|
             | Accumulation | Breakdown    |
             | Exhaustion   | Coherent     |
             +=============================+
```

### Dinh nghia Hai Mat Phang

| Mat Phang | Truc X | Truc Y | Do luong | Muc dich |
|---|---|---|---|---|
| **Plane 1: Price Dynamics** | Weighted Permutation Entropy (WPE) | Annualized Volatility | "Physical Chaos" + Kinematic Vectors (V, a) | Do muc do hon loan trong dong luc gia. WPE do tinh ngau nhien cua ordinal patterns, Volatility do bien do dao dong. V = dE/dt (huong), a = d2E/dt2 (luc). |
| **Plane 2: Liquidity Structure** | Volume Shannon Entropy | Volume Sample Entropy | "Liquidity Structure" | Do cau truc dong tien. Shannon do su phan tan/tap trung cua volume. SampEn do tinh quy luat cua xung volume. |

### Vai tro Agent: Cross-Plane Reasoning Engine

Agent khong chi phan tich tung plane rieng le ma thuc hien **tong hop cheo hai mat phang** 
de phat hien nhung divergence he thong ma khong the nhan thay tu mot goc nhin don le:

| Price Plane | Volume Plane | Ket luan | Y nghia |
|---|---|---|---|
| Fragile/Chaos | Consensus Flow | **STRUCTURAL ACCUMULATION** | Chaos gia bi kiem soat boi thanh khoan co to chuc. Smart Money hap thu. |
| Fragile/Chaos | Erratic/Noisy Flow | **CRITICAL BREAKDOWN** | Chaos gia duoc khuech dai boi thanh khoan phan manh. Rui ro he thong cao. |
| Stable Growth | Erratic/Noisy Flow | **TREND EXHAUSTION** | Xu huong gia on dinh nhung cau truc thanh khoan dang do vo. |
| *Khac* | *Khac* | **SYSTEM COHERENT** | Hai mat phang dong bo. Khong co phan ky cheo. |

---

## 2. Nguyen tac Thiet ke

| Nguyen tac | Mo ta |
|---|---|
| **Separation of Concerns** | Moi skill chi chiu trach nhiem duy nhat mot domain (Data / Math / ML). |
| **DRY** | Moi ham chi duoc dinh nghia mot lan tai skill goc, cac module khac import. |
| **Vectorized First** | Toan bo phep toan tren mang su dung `numpy` vectorized. Loop chi khi bat buoc va phai dung `@numba.jit(nopython=True)`. |
| **Type Safety** | Strict type hints cho moi function signature. |
| **Testable** | Moi file ket thuc bang `if __name__ == "__main__":` block voi du lieu test. |
| **Dual-Plane Independence** | Hai classifier (Price GMM, Volume GMM) hoat dong doc lap. Agent la diem duy nhat tong hop. |

---

## 3. Module Chi tiet

### 3.1 `skills/data_skill.py` -- Data Ingestion Layer

**Trach nhiem**: Thu thap du lieu thi truong real-time tu API, xu ly fallback, va chuan hoa output.

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `fetch_vnindex(ticker, start, end)` | `ticker: str`, `start: str`, `end: str` | DataFrame OHLCV + DatetimeIndex | `vnstock` API. Columns: `Open, High, Low, Close, Volume`. |
| `fetch_vn30_returns(start, end)` | `start: str`, `end: str` | DataFrame pct_change returns VN30 | `yfinance`. `ffill()` truoc `pct_change()`. |
| `load_local_file(path)` | `path: str` | DataFrame OHLCV | Fallback. Ho tro `.csv` va `.xlsx`. |
| `get_latest_market_data(...)` | params | DataFrame OHLCV | Convenience wrapper: API uu tien, fallback neu fail. |

---

### 3.2 `skills/quant_skill.py` -- Quantitative Physics Engine

**Trach nhiem**: Tinh toan Symbolic Dynamics (WPE, Complexity, MFI), Volume Entropy (Shannon, SampEn)
va Cross-Sectional Entropy.

#### 3.2.1 Plane 1: Price Entropy

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `_calc_wpe_complexity_jit(x, m, tau)` | `np.ndarray`, `int`, `int` | `(H, C)` | Numba JIT. WPE + Jensen-Shannon Complexity. |
| `calc_rolling_wpe(log_returns, m, tau, window)` | arrays + params | `(wpe_arr, c_arr)` | Rolling window. Numba JIT. |
| `calc_wpe_complexity(x, m, tau)` | `np.ndarray` | `(float, float)` | Public wrapper single array. |
| `calc_mfi(wpe, complexity)` | `np.ndarray`, `np.ndarray` | `np.ndarray` | MFI = WPE * (1 - C). Vectorized. |

**Kinematic Vectors (tinh trong pipeline, khong phai ham rieng)**:

| Vector | Cong thuc | Tham so | Y nghia |
|---|---|---|---|
| `PE_Velocity` (V) | `df['WPE'].diff(3)` | 3-day momentum | Huong thay doi entropy. V > 0: chaos mo rong. V < 0: trat tu dang hinh thanh. |
| `PE_Acceleration` (a) | `PE_Velocity.diff(3)` | 3-day momentum | Luc thay doi. a > 0: xu huong dang tang toc. a < 0: dong luc dang can kiet. |

**Xu ly NaN**: `fillna(0)` de tranh break GMM clustering va JSON serialization.

#### 3.2.2 Plane 2: Volume Entropy

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `_calc_sample_entropy_jit(x, m, r)` | `np.ndarray`, `int`, `float` | `float` | Numba JIT. O(N^2). SampEn = -ln(A/B). |
| `calc_sample_entropy(x, m, r)` | `np.ndarray` | `float` | Public wrapper. r = 0.2*std neu None. |
| `calc_shannon_entropy_hist(x, bins)` | `np.ndarray`, `str|int` | `float [0,1]` | Histogram Shannon. bins='auto' (Freedman-Diaconis). |
| `calc_rolling_volume_entropy(volume, window)` | `np.ndarray`, `int=60` | `(shannon_arr, sampen_arr)` | Rolling wrapper. `log1p` transform. Window=60 cho SampEn hoi tu. |

**Ly do chon tham so**:
- `bins='auto'`: Volume data co phan phoi heavy-tailed, `bins=10` se tao nhieu empty bins. Freedman-Diaconis tu dong dieu chinh.
- `window=60`: SampEn voi m=2 can N >= 10^m = 100 ly tuong. 60 la muc toi thieu thuc te dam bao hoi tu.
- `log1p(volume)`: On dinh hoa phan phoi, lam tolerance r tuong doi hon.

#### 3.2.3 Cross-Sectional Correlation Entropy (VN30)

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `calc_correlation_entropy(df_returns, window)` | `pd.DataFrame`, `int` | `pd.Series` 0-100 | EVD tren Pearson Correlation Matrix. |

---

### 3.3 `skills/ds_skill.py` -- Data Science / ML Layer (Dual GMM)

**Trach nhiem**: Unsupervised Regime Classification cho **ca hai mat phang**.

#### 3.3.1 Price Regime (Plane 1)

| Component | Mo ta |
|---|---|
| `REGIME_NAMES` | `{0: "Stable Growth", 1: "Fragile Growth", 2: "Chaos/Panic"}` |
| `RegimeClassifier` | GMM `n_components=3`, `covariance_type='full'`. Mapping: sort by mean feature value. |
| `fit_predict_regime(features)` | Functional API -> `(labels, classifier)` |

#### 3.3.2 Volume Regime (Plane 2)

| Component | Mo ta |
|---|---|
| `VOLUME_REGIME_NAMES` | `{0: "Consensus Flow", 1: "Dispersed Flow", 2: "Erratic/Noisy Flow"}` |
| `VolumeRegimeClassifier` | GMM `n_components=3`, `covariance_type='full'`. Mapping: sort by sum(Shannon + SampEn). Thap = Consensus, Cao = Erratic. |
| `fit_predict_volume_regime(features)` | Functional API -> `(labels, classifier)` |

**Ngu nghia Volume Regimes**:
- **Consensus Flow**: Shannon thap + SampEn thap = Volume tap trung, deu dan. -> Institutional/Smart Money.
- **Dispersed Flow**: Shannon cao + SampEn trung binh = Volume phan tan nhung khong bat quy luat.
- **Erratic/Noisy Flow**: Shannon cao + SampEn cao = Volume vua phan tan vua bat quy luat. -> Retail/panic.

---

### 3.4 `agent_orchestrator.py` -- Cross-Plane Reasoning Engine

> **Disclaimer (Human-in-the-Loop):** The Agent is designed as a structural telemetry tool. It provides the "map" (Entropy states) and the "vehicle's dashboard" (Kinematic vectors V and a) to interpret complex market dynamics. However, the Agent is strictly an analytical observer. The final decision to act upon these conclusions rests entirely on human judgment and execution strategy.

**Trach nhiem**: Trung tam dieu phoi Dual-Plane. Goi 5 tools lien tiep, tinh Kinematic Vectors, tong hop Cross-Plane Synthesis.

#### Tool Execution Order

```
[1] fetch_market_data      -> OHLCV data
[2] compute_entropy_metrics -> Plane 1 (WPE, C, MFI, Volatility, V, a)
[3] compute_volume_entropy  -> Plane 2 (Shannon, SampEn)
[4] predict_market_regime   -> Price Regime label
[5] predict_volume_regime   -> Volume Regime label
[6] Cross-Plane Synthesis   -> Unified conclusion
```

#### Cross-Plane Synthesis Matrix (trong code)

```python
def _cross_plane_synthesis(price_regime, volume_regime):
    if price_fragile_chaos and vol_consensus:
        return "STRUCTURAL ACCUMULATION"
    elif price_fragile_chaos and vol_erratic:
        return "CRITICAL BREAKDOWN"
    elif price_stable and vol_erratic:
        return "TREND EXHAUSTION"
    else:
        return "SYSTEM COHERENT"
```

#### Diagnostic Output Format

```
=========================================
=========================================
  PLANE 1 -- PRICE DYNAMICS
=========================================
REGIME DETECTED       : [FRAGILE GROWTH]
WPE                   : 0.8745
PE Velocity (V)       : +0.0312 (chaos expanding)
PE Acceleration (a)   : -0.0045 (momentum fading)
Market Fragility (MFI): 0.8612

=========================================
  PLANE 2 -- LIQUIDITY STRUCTURE
=========================================
REGIME DETECTED       : [CONSENSUS FLOW]
Shannon Entropy       : 0.8234
Sample Entropy        : 1.4521

=========================================
  CROSS-PLANE SYNTHESIS
=========================================
SYNTHESIS             : [STRUCTURAL ACCUMULATION]
SYSTEMIC RISK LEVEL   : [MODERATE]
```

---

## 4. Data Flow Pipeline (Dual-Plane)

```
[1] User Query: "Phan tich VNINDEX voi Cross-Plane synthesis"
                |
[2] Orchestrator THINK: "Can 5 tools: data -> price entropy -> volume entropy -> 2 GMM"
                |
[3] ACT: fetch_market_data(ticker="VNINDEX", start="2024-01-01")
                |
[4] ACT: compute_entropy_metrics()    -- Plane 1
    ACT: compute_volume_entropy()     -- Plane 2
                |
[5] ACT: predict_market_regime()      -- GMM Plane 1
    ACT: predict_volume_regime()      -- GMM Plane 2
                |
[6] SYNTHESIS: Cross-Plane Matrix
    Price = "Fragile Growth" + Volume = "Consensus Flow"
    -> Conclusion: "STRUCTURAL ACCUMULATION"
                |
[7] RESPOND: "VN-Index Price Plane dang o trang thai Fragile Growth (MFI=0.86).
              Volume Plane xac nhan dong tien Consensus Flow (institutional).
              Cross-Plane Synthesis: STRUCTURAL ACCUMULATION.
              Chaos gia chi la be mat, thanh khoan van co cau truc."
```

---

## 5. Cau truc Thu muc

```
Financial Entropy Agent/
|-- agent_orchestrator.py       # Cross-Plane Reasoning Engine (5 tools + synthesis)
|-- dashboard.py                # Streamlit UI: Dual scatter plots + agent diagnostic
|-- architecture.md             # <<< File nay
|-- skills/
|   |-- data_skill.py           # Data ingestion (vnstock, yfinance, local file)
|   |-- quant_skill.py          # WPE, MFI, Shannon, SampEn, Cross-Sectional Entropy
|   |-- ds_skill.py             # Dual GMM: RegimeClassifier + VolumeRegimeClassifier
|-- _reference_VSE/             # Codebase goc (Streamlit monolith) - READ ONLY
|-- .agents/
|   |-- workflows/              # Workflow definitions
```

---

## 6. Dependency Map

| Package | Version | Module su dung | Muc dich |
|---|---|---|---|
| `numpy` | >=1.24 | `quant_skill`, `ds_skill` | Vector operations, linear algebra |
| `pandas` | >=2.0 | `data_skill`, `quant_skill`, `dashboard` | DataFrame manipulation |
| `numba` | >=0.58 | `quant_skill` | JIT: WPE rolling, SampEn O(N^2) |
| `vnstock` | >=2.0 | `data_skill` | Fetch VN-Index OHLCV |
| `yfinance` | >=0.2 | `data_skill` | Fetch VN30 component prices |
| `scikit-learn` | >=1.3 | `ds_skill` | GaussianMixture, StandardScaler |
| `anthropic` | >=0.30 | `agent_orchestrator` | Claude API, Tool Use protocol |
| `streamlit` | >=1.30 | `dashboard` | Web UI framework |
| `plotly` | >=5.18 | `dashboard` | Interactive charts |

---

## 7. Quy tac Phat trien (Dev Rules)

1. **KHONG BAO GIO** dinh nghia lai ham da ton tai trong mot skill khac. Luon `from skills.quant_skill import ...`.
2. **Logic toan hoc** chi nam trong `quant_skill.py`. **ML models** chi nam trong `ds_skill.py`. Khong tron lan.
3. Moi phep toan tren mang **PHAI** dung `numpy` vectorized. Chi dung loop khi khong the vectorize va phai danh dau `@numba.jit(nopython=True)`.
4. **Type hints** bat buoc cho moi function signature. Docstring chi tap trung vao I/O va muc dich toan hoc.
5. Moi file **PHAI** co `if __name__ == "__main__":` block de test doc lap.
6. **Hai GMM classifier hoat dong doc lap**. Agent la diem duy nhat tong hop cheo.
