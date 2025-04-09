import pandas as pd
import seaborn as sns
import os
from django.conf import settings
from django.core.files import File
from django.core.files.base import ContentFile
from .models import UploadedFile
import re
import uuid

# File path
# file_path = os.path.join(settings.BASE_DIR, 'assets', 'cleaned_dataset_splitted.csv')
FILE_PATH = os.path.join(settings.BASE_DIR, 'assets', 'Registered_Incident.csv')
SERIAL_COLUMN_NAME = "S.No"

# Set figure size and color palette
FIG_SIZE = (20, 10)
LABEL_FONT_SIZE = 10  # Increased font size for better readability
LABEL_FONT_WEIGHT = 800
PALETTE = sns.color_palette("Set2")
THRESHOLD_EMPTY_DATA_PERCENT = 0.5


def truncate_label(label, max_length=200):
    return label[:max_length] + "..." if len(label) > max_length else label

def clean_dataset(df, threshold=0.7):
    """
    Dynamically drops irrelevant columns from the dataset.
    
    - Drops columns with too many unique values (e.g., IDs, Names).
    - Drops columns with more than `threshold`% missing values.
    - Drops highly descriptive text columns (e.g., Remarks, Summaries).
    """
    df = df.copy()  # Work on a copy to avoid modifying the original

    # Identify categorical & numerical columns
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    numerical_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

    # **1. Drop Columns with High Cardinality (e.g., Unique IDs, Names)**
    high_cardinality_cols = [col for col in categorical_cols if df[col].nunique() > 0.7 * len(df)]
    
    # **2. Drop Columns with High Missing Values**
    missing_value_cols = [col for col in df.columns if df[col].isnull().mean() > threshold]
    
    # **3. Drop Columns with Large Text Data (e.g., Summaries, Descriptions)**
    long_text_cols = [col for col in categorical_cols if df[col].apply(lambda x: isinstance(x, str) and len(x) > 50).sum() > 0.3 * len(df)]
    
    # Combine all columns to drop
    cols_to_drop = set(high_cardinality_cols + missing_value_cols + long_text_cols)
    
    print(f"Dropping Columns: {cols_to_drop}")
    
    # Drop identified columns
    df_cleaned = df.drop(columns=cols_to_drop, errors="ignore")

    return df_cleaned


def load_file(file_path):
    """Loads CSV, Excel, or JSON file into a Pandas DataFrame."""
    try:
        file_name = file_path.name
        if file_name.endswith(".csv"):
            return pd.read_csv(file_path)
        elif file_name.endswith(".xlsx"):
            return pd.read_excel(file_path, engine="openpyxl")
        elif file_name.endswith(".json"):
            return pd.read_json(file_path)
        else:
            return None
    except Exception as e:
        print(f"Error loading file: {e}")
        return None


def process_dataframe(df):
    """Cleans dataset and identifies column types."""
    # ✅ Drop "S.No." column if it exists
    if SERIAL_COLUMN_NAME in df.columns:
        df.drop(columns=[SERIAL_COLUMN_NAME], inplace=True)

    # ✅ Clean dataset
    df = clean_dataset(df, THRESHOLD_EMPTY_DATA_PERCENT)

    return df


