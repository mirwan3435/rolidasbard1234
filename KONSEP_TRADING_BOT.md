# KONSEP SISTEM TRADING 5 AGENT + GROK CORE (SCALPING, MULTI-PAIR)

Dokumen ini adalah sumber acuan untuk Cursor dan untuk dasbor. Kalau ada yang bertentangan dengan kode yang sudah ada di `PYTHON_AI_LAB`, **kode yang sudah ada dibaca dulu**, lalu dokumen ini dipakai untuk menutup kekurangannya, bukan untuk menimpa.

Semua angka di dokumen ini adalah **nilai awal**. Wajib di-tuning lewat backtest, paper trading, dan demo. Tidak ada angka di sini yang merupakan jaminan hasil.

---

## 1. Prinsip yang tidak boleh dilanggar

1. **RISK deterministik dan terpisah dari AI.** Tidak ada LLM di RISK dan EXEC.
2. **AI tidak punya akses order.** Hanya EXEC (dan EA MQL5 untuk manajemen posisi) yang boleh menyentuh order.
3. **Grok Core hanya boleh menurunkan skor atau menolak.** Tidak boleh menaikkan skor, menaikkan lot, atau menjauhkan SL.
4. **Fail-closed.** Data aneh, API error, budget token habis, output Grok tidak valid: hasilnya tidak trade.
5. **SL server-side, dikirim bersamaan dengan order.** Tidak ada order tanpa SL.
6. **Dilarang:** martingale, grid, averaging down, menggeser SL menjauh, trade tanpa SL.
7. **Tahap promosi tidak boleh dilompati:** backtest → paper → demo → micro live.
8. **Jujur soal hasil.** Tidak ada jaminan 0% margin call dan tidak ada jaminan pertumbuhan modal.

---

## 2. Mode: SCALP (default)

| Mode | TF entry | TF bias | Lama posisi | SL/TP |
|---|---|---|---|---|
| `scalp` (default) | M1/M5 | H1/H4 | menit sampai ±2 jam | kecil, berbasis ATR M5 |
| `intraday` | M15/H1 | H4/D1 | beberapa jam, tutup sebelum rollover | sedang |
| `swing` | H4/D1 | W1 | hari sampai minggu | besar, hitung swap |

Mode diatur per pair di YAML profil. Kalau scalp tidak punya edge setelah biaya di backtest untuk satu pair, PAIR PROFILER menyarankan pindah mode, bukan memaksa scalping.

---

## 3. Komponen (13)

**Tier A, pengambil keputusan**

| ID | Tugas | LLM? |
|---|---|---|
| `SCOPE` | Detektor semua strategi, output `Signal` berskor 0-100 | Tidak |
| `WHALES` | Proksi order flow dan aktivitas besar (tick volume, delta tick, absorption) | Sesuai JSON agen yang sudah ada |
| `DEBATE` | Bull vs bear, mencari alasan sinyal bisa gagal | Ya |
| `RISK` | Hitung lot, semua batas, kill switch, hak veto mutlak | Tidak |
| `EXEC` | Kirim order, tangani reject/requote/slippage, cegah order ganda | Tidak |
| `CORE` (Grok Core) | Agregator dan penilai akhir | Ya |

**Tier B, penutup kekurangan**

| ID | Tugas |
|---|---|
| `DATA` | Tarik candle/tick multi-TF, cek kualitas data, sinkron waktu server |
| `CONTEXT` | Sesi/killzone, kalender berita, rezim volatilitas, tren HTF |
| `PROFILER` | Statistik pair × strategi × sesi, pilih parameter, walk-forward |
| `POSMGR` | Trailing SL dan stop order follow price, berpasangan (di EA MQL5) |
| `PORTFOLIO` | Korelasi, keranjang risiko, portfolio heat |
| `JOURNAL` | Catat setiap keputusan lengkap dengan input-nya |
| `WATCHDOG` | Heartbeat, data basi, order tanpa SL, koneksi putus |

**Alur keputusan**

```
DATA → CONTEXT → SCOPE (+ plugin strategi) → WHALES → PROFILER (filter edge)
   → DEBATE → CORE → PORTFOLIO → RISK (veto) → EXEC → EA MQL5 (POSMGR)
JOURNAL dan WATCHDOG memantau semuanya.
```

---

## 4. Arsitektur hybrid Python + MQL5

