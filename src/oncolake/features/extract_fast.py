"""Version optimisee (etape 7) : ThreadPoolExecutor (I/O AFDB) + Numba (calculs CA).

TODO etape 7 :
  - paralleliser fetch_cif sur le batch via ThreadPoolExecutor
  - rayon de giration / distances en Numba @njit
  - composition d'AA vectorisee NumPy
Objectif : battre /ingest d'au moins 30 %.
"""