def generate_graph_options(df):
    """Generates a list of possible graph combinations based on column types."""
    numerical_cols = [col for col in df.select_dtypes(include=["int64", "float64"]).columns if df[col].nunique() > 1]
    categorical_cols = [col for col in df.select_dtypes(include=["object", "category"]).columns if df[col].nunique() > 1]
    date_columns = [col for col in df.columns if ("date" in col.lower() or "time" in col.lower()) and df[col].nunique() > 1]
    categorical_cols = [col for col in categorical_cols if col not in date_columns]

    graph_possibilities = []
    seen_pairs = set()

    # ✅ Bar Chart (Categorical vs Numerical)
    for cat in categorical_cols:
        for num in numerical_cols:
            pair = (cat, num)
            if pair not in seen_pairs:
                graph_possibilities.append({"Graph Type": "Bar Chart", "X": cat, "Y": num})
                seen_pairs.add(pair)

    # ✅ Count Plot (Single Categorical)
    for cat in categorical_cols:
        if cat not in seen_pairs:
            graph_possibilities.append({"Graph Type": "Count Plot", "X": cat})
            seen_pairs.add((cat,))

    # ✅ Stacked Bar Chart (Categorical vs Categorical)
    for i, cat1 in enumerate(categorical_cols):
        for cat2 in categorical_cols[i+1:]:
            pair = tuple(sorted([cat1, cat2]))
            if pair not in seen_pairs:
                graph_possibilities.append({"Graph Type": "Stacked Bar Chart", "X": cat1, "Y": cat2})
                seen_pairs.add(pair)

    # ✅ Pie Chart (Categorical Columns)
    for cat in categorical_cols:
        if (cat,) not in seen_pairs:
            graph_possibilities.append({"Graph Type": "Pie Chart", "X": cat})
            seen_pairs.add((cat,))

    # ✅ Scatter Plot (Numerical vs Numerical)
    for i, num1 in enumerate(numerical_cols):
        for num2 in numerical_cols[i+1:]:
            pair = tuple(sorted([num1, num2]))
            if pair not in seen_pairs:
                graph_possibilities.append({"Graph Type": "Scatter Plot", "X": num1, "Y": num2})
                seen_pairs.add(pair)

    # ✅ Correlation Heatmap (If more than one numerical column)
    if len(numerical_cols) > 1 and "Correlation Heatmap" not in seen_pairs:
        graph_possibilities.append({"Graph Type": "Correlation Heatmap", "Columns": numerical_cols})
        seen_pairs.add("Correlation Heatmap")

    # ✅ Line Chart (Date vs Numerical)
    for date_col in date_columns:
        for num in numerical_cols:
            pair = (date_col, num)
            if pair not in seen_pairs:
                graph_possibilities.append({"Graph Type": "Line Chart", "X": date_col, "Y": num})
                seen_pairs.add(pair)

    # ✅ Box Plot (Numerical grouped by Categorical)
    for cat in categorical_cols:
        for num in numerical_cols:
            pair = (cat, num)
            if pair not in seen_pairs:
                graph_possibilities.append({"Graph Type": "Box Plot", "X": cat, "Y": num})
                seen_pairs.add(pair)

    return graph_possibilities


# Function to sanitize the filename
def sanitize_filename(filename):
    filename = filename.replace(" ", "_")  # Replace spaces with underscores
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)  # Remove unsafe characters
    return filename

# Function to generate a unique filename
def generate_unique_filename(extension):
    return f"{uuid.uuid4()}.{extension}"


def save_cleaned_file_to_model(df, original_filename):
    """ Clean the file, save it to Django's media storage, and store it in the UploadedFile model. """
    
    # Define the media directory for storing cleaned files
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_files')
    os.makedirs(upload_dir, exist_ok=True)  # Ensure directory exists

    # Generate a unique filename
    file_extension = original_filename.split('.')[-1].lower()
    unique_filename = f"cleaned_{uuid.uuid4().hex}.{file_extension}"
    cleaned_file_path = os.path.join(upload_dir, unique_filename)

    # Save the DataFrame to the cleaned file
    if file_extension == 'csv':
        df.to_csv(cleaned_file_path, index=False)
    elif file_extension == 'xlsx':
        df.to_excel(cleaned_file_path, index=False)
    elif file_extension == 'json':
        df.to_json(cleaned_file_path, orient='records', lines=True)
    else:
        raise ValueError("Unsupported file extension")

    # ✅ Correctly attach the file to Django's FileField
    with open(cleaned_file_path, 'rb') as file:
        django_file = ContentFile(file.read())  # Read file as Django ContentFile
        file_instance = UploadedFile()  # Create model instance
        file_instance.file.save(unique_filename, django_file)  # Save file properly
        file_instance.save()  # Ensure it's committed to DB

    return file_instance  # Return the saved file instance