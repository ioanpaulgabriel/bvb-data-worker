# Arhitectura proiectului BVB Data Worker

## Scop

Proiectul descarca si valideaza date zilnice BVB.

## Fluxul datelor

BVB CSV -> src/fetch_bvb.py -> prices_daily_raw -> prices_daily -> price_adjustments

## Componente

- src/fetch_bvb.py: descarca si valideaza CSV-ul BVB.
- prices_daily_raw: pastreaza raspunsul original pentru audit.
- prices_daily: pastreaza datele normalizate REGS.
- corporate_actions: pastreaza evenimentele corporative.
- price_adjustments: pastreaza planul de ajustare.

## Statusuri corporate actions

- pending: importat, dar neverificat.
- verified: verificat si disponibil pentru procesare.
- rejected: respins si neprocesabil.

## Starea actuala

Colectarea, validarea, persistenta raw si importul evenimentelor sunt implementate. Aplicarea efectiva a ajustarilor nu este inca implementata.
