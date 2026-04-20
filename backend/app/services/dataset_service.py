import pandas as pd
import numpy as np
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

class DatasetService:
    def __init__(self):
        self._cache = {}  # dataset_id -> DataFrame
        self.registry_file = settings.upload_path / "registry.json"
        self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")
        return {}

    def _save_to_registry(self, dataset_id: str, metadata: Dict[str, Any]):
        registry = self._load_registry()
        registry[dataset_id] = metadata
        try:
            with open(self.registry_file, "w") as f:
                json.dump(registry, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save to registry: {e}")

    def load_dataset(self, file_path: Path, dataset_id: str) -> Dict[str, Any]:
        """
        Loads CSV/XLSX into pandas, validates, and registers.
        """
        try:
            suffix = file_path.suffix.lower()
            if suffix == '.csv':
                # Try UTF-8, fallback to latin-1
                try:
                    df = pd.read_csv(file_path)
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, encoding='latin-1')
            elif suffix in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format: {suffix}")
            
            if df.empty:
                raise ValueError("The uploaded file is empty.")

            # Basic cleaning
            df.columns = [str(c).strip() for c in df.columns]
            
            # Store in cache
            self._cache[dataset_id] = df
            
            # RAG Indexing
            indexed_count = rag_service.index_dataframe(df, dataset_id, file_path.name)
            
            # Register metadata
            metadata = {
                "dataset_id": dataset_id,
                "filename": file_path.name,
                "original_name": file_path.name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": df.columns.tolist(),
                "rag_indexed": True,
                "indexed_row_count": indexed_count
            }
            self._save_to_registry(dataset_id, metadata)
            
            return metadata
        except Exception as e:
            logger.error(f"Failed to load dataset {file_path}: {e}")
            raise ValueError(f"Error processing file: {str(e)}")

    def get_dataframe(self, dataset_id: str) -> Optional[pd.DataFrame]:
        """
        Gets dataframe from cache or reloads from disk if registered.
        """
        if dataset_id in self._cache:
            return self._cache[dataset_id]
        
        # Try to reload from registry
        registry = self._load_registry()
        if dataset_id in registry:
            meta = registry[dataset_id]
            file_path = settings.upload_path / meta["filename"]
            if file_path.exists():
                try:
                    logger.info(f"Reloading dataset {dataset_id} from {file_path}")
                    # Recursively call load_dataset or just reload
                    suffix = file_path.suffix.lower()
                    if suffix == '.csv':
                        df = pd.read_csv(file_path)
                    else:
                        df = pd.read_excel(file_path)
                    self._cache[dataset_id] = df
                    return df
                except Exception as e:
                    logger.error(f"Failed to reload dataset: {e}")
        
        return None

    def get_summary(self, dataset_id: str) -> Dict[str, Any]:
        """
        Profiles the dataset schema and returns statistics.
        """
        df = self.get_dataframe(dataset_id)
        if df is None:
            raise KeyError("Dataset not found or could not be loaded.")

        # Data types
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        
        # Null counts
        null_counts = df.isnull().sum().to_dict()
        
        # Numeric summary
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_summary = df[numeric_cols].describe().to_dict() if not numeric_cols.empty else {}
        
        # Categorical top values (for non-numeric columns)
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns
        top_values = {}
        for col in categorical_cols:
            # Also include datetime detection
            if "date" in col.lower() or "time" in col.lower():
                try:
                    pd.to_datetime(df[col], errors='raise')
                    top_values[col] = {"info": "Date/Time column detected"}
                    continue
                except:
                    pass
            top_values[col] = df[col].value_counts().head(5).to_dict()
            
        # Sample rows
        sample_rows = df.head(5).replace({np.nan: None}).to_dict(orient='records')

        # Registry meta
        registry = self._load_registry()
        meta = registry.get(dataset_id, {})

        return {
            "dataset_id": dataset_id,
            "filename": meta.get("filename", "unknown"),
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "dtypes": dtypes,
            "null_counts": null_counts,
            "sample_rows": sample_rows,
            "numeric_summary": numeric_summary,
            "top_categorical_values": top_values,
            "shape": list(df.shape)
        }

    def get_context_for_nvidia(self, dataset_id: str) -> str:
        """
        Prepares a structured, compact text summary for NVIDIA context.
        """
        df = self.get_dataframe(dataset_id)
        if df is None:
            return "No dataset context available."

        context = {
            "columns": df.columns.tolist(),
            "shape": list(df.shape),
            "categorical_summary": {},
            "numeric_summary": {}
        }
        
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        for col in cat_cols:
            context["categorical_summary"][col] = df[col].value_counts().head(5).to_dict()
            
        num_cols = df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            context["numeric_summary"][col] = {
                "mean": round(float(df[col].mean()), 2) if not df[col].isnull().all() else None,
                "median": round(float(df[col].median()), 2) if not df[col].isnull().all() else None,
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

dataset_service = DatasetService()
