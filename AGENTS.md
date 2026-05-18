# AGENTS.md — OpenCode Project Context

## What This Is

`code-to-business` transforms Java code into business documentation with Mermaid diagrams. HTML output that non-engineers can read.

## How To Use

When asked to analyze a Java project, follow the SKILL.md instructions (loaded by OpenCode automatically).

Quick reference:

| Step | Command |
|------|---------|
| 1. Collect | `python scripts/collector.py --target <path> --mode deep --output output/file_groups.json` |
| 2. Analyze | **You do this** — use your LLM with `references/prompt_template.md`, save each cluster as `output/analyses/<id>.md` |
| 3. Parse | `python scripts/parse_analysis.py --dir output/analyses --groups output/file_groups.json --output output/analysis_results.jsonl` |
| 4. HTML | `python scripts/aggregator.py --results output/analysis_results.jsonl --output output/final_model.json && python scripts/html_assembler.py --model output/final_model.json --output output/business_doc.html` |
| 5. Verify | `python scripts/verifier.py --input output/final_model.json` |

## Key Rules

- Analysis output goes to **`.md` files** (not JSON) — `parse_analysis.py` handles conversion
- call_chain format: `→` arrows with indentation
- For large projects, batch ~10 clusters per turn
