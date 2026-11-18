# test2: independent-model audit

Oracle mode (passages + claim texts only). Agreement with the draft gold:

- **qwen3.8-max**: 134/141 = 0.950; disagreements {'C->S': 2, 'S->C': 1, 'U->S': 3, 'S->U': 1}
- **kimi-k3**: 135/141 = 0.957; disagreements {'C->S': 2, 'U->S': 3, 'S->U': 1}

7 claims with at least one disagreement.

## Disagreements

### test2-git-gc-distortion c10: gold C (contestable)
> By default the commit-graph is rewritten on every git gc run.

- qwen3.8-max: **S** Passage [6] states that if gc.writeCommitGraph is true (which is the default), gc will rewrite the commit-graph file when git-gc is run.
- kimi-k3: **S** Passage [6] states that when gc.writeCommitGraph is true, gc rewrites the commit-graph file whenever git-gc is run, and the default is true.

### test2-git-gc-natural c18: gold S (contestable)
> When git gc runs concurrently with a writing process, it may delete an object that process created but has not yet referenced.

- qwen3.8-max: **C** Passage [9] states the risk is deleting an object that the other process 'is using but hasn't created a reference to', not an object that the process 'created' but hasn't referenced.
- kimi-k3: **S** Passage [9] describes the risk of git gc deleting an object another concurrent process is using but has not yet referenced.

### test2-git-gc-natural c21: gold U (contestable)
> Using --prune=now significantly raises the danger of corruption.

- qwen3.8-max: **S** Passage [1] states that --prune=now prunes loose objects regardless of age and increases the risk of corruption if another process is writing concurrently.
- kimi-k3: **S** Passage [1] says --prune=now increases the risk of corruption when another process writes concurrently.

### test2-git-gc-natural c26: gold U (contestable)
> Git has mitigating features beyond the two-week grace period.

- qwen3.8-max: **S** Passage [9] mentions that 'Git has two features that significantly mitigate this problem', indicating mitigating features beyond just the grace period discussed in passage [5].
- kimi-k3: **S** Passage [9] says Git has two features that mitigate the concurrent-deletion problem, and [5] identifies the grace period as one such feature, implying at least one further mitigating feature beyond it.

### test2-http-caching-multipassage c5: gold C (contestable)
> A private cache holding a stale response marked proxy-revalidate may reuse it without revalidating.

- qwen3.8-max: **S** Passage [6] states that proxy-revalidate is analogous to must-revalidate except that it does not apply to private caches. Therefore, a private cache is not bound by it and may reuse the stale response without revalidating.
- kimi-k3: **S** proxy-revalidate's revalidation requirement applies to shared caches only and explicitly does not apply to private caches, so a private cache is not bound by it to revalidate before reuse.

### test2-http-caching-natural c2: gold U (contestable)
> Explicit expiration times reflect the server's belief that the representation will not change significantly before then.

- qwen3.8-max: **S** Passage 0 explains that origin servers assign future explicit expiration times believing the representation won't change significantly before then.
- kimi-k3: **S** Passage 0 says origin servers assign future explicit expiration times in the belief that the representation is not likely to change in a semantically significant way before then.

### test2-http-caching-natural c9: gold S (contestable)
> no-store is stricter than no-cache.

- qwen3.8-max: **U** While one could infer from the passages that no-store prevents storage entirely while no-cache allows storage but requires revalidation, the passages never explicitly compare them or state that one is 'stricter' than the other.
- kimi-k3: **U** The passages define no-store and no-cache separately but never compare them or state that one is stricter than the other.

