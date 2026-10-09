# Modelul de date

## Scop

Acest document descrie tabelele principale ale proiectului si relatiile dintre ele.

## prices_daily_raw

Pastreaza raspunsul original primit de la BVB, fara transformari.

Campuri importante:

- id: identificator unic.
- trade_date: data tranzactiei.
- source: sursa datelor.
- payload: continutul original CSV in format JSONB.
- created_at: momentul importului.

## prices_daily

Pastreaza datele REGS normalizate pentru fiecare simbol si zi de tranzactionare.

Campuri importante:

- id: identificator unic.
- trade_date: data tranzactiei.
- symbol: simbolul instrumentului.
- open: pretul de deschidere.
- low: pretul minim.
- high: pretul maxim.
- close: pretul de inchidere.
- avg_price: pretul mediu.
- ref_price: pretul de referinta.
- source: sursa datelor.

Regula de unicitate recomandata este trade_date, symbol si source.

## corporate_actions

Pastreaza evenimentele corporative asociate unui simbol.

Campuri importante:

- id: identificator unic.
- symbol: simbolul instrumentului.
- action_type: tipul evenimentului.
- ex_date: data ex-event.
- ratio: raportul evenimentului, unde este aplicabil.
- source_reference: documentul sau pagina oficiala.
- status: pending, verified sau rejected.

## price_adjustments

Pastreaza factorii calculati pentru ajustarea istorica a preturilor.

Nu modifica preturile originale din prices_daily.

Pentru un bonus_issue, formula este: factor = 1 / (1 + ratio).

Ajustarea se aplica numai datelor anterioare datei ex-date.
