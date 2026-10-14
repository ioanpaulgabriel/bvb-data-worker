# ADR-0002: Drawdown zilnic al portofoliului

## Status

Propus

## Context

Metricile actuale calculeaza equity trade-by-trade, secvential. Aceasta abordare masoara robustetea regulilor de decizie, dar nu riscul real al unui portofoliu cu mai multe pozitii deschise simultan.

Baseline-ul dinamic actual are 43 de tranzactii si 5 stopuri, inclusiv o concentrare de pierderi in februarie-martie 2022. Un calcul zilnic poate evidentia corect suprapunerea temporala a acestor pozitii.

## Decizia

Vom adauga un calcul separat, fara a inlocui metricile trade-by-trade:

- daily_equity_curve: valoarea portofoliului la inchiderea fiecarei zile de tranzactionare.
- portfolio_max_drawdown_daily: scaderea maxima fata de varful anterior al equity-ului zilnic.
- Pozitiile deschise sunt evaluate la pretul de inchidere al zilei.
- Stopurile intraday raman parte din simularea tranzactiilor.
- Comisioanele si costurile existente se aplica la intrare si iesire, conform regulilor deja implementate.
- Zilele fara preturi disponibile nu modifica equity-ul; ultima valoare cunoscuta ramane valabila.

## Reguli de implementare

- Nu se modifica baseline-ul trade-by-trade existent.
- Metricile zilnice se adauga ca campuri separate in JSON-ul generat.
- Fiecare punct din equity curve trebuie sa poata fi explicat prin tranzactiile active in acea zi.
- Drawdown-ul zilnic nu trebuie comparat direct cu drawdown-ul trade-by-trade, deoarece masoara riscuri diferite.

## Consecinte pozitive

- Masoara riscul real al portofoliului.
- Evidentiaza pierderile simultane din tranzactiile suprapuse.
- Creeaza baza corecta pentru ATR Dynamic Sizing si pentru limita de expunere pe portofoliu.

## Consecinte negative

- Implementarea este mai complexa decat calculul secvential.
- Este nevoie de o definitie clara a capitalului alocat si a pozitiilor simultane.