- Python = otak (analisa, skor, risk, keputusan).
- EA MQL5 = tangan per tick (trailing, stop order follow price, pairing SL-stop order). Python mengirim perintah dan parameter ke EA lewat file, socket, atau ZeroMQ.
- Alasan: polling Python punya latensi, sedangkan aturan lo "tidak boleh ada delay SL/stop order mengejar harga".
- Aturan pairing (dari proyek EA lo): SL dan stop order selalu berpasangan, stop order ±5 poin di depan SL, tidak boleh ada stop order terisi tanpa SL.

---

## 5. Strategi sebagai plugin

Semua strategi mengimplementasikan antarmuka yang sama:

```python
class Strategy(Protocol):
    id: str                      # "smc_ob_fvg", "crt", "snd", ...
    param_schema: dict           # JSON Schema parameter yang bisa di-tuning
    def detect(self, candles: "MultiTF", ctx: "Context") -> "Signal | None": ...
```

| ID plugin | Inti deteksi | Pemicu entry | SL | TP |
|---|---|---|---|---|
| `smc` | BOS/CHOCH, OB, FVG, premium/discount | Kembali ke OB/FVG searah bias HTF + CHOCH TF kecil | Luar OB + buffer ATR | Likuiditas berikutnya / RR minimum |
| `ict` | Liquidity sweep, killzone, OTE 62-79%, Power of 3, Unicorn | Sweep → displacement → retrace ke OTE | Balik ujung sweep | Sisi likuiditas berlawanan |
| `breakout` | Range konsolidasi, candle body besar close di luar range | Close breakout atau retest | Sisi lain range | Proyeksi range / ATR |
| `crt` | Candle referensi HTF, sweep high/low lalu close kembali ke dalam | Setelah close kembali | Balik ujung sweep | Sisi lain range referensi |
| `snd` | RBR/DBD/DBR/RBD, zona fresh | Sentuhan pertama zona fresh | Luar zona | Zona berlawanan |
| `sbr_rbs` | Support jebol jadi resistance (dan sebaliknya) | Retest + candle penolakan | Balik level | Swing sebelumnya |
| `orderflow_proxy` | Delta tick, lonjakan volume, absorption | Hanya konfirmasi | Tidak ada | Tidak ada |
| `session_sweep` | Range Asia disapu saat London/NY | Setelah sweep + displacement | Balik ujung sweep | Sisi berlawanan |
| `wyckoff` | Spring/upthrust | Setelah penolakan | Balik ujung | Range berlawanan |
| `mean_reversion` | Hanya rezim ranging | Ekstrem range + penolakan | Luar ekstrem | Tengah range |

Catatan: **stop order follow price + trailing SL** adalah manajemen posisi (POSMGR), bukan sinyal entry.

**Skor konfluen (bobot awal)**

| Komponen | Bobot |
|---|---|
| Bias HTF searah | 20 |
| Kualitas zona (OB/SND/FVG fresh) | 20 |
| Pemicu (CHOCH/breakout/CRT) | 20 |
| Liquidity sweep | 15 |
| Sesi/killzone | 10 |
| RR ≥ minimum | 10 |
| Proksi order flow | 5 |

**Definisi "high probability" (semua harus terpenuhi):** skor ≥ 80, RR ≥ 2, spread aman, tidak dekat berita, dan kombinasi pair × strategi itu punya expectancy positif setelah biaya di data historis (sampel ≥ 100 trade).

---

## 6. Spesifikasi `Signal`

```python
@dataclass(frozen=True)
class Signal:
    id: str                       # uuid4
    ts: datetime                  # UTC
    symbol: str                   # nama kanonik: "XAUUSD"
    broker_symbol: str            # hasil mapping dari data/symbols.json: "XAUUSD.e"
    direction: Literal["buy", "sell"]
    strategy: str                 # id plugin
    mode: Literal["scalp", "intraday", "swing"]
    tf_entry: str                 # "M1" | "M5" | ...
    tf_bias: str                  # "H1" | "H4" | ...
    order_type: Literal["market", "limit", "stop"]
    entry: float
    sl: float
    tp: float
    rr: float
    atr: float                    # ATR TF entry saat sinyal
    spread_at_signal: float
    tags: list[str]               # ["bos", "ob", "fvg", "sweep", ...]
    score_components: dict[str, float]
    score: int                    # 0-100
    expectancy_ref: float | None  # expectancy R pair×strategi dari PROFILER
    valid_until: datetime         # setelah ini sinyal kedaluwarsa
    invalidation: str             # kondisi pembatalan (teks singkat)
    source: Literal["real", "sample"] = "real"
```

