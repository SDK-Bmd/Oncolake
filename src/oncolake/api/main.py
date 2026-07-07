from oncolake.ingest.fast import ingest_fast

@app.post("/ingest_fast")
def post_ingest_fast(req: IngestRequest):
    return ingest_fast([item.model_dump() for item in req.items])