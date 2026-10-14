# ADR-0004: Limite de expunere pe portofoliu

## Status

Acceptata

Propus

## Context

Dimensionarea ATR atribuie fiecărei tranzactii o greutate proportionala cu riscul tintit si invers proportionala cu volatilitatea.

Fara o limita explicita, mai multe pozitii simultane pot produce o expunere totala excesiva sau o concentrare necontrolata intr-un simbol.

## Decizia

Vom introduce limite separate, aplicate in ordinea deschiderii tranzactiilor:

- Expunere maxima totala: 100% din equity.
- Expunere maxima per simbol: 25% din equity.
- Numar maxim de pozitii simultane: 5.
- Riscul monetar tintit per tranzactie ramane 1% din equity.
- Daca o noua tranzactie ar depasi o limita, dimensiunea ei este redusa la limita disponibila.
- Daca limita disponibila este zero, tranzactia este ignorata in modelul ATR, dar ramane in metricile de baza.

## Reguli de implementare

- Limitele se aplica la deschiderea pozitiei, folosind equity-ul disponibil la acea data.
- Expunerea totala este suma greutatilor pozitiilor active.
- Expunerea per simbol este suma greutatilor pozitiilor active ale acelui simbol.
- Nu se modifica retroactiv pozitiile deja deschise.
- Baseline-ul trade-by-trade si equity-ul equal-weight raman neschimbate.

## Consecinte pozitive

- Previne leverage-ul accidental.
- Limiteaza concentrarea intr-un singur simbol.
- Face ATR Dynamic Sizing compatibil cu un portofoliu real.
- Creeaza o baza clara pentru viitoarea limita de risc zilnic.

## Consecinte negative

- Unele tranzactii pot primi dimensiuni reduse.
- Rezultatele ATR se vor schimba fata de versiunea actuala.
- Este necesara auditarea tranzactiilor reduse sau ignorate.
