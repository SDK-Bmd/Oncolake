import json, requests

manifest = json.load(open("data/raw/manifest.json"))
items = [{"accession": m["accession"], "sequence": m["sequence"]}
         for m in manifest if m["has_structure"]]

for n in (1, 100):
    payload = {"items": items[:n]}
    t_slow = requests.post("http://localhost:8000/ingest",      json=payload, timeout=600).json()["elapsed_seconds"]
    t_fast = requests.post("http://localhost:8000/ingest_fast", json=payload, timeout=600).json()["elapsed_seconds"]
    gain = 100 * (t_slow - t_fast) / t_slow if t_slow else 0
    print(f"batch {n:3d} : ingest={t_slow:.2f}s  ingest_fast={t_fast:.2f}s  gain={gain:.0f}%")