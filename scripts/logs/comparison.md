# Comparaison de performance -- /ingest vs /ingest_fast

_Genere le 2026-07-08T20:40:41+00:00_

| Variante | Temps (s) | Proteines | Structures | Debit (prot/s) | Workers |
|---|---|---|---|---|---|
| `ingest` (naif, sequentiel) | 53.81 | 418 | 414 | 7.8 | 1 |
| `ingest_fast` (ThreadPool) | 11.56 | 418 | 414 | 36.2 | 16 |

- **Acceleration : x4.66**
- **Gain de performance : 78.5 %**
