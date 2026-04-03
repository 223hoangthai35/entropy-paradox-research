# InfoStat Dynamics -- Architecture Blueprint

> **Muc tieu**: Chuyen doi ung dung monolith Streamlit (`_reference_VSE/app.py`) thanh kien truc **Agent-Driven Modular**, 
> trong do mot LLM Orchestrator (Anthropic Claude) dieu phoi 3 skill modules thong qua vong lap **ReAct** (Reasoning + Acting) 
> va **Tool Use** protocol.

---

## 1. Tong quan Kien truc

```
                          +---------------------------+
                          |   agent_orchestrator.py   |
                          |   (ReAct Loop + Claude    |
                          |    Anthropic Tool Use)    |
                          +---------------------------+
                           /           |            \
                          /            |             \
              +-----------+    +---------------+    +----------+
              | data_skill|    | quant_skill   |    | ds_skill |
              | .py       |    | .py           |    | .py      |
              +-----------+    +---------------+    +----------+
              | vnstock   |    | WPE           |    | GMM      |
              | VN30 fetch|    | Cross-Sect.   |    | Regime   |
              | Fallback  |    | CECP Boundary |    | Classify |
              +-----------+    +---------------+    +----------+
                    |                 |                   |
                    v                 v                   v
              [Market Data]    [Entropy Metrics]    [Regime Labels]
```

### Nguyen tac Thiet ke

| Nguyen tac | Mo ta |
|---|---|
| **Separation of Concerns** | Moi skill chi chiu trach nhiem duy nhat mot domain (Data / Math / ML). |
| **DRY** | Moi ham chi duoc dinh nghia mot lan tai skill goc, cac module khac import. |
| **Vectorized First** | Toan bo phep toan tren mang su dung `numpy` vectorized. Loop chi khi bat buoc va phai dung `@numba.jit(nopython=True)`. |
| **Type Safety** | Strict type hints cho moi function signature. |
| **Testable** | Moi file ket thuc bang `if __name__ == "__main__":` block voi du lieu test. |

---

## 2. Module Chi tiet

### 2.1 `skills/data_skill.py` -- Data Ingestion Layer

**Trach nhiem**: Thu thap du lieu thi truong real-time tu API, xu ly fallback, va chuan hoa output.

**Nguon Tham chieu**: `_reference_VSE/app.py` dong 36-59 (`fetch_market_data`, `fetch_vn30_components`).

#### Cac ham can triet xuat va tai cau truc:

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `fetch_vnindex(ticker, start, end) -> pd.DataFrame` | `ticker: str`, `start: str`, `end: str` | DataFrame OHLCV voi DatetimeIndex | Dung `vnstock.Vnstock().stock().quote.history()`. Columns chuan hoa: `Open, High, Low, Close, Volume`. |
| `fetch_vn30_returns(start, end) -> pd.DataFrame` | `start: str`, `end: str` | DataFrame pct_change returns cho ~28 VN30 tickers | Dung `yfinance` lam nguon. `ffill()` truoc khi `pct_change()`. |
| `load_local_file(path) -> pd.DataFrame` | `path: str` | DataFrame OHLCV | Fallback khi API bi rate-limit. Ho tro `.csv` va `.xlsx`. Tu dong detect cot ngay va rename columns. |

#### Luu y Ky thuat:
- **Caching**: Ap dung `@functools.lru_cache` hoac tuong duong de cache ket qua API (TTL ~1h).
- **VN30 Ticker List**: Hardcode danh sach ticker nhu trong reference (dong 49-54). Can xem xet co che cap nhat dong trong tuong lai.
- **Error Handling**: Khi `vnstock` that bai, raise custom exception de orchestrator co the chuyen sang fallback strategy.

---

### 2.2 `skills/quant_skill.py` -- Quantitative Physics Engine

**Trach nhiem**: Toan bo tinh toan Information Theory: Weighted Permutation Entropy (WPE), Statistical Complexity (C_JS), 
Market Fragility Index (MFI), Cross-Sectional Correlation Entropy, va CECP Boundary curves.

**Nguon Tham chieu**: `_reference_VSE/app.py` dong 65-240 va `_reference_VSE/README.md` (cong thuc toan hoc).

#### 2.2.1 Weighted Permutation Entropy (WPE)

**Cong thuc Goc** (tu README):

```
H(WPE) = - (1 / ln(m!)) * SUM[ p_i^(w) * ln(p_i^(w)) ]
```

