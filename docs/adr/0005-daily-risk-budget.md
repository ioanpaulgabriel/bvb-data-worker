# ADR-0005: Buget de risc zilnic pe portofoliu

## Status

Acceptata

Propus

## Context

Portofoliul are deja limite de expunere totala, expunere per simbol si numar maxim de pozitii simultane.

Totusi, aceste limite nu garanteaza o pierdere maxima intr-o singura zi. Mai multe pozitii corelate pot genera in aceeasi zi o pierdere semnificativa, chiar daca fiecare pozitie are un risc individual limitat.

## Decizia

Vom defini un buget de risc zilnic pentru portofoliu:

- Pierdere maxima acceptata intr-o zi: 2% din equity.
- Riscul zilnic estimat este suma riscurilor monetare ale pozitiilor active.
- Riscul monetar al unei pozitii este distanta pana la stop, exprimata in procent din equity.
- Daca riscul zilnic estimat depaseste bugetul, noile tranzactii nu mai primesc alocare ATR pana cand riscul estimat revine sub limita.
- Pozitiile deja deschise nu sunt inchise automat de generatorul de metrici.
- Generatorul va calcula si publica daily_risk_used si daily_risk_remaining.

## Reguli de implementare

- Riscul zilnic se calculeaza la deschiderea fiecarei noi tranzactii.
- Se folosesc doar pozitiile active in acea zi.
- Riscul unei pozitii este: allocation_weight * stop_distance / entry_price.
- Bugetul initial este 2% din equity.
- Limita este un mecanism de prevenire, nu o comanda de vanzare.
- Baseline-ul trade-by-trade si equity-ul equal-weight raman neschimbate.

## Consecinte pozitive

- Limiteaza pierderea maxima estimata intr-o zi.
- Creeaza o regula clara pentru alerte.
- Previne suprascrierea risk budget-ului de catre mai multe semnale simultane.
- Pregateste integrarea cu Home Assistant.

## Consecinte negative

- Unele semnale valide pot fi ignorate in zilele cu risc ridicat.
- Este necesara validarea separata a riscului estimat fata de pierderea reala zilnica.
- Bugetul de 2% trebuie revizuit dupa colectarea unui istoric mai lung.
