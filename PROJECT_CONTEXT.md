
## Rezultat Etapa 6 - Stop-loss -8%

Perioada: 2021-2026.
Univers: 43 tranzacții generate din historical_ohlcv.

| Varianta | Tranzacții | Win rate | Randament mediu net | Net Profit Factor | Maximum Drawdown |
|---|---:|---:|---:|---:|---:|
| Baseline, iesire 5 zile | 43 | 65.12% | 2.58% | 2.7914 | -13.00% |
| Stop-loss -8% | 43 | 65.12% | 2.78% | 3.2306 | -8.00% |

Concluzie:
- Stop-loss -8% reduce drawdown-ul si imbunatateste Profit Factor-ul net.
- Sunt oprite 3 tranzactii.
- Rezultatul este promitator, dar esantionul ramane moderat.
- 2025 este usor negativ; 2023 are o singura tranzactie.
- Stop-loss -8% este candidat pentru configuratia recomandata,
  nu yet implementat in productie.

## Dynamic metrics baseline — 2026-10-14

`src/metrics_generator.py` calculează acum metricile istoric direct din `historical_ohlcv`, folosind prețuri OHLC reale.

- Stop-loss-ul este simulat intraday: dacă `Low` atinge `-8%` față de prețul de intrare, poziția este închisă la acel nivel.
- Baseline-ul dinamic canonic este: `output/portfolio_metrics_history_stop8_dynamic_baseline.json`.
- Rezultatele dinamice sunt mai conservatoare decât baseline-ul static, deoarece includ stopuri reale intraday.

### Rezultate baseline

- Total trades: 43
- Win rate: 60.47%
- Net profit factor: 2.3676
- Max drawdown: -15.36%
- Final equity: 2.3130
- Stopped out: 5 din 43, adică 11.63%

### Decizie metodologică

`max_drawdown` este calculat momentan trade-by-trade, secvențial.

Această metrică măsoară robustețea regulilor de decizie, dar nu riscul real al unui portofoliu cu poziții simultane. Următoarea fază va adăuga separat un `daily_equity_curve` și un `portfolio_max_drawdown_daily`, calculate zilnic din pozițiile active și suprapunerea temporală a tranzacțiilor.
