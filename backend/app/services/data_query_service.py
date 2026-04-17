import pandas as pd
import numpy as np
import re
from typing import Optional, Dict, Any, List

# Column Alias Mapping
COLUMN_ALIASES = {
    "duke stage": "Dukes Stage",
    "dukes stage": "Dukes Stage",
    "stage": "Dukes Stage",
    "dfs": "DFS (in months)",
    "dfs months": "DFS (in months)",
    "survival": "DFS (in months)",
    "survival time": "DFS (in months)",
    "dfs event": "DFS event",
    "age": "Age (in years)",
    "radio": "Adj_Radio",
    "radiotherapy": "Adj_Radio",
    "chemo": "Adj_Chem",
    "chemotherapy": "Adj_Chem",
    "gender": "Gender",
    "sex": "Gender",
    "location": "Location",
}

def resolve_column_name(df: pd.DataFrame, text: str) -> Optional[str]:
    text_lower = text.lower()
    for alias, actual in COLUMN_ALIASES.items():
        if alias in text_lower and actual in df.columns:
            return actual
    for col in df.columns:
        if col.lower() in text_lower:
            return col
    return None

def handle_percentage_questions(df: pd.DataFrame, msg: str, target_col: str) -> Optional[Dict[str, Any]]:
    try:
        match = re.search(r"=\s*(\d+)", msg)
        val = match.group(1) if match else "1"
        # Check if column is numeric or categorical
        if np.issubdtype(df[target_col].dtype, np.number):
             count = (df[target_col].astype(float) == float(val)).sum()
        else:
             count = (df[target_col].astype(str) == str(val)).sum()
             
        percent = (count / len(df)) * 100
        return {
            "answer": f"{percent:.1f}% of patients ({count}/{len(df)}) have {target_col} = {val}.",
            "answer_type": "percentage",
            "confidence": 0.99,
            "source_columns": [target_col]
        }
    except:
        return None

def handle_groupby_mean_questions(df: pd.DataFrame, msg: str, target_col: str, group_col: str) -> Optional[Dict[str, Any]]:
    try:
        if not np.issubdtype(df[target_col].dtype, np.number):
             # Try to swap if group_col is numeric and target is not
             if np.issubdtype(df[group_col].dtype, np.number):
                 target_col, group_col = group_col, target_col
             else:
                 return None

        means = df.groupby(group_col)[target_col].mean().sort_values(ascending=False).replace({np.nan: "N/A"})
        formatted = f"Average {target_col} by {group_col}:\n"
        for label, val in means.items():
            formatted += f"* {label}: {val:.2f}\n" if isinstance(val, (int, float)) else f"* {label}: {val}\n"
        return {
            "answer": formatted.strip(),
            "answer_type": "groupby_mean",
            "confidence": 0.99,
            "source_columns": [target_col, group_col]
        }
    except:
        return None

def handle_distribution_questions(df: pd.DataFrame, col: str) -> Optional[Dict[str, Any]]:
    try:
        if not np.issubdtype(df[col].dtype, np.number):
            return None
        s = df[col].describe()
        formatted = f"{col} distribution summary:\n"
        formatted += f"* Total count: {s['count']:.0f}\n"
        formatted += f"* Mean: {s['mean']:.2f}\n"
        formatted += f"* Std Dev: {s['std']:.2f}\n"
        formatted += f"* Min: {s['min']:.2f}\n"
        formatted += f"* 25th percentile: {s['25%']:.2f}\n"
        formatted += f"* Median (50%): {s['50%']:.2f}\n"
        formatted += f"* 75th percentile: {s['75%']:.2f}\n"
        formatted += f"* Max: {s['max']:.2f}"
        return {
            "answer": formatted,
            "answer_type": "distribution",
            "confidence": 0.99,
            "source_columns": [col]
        }
    except:
        return None

def handle_comparison_questions(df: pd.DataFrame, target_col: str, group_col: str) -> Optional[Dict[str, Any]]:
    try:
        if not np.issubdtype(df[target_col].dtype, np.number):
            return None
        means = df.groupby(group_col)[target_col].mean().sort_index()
        
        formatted = f"Comparison of Average {target_col} across {group_col}:\n"
        for label, val in means.items():
            display_label = "Positive (1)" if str(label) == "1" else "Negative (0)" if str(label) == "0" else str(label)
            formatted += f"* {display_label}: {val:.2f}\n"
            
        if len(means) == 2:
            diff = abs(means.iloc[0] - means.iloc[1])
            higher = means.idxmax()
            higher_label = "Positive (1)" if str(higher) == "1" else "Negative (0)" if str(higher) == "0" else str(higher)
            formatted += f"\nGroup '{higher_label}' has a higher average by {diff:.2f}."
            
        return {
            "answer": formatted.strip(),
            "answer_type": "comparison",
            "confidence": 0.99,
            "source_columns": [target_col, group_col]
        }
    except:
        return None

