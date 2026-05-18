# AGENTS.md — OpenCode Instructions

## What This Repo Does

`code-to-business` transforms a Java codebase into business documentation that non-engineers can read. HTML output with Mermaid sequence diagrams and flowcharts.

## Pipeline (5 steps)

```
Java Source ──▶ collector.py ──▶ llm_analyzer.py ──▶ aggregator.py ──▶ html_assembler.py ──▶ business_doc.html
                                  (needs LLM API)
```

## How To Use (one-liner)

```bash
python cli.py run --target /path/to/java/project --config config.yaml
```

Or step by step:

```bash
# 1. Collect Java files & group by feature cluster
python scripts/collector.py --target /path/to/project --output file_groups.json

# 2. LLM business analysis (requires config.yaml with API credentials)
python scripts/llm_analyzer.py --config config.yaml --input file_groups.json --output analysis.json

# 3. Aggregate results into final model
python scripts/aggregator.py --input analysis.json --output final_model.json

# 4. Generate HTML document
python scripts/html_assembler.py --model final_model.json --output 业务文档.html

# 5. (Optional) Self-verify completeness
python scripts/verifier.py --input final_model.json
```

## Prerequisites

- Python 3.10+
- LLM API access (OpenAI-compatible endpoint)
- `config.yaml` based on `config.example.yaml`

## Config Setup

```bash
cp config.example.yaml config.yaml
# Edit: base_url, api_key, model
```

## What You Should Do When Asked

When the user says "analyze this Java project" or "generate business docs from this code":
1. First check if `config.yaml` exists and has valid settings
2. If not, guide the user through config setup
3. Run the pipeline (one-liner or step by step)
4. Report results: how many files analyzed, what business modules were found
5. Point to the generated HTML in the output directory

## Important Notes

- All scripts are standalone Python files — no framework, no dependencies beyond stdlib
- The LLM step calls an OpenAI-compatible API — make sure base_url is accessible
- For large projects (>100 files), the analysis step will be slow — tell the user upfront
