"""Loaders for the Tidewell data pack.

Only 01_income_statement_monthly_actuals.csv was provided as a file. Everything under
data/pack/ is hand-encoded from the summary tables in the PDF, and each file names the
appendix it came from.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PACK_DIR = DATA_DIR / "pack"

INCOME_STATEMENT_FILE = "01_income_statement_monthly_actuals.csv"


def _parse_money(series: pd.Series) -> pd.Series:
    """'$1,234.00' / '-$5.00' -> float."""
    return series.astype(str).str.replace(r"[$,]", "", regex=True).astype(float)


@lru_cache
def income_statement() -> pd.DataFrame:
    """Monthly P&L actuals, Oct 2024 - Sep 2026, indexed by 'YYYY-MM'."""
    df = pd.read_csv(DATA_DIR / INCOME_STATEMENT_FILE)
    for col in df.columns[1:]:
        df[col] = _parse_money(df[col])
    return df.set_index("month")


@lru_cache
def quarterly(name: str) -> pd.DataFrame:
    """A quarterly table from data/pack/<name>.csv, indexed by quarter label."""
    df = pd.read_csv(PACK_DIR / f"{name}.csv")
    return df.set_index(df.columns[0])


@lru_cache
def pack(name: str):
    """A YAML file from data/pack/<name>.yaml."""
    with open(PACK_DIR / f"{name}.yaml") as f:
        return yaml.safe_load(f)


def company() -> dict:
    return pack("company")


def questions() -> list[dict]:
    return pack("questions")


def question(qid: int) -> dict:
    return next(q for q in questions() if q["id"] == qid)


def investor_profiles() -> dict:
    return pack("investor_profiles")


def sources() -> list[dict]:
    return pack("sources")


def glossary() -> dict:
    return pack("glossary")