def try_answer_with_pandas(df: pd.DataFrame, message: str) -> Optional[Dict[str, Any]]:
    if df is None: return None
    msg = message.lower().strip()
    
    # 1. Structural / Metadata
    if any(x in msg for x in ["how many rows", "total rows", "row count", "number of records"]):
        return {"answer": f"The dataset has {len(df)} rows.", "answer_type": "metadata", "confidence": 1.0, "source_columns": []}
    
    if any(x in msg for x in ["how many columns", "total columns", "list columns", "what are the columns"]):
        return {"answer": f"The dataset has {len(df.columns)} columns: {', '.join(df.columns.tolist())}", "answer_type": "metadata", "confidence": 1.0, "source_columns": []}

    if any(x in msg for x in ["summary", "overview", "describe dataset"]):
        return {"answer": f"Dataset Summary: {len(df)} rows and {len(df.columns)} columns.", "answer_type": "summary", "confidence": 1.0, "source_columns": []}

    # 2. Identify potential columns
    found_cols = []
    # Use aliases first to be specific
    for alias, actual in COLUMN_ALIASES.items():
        if alias in msg and actual in df.columns and actual not in found_cols:
            found_cols.append(actual)
    # Then actual names
    for col in df.columns:
        if col.lower() in msg and col not in found_cols:
            found_cols.append(col)

    # 3. Analyze query pattern
    
    # Percentage
    if "percent" in msg or "%" in msg:
        if found_cols:
            return handle_percentage_questions(df, msg, found_cols[0])

    # Distribution
    if "distribution" in msg or "stats" in msg or "summary" in msg and len(found_cols) == 1:
        if found_cols:
            return handle_distribution_questions(df, found_cols[0])

    # Comparison
    if "compare" in msg or " vs " in msg or " versus " in msg:
        if len(found_cols) >= 2:
            return handle_comparison_questions(df, found_cols[0], found_cols[1])

    # Groupby (average/mean/count)
    if " by " in msg or " per " in msg or " each " in msg:
        if len(found_cols) >= 2:
            if "average" in msg or "mean" in msg:
                return handle_groupby_mean_questions(df, msg, found_cols[0], found_cols[1])
            else:
                # Grouped Count
                counts = df.groupby(found_cols[1]).size().sort_values(ascending=False)
                res = f"Counts of patients by {found_cols[1]}:\n" + "\n".join([f"* {k}: {v}" for k, v in counts.items()])
                return {"answer": res.strip(), "answer_type": "groupby_count", "confidence": 0.99, "source_columns": [found_cols[1]]}
        elif len(found_cols) == 1:
             # Likely asking for value counts of the single column
             counts = df[found_cols[0]].value_counts().head(10)
             res = f"Value counts for {found_cols[0]}:\n" + "\n".join([f"* {k}: {v}" for k, v in counts.items()])
             return {"answer": res.strip(), "answer_type": "counts", "confidence": 0.95, "source_columns": [found_cols[0]]}

    # Highest / Lowest (Extremes)
    if "highest" in msg or "lowest" in msg or "max" in msg or "min" in msg:
        if len(found_cols) >= 2:
            target, group = (found_cols[0], found_cols[1]) if np.issubdtype(df[found_cols[0]].dtype, np.number) else (found_cols[1], found_cols[0])
            try:
                means = df.groupby(group)[target].mean()
                result_idx = means.idxmax() if "highest" in msg or "max" in msg else means.idxmin()
                result_val = means.max() if "highest" in msg or "max" in msg else means.min()
                word = "highest" if "highest" in msg or "max" in msg else "lowest"
                return {
                    "answer": f"The {group} with the {word} average {target} is '{result_idx}' with {result_val:.2f}.",
                    "answer_type": "extreme",
                    "confidence": 0.95,
                    "source_columns": [target, group]
                }
            except: pass

    # Basic Means / Medians
    if "average" in msg or "mean" in msg:
        if found_cols:
            col = found_cols[0]
            if np.issubdtype(df[col].dtype, np.number):
                return {"answer": f"The average {col} is {df[col].mean():.2f}.", "answer_type": "mean", "confidence": 0.99, "source_columns": [col]}

    if "median" in msg:
        if found_cols:
            col = found_cols[0]
            if np.issubdtype(df[col].dtype, np.number):
                return {"answer": f"The median {col} is {df[col].median():.2f}.", "answer_type": "median", "confidence": 0.99, "source_columns": [col]}

    # Check for conditional counts (e.g. "how many stage A")
    if "how many" in msg or "count" in msg:
        for col in found_cols:
             unique_vals = df[col].dropna().unique()
             for uv in unique_vals:
                 if str(uv).lower() in msg:
                     c = (df[col].astype(str).str.lower() == str(uv).lower()).sum()
                     return {"answer": f"There are {c} patients where {col} is '{uv}'.", "answer_type": "count_cond", "confidence": 0.99, "source_columns": [col]}
    
    return None
