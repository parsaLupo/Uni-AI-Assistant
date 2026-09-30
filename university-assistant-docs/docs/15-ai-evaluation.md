# 15 — AI Evaluation Plan

## 1. Why evaluation matters

A chatbot can sound correct while citing the wrong regulation or inventing details. Evaluation therefore separates retrieval quality from generation quality.

## 2. Evaluation categories

### Retrieval

- source relevance
- top-k usefulness
- correct document version
- page/section alignment

### Generation

- factual consistency with retrieved evidence
- citation correctness
- completeness
- refusal/insufficiency behavior
- language quality

## 3. Golden dataset

Create at least a small representative set for:

- regulations
- course prerequisites
- exam schedule
- academic calendar
- professors
- hybrid queries
- unsupported questions

## 4. Regression rule

When prompts, embeddings, models, chunking, or retrieval parameters change, rerun the golden dataset and compare results before release.
