import sqlite3
import pandas as pd
from pathlib import Path


def generate_reports(db_path: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    try:
        # P&L Report
        trades_df = pd.read_sql_query("SELECT * FROM trades", conn)
        if not trades_df.empty:
            pnl_report = (
                trades_df.groupby("symbol")
                .agg(
                    total_trades=("symbol", "size"),
                    win_rate=("pnl_pct", lambda x: (x > 0).mean()),
                    avg_pnl_pct=("pnl_pct", "mean"),
                    total_pnl_pct=("pnl_pct", "sum"),
                )
                .reset_index()
            )
            pnl_report.to_csv(output_dir / "pnl_report.csv", index=False)
            print(f"P&L report saved to {output_dir / 'pnl_report.csv'}")

        # Equity Report
        equity_df = pd.read_sql_query("SELECT * FROM equity", conn)
        if not equity_df.empty:
            equity_df["ts"] = pd.to_datetime(equity_df["ts"])
            equity_df = equity_df.set_index("ts")
            drawdown = (equity_df["equity_usd"] / equity_df["equity_usd"].cummax()) - 1
            max_drawdown = drawdown.min()
            equity_report = pd.DataFrame(
                {"max_drawdown": [max_drawdown], "final_equity": [equity_df["equity_usd"].iloc[-1]]}
            )
            equity_report.to_csv(output_dir / "equity_report.csv", index=False)
            print(f"Equity report saved to {output_dir / 'equity_report.csv'}")

    finally:
        conn.close()


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "logs" / "tracker.db"
    output_dir = Path(__file__).parent.parent / "logs" / "reports"
    generate_reports(db_path, output_dir)
