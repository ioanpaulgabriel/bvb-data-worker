# ADR-0001: Pastrarea datelor brute inainte de normalizare

## Status

Acceptata

## Context

Datele BVB pot avea modificari de format, coloane lipsa, valori invalide sau raspunsuri care nu sunt CSV. Daca pastram numai datele transformate, investigarea si reimportul devin dificile.

## Decizia

Salvam raspunsul original BVB in prices_daily_raw inainte de validare si normalizare.

Aplicatia poate produce apoi date curatate in prices_daily, dar payload-ul original ramane neschimbat.

## Consecinte pozitive

- Putem audita exact raspunsul primit.
- Putem reexecuta parserul dupa o corectie.
- Putem compara versiuni diferite ale parserului.
- Erorile de import pot fi investigate fara recontactarea sursei.

## Consecinte negative

- Baza de date necesita mai mult spatiu.
- Payload-ul raw poate contine formatari sau date care trebuie protejate.
- Este necesara o politica de retentie si backup.

## Reguli

- prices_daily_raw este append-only, cu exceptia operatiilor administrative documentate.
- Normalizarea nu modifica payload-ul original.
- Orice corectie se face printr-un nou proces de import sau printr-o migratie documentata.
