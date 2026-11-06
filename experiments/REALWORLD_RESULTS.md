# Real-life tests (ground truth not produced by an LLM)

## Test 1: does the tagger find the writers' episode-ending cliffhanger? (last 8s)

| tagger | episodes hit | random-tagger expectation | one-sided p |
|---|---|---|---|
| v2: gemini-3.1-flash-lite (free) | 47/50 = 94% (95% CI 84%-98%) | 18% | 2.2e-31 |
| v3: vertex gemini-3.5-flash | 41/50 = 82% (95% CI 69%-90%) | 26% | 1.3e-16 |

A hit means the model independently labelled a beat inside the writers' final beat window as a cliffhanger. The writers' intent is the ground truth here.

## Test 2: planted hooks in 29 real episodes (tagger: `vertex/gemini-3.5-flash`)

| metric | result | random tagger |
|---|---|---|
| planted shocking line tagged as a hook | 26/29 = 90% (95% CI 74%-96%) | 13% |
| neutral decoy tagged as a hook | 0/29 = 0% (95% CI 0%-12%) | 13% |
| a final candidate window starts on the planted hook | 25/29 = 86% (95% CI 69%-95%) | - |

Recall vs random: one-sided p = 2.8e-20. The plant competes with every real hook in the episode (up to 6 hooks are tagged), so recall below 100% can mean the episode already had stronger moments, not a miss. Decoy false positives are a clean error rate.
