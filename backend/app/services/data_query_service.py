import pandas as pd
import re

def try_answer_with_pandas(df: pd.DataFrame, message: str):
    if df is None:
        return None
        
    msg = message.lower().strip()

    # ROWS
    if "how many rows" in msg or "number of rows" in msg or "total rows" in msg:
        return f"The dataset has {len(df)} rows."

    # COLUMNS
    if "how many columns" in msg or "total columns" in msg:
        return f"The dataset has {len(df.columns)} columns."

    if "what are the columns" in msg or "list columns" in msg:
        return "Columns are: " + ", ".join(df.columns)

    # SUMMARY
    if "summary of dataset" in msg or "dataset summary" in msg:
        return f"Rows: {len(df)}, Columns: {len(df.columns)}"

    # MEAN DFS EVENT
    if "dfs event" in msg and ("average" in msg or "mean" in msg):
        if "DFS event" in df.columns:
            val = df["DFS event"].mean()
            return f"Average DFS event is {val:.4f}"

    # MEAN DFS MONTHS
    if "dfs" in msg and "months" in msg and ("average" in msg or "mean" in msg):
        if "DFS (in months)" in df.columns:
            val = df["DFS (in months)"].mean()
            return f"Average DFS (in months) is {val:.2f}"

    # MEDIAN DFS
    if "median" in msg and "dfs" in msg:
        if "DFS (in months)" in df.columns:
            val = df["DFS (in months)"].median()
            return f"Median DFS is {val:.0f} months"

    # STAGE COUNT
    if "how many patients in" in msg and "stage" in msg:
        if "Dukes Stage" in df.columns:
            match = re.search(r"\b([abcd])\b", msg)
            if match:
                stage = match.group(1).upper()
                count = (df["Dukes Stage"].astype(str).str.upper() == stage).sum()
                return f"There are {count} patients in Dukes Stage {stage}"

    # COUNT BY STAGE
    if "patients by dukes stage" in msg:
        if "Dukes Stage" in df.columns:
            counts = df["Dukes Stage"].value_counts()
            return "\n".join([f"{k}: {v}" for k, v in counts.items()])

    return None