JSON Schema (untuk validasi dan untuk event `signal` di `logs/events.jsonl`):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Signal",
  "type": "object",
  "additionalProperties": false,
  "required": ["id","ts","symbol","broker_symbol","direction","strategy","mode","tf_entry","tf_bias",
               "order_type","entry","sl","tp","rr","atr","spread_at_signal","tags","score_components",
               "score","valid_until","invalidation"],
  "properties": {
    "id": {"type": "string"},
    "ts": {"type": "string", "format": "date-time"},
    "symbol": {"type": "string"},
    "broker_symbol": {"type": "string"},
    "direction": {"enum": ["buy","sell"]},
    "strategy": {"type": "string"},
    "mode": {"enum": ["scalp","intraday","swing"]},
    "tf_entry": {"type": "string"},
    "tf_bias": {"type": "string"},
    "order_type": {"enum": ["market","limit","stop"]},
    "entry": {"type": "number"},
    "sl": {"type": "number"},
    "tp": {"type": "number"},
    "rr": {"type": "number", "minimum": 0},
    "atr": {"type": "number", "exclusiveMinimum": 0},
    "spread_at_signal": {"type": "number", "minimum": 0},
    "tags": {"type": "array", "items": {"type": "string"}},
    "score_components": {"type": "object", "additionalProperties": {"type": "number"}},
    "score": {"type": "integer", "minimum": 0, "maximum": 100},
    "expectancy_ref": {"type": ["number","null"]},
    "valid_until": {"type": "string", "format": "date-time"},
    "invalidation": {"type": "string", "maxLength": 240},
    "source": {"enum": ["real","sample"]}
  }
}
```

Validasi tambahan di kode (bukan di schema): SL di sisi yang benar dari entry, `rr` konsisten dengan entry/sl/tp, `valid_until` > `ts`.

---

## 7. Skema JSON untuk output Grok (`Verdict`)

Grok **tidak pernah** menghasilkan harga, lot, atau SL/TP. Hanya penilaian.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Verdict",
  "type": "object",
  "additionalProperties": false,
  "required": ["signal_id","verdict","score_adjust","reasons","risk_flags","confidence"],
  "properties": {
    "signal_id": {"type": "string"},
    "verdict": {"enum": ["accept","reduce","reject"]},
    "score_adjust": {"type": "integer", "minimum": -10, "maximum": 0},
    "reasons": {"type": "array", "items": {"type": "string", "maxLength": 200}, "maxItems": 5},
    "risk_flags": {"type": "array", "items": {"enum": ["news","low_liquidity","htf_conflict","overextended","correlation","spread","other"]}, "maxItems": 6},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  }
}
```

Aturan parsing:
- Output yang bukan JSON valid, punya field tambahan, atau di luar rentang: **ditolak otomatis** (sama dengan `reject`).
- `reduce` berarti RISK memakai pengali lot ≤ 1.0 dari kebijakan di config (Grok tidak menentukan angkanya).
- Panggilan Grok dibatasi budget token. Budget habis atau API gagal: default tidak trade.

---

## 8. Profil risiko `micro_10usd` (modal uji 10 USD)

Tambahkan sebagai profil baru di `config.py` dan `data/config.json`. Profil `standard` dan `experiment_a` tidak dihapus.

```python
"micro_10usd": {
    "virtual_capital_usd": 10.0,
    "account_type": "cent",                   # 10 USD = 1000 USC
    "risk_per_trade_pct": 2.0,
    "skip_if_min_lot_risk_pct": 3.0,          # kalau risiko di lot minimum > ini, SKIP trade
    "max_portfolio_heat_pct": 5.0,
    "daily_loss_limit_pct": 5.0,
    "kill_switch_drawdown_pct": 15.0,         # dari puncak equity
    "loss_streak_cooldown": {"3": 120, "5": "end_of_day"},   # menit / sisa hari
    "min_margin_level_pct": 500,
    "max_concurrent_positions": 2,
    "max_open_per_symbol": 1,
    "max_spread_atr_ratio": 0.15,
    "news_blackout_min": 20,
    "commission_per_lot_usd": 0.03,           # 3 USC per lot (spesifikasi XAUUSD.e EC Markets); WAJIB diverifikasi
    "commission_verified": False
}
```

