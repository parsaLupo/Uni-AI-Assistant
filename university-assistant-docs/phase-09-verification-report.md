# Phase 09 Verification Report

## Scope
Deterministic/mock-based Phase 09 verification. No live Groq API call was performed.

## Test commands and results
- `cd backend && .venv\Scripts\python -m pytest apps/ai/tests/test_phase09.py -q` → exit code 0, 40 passed.
- `cd backend && .venv\Scripts\python -m pytest -q` → exit code 0, 188 passed.

## Routing coverage
- STRUCTURED: `امتحان درس X چه زمانی است؟`
- RAG: `شرایط مشروطی چیست؟`
- HYBRID: `با توجه به آیین‌نامه و دروس پاس‌شده من چه درس‌هایی را می‌توانم بردارم؟`
- GENERAL: `هواشناسی چیست؟`
- OUT_OF_SCOPE: `مریخ`

## Structured-only path
- Test: `Phase09PathTests.test_structured_path_does_not_retrieve`
- Result: structured service called, retrieval not called, no sources returned.

## RAG-with-sources
- Test: `Phase09PathTests.test_rag_path_returns_sources`
- Result: RAG mode, one source returned, answer contains `[1]`.

## Hybrid merging
- Test: `Phase09PathTests.test_hybrid_path_combines_structured_and_retrieved`
- Result: structured facts and retrieved sources both supplied to prompt; one source returned.

## Empty-evidence refusal
- Test: `Phase09PathTests.test_empty_evidence_refuses`
- Result: `insufficient_evidence=true`, Persian refusal message present.

## Citation integrity
- Test: `Phase09SecurityAndProviderTests.test_citation_integrity`
- Result: invalid citation marker `[999]` removed; valid `[1]` retained.

## Prompt injection
- Test: `Phase09InjectionTests.test_prompt_contains_untrusted_delimiters`
- Result: prompt includes system rules, untrusted delimiters, and retrieved content.
- Limitation: prompt-level controls and citation validation only; not a complete guarantee.

## Provider timeout/retry
- Test: `Phase09SecurityAndProviderTests.test_provider_retry_success`
- Result: one HTTP 500 retried, second request succeeded.

## Provider failure
- Tests: `test_provider_outage_maps_to_ai_provider_error`, `test_malformed_provider_output_maps_to_ai_provider_error`
- Result: `AI_PROVIDER_ERROR`, HTTP 503, no internal exception text leaked.

## Golden-set representative report (mock-based)
| Question | Expected | Observed | Source validity | Citation validity | Status |
|---|---|---|---|---|---|
| شرایط مشروطی چیست؟ | RAG with source | RAG with source [1] | Valid | Valid | Pass |
| امتحان درس X چه زمانی است؟ | STRUCTURED, no RAG | STRUCTURED, no retrieval | N/A | N/A | Pass |
| با توجه به آیین‌نامه و دروس پاس‌شده من چه درس‌هایی را می‌توانم بردارم؟ | HYBRID | HYBRID, structured + source | Valid | Valid | Pass |
| شرایط مشروطی چیست؟ with no evidence | Persian refusal | Refusal returned | None | None | Pass |

## Remaining blockers
- OA-05 remains unresolved.
- Mode persistence on message is a Phase 10 dependency.
- SSE streaming remains optional/deferred.
- No live Groq verification was performed.
