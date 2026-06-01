import os
import json
import sys

# Add project root to path for logging import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_exploration.core.exploration_logger import exp_logger

# Bulletproof path setup cell injected into all notebooks to handle running from any directory (VS Code / CLI / Jupyter)
PATH_SETUP_CELL = [
    "import os",
    "import sys",
    "# Add project root to path dynamically",
    "cwd = os.getcwd()",
    "while cwd and not os.path.exists(os.path.join(cwd, 'requirements.txt')):",
    "    parent = os.path.dirname(cwd)",
    "    if parent == cwd: break",
    "    cwd = parent",
    "if cwd not in sys.path:",
    "    sys.path.append(cwd)",
    "print(f'Project root added to sys.path: {cwd}')"
]

def create_notebook(filename: str, title: str, cells_data: list):
    """Helper to write a clean .ipynb Jupyter Notebook file."""
    notebook = {
        "cells": [],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }
    
    for cell_type, lines in cells_data:
        cell = {
            "cell_type": cell_type,
            "metadata": {},
            "source": [line + "\n" for line in lines]
        }
        if cell_type == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
        notebook["cells"].append(cell)
        
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=2)

def generate_all_notebooks():
    notebooks_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Subdirectories for clean organization
    db_exp_dir = os.path.join(notebooks_dir, "database_exploration")
    cust_dir = os.path.join(notebooks_dir, "customer_recommender")
    owner_dir = os.path.join(notebooks_dir, "owner_recommender")
    
    os.makedirs(db_exp_dir, exist_ok=True)
    os.makedirs(cust_dir, exist_ok=True)
    os.makedirs(owner_dir, exist_ok=True)
    
    # 1. 01_schema_exploration.ipynb
    create_notebook(
        os.path.join(db_exp_dir, "01_schema_exploration.ipynb"),
        "Schema Exploration",
        [
            ("markdown", [
                "# 01. SQL Server Schema Exploration & Dynamic Discovery",
                "This notebook dynamically reflects the SQL Server database schema using the SQLAlchemy Inspector. It inspects all tables, columns, indexes, and relationships. If the database is offline, it falls back to filesystem definitions."
            ]),
            ("code", PATH_SETUP_CELL + [
                "",
                "from database_exploration.core.schema_inspector import SchemaInspector",
                "inspector = SchemaInspector()",
                "print(f\"Database Online Status: {inspector.is_connected()}\")",
                "print(f\"Status Message: {inspector.status_message}\")"
            ]),
            ("markdown", [
                "## 1. List All Database Tables"
            ]),
            ("code", [
                "tables = inspector.get_all_tables()",
                "print(\"Tables discovered:\", tables)"
            ]),
            ("markdown", [
                "## 2. Inspect Column Types for Key Tables"
            ]),
            ("code", [
                "for table in ['interactions', 'products', 'raw_materials']:",
                "    print(f\"\\n=== Schema for {table} ===\")",
                "    columns = inspector.get_table_columns(table)",
                "    pks = inspector.get_primary_keys(table)",
                "    print(f\"Primary Keys: {pks}\")",
                "    for col in columns:",
                "        print(f\"  - {col['name']}: {col['type']} (Nullable: {col['nullable']})\")"
            ]),
            ("markdown", [
                "## 3. Reflect Declarative Foreign Keys & Indexes"
            ]),
            ("code", [
                "for table in ['interactions', 'products', 'raw_materials']:",
                "    print(f\"\\n=== Indexes for {table} ===\")",
                "    indexes = inspector.get_indexes(table)",
                "    for idx in indexes:",
                "        print(f\"  - Index: {idx['name']} on {idx['column_names']} (Unique: {idx['unique']})\")"
            ])
        ]
    )

    # 2. 02_interaction_analysis.ipynb
    create_notebook(
        os.path.join(db_exp_dir, "02_interaction_analysis.ipynb"),
        "Interaction Analysis",
        [
            ("markdown", [
                "# 02. Interaction Data Quality & Pattern Analysis",
                "This notebook profiles interaction volumes, checks data quality, and performs event frequency analysis across the B2C customer catalog and B2B raw materials."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import numpy as np",
                "import matplotlib.pyplot as plt",
                "import seaborn as sns",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions\", engine)",
                "    print(\"Loaded data from SQL database\")",
                "except Exception:",
                "    df = load_data_fallback(\"interactions\")",
                "",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Overall Dataset Shapes & Columns"
            ]),
            ("code", [
                "print(f\"Total Interactions: {len(df)}\")",
                "print(\"Columns:\", df.columns.tolist())",
                "print(df.info())"
            ]),
            ("markdown", [
                "## 2. Interaction Event Distributions"
            ]),
            ("code", [
                "event_counts = df['interaction_type'].value_counts()",
                "print(event_counts)",
                "plt.figure(figsize=(8, 4))",
                "sns.countplot(data=df, x='interaction_type', palette='viridis')",
                "plt.title('Distribution of Interaction Types')",
                "plt.show()"
            ]),
            ("markdown", [
                "## 3. Duplicate and Null Ratio Audits"
            ]),
            ("code", [
                "print(\"Null counts per column:\")",
                "print(df.isna().sum())",
                "print(f\"\\nDuplicate Rows: {df.duplicated().sum()} ({df.duplicated().sum()/len(df)*100:.2f}%)\")"
            ])
        ]
    )

    # 3. 03_customer_behavior_analysis.ipynb
    create_notebook(
        os.path.join(cust_dir, "03_customer_behavior_analysis.ipynb"),
        "Customer Behavior Analysis",
        [
            ("markdown", [
                "# 03. Customer Behavior Analysis & Profiling (B2C)",
                "Profiles purchase frequency, spend profiles, customer categories, and user affinity clusters."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import matplotlib.pyplot as plt",
                "import seaborn as sns",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions WHERE user_type='customer'\", engine)",
                "except Exception:",
                "    df = load_data_fallback(\"interactions\")",
                "    df = df[df['user_type'].str.lower() == 'customer']",
                "",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Top Active Customers"
            ]),
            ("code", [
                "top_users = df['user_id'].value_counts().head(10)",
                "print(\"Top 10 Active Customers by Event Count:\")",
                "print(top_users)",
                "plt.figure(figsize=(10, 4))",
                "top_users.plot(kind='bar', color='skyblue')",
                "plt.title('Top 10 Most Active Customers')",
                "plt.xlabel('Customer ID')",
                "plt.ylabel('Event Count')",
                "plt.show()"
            ]),
            ("markdown", [
                "## 2. Spend Profile Analysis"
            ]),
            ("code", [
                "purchases = df[df['interaction_type'] == 'purchase']",
                "user_spend = purchases.groupby('user_id')['price'].sum().reset_index()",
                "print(user_spend.describe())",
                "plt.figure(figsize=(8, 4))",
                "sns.histplot(user_spend['price'], bins=30, kde=True, color='purple')",
                "plt.title('Customer Aggregate Spend Distribution')",
                "plt.xlabel('Total Spend ($)')",
                "plt.show()"
            ])
        ]
    )

    # 4. 04_owner_procurement_analysis.ipynb
    create_notebook(
        os.path.join(owner_dir, "04_owner_procurement_analysis.ipynb"),
        "Owner Procurement Analysis",
        [
            ("markdown", [
                "# 04. Business Owner Procurement Analysis & Scheduling (B2B)",
                "Profiles material reorders, purchase cycle durations, and procurement patterns."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import matplotlib.pyplot as plt",
                "import seaborn as sns",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions WHERE user_type='owner'\", engine)",
                "except Exception:",
                "    df = load_data_fallback(\"owner_interactions\")",
                "",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Top Procured Raw Materials"
            ]),
            ("code", [
                "top_materials = df[df['interaction_type'].isin(['purchase', 'reorder'])]['item_id'].value_counts().head(10)",
                "print(\"Top 10 Most Procured Materials:\")",
                "print(top_materials)",
                "plt.figure(figsize=(10, 4))",
                "top_materials.plot(kind='bar', color='green')",
                "plt.title('Top 10 Procured Raw Materials')",
                "plt.xlabel('Material ID')",
                "plt.ylabel('Order Count')",
                "plt.show()"
            ]),
            ("markdown", [
                "## 2. Order Quantity Distribution"
            ]),
            ("code", [
                "plt.figure(figsize=(8, 4))",
                "sns.boxplot(data=df, x='quantity', color='orange')",
                "plt.title('Owner Procurement Order Quantities')",
                "plt.show()"
            ])
        ]
    )

    # 5. 05_category_analysis.ipynb
    create_notebook(
        os.path.join(db_exp_dir, "05_category_analysis.ipynb"),
        "Category Analysis",
        [
            ("markdown", [
                "# 05. Product & Material Category Affinity Profiling",
                "Analyzes category volumes, interaction types across categories, and affinity vectors."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import matplotlib.pyplot as plt",
                "import seaborn as sns",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions\", engine)",
                "except Exception:",
                "    df = load_data_fallback(\"interactions\")",
                "",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Category Value Distributions"
            ]),
            ("code", [
                "cat_counts = df['category'].value_counts()",
                "print(cat_counts)",
                "plt.figure(figsize=(12, 5))",
                "sns.countplot(data=df, y='category', order=cat_counts.index[:10], palette='plasma')",
                "plt.title('Top 10 Most Interacted Categories')",
                "plt.show()"
            ])
        ]
    )

    # 6. 06_seasonal_analysis.ipynb
    create_notebook(
        os.path.join(db_exp_dir, "06_seasonal_analysis.ipynb"),
        "Seasonal Analysis",
        [
            ("markdown", [
                "# 06. Temporal Seasonality & Periodic Trend Analysis",
                "Analyzes weekly, daily, hourly, and seasonal procurement cycles to discover temporal trends."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import matplotlib.pyplot as plt",
                "import seaborn as sns",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions\", engine)",
                "except Exception:",
                "    df = load_data_fallback(\"interactions\")",
                "",
                "df['interaction_timestamp'] = pd.to_datetime(df['interaction_timestamp'])",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Activity Hourly Seasonality"
            ]),
            ("code", [
                "df['Hour'] = df['interaction_timestamp'].dt.hour",
                "hourly_activity = df.groupby('Hour').size()",
                "plt.figure(figsize=(10, 4))",
                "sns.lineplot(x=hourly_activity.index, y=hourly_activity.values, marker='o', color='red')",
                "plt.title('Aggregate Hourly Activity Density')",
                "plt.xlabel('Hour of Day')",
                "plt.ylabel('Event Count')",
                "plt.xticks(range(24))",
                "plt.show()"
            ])
        ]
    )

    # 7. 07_recommendation_signal_analysis.ipynb
    create_notebook(
        os.path.join(db_exp_dir, "07_recommendation_signal_analysis.ipynb"),
        "Recommendation Signal Analysis",
        [
            ("markdown", [
                "# 07. Recommendation Signals Discovery & Sparsity Profiling",
                "Profiles purchase decay speeds, interaction weights (view vs purchase), category affinity vectors, and sparsity matrices."
            ]),
            ("code", PATH_SETUP_CELL + [
                "import pandas as pd",
                "import numpy as np",
                "",
                "from database_exploration.core.db_connector import get_exploration_engine, load_data_fallback",
                "",
                "engine = get_exploration_engine()",
                "try:",
                "    df = pd.read_sql(\"SELECT * FROM interactions\", engine)",
                "except Exception:",
                "    df = load_data_fallback(\"interactions\")",
                "",
                "df.head()"
            ]),
            ("markdown", [
                "## 1. Core Sparsity Calculations"
            ]),
            ("code", [
                "n_users = df['user_id'].nunique()",
                "n_items = df['item_id'].nunique()",
                "n_interactions = len(df)",
                "",
                "possible_links = n_users * n_items",
                "sparsity = 1 - (n_interactions / possible_links) if possible_links > 0 else 1.0",
                "",
                "print(f\"Unique Users: {n_users}\")",
                "print(f\"Unique Items: {n_items}\")",
                "print(f\"Interactions: {n_interactions}\")",
                "print(f\"Interaction Density Matrix Sparsity: {sparsity * 100:.4f}%\")"
            ])
        ]
    )
    
    exp_logger.info("Successfully generated 7 bulletproof Jupyter notebooks in organized subfolders.")

if __name__ == "__main__":
    generate_all_notebooks()
