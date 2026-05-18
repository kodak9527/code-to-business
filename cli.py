#!/usr/bin/env python3
"""
code-to-business CLI — one-command pipeline for OpenCode

Usage:
  python cli.py run --target /path/to/java/project --config config.yaml
  python cli.py run --target /path/to/java/project --config config.yaml --verify
  python cli.py run --target /path/to/SomeController.java --config config.yaml
  python cli.py step 1 --target /path/to/project            # collector only
  python cli.py step 2 --config config.yaml                   # llm only (needs file_groups.json)
  python cli.py step 3                                        # aggregator only
  python cli.py step 4 --output 业务文档.html                  # html only
  python cli.py step 5                                        # verify only
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"
OUTPUT_DIR = Path.cwd() / "output"


def run_step(step_name: str, cmd: list[str]) -> bool:
    """Run a pipeline step and report result."""
    print(f"\n{'='*60}")
    print(f"  STEP: {step_name}")
    print(f"  CMD:  {' '.join(cmd)}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(cmd, cwd=str(SCRIPTS_DIR))
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"  ❌ FAILED ({elapsed:.1f}s)")
        return False
    print(f"  ✅ DONE ({elapsed:.1f}s)")
    return True


def cmd_run(args):
    """Full pipeline: collector → llm → aggregator → html [→ verify]"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    fg = str(OUTPUT_DIR / "file_groups.json")
    an = str(OUTPUT_DIR / "analysis_output.json")
    fm = str(OUTPUT_DIR / "final_model.json")
    html_out = args.output or str(OUTPUT_DIR / "business_doc.html")

    steps = [
        ("1/5 Collector — 收集 Java 文件",
         ["python3", "collector.py", "--target", args.target, "--mode", "deep", "--output", fg]),
        ("2/5 LLM Analyzer — 业务语义分析",
         ["python3", "llm_analyzer.py", "--config", args.config, "--input", fg, "--output", an]),
        ("3/5 Aggregator — 聚合数据模型",
         ["python3", "aggregator.py", "--input", an, "--output", fm]),
        ("4/5 HTML Assembler — 生成文档",
         ["python3", "html_assembler.py", "--model", fm, "--output", html_out]),
    ]

    if args.verify:
        steps.append(("5/5 Verifier — 完整性验证",
                       ["python3", "verifier.py", "--input", fm]))

    results = []
    for name, cmd in steps:
        ok = run_step(name, cmd)
        results.append(ok)
        if not ok:
            print(f"\n⚠️  Pipeline stopped at: {name}")
            break

    passed = sum(results)
    total = len(results)
    print(f"\n{'='*60}")
    print(f"  PIPELINE: {passed}/{total} steps passed")
    print(f"  OUTPUT:   {OUTPUT_DIR}/")
    if html_out:
        print(f"  HTML:     {html_out}")
    print(f"{'='*60}")


def cmd_step(args):
    """Run a single pipeline step."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    step_cmds = {
        1: ("collector", ["python3", "collector.py", "--target", args.target,
                           "--mode", args.mode or "deep",
                           "--output", str(OUTPUT_DIR / "file_groups.json")]),
        2: ("llm_analyzer", ["python3", "llm_analyzer.py", "--config", args.config,
                              "--input", str(OUTPUT_DIR / "file_groups.json"),
                              "--output", str(OUTPUT_DIR / "analysis_output.json")]),
        3: ("aggregator", ["python3", "aggregator.py",
                            "--input", str(OUTPUT_DIR / "analysis_output.json"),
                            "--output", str(OUTPUT_DIR / "final_model.json")]),
        4: ("html_assembler", ["python3", "html_assembler.py",
                                "--model", str(OUTPUT_DIR / "final_model.json"),
                                "--output", args.output or str(OUTPUT_DIR / "business_doc.html")]),
        5: ("verifier", ["python3", "verifier.py",
                          "--input", str(OUTPUT_DIR / "final_model.json")]),
    }

    if args.num not in step_cmds:
        print(f"❌ Unknown step: {args.num}. Valid: 1-5")
        sys.exit(1)

    name, cmd = step_cmds[args.num]
    ok = run_step(f"Step {args.num} — {name}", cmd)
    sys.exit(0 if ok else 1)


def main():
    parser = argparse.ArgumentParser(description="code-to-business — Java → Business Doc")
    sub = parser.add_subparsers(dest="command")

    # run (full pipeline)
    p_run = sub.add_parser("run", help="Run full pipeline")
    p_run.add_argument("--target", required=True, help="Java project directory or file")
    p_run.add_argument("--config", required=True, help="Path to config.yaml")
    p_run.add_argument("--output", help="HTML output path (default: output/business_doc.html)")
    p_run.add_argument("--verify", action="store_true", help="Run verifier after HTML generation")
    p_run.set_defaults(func=cmd_run)

    # step (single step)
    p_step = sub.add_parser("step", help="Run a single pipeline step (1-5)")
    p_step.add_argument("num", type=int, choices=[1, 2, 3, 4, 5])
    p_step.add_argument("--target", help="Java project path (required for step 1)")
    p_step.add_argument("--config", help="Config path (required for step 2)")
    p_step.add_argument("--mode", choices=["overview", "deep"], help="Collector mode (step 1)")
    p_step.add_argument("--output", help="Output path (step 4)")
    p_step.set_defaults(func=cmd_step)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