Aturan perhitungan lot (ambil dari `symbol_info()`, jangan hardcode):

```
lot = (equity × risk_pct) / (jarak_SL_poin × nilai_per_poin_per_lot)
lot dibulatkan ke volume_step, dibatasi volume_min/volume_max
kalau risiko pada volume_min > skip_if_min_lot_risk_pct → SKIP
```

Catatan jujur untuk modal 10 USD:
- Di akun cent, 10 USD = 1000 USC dan lot 0.01 jauh lebih layak daripada akun standar. Di akun standar, 10 USD hampir tidak bisa dipakai dengan risk management yang benar.
- Biaya (spread, komisi) paling besar porsinya di akun kecil, dan scalping memperburuknya. Karena itu filter `spread/ATR` dan syarat expectancy positif setelah biaya itu wajib.
- Pertumbuhan modal tidak bisa dijanjikan. Ukurlah proses: expectancy (dalam R), profit factor, max drawdown.
- `commission_per_lot_usd` di profil `standard` masih placeholder 7.0. Angka yang salah merusak seluruh perhitungan edge. Jangan menganggap hasil backtest valid sebelum `commission_verified` bernilai True.

---

## 9. Profil per pair (YAML)

File: `profiles/pairs.yaml`. Nama pair kanonik; nama simbol broker diambil dari `data/symbols.json` (broker lo bisa memakai `.e` atau akhiran `m`, jangan hardcode).

Semua isi di bawah berstatus **`hypothesis`** sampai divalidasi data. PAIR PROFILER yang menaikkan statusnya jadi `validated` atau menurunkannya jadi `disabled`.

```yaml
version: 1

defaults: &defaults
  mode: scalp
  tf_entry: [M1, M5]
  tf_bias: [H1, H4]
  min_score: 80
  min_rr: 2.0
  max_spread_atr_ratio: 0.15      # spread / ATR(M5)
  news_blackout_min: 20
  min_trades_valid: 100           # sampel minimum sebelum status validated
  status: hypothesis              # hypothesis | validated | disabled
  weight_bounds: {min: 0.5, max: 1.5}   # batas penyesuaian bobot adaptif

pairs:
  XAUUSD:
    <<: *defaults
    sessions: [london, ny]
    strategies:
      snd: 1.0
      smc: 1.0
      crt: 0.9
      session_sweep: 0.8
    atr_sl_mult: 1.2
    atr_tp_mult: 2.6

  XAGUSD:
    <<: *defaults
    sessions: [london, ny]
    max_spread_atr_ratio: 0.12    # spread perak cenderung lebar, lebih ketat
    strategies:
      snd: 0.8
      breakout: 0.8
    atr_sl_mult: 1.3
    atr_tp_mult: 2.6
    correlation_group: metals     # satu keranjang risiko dengan XAUUSD

  USOIL:
    <<: *defaults
    sessions: [ny]
    news_blackout_min: 30         # hari data inventori minyak
    strategies:
      breakout: 1.0
      smc: 0.8
    atr_sl_mult: 1.3
    atr_tp_mult: 2.7

  USDJPY:
    <<: *defaults
    sessions: [tokyo, ny]
    strategies:
      breakout: 1.0
      sbr_rbs: 1.0
      smc: 0.8
    atr_sl_mult: 1.1
    atr_tp_mult: 2.4

  EURUSD:
    <<: *defaults
    sessions: [london]
    strategies:
      smc: 1.0
      ict: 1.0
      sbr_rbs: 0.8
    atr_sl_mult: 1.1
    atr_tp_mult: 2.3

  USTEC:
    <<: *defaults
    sessions: [ny]
    strategies:
      breakout: 1.0
      smc: 0.9
    atr_sl_mult: 1.4
    atr_tp_mult: 2.8

context_only:
  - DXY            # filter korelasi, tidak pernah di-entry
```

---

## 10. Struktur folder (usulan, disesuaikan dengan repo yang ada)

Folder dasbor (`dashboard_api/`, `dashboard_ui/`, `data/`, `logs/`, `scripts/`) sudah ada dan **tidak diubah strukturnya**. Tambahan untuk sistem trading:

