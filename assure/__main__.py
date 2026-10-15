"""Command-line entry point.

  python -m assure run      --config config.yaml   # run the experiment (resumable)
  python -m assure score    --config config.yaml   # compute metrics (resumable)
  python -m assure analyze  --config config.yaml   # statistics and LaTeX macros
  python -m assure plan     --config config.yaml   # print the experiment size
"""
import argparse
import copy

import yaml

DEFAULTS = {
    "campaign": "pilot", "output_dir": "results", "seed": 2026, "runs": 3,
    "conditions": ["SV", "A", "B", "AB", "ABp"], "workers": 4, "scoring_workers": 4,
    "max_hidden": None, "hypothesis_max_examples": 100, "scoring_max_examples": 50,
    "scoring_mutants": 30,
    "budgets": {"self_rounds": 5, "cex_rounds": 3, "inner_repair_rounds": 2,
                "max_counterexamples": 5, "phase_b_mutants": 30, "phase_b_survivors_shown": 6},
}


def load_config(path):
    cfg = copy.deepcopy(DEFAULTS)
    with open(path) as f:
        user = yaml.safe_load(f) or {}
    budgets = dict(cfg["budgets"], **user.pop("budgets", {}))
    cfg.update(user)
    cfg["budgets"] = budgets
    if "ABp" in cfg["conditions"] and "verifier_alt" not in cfg["models"]:
        raise SystemExit("condition ABp requires models.verifier_alt")
    return cfg


def main():
    ap = argparse.ArgumentParser(prog="assure")
    ap.add_argument("command", choices=["run", "score", "analyze", "plan"])
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    if args.command == "plan":
        from .pipeline import load_all_tasks
        tasks = load_all_tasks(cfg)
        n_units = len(tasks) * cfg["runs"]
        print(f"{len(tasks)} tasks, {cfg['runs']} runs, {n_units} units, "
              f"{n_units * len(cfg['conditions'])} condition executions")
    elif args.command == "run":
        from .pipeline import run_campaign
        run_campaign(cfg)
    elif args.command == "score":
        from .scoring import score_campaign
        score_campaign(cfg)
    else:
        from .analyze import analyze_campaign
        analyze_campaign(cfg)


if __name__ == "__main__":
    main()
