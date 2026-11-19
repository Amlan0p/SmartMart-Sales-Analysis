"""
data_loader.py

Responsible only for loading the raw sales CSV and validating its basic
structure. No cleaning or analysis logic lives here - see
``preprocessing.py`` and ``analysis.py`` respectively.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import REQUIRED_COLUMNS
from src.utils import get_logger

logger = get_logger(__name__)


class DatasetNotFoundError(FileNotFoundError):
    """Raised when the raw dataset file cannot be located on disk."""


class MissingColumnsError(ValueError):
    """Raised when the dataset is missing one or more required columns."""


class EmptyDatasetError(ValueError):
    """Raised when the loaded dataset contains no rows."""


def validate_columns(dataframe: pd.DataFrame, required_columns: list[str] = REQUIRED_COLUMNS) -> None:
    """Validate that every required column is present in ``dataframe``.

    Raises:
        MissingColumnsError: if one or more required columns are absent.
    """
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise MissingColumnsError(
            f"Dataset is missing required column(s): {', '.join(missing)}"
        )
    logger.info("Column validation passed. All %d required columns present.", len(required_columns))


def load_sales_data(file_path: Path) -> pd.DataFrame:
    """Load the raw sales dataset from ``file_path`` into a DataFrame.

    Performs existence, structural and emptiness validation, and raises
    descriptive exceptions on failure rather than letting a low-level
    pandas error propagate uninterpreted.

    Raises:
        DatasetNotFoundError: if the file does not exist.
        EmptyDatasetError: if the file contains no data rows.
        MissingColumnsError: if required columns are missing.
    """
    path = Path(file_path)

    if not path.exists():
        raise DatasetNotFoundError(
            f"Raw dataset not found at '{path}'. "
            "Run 'python -m src.generate_dataset' or 'python main.py' to generate it."
        )

    try:
        dataframe = pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise EmptyDatasetError(f"Dataset file '{path}' is empty.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Dataset file '{path}' could not be parsed as CSV: {exc}") from exc

    if dataframe.empty:
        raise EmptyDatasetError(f"Dataset file '{path}' contains no data rows.")

    validate_columns(dataframe)

    logger.info("Loaded raw dataset from %s with %d rows and %d columns.",
                path, len(dataframe), len(dataframe.columns))

    return dataframe
