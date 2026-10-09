# Diagnosticarea problemelor

## CSV lipsa sau gol

- Verifica daca BVB a raspuns cu status HTTP valid.
- Verifica dimensiunea fisierului din data/raw/.
- Deschide primele randuri ale fisierului cu head.
- Confirma ca raspunsul este CSV si nu o pagina HTML de eroare.

## Coloane lipsa

- Compara antetul CSV cu lista de coloane asteptate.
- Nu importa datele pana cand formatul nu este clarificat.

## Valori numerice invalide

- Identifica randul si simbolul problematic.
- Pastreaza fisierul raw pentru investigatie.
- Corecteaza parserul numai dupa confirmarea formatului BVB.

## Low mai mare decat High

- Marcheaza randul ca invalid.
- Nu modifica manual valorile.
- Verifica fisierul original si logurile importului.

## Date duplicate

- Verifica cheia trade_date, symbol si source.
- Nu sterge automat duplicatele.
- Determina daca sunt surse diferite sau reimporturi.

## Eroare PostgreSQL

- Verifica daca serviciul PostgreSQL ruleaza.
- Verifica variabilele de conexiune.
- Verifica daca migrarile au fost aplicate.
- Verifica permisiunile utilizatorului bazei de date.

## Date deja importate

- Verifica daca importul este idempotent.
- Nu duplica randurile la rerulare.
- Compara numarul de randuri inainte si dupa rerulare.

## Regula generala

Nu sterge datele raw inainte de finalizarea investigatiei.