- `m`: Embedding dimension (mac dinh = 3, toi da 7).
- `tau`: Time lag (mac dinh = 1).
- `p_i^(w)`: Tan suat trong so (weighted by variance) cua ordinal pattern thu i.

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `get_ordinal_patterns_wpe(x, m, tau) -> tuple[np.ndarray, np.ndarray]` | `x: np.ndarray` (time series), `m: int`, `tau: int` | `(patterns, weights)` | Pattern = argsort cua embedded vectors. Weight = variance cua amplitude. |
| `calc_wpe_complexity(x, m, tau) -> tuple[float, float]` | `x: np.ndarray`, `m: int`, `tau: int` | `(H_wpe, C_js)` | Tra ve normalized entropy `H` va Jensen-Shannon Statistical Complexity `C`. |
| `calc_rolling_entropy(series, m, tau, window) -> np.ndarray` | `series: np.ndarray`, cac tham so | Mang entropy rolling | Ap dung `calc_wpe_complexity` tren sliding window. Day la ham iterative -> **uu tien `@numba.jit`**. |

#### 2.2.2 Jensen-Shannon Statistical Complexity (C_JS) va MFI

**Cong thuc Goc**:

```
C = Q0 * JSD(P, U) * H

MFI = WPE * (1 - C)
```

- `JSD(P, U)`: Jensen-Shannon Divergence giua phan phoi thuc nghiem `P` va phan phoi deu `U`.
- `Q0`: He so chuan hoa (1 / D_max).
- `MFI` tang khi he thong dong thoi random (WPE cao) va mat complexity (C thap) -> bao hieu fragility.

Logic tinh `Q0`, `JSD`, `C_JS` da duoc implement tai `_reference_VSE/app.py:76-114`. Can trich xuat nguyen khoi, chi refactor type hints va bien naming.

#### 2.2.3 Cross-Sectional Correlation Entropy (VN30)

**Cong thuc Goc**:

```
p_i = lambda_i / SUM(lambda_j)
S_corr = - ( SUM(p_i * ln(p_i)) / ln(M) ) * 100
```

- `C`: Ma tran Pearson Correlation cua returns M co phieu (M ~ 28-30).
- Eigenvalue Decomposition (EVD) tren `C` -> `lambda_i`.
- Output: Gia tri 0-100. Thap (<40) = consensus manh, Cao (>70) = fragmented/chaos.

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `calc_correlation_entropy(df_returns, window) -> pd.Series` | `df_returns: pd.DataFrame`, `window: int` | Series entropy 0-100 | Rolling window tren correlation matrix. Ref: dong 219-240. |

#### 2.2.4 CECP Boundary Curves (Lopez-Ruiz)

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `generate_cecp_boundary(m) -> tuple[list, list, list, list]` | `m: int` | `(H_max, C_max, H_min, C_min)` | Upper/Lower bound curves cho Complexity-Entropy plane. Ref: dong 173-217. |

#### 2.2.5 Multi-Scale WPE

Tinh WPE tren 3 time scale doc lap:
- **Daily**: Rolling window tren log-return hang ngay.
- **Weekly**: Resample `Close` theo tuan, tinh log-return, rolling window = 12 tuan.
- **Monthly**: Resample `Close` theo thang, tinh log-return, rolling window = 6 thang.

Ref: `_reference_VSE/app.py:146-170`.

---

### 2.3 `skills/ds_skill.py` -- Data Science / ML Layer

**Trach nhiem**: Unsupervised Regime Classification su dung Gaussian Mixture Model (GMM), thay the logic rule-based hien tai.

**Nguon Tham chieu**: `_reference_VSE/app.py` dong 242-271 (`detect_market_regime` -- hien la **rule-based**).

#### Hien trang (Rule-Based)

Logic hien tai su dung hard-coded thresholds:
```python
if price >= MA20 and MFI < 50:        -> "Stable Growth"
if price >= MA20 and MFI >= 50:       -> "Fragile Growth"
if price < MA20 and MFI > 65:         -> "Chaos/Panic"
if price < MA20 and entropy_diff < 0: -> "Structural Recomposition"
```

#### Thiet ke Moi (GMM-Based)

Thay the rule-based bang **Gaussian Mixture Model** (tu `sklearn.mixture.GaussianMixture`) de tu dong phat hien regime clusters trong khong gian dac trung da chieu.

