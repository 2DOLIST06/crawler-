from pathlib import Path
import pandas as pd


def export_csv(path: Path, records: list[dict]) -> None:
    pd.DataFrame(records).to_csv(path, index=False)
