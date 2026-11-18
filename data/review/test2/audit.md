# test2: independent-model audit

Oracle mode (passages + claim texts only). Agreement with the draft gold:

- **qwen3.8-max**: 126/131 = 0.962; disagreements {'C->S': 2, 'S->C': 1, 'U->S': 1, 'S->U': 1}
- **kimi-k3**: 127/131 = 0.969; disagreements {'C->S': 2, 'U->S': 2}

6 claims with at least one disagreement.

## Disagreements

### test2-git-gc-distortion c10: gold C
> By default the commit-graph is rewritten on every git gc run.

- qwen3.8-max: **S** Passage [5] states that if gc.writeCommitGraph is true, gc will rewrite the commit-graph file when git-gc is run, and the default is true.
- kimi-k3: **S** gc.writeCommitGraph defaults to true, and when true gc rewrites the commit-graph file whenever git-gc is run.

### test2-git-gc-natural c18: gold S
> When git gc runs concurrently with a writing process, it may delete an object that process created but has not yet referenced.

- qwen3.8-max: **C** Passage [9] states the risk is deleting an object that the other process 'is using but hasn't created a reference to', not an object that the process 'created'.
- kimi-k3: **S** Passage [9] describes the risk of git gc deleting an object a concurrent process is using but has not yet referenced.

### test2-git-gc-natural c21: gold U (contestable)
> Using --prune=now significantly raises the danger of corruption.

- qwen3.8-max: **S** Passage [1] states that --prune=now prunes loose objects regardless of age and increases the risk of corruption if another process is writing concurrently.
- kimi-k3: **S** Passage [1] says --prune=now prunes regardless of age and increases the risk of corruption when another process writes concurrently.

### test2-http-caching-multipassage c5: gold C
> A private cache holding a stale response marked proxy-revalidate may reuse it without revalidating.

- qwen3.8-max: **S** Passage [6] states that proxy-revalidate is analogous to must-revalidate except that it does not apply to private caches. Therefore, a private cache is not bound by proxy-revalidate and may reuse the stale response without revalidating.
- kimi-k3: **S** proxy-revalidate requires shared caches to revalidate stale responses before reuse, but the passages state it does not apply to private caches, so a private cache is not bound by that revalidation requirement.

### test2-http-caching-natural c9: gold S (contestable)
> no-store is stricter than no-cache.

- qwen3.8-max: **U** While one could infer from the passages that no-store prevents storage entirely while no-cache allows storage but requires revalidation, the passages never explicitly compare the two directives or state that one is 'stricter' than the other.
- kimi-k3: **S** no-store ([9]) forbids storing any part of the request/response and forbids reuse unconditionally, whereas the no-cache response directive ([8]) only forbids reuse absent successful validation; hence no-store is strictly more restrictive.

### test2-http-caching-natural c19: gold U (contestable)
> Together these directives give fine-grained control over storage, revalidation and freshness for different classes of cache.

- qwen3.8-max: **U** The passages describe individual directives but never make a collective statement about them providing 'fine-grained control over storage, revalidation and freshness for different classes of cache'. This is an editorial summary not found in the text.
- kimi-k3: **S** The passages collectively present directives governing revalidation (must-revalidate), storage (no-store), cache classes (shared vs private via private), and freshness lifetime overrides for shared caches (s-maxage), which together provide differentiated control over storage, revalidation and freshn