| Ham | Input | Output | Ghi chu |
|---|---|---|---|
| `build_feature_matrix(df) -> np.ndarray` | `df: pd.DataFrame` (chua WPE, C, MFI, System_Entropy) | Ma tran dac trung N x F | Feature engineering: `[WPE_Price, Complexity_Price, MFI_Price, System_Entropy, price_vs_ma20_ratio]`. Chuan hoa voi `StandardScaler`. |
| `fit_gmm(features, n_components) -> GaussianMixture` | `features: np.ndarray`, `n_components: int = 4` | Fitted GMM model | 4 components tuong ung 4 regimes. Su dung `covariance_type='full'` va `n_init=10` de on dinh. |
| `classify_regime(model, features) -> np.ndarray` | `model: GaussianMixture`, `features: np.ndarray` | Mang regime labels (0-3) | `model.predict(features)`. Can mapping cluster index -> regime name dua tren dac tinh centroid. |
| `map_cluster_to_regime(model) -> dict[int, str]` | `model: GaussianMixture` | `{0: 'Stable Growth', ...}` | Phan tich `model.means_` de tu dong gan nhan: cluster co MFI thap nhat -> Stable, MFI cao nhat + WPE cao -> Chaos, v.v. |

#### Luu y:
- GMM cho phep soft classification (probability per regime), huu ich hon binary thresholds.
- Can giu nguyen 4 regime labels de tuong thich voi he thong hien tai: `Stable Growth`, `Fragile Growth`, `Chaos/Panic`, `Structural Recomposition`.

---

### 2.4 `agent_orchestrator.py` -- ReAct Loop + Anthropic Tool Use

**Trach nhiem**: Trung tam dieu phoi. Nhan truy van tu nguoi dung (hoac trigger tu dinh ky), chay vong lap ReAct 
de goi cac skill nhu tools, tong hop ket qua, va tra ve phan tich cuoi cung.

#### Kien truc ReAct Loop

```
User Query / Scheduled Trigger
        |
        v
+-------------------+
| THINK (Reasoning) | <-- Claude phan tich truy van, quyet dinh can data gi
+-------------------+
        |
        v
+-------------------+
| ACT (Tool Call)   | <-- Goi skill tuong ung qua Anthropic Tool Use API
+-------------------+     (fetch_vnindex, calc_wpe_complexity, fit_gmm, ...)
        |
        v
+-------------------+
| OBSERVE           | <-- Nhan ket qua tu tool, Claude danh gia
+-------------------+
        |
        v
   Ket qua da du? --No--> quay lai THINK
        |
       Yes
        v
+-------------------+
| RESPOND           | <-- Tong hop narrative + du lieu -> tra ve user
+-------------------+
```

#### Tool Definitions (Anthropic Format)

Moi skill function duoc expose nhu mot tool voi schema JSON:

```python
TOOLS = [
    {
        "name": "fetch_vnindex",
        "description": "Thu thap du lieu OHLCV cua VN-Index tu vnstock API.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "default": "VNINDEX"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"}
            },
            "required": ["start_date"]
        }
    },
    {
        "name": "fetch_vn30_returns",
        "description": "Lay returns cua ro VN30 de tinh Cross-Sectional Entropy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"}
            },
            "required": ["start_date"]
        }
    },
    {
        "name": "calc_full_entropy_analysis",
        "description": "Tinh toan WPE, Complexity, MFI cho chuoi gia. Tra ve DataFrame da enriched.",
        "input_schema": {
            "type": "object",
            "properties": {
                "embed_dim": {"type": "integer", "default": 3},
                "rolling_window": {"type": "integer", "default": 22}
            }
        }
    },
    {
        "name": "calc_correlation_entropy",
        "description": "Tinh Cross-Sectional Entropy tu returns VN30 (EVD-based).",
        "input_schema": {
            "type": "object",
            "properties": {
                "window": {"type": "integer", "default": 22}
            }
        }
    },
    {
        "name": "classify_regime",
        "description": "Phan loai trang thai thi truong (GMM unsupervised) tu cac entropy features.",
        "input_schema": {
            "type": "object",
            "properties": {
                "n_components": {"type": "integer", "default": 4}
            }
        }
    },
    {
        "name": "generate_cecp_boundary",
        "description": "Tao duong gioi han Lopez-Ruiz cho CECP plot.",
        "input_schema": {
            "type": "object",
            "properties": {
                "embed_dim": {"type": "integer", "default": 3}
            }
        }
    }
]
```

#### Xu ly Tool Call (Dispatcher)

