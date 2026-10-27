
## Sistem de risc post-eveniment (Event Risk Guard)

Flux:
1. `market_events` — evenimente corporate (earnings, contracte, legal) ingestionate din feed-uri BVB.
2. `v_market_event_windows` — view care calculează fereastra de risc (`block_days=5`, `peer_propagate`) și `is_blocked` pe zi.
3. `src/live_signal_generator.py` — generează zilnic `output/live_signal_status.json` cu simbolurile blocate (deduplicate).
4. `src/check_trade_allowed.py SYMBOL` — interfață de decizie: returnează JSON `allowed`/`blocked` înainte de deschiderea unei poziții.
5. `src/auto_exit_blocked.py` — detectează pozițiile deschise (`strategy_trades` cu `exit_date >= azi`) pe simboluri blocate și salvează `output/auto_exit_status.json`.

Automatizare (cron, zile lucrătoare):
- 08:30 — regenerare status blocare (`live_signal_generator.py`)
- 08:35 — verificare expunere portofoliu (`auto_exit_blocked.py`)

Log: `logs/cron.log`.

## Integrare Home Assistant (MQTT)

- Publisher: `src/mqtt_publisher.py` — publică pe `homelab/bvb-info/risk/status` (retain, QoS 1).
- Senzor HA: `sensor.bvb_event_risk_guard` — stare = blocked_count, atribute: date, blocked_symbols, exposed_count, exposed_symbols.
- Automatizare: alertă `notify.persistent_notification` dacă `exposed_count > 0`.
- Cron: 08:40 zile lucrătoare, după generator (08:30) și verificare expunere (08:35).
