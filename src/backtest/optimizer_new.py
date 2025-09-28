"""
Refactored optimizer entry point.
Uses the new modular optimization structure.
"""

import argparse
from pathlib import Path

from rich.console import Console

from .optimization import OptimizationRunner


def main():
    """Main entry point for optimization."""
    parser = argparse.ArgumentParser(description="Optimize trading parameters")
    parser.add_argument("--coin", type=str, help="Specific coin to optimize")
    parser.add_argument("--max-combinations", type=int, help="Maximum combinations to test")
    parser.add_argument("--walk-forward", action="store_true", help="Use walk-forward validation")
    parser.add_argument("--folds", type=int, default=3, help="Number of folds for walk-forward")
    parser.add_argument("--config", type=str, help="Path to config file")

    args = parser.parse_args()

    console = Console()

    try:
        # Initialize optimizer
        config_path = args.config or str(
            Path(__file__).resolve().parents[2] / "config" / "config.yaml"
        )
        optimizer = OptimizationRunner(config_path)

        if args.coin:
            # Optimize specific coin
            if args.walk_forward:
                results = optimizer.run_walk_forward_optimization(args.coin, args.folds)
            else:
                results = optimizer.optimize_coin(args.coin, args.max_combinations)
        else:
            # Optimize all coins
            _ = optimizer.optimize_all_coins(args.max_combinations)

        console.print("[green]Optimization completed successfully![/green]")

    except Exception as ex:
        console.print(f"[red]Optimization failed: {ex}[/red]")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
