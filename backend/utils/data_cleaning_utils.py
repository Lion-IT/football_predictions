import pandas as pd

def clean_dataframe(df):
    """
    Cleans a pandas DataFrame by removing duplicates and filling missing values.

    - Removes duplicate rows.
    - Fills missing numerical values with the column median.
    - Fills missing categorical values with the most frequent value, except for specific columns.

    :param df: Input pandas DataFrame.
    :return: Cleaned pandas DataFrame.
    """
    # Remove duplicates
    df = df.drop_duplicates()

    # Fill missing numerical values with the median
    numerical_cols = df.select_dtypes(include=['float64', 'int64']).columns
    df[numerical_cols] = df[numerical_cols].apply(lambda col: col.fillna(col.median()), axis=0)

    # Fill missing categorical values with the most frequent value
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns

    # Exclude specific columns from being filled
    if 'country_code' in categorical_cols:
        df['country_code'] = df['country_code'].fillna(None)  # Don't fill missing country_code values
        categorical_cols = categorical_cols.drop('country_code')

    df[categorical_cols] = df[categorical_cols].apply(lambda col: col.fillna(col.mode()[0] if not col.mode().empty else ""), axis=0)

    return df

def validate_data(df, required_columns):
    """
    Validates a pandas DataFrame by checking for required columns and null values.

    - Ensures all required columns are present.
    - Checks for any remaining null values after cleaning.

    :param df: Input pandas DataFrame.
    :param required_columns: List of required column names.
    :return: True if validation passes, otherwise raises ValueError.
    """
    # Check if all required columns are present
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required column(s): {', '.join(missing_columns)}")

    # Check for any null values
    if df.isnull().values.any():
        raise ValueError("Data contains null values after cleaning.")

    print("Data validation passed.")
    return True
