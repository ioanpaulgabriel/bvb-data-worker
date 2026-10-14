# ADR-0003: Dimensionare dinamica ATR

## Status

Propus

## Context

Metricile actuale evalueaza tranzactiile cu un model simplu, iar portofoliul zilnic foloseste greutati egale pentru pozitiile active. Aceasta abordare nu tine cont de volatilitatea individuala a simbolurilor.

Un simbol cu ATR mare poate genera miscari zilnice mult mai ample decat un simbol cu ATR mic, chiar daca ambele pozitii au aceeasi greutate nominala.

## Decizia

Vom introduce dimensionarea dinamica bazata pe ATR, ca extensie separata a generatorului de metrici.

Formula initiala:

position_size = (equity * risk_per_trade) / (ATR * atr_multiplier)

Parametri initiali:

- risk_per_trade = 0.01, adica 1% din equity.
- atr_period = 14 zile.
- atr_multiplier = 2.0.
- ATR-ul se calculeaza pe seria ajustata de preturi, folosind High, Low si Close.
- ATR-ul folosit este cel din ziua anterioara intrarii, pentru a evita look-ahead bias.
- Pozitia este limitata de capitalul disponibil si de o limita maxima de expunere per simbol.

## Reguli de implementare

- Nu se modifica baseline-ul trade-by-trade existent.
- Se adauga un nou mod de calcul, activabil prin configuratie.
- Fiecare tranzactie va primi campuri suplimentare: atr_value, position_size, risk_amount si allocation_weight.
- Equity curve-ul zilnic va folosi noile greutati de alocare.
- Drawdown-ul trade-by-trade si cel zilnic raman metrici separate.

## Consecinte pozitive

- Riscul per tranzacție devine mai uniform.
- Pozitiile volatile primesc automat dimensiuni mai mici.
- Creeaza baza pentru o limita reala de expunere pe portofoliu.

## Consecinte negative

- Este necesara validarea atenta a seriei ATR.
- Rezultatele istorice se vor schimta fata de baseline-ul actual.
- Trebuie definit clar ce se intampla cand ATR lipseste sau este zero.
