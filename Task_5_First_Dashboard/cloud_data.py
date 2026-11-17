from pathlib import Path
import pandas as pd
import streamlit as st

# Project root and public Parquet export folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "cloud_data_parquet"

@st.cache_data(ttl=300)
def load_parquet(dataset_name: str) -> pd.DataFrame:
    """
    Load an exported Parquet dataset by its view/table name.
    Example: load_parquet("metric_m01_headcount")
    """
    if not dataset_name or Path(dataset_name).name != dataset_name:
        raise ValueError("Invalid dataset name.")

    file_path = DATA_DIR / f"{dataset_name}.parquet"

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Parquet dataset not found: {file_path.name}"
        )

    return pd.read_parquet(file_path, engine="pyarrow")


def clear_parquet_cache():
    load_parquet.clear()
