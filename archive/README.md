# Danish Housing Market Analysis

A Python-based tool for analyzing and scoring housing opportunities in Denmark.

## Setup

1. Create a virtual environment:
```
python -m venv venv
.\venv\Scripts\activate
```

2. Install requirements:
```
pip install -r requirements.txt
```

3. Set up your database connection in a `.env` file (copy from `.env.example`)

## Project Structure

- `src/`: Main source code
  - `main.py`: Streamlit application entry point
  - `data_loader.py`: Functions for loading and processing housing data
  - `database.py`: Database connection and queries
  - `models.py`: Data models and schemas
  - `scoring.py`: House scoring algorithms
- `data/`: Raw and processed data files
- `notebooks/`: Jupyter notebooks for analysis and experimentation
- `tests/`: Unit tests