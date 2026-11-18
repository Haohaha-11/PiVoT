"""Generate 'natural' RAG answers with a model that is NOT in the evaluation pool.
The generator is told it may add background knowledge, so realistic extrinsic
content shows up. Output: natural_answers.json (answers are then hand-labeled in spec_hard.json)."""
import json, os, pathlib, sys
from run import call
ROOT = pathlib.Path(__file__).resolve().parent
src = {n: json.loads((ROOT / "sources" / f).read_text())["paragraphs"] for n, f in {"sqlite": "sqlite_wal.json", "redis": "redis_persistence.json"}.items()}
JOBS = [
    {"id": "natural-01-sqlite-wal-growth", "refs": ["sqlite:16", "sqlite:17", "sqlite:35", "sqlite:36", "sqlite:37", "sqlite:38", "sqlite:39", "sqlite:40", "sqlite:41"],
     "q": "What can make a SQLite WAL file keep growing, and what can an application do to keep it under control?"},
    {"id": "natural-02-redis-rdb-vs-aof", "refs": ["redis:3", "redis:4", "redis:5", "redis:6", "redis:8", "redis:9", "redis:10", "redis:36"],
     "q": "For a production Redis deployment, should I use RDB, AOF, or both? Explain the trade-offs."},
]
SYS = "You are a helpful database expert answering questions for engineers. Use the provided documentation passages, and feel free to add useful details from your own knowledge. Answer in one paragraph of 6-8 sentences, plain prose, no lists."
model = sys.argv[1] if len(sys.argv) > 1 else "glm-5.3"
out = []
for j in JOBS:
    passages = [src[r.split(":")[0]][int(r.split(":")[1])] for r in j["refs"]]
    ctx = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages))
    resp = call(model, [{"role": "system", "content": SYS}, {"role": "user", "content": f"Documentation:\n{ctx}\n\nQuestion: {j['q']}"}], os.environ["DASHSCOPE_API_KEY"], json_mode=False, timeout=300)
    out.append({**j, "generator": model, "answer": resp["choices"][0]["message"]["content"].strip()})
(ROOT / "natural_answers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for o in out: print(o["id"], "\n", o["answer"], "\n")
