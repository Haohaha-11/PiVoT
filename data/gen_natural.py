"""Generate 'natural' answers for the test split with a model that is NOT the verifier's base model.
The generator may add background knowledge, so realistic extrinsic content appears.
Output: data/natural_answers.json (answers are then hand-labelled in data/build.py).

    python -m data.gen_natural --model glm-5.3 [--split test2]
"""
import argparse
import json
import pathlib

from verifier.llm import OpenAICompatLLM

ROOT = pathlib.Path(__file__).resolve().parent
JOBS = [
    {"id": "test-sqlite-limits-natural", "refs": ["sqlite_limits:5", "sqlite_limits:8", "sqlite_limits:12", "sqlite_limits:13",
                                                 "sqlite_limits:15", "sqlite_limits:19", "sqlite_limits:23", "sqlite_limits:25", "sqlite_limits:27"],
     "q": "What default limits in SQLite should I know about when designing a schema and writing queries?"},
    {"id": "test-redis-replication-natural", "refs": ["redis_replication:2", "redis_replication:3", "redis_replication:6", "redis_replication:11",
                                                     "redis_replication:37", "redis_replication:38", "redis_replication:39", "redis_replication:40", "redis_replication:54"],
     "q": "How does Redis replication deal with consistency and data loss, and what should I watch out for?"},
    {"id": "test-k8s-probes-natural", "refs": ["k8s_probes:1", "k8s_probes:6", "k8s_probes:13", "k8s_probes:16", "k8s_probes:19",
                                              "k8s_probes:20", "k8s_probes:21", "k8s_probes:22", "k8s_probes:23"],
     "q": "How should I configure liveness, readiness and startup probes for a service that starts slowly?"},
    {"id": "test-pg-isolation-natural", "refs": ["pg_isolation:2", "pg_isolation:3", "pg_isolation:5", "pg_isolation:16", "pg_isolation:17",
                                                "pg_isolation:20", "pg_isolation:22", "pg_isolation:23", "pg_isolation:27", "pg_isolation:30"],
     "q": "How do PostgreSQL's isolation levels differ, and when should I use Serializable?"},
]
JOBS_TEST2 = [
    {"id": "test2-git-gc-natural", "refs": ["git_gc:1", "git_gc:7", "git_gc:15", "git_gc:17", "git_gc:18", "git_gc:26", "git_gc:28",
                                         "git_gc:29", "git_gc:36", "git_gc:37", "git_gc:39"],
     "q": "How does git gc decide when to run automatically and what does it prune? What risks should I know about?"},
    {"id": "test2-http-caching-natural", "refs": ["http_caching:52", "http_caching:60", "http_caching:61", "http_caching:62", "http_caching:115",
                                                 "http_caching:118", "http_caching:123", "http_caching:124", "http_caching:128", "http_caching:133",
                                                 "http_caching:137", "http_caching:144"],
     "q": "What do no-cache, no-store, must-revalidate, private and s-maxage mean for HTTP caches, and how is freshness determined?"},
]
SPLITS = {"test": (JOBS, "natural_answers.json"), "test2": (JOBS_TEST2, "natural_answers_test2.json")}
SYSTEM = ("You are a helpful database and infrastructure expert answering questions for engineers. Use the provided "
          "documentation passages, and feel free to add useful details from your own knowledge. Answer in one paragraph "
          "of 6-8 sentences, plain prose, no lists.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="glm-5.3")
    ap.add_argument("--split", default="test", choices=sorted(SPLITS))
    args = ap.parse_args()
    jobs, out_name = SPLITS[args.split]
    llm = OpenAICompatLLM(model=args.model, json_mode=False, timeout_s=300, max_retries=2)
    out = []
    for job in jobs:
        passages = [json.loads((ROOT / "sources" / f"{r.split(':')[0]}.json").read_text())["paragraphs"][int(r.split(":")[1])]
                    for r in job["refs"]]
        ctx = "\n\n".join(f"[{i}] {p}" for i, p in enumerate(passages))
        c = llm.complete([{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": f"Documentation:\n{ctx}\n\nQuestion: {job['q']}"}])
        out.append({**job, "generator": args.model, "answer": c.text.strip()})
        print(job["id"], "\n", c.text.strip(), "\n", flush=True)
    (ROOT / out_name).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