```text
PYTHON_AI_LAB/
├── agents/
│   ├── scope/            # runner SCOPE + registry plugin
│   ├── whales/
│   ├── debate/
│   ├── core/             # Grok Core, parse_verdict()
│   ├── risk/             # risk_engine (sudah ada, FASE 3)
│   └── exec/
├── strategies/           # satu file per plugin (smc.py, ict.py, crt.py, snd.py, ...)
│   └── reference_atr_breakout.py   # implementasi referensi untuk uji pipeline
├── services/
│   ├── data_feed.py      # DATA
│   ├── context.py        # CONTEXT
│   ├── profiler.py       # PROFILER
│   ├── portfolio.py      # PORTFOLIO
│   ├── journal.py        # JOURNAL (SQLite: data/journal.db)
│   └── watchdog.py       # WATCHDOG
├── backtest/
│   ├── engine.py
│   └── costs.py
├── mql5/
│   └── PosMgr_EA.mq5     # POSMGR + bridge
├── profiles/
│   └── pairs.yaml
├── contracts/
│   ├── signal.schema.json
│   └── verdict.schema.json
└── tests/
```

---

## 11. Pipeline multi-pair dan siap pasang order

1. **Pra-hitung zona** semua pair di TF besar (watchlist zona dengan masa berlaku).
2. Tiap candle M1/M5 ditutup, scan async semua pair whitelist.
3. Harga mendekati zona (dalam sekian ATR) → aktifkan konfirmasi TF kecil.
4. Sinyal lolos skor dan edge → antrean kandidat, urut `skor × expectancy`.
5. Hanya N kandidat teratas yang dikirim ke DEBATE dan Grok. Pre-filter deterministik dulu supaya token tidak boros.
6. PORTFOLIO cek korelasi dan heat → RISK hitung lot → EXEC pasang order dengan waktu kedaluwarsa.
7. Pending order dibatalkan otomatis kalau zona batal atau berita mendekat.

"Semua simbol forex" artinya scan boleh luas, tetapi trade hanya pair di whitelist yang lolos filter spread, edge, dan korelasi.

---

## 12. Backtest dan tahap promosi

Aturan mesin backtest:
- Tidak ada look-ahead. Entry di open bar berikutnya setelah sinyal.
- Kalau SL dan TP tersentuh di bar yang sama, asumsikan **SL duluan**.
- Biaya selalu dihitung: spread (variabel kalau datanya ada), komisi, slippage.
- Walk-forward: optimasi di jendela A, uji di jendela B yang belum pernah dilihat.
- Strategi aktif hanya kalau sampel ≥ 100 trade dan expectancy > 0 setelah biaya.

Tahap promosi (kriteria dihitung dari data, bukan perasaan):

| Tahap | Syarat naik ke tahap berikutnya |
|---|---|
| Backtest | Sampel cukup, expectancy > 0 setelah biaya, drawdown dalam batas profil, `commission_verified` True |
| Paper | Jumlah trade dan hari minimum, metrik mendekati backtest |
| Demo MT5 | Beberapa minggu, tanpa pelanggaran aturan keras |
| Micro live | Keputusan manual di luar dasbor |

---

## 13. Daftar kekurangan yang harus ditutup

1. Mesin backtest dengan biaya realistis.
2. Kualitas data (candle hilang, spread melonjak di rollover, zona waktu server dan DST).
3. Pemetaan simbol per broker (`m` vs `.e`).
4. Latensi Python, jadi trailing dan pairing di EA MQL5.
5. State persistence dan recovery: restart di tengah posisi harus bisa memulihkan keadaan dari MT5 + database.
6. Idempotensi order, partial fill, reject, requote.
7. Kontrol biaya dan latensi LLM (budget, cache, timeout, default aman).
8. LLM tidak pernah menghitung lot atau harga.
9. Replay deterministik dari log JOURNAL.
10. Unit test semua detektor dan semua aturan RISK.
11. Monitor drift dan atribusi performa per strategi.
12. Alarm ke HP dan kill switch manual.
13. Manajemen rahasia (`.env`, tidak di-commit, rotasi kalau bocor).
14. Uji kegagalan (koneksi putus, spread melebar, data basi).
15. Dasbor tidak boleh bisa melonggarkan batas risiko keras.

---

## 14. Urutan pengerjaan di Cursor

`SCOPE (plugin + test) → backtest engine → PROFILER → POSMGR (EA) → PORTFOLIO + CONTEXT → Grok Core + DEBATE → JOURNAL + WATCHDOG`

Dasbor dikerjakan lewat file `PROMPT_DASHBOARD_CURSOR.md` dan boleh berjalan paralel. Tiap bagian selesai dengan test lolos dan satu git commit sebelum lanjut.
