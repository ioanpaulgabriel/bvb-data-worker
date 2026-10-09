# Evenimente corporative si ajustari istorice

## Scop

Acest document descrie modul in care evenimentele corporative sunt importate, verificate si transformate in ajustari istorice.

## Principiul de baza

Datele originale din prices_daily nu se modifica. Ajustarile sunt pastrate separat in price_adjustments si se aplica la calculul unei serii ajustate.

Formula generala:

Adjusted Price = Unadjusted Price * Adjustment Factor

Factorul se aplica datelor anterioare datei ex-date.

## Tipuri de evenimente

- cash_dividend: dividend platit in numerar.
- stock_split: impartirea sau consolidarea actiunilor.
- bonus_issue: distribuirea de actiuni bonus.
- rights_issue: oferta de drepturi, care necesita reguli separate.

## Bonus issue

Pentru un bonus issue cu raportul ratio, factorul pretului este:

factor = 1 / (1 + ratio)

Exemplu: la un raport 1:4, ratio este 0.25, iar factorul este 0.8.

Preturile anterioare datei ex-date se inmultesc cu factorul.

## Split forward

Pentru un split 2-la-1, factorul pretului este 0.5. Preturile istorice dinaintea ex-datei se inmultesc cu 0.5.

Volumul, daca va fi ajustat in viitor, se modifica in directie opusa pretului.

## Consolidare

Pentru o consolidare 1-la-5, pretul istoric se inmulteste cu 5, in functie de reprezentarea folosita pentru raport.

Raportul trebuie documentat explicit in corporate_actions inainte de calcul.

## Dividend cash

Ajustarea proportionala poate folosi formula:

factor = (previous_close - dividend_amount) / previous_close

Aceasta formula necesita previous_close valid si dividend_amount confirmat dintr-o sursa oficiala.

## Statusuri

- pending: eveniment importat, dar neverificat.
- verified: eveniment verificat si eligibil pentru ajustare.
- rejected: eveniment invalid sau neconfirmat.

Numai evenimentele verified pot genera price_adjustments.

## Reguli de siguranta

- Nu ajusta datele raw.
- Nu ajusta datele viitoare sau datele de la ex-date inainte.
- Nu aplica un eveniment pending.
- Pastreaza source_reference pentru fiecare eveniment.
- Verifica rezultatul inainte de publicarea seriei ajustate.

## Audit

Fiecare ajustare trebuie sa poata fi explicata prin simbol, ex-date, tip, factor, sursa si momentul procesarii.