```python
def dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """
    Map tool_name -> skill function, thuc thi, serialize ket qua.
    """
    if tool_name == "fetch_vnindex":
        df = data_skill.fetch_vnindex(**tool_input)
        return df.to_json(orient="split", date_format="iso")
    elif tool_name == "calc_full_entropy_analysis":
        # Su dung du lieu da fetch truoc do (stored in session state)
        ...
    elif tool_name == "classify_regime":
        ...
    ...
```

#### Conversation Loop

```python
def run_react_loop(user_query: str, max_iterations: int = 10) -> str:
    messages = [{"role": "user", "content": user_query}]
    
    for _ in range(max_iterations):
        response = anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
            system=SYSTEM_PROMPT
        )
        
        # Kiem tra stop_reason
        if response.stop_reason == "end_turn":
            return extract_text(response)
        
        if response.stop_reason == "tool_use":
            # Xu ly tung tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
    
    return "Max iterations reached."
```

---

## 3. Data Flow Pipeline

```
[1] User Query: "Phan tich trang thai VN-Index hom nay"
                |
[2] Orchestrator THINK: "Can fetch data -> tinh entropy -> classify regime"
                |
[3] ACT: fetch_vnindex(start="2024-01-01", end="2025-04-03")
    ACT: fetch_vn30_returns(start="2024-01-01", end="2025-04-03")
                |
[4] OBSERVE: Nhan 2 DataFrames
                |
[5] ACT: calc_full_entropy_analysis(embed_dim=3, rolling_window=22)
    ACT: calc_correlation_entropy(window=22)
                |
[6] OBSERVE: Nhan enriched DataFrame voi WPE, C, MFI, System_Entropy
                |
[7] ACT: classify_regime(n_components=4)
                |
[8] OBSERVE: Regime labels cho tung ngay
                |
[9] RESPOND: "VN-Index hien dang o trang thai Fragile Growth (MFI = 72.3/100).
              Cross-Sectional Entropy = 68.5 cho thay dong tien dang phan manh.
              Tren CECP, diem hien tai bam sat Lower Bound voi H=0.85, C=0.08..."
```

---

## 4. Cau truc Thu muc

```
InfoStatDynamics/
|-- agent_orchestrator.py       # ReAct loop + Anthropic Tool Use
|-- skills/
|   |-- data_skill.py           # Data ingestion (vnstock, yfinance, local file)
|   |-- quant_skill.py          # WPE, C_JS, MFI, Cross-Sectional Entropy, CECP
|   |-- ds_skill.py             # GMM Regime Classification
|-- _reference_VSE/             # Codebase goc (Streamlit monolith) - READ ONLY
|   |-- app.py                  # 654 dong, toan bo logic goc
|   |-- README.md               # Cong thuc toan hoc & ly thuyet
|-- .agents/
|   |-- workflows/              # Workflow definitions
|-- architecture.md             # <<< File nay
```

---

## 5. Dependency Map

| Package | Version | Module su dung | Muc dich |
|---|---|---|---|
| `numpy` | >=1.24 | `quant_skill`, `ds_skill` | Vector operations, linear algebra |
| `pandas` | >=2.0 | `data_skill`, `quant_skill` | DataFrame manipulation |
| `numba` | >=0.58 | `quant_skill` | JIT compilation cho rolling loops |
| `vnstock` | >=2.0 | `data_skill` | Fetch VN-Index OHLCV |
| `yfinance` | >=0.2 | `data_skill` | Fetch VN30 component prices |
| `scikit-learn` | >=1.3 | `ds_skill` | GaussianMixture, StandardScaler |
| `anthropic` | >=0.30 | `agent_orchestrator` | Claude API, Tool Use protocol |
| `scipy` | >=1.11 | `quant_skill` | Bo sung (eigenvalue, statistical functions) |

---

## 6. Quy tac Phat trien (Dev Rules)

1. **KHONG BAO GIO** dinh nghia lai ham da ton tai trong mot skill khac. Luon `from skills.quant_skill import ...`.
2. **Logic toan hoc** chi nam trong `quant_skill.py`. **ML models** chi nam trong `ds_skill.py`. Khong tron lan.
3. Moi phep toan tren mang **PHAI** dung `numpy` vectorized. Chi dung loop khi khong the vectorize va phai danh dau `@numba.jit(nopython=True)`.
4. **Type hints** bat buoc cho moi function signature. Docstring chi tap trung vao I/O va muc dich toan hoc, khong viet boilerplate.
5. Moi file **PHAI** co `if __name__ == "__main__":` block de test doc lap.
