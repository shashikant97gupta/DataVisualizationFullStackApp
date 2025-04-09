from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import UploadedFile

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from .utility import clean_dataset, load_file, process_dataframe, generate_graph_options, save_cleaned_file_to_model
import json

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

@csrf_exempt
def fileprocessing(request):
    if request.method == "POST" and request.FILES.get("file"):
        uploaded_file = request.FILES["file"]

        try:
            # ✅ Load file dynamically
            df = load_file(uploaded_file)
            if df is None:
                return JsonResponse({"error": "Unsupported file format"}, status=400)

            # ✅ Clean the dataset (Without Saving)
            df = clean_dataset(df, THRESHOLD_EMPTY_DATA_PERCENT)

            # ✅ Generate graph possibilities (Without Saving)
            graph_possibilities = generate_graph_options(df)

            return JsonResponse({
                "Possible Graphs": graph_possibilities,
                "Columns": df.columns.tolist()
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request or no file uploaded"}, status=400)


@csrf_exempt
def generate_graph(request):
    """API to process multiple graph requests directly from an uploaded file."""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed."}, status=405)

    try:
        # ✅ Check if file is uploaded
        if "file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded."}, status=400)

        uploaded_file = request.FILES["file"]

        # ✅ Load file dynamically
        df = load_file(uploaded_file)
        if df is None:
            return JsonResponse({"error": "Unsupported or corrupted file format."}, status=400)

        # ✅ Clean dataset (Without Saving)
        df = process_dataframe(df)

        # ✅ Parse request body for graph options
        data = json.loads(request.POST.get("graphs", "[]"))
        if not isinstance(data, list) or len(data) == 0:
            return JsonResponse({"error": "Invalid request. 'graphs' list is required."}, status=400)

        results = []

        for graph_request in data:
            graph_type = graph_request.get("graph_type")
            columns = graph_request.get("columns_selected", {})
            x_col = columns.get("x_axis")
            y_col = columns.get("y_axis")

            if not graph_type or not x_col or (graph_type not in ["Count Plot", "Pie Chart"] and not y_col):
                results.append({"error": f"Invalid graph request: {graph_request}"})
                continue

            if x_col not in df.columns or (y_col and y_col not in df.columns):
                results.append({"error": f"Invalid columns: {columns}"})
                continue

            plt.figure(figsize=FIG_SIZE, dpi=100)

            try:
                # ✅ Generate the graph based on type
                if graph_type == "Bar Chart":
                    sns.barplot(x=df[x_col], y=df[y_col], palette=PALETTE)
                elif graph_type == "Count Plot":
                    sns.countplot(x=df[x_col], palette=PALETTE)
                elif graph_type == "Stacked Bar Chart":
                    stacked_data = pd.crosstab(df[x_col], df[y_col])
                    stacked_data.plot(kind="bar", stacked=True, colormap="Set2")
                elif graph_type == "Pie Chart":
                    df[x_col].value_counts().plot(kind="pie", autopct="%1.1f%%")
                elif graph_type == "Scatter Plot":
                    sns.scatterplot(x=df[x_col], y=df[y_col], palette=PALETTE)
                elif graph_type == "Correlation Heatmap":
                    sns.heatmap(df.corr(), annot=True, cmap="coolwarm")
                elif graph_type == "Line Chart":
                    sns.lineplot(x=df[x_col], y=df[y_col], palette=PALETTE)
                elif graph_type == "Box Plot":
                    sns.boxplot(x=df[x_col], y=df[y_col], palette=PALETTE)
                else:
                    results.append({"error": f"Unsupported graph type: {graph_type}"})
                    continue
            except Exception as e:
                results.append({"error": f"Error generating graph: {str(e)}"})
                continue

            # ✅ Set labels
            plt.xlabel(x_col, fontsize=LABEL_FONT_SIZE, fontweight=LABEL_FONT_WEIGHT)
            plt.ylabel(y_col if y_col else "", fontsize=LABEL_FONT_SIZE, fontweight=LABEL_FONT_WEIGHT)
            plt.xticks(fontsize=LABEL_FONT_SIZE, fontweight=LABEL_FONT_WEIGHT, rotation=30, ha="right")
            plt.yticks(fontsize=LABEL_FONT_SIZE, fontweight=LABEL_FONT_WEIGHT)

            # ✅ Convert plot to base64
            img = io.BytesIO()
            plt.savefig(img, format="png", bbox_inches="tight")
            img.seek(0)
            graph_url = base64.b64encode(img.getvalue()).decode()
            plt.close()

            results.append({
                "graph_type": graph_type,
                "columns": columns,
                "graph_url": f"data:image/png;base64,{graph_url}"
            })

        return JsonResponse({"graphs": results})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)