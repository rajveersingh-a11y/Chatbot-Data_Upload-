import pandas as pd
import numpy as np
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

logger = logging.getLogger(__name__)

class DatasetService:
    def __init__(self):
        # In a real app, you'd use a database, but here we store in memory for MVP
        self._cache = {} # dataset_id -> DataFrame

    def load_dataset(self, file_path: Path, dataset_id: str) -> Dict[str, Any]:
        """
        Loads CSV/XLSX into pandas and returns basic specs.
        """
        try:
            suffix = file_path.suffix.lower()
            if suffix == '.csv':
                df = pd.read_csv(file_path)
            elif suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            # Store in cache
            self._cache[dataset_id] = df
            
            return {
                "dataset_id": dataset_id,
                "filename": file_path.name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist()
            }
        except Exception as e:
            logger.error(f"Failed to load dataset {file_path}: {e}")
            raise ValueError(f"Error processing file: {str(e)}")

    def get_summary(self, dataset_id: str) -> Dict[str, Any]:
        """
        Profiles the dataset schema and returns statistics.
        """
        df = self._cache.get(dataset_id)
        if df is None:
            raise KeyError("Dataset not found in session memory.")

        # Data types
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Null counts
        null_counts = df.isnull().sum().to_dict()
        
        # Numeric summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_summary = df[numeric_cols].describe().to_dict() if not numeric_cols.empty else {}
        
        # Categorical top values
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns
        top_values = {}
        for col in categorical_cols:
            top_values[col] = df[col].value_counts().head(5).to_dict()
            
        # Sample rows
        sample_rows = df.head(5).replace({np.nan: None}).to_dict(orient='records')

        return {
            "columns": df.columns.tolist(),
            "dtypes": dtypes,
            "null_counts": null_counts,
            "sample_rows": sample_rows,
            "numeric_summary": numeric_summary,
            "top_categorical_values": top_values,
            "shape": df.shape
        }

    def get_context_for_gemini(self, dataset_id: str) -> str:
        """
        Prepares a structured, compact text summary for Gemini context.
        """
        df = self._cache.get(dataset_id)
        if df is None:
            return "No dataset context available."

        context = {
            "columns": df.columns.tolist(),
            "shape": list(df.shape),
            "categorical_summary": {},
            "numeric_summary": {}
        }
        
        # Categorical Summary (Top 5 for objects/categories)
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        for col in cat_cols:
            context["categorical_summary"][col] = df[col].value_counts().head(5).to_dict()
            
        # Numeric Summary (Key stats for numeric cols)
        num_cols = df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            context["numeric_summary"][col] = {
                "mean": round(float(df[col].mean()), 2),
                "median": round(float(df[col].median()), 2),
                "nulls": int(df[col].isnull().sum())
            }

        prompt_context = f"""
### DATASET STRUCTURE
Columns: {context['columns']}
Shape: {context['shape'][0]} rows, {context['shape'][1]} columns

### CATEGORICAL DATA SUMMARY (Top Values)
{json.dumps(context['categorical_summary'], indent=2)}

### NUMERIC DATA SUMMARY
{json.dumps(context['numeric_summary'], indent=2)}

### DATA PREVIEW (First 3 rows)
{df.head(3).to_string()}
"""
        return prompt_context

    def get_deterministic_answer(self, dataset_id: str, message: str) -> Optional[str]:
        """
        Fast-path for simple questions to avoid LLM latency/costs.
        """
        df = self._cache.get(dataset_id)
        if df is None:
            return None
            
        msg = message.lower()
        
        # Row count
        if any(x in msg for x in ["how many rows", "total rows", "row count", "number of records"]):
            return f"The dataset contains {len(df)} rows."
            
        # Column names
        if any(x in msg for x in ["list columns", "what are the columns", "column names"]):
            return f"The columns are: {', '.join(df.columns.tolist())}."
            
        # Shape
        if "shape" in msg:
            return f"The dataset has {df.shape[0]} rows and {df.shape[1]} columns."
            
        # Missing values
        if any(x in msg for x in ["missing values", "null counts", "how many nulls"]):
            nulls = df.isnull().sum()
            if nulls.sum() == 0:
                return "There are no missing values in the dataset."
            non_zero_nulls = nulls[nulls > 0].to_dict()
            return f"Missing value counts per column: {non_zero_nulls}"
            
        return None

dataset_service = DatasetService()
