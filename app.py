from flask import Flask, jsonify, render_template, request
import pandas as pd
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Timer
import webbrowser
import numpy as np

app = Flask(__name__)

# Global data holder
preloaded_data = pd.DataFrame()

# Path to the data folder
BASE_FOLDER = r"F:\IWFM Nodi Project\Current Project\DATA"

# Column keywords
river_keywords = ["river", "rivername", "river_name"]
station_id_keywords = ["stationid", "station_id", "station ID"]
station_name_keywords = ["stationname", "station_name", "station name"]
station_type_keywords = ["stationtype", "type_of_station", "station_type", "TIDAL_STS", "tidal status"]
date_keywords = ["date", "datetime"]
latitude_keywords = ["Latitude", "latitude", "L_Latitude"]
longitude_keywords = ["Longitude", "longitude", "L_Longitude"]
distance_keywords = ["distance"]
rl_keywords = ["rl", "elevation"]


data_column_keywords = {
    "Water level": ["WL(m)", "Daily_Average_WL(m)", "Water Level", "waterlevel", "wl"],
    "Discharge": ["Discharge(m)3/s", "flow", "q(m3/s)"],
    "Cross section": ["RL"],
    "Sediment": [
        "Bulk Concentration in PPM",
        "Coarse Suspended Sediment kg/s",
        "Bulk Suspended Sediment kg/s",
        "Total Sediment Kg/s",
        "MaxSandConcPPM",
        "SedCombPPM"
    ],
    "Salinity": ["salinity", "salt"],
    "Water quality": ["quality", "pollutants", "wq"],
}

def normalize_string(value):
    return value.replace("_", "").replace(" ", "").lower()

def find_matching_columns(columns, data_type):
    river_col, station_id_col, station_name_col, date_col, station_type_col, lat_col, lon_col = (
        None, None, None, None, None, None, None
    )
    data_columns = []
    distance_col, rl_col = None, None  # For cross-section data

    for col in columns:
        normalized_col = normalize_string(col)

        # For station type, use a case-insensitive check:
        if any(keyword.lower() in col.lower() for keyword in station_type_keywords):
            station_type_col = col

        # Now for the other columns, we use normalized matching:
        if any(normalize_string(keyword) in normalized_col for keyword in river_keywords):
            river_col = col
        elif any(normalize_string(keyword) in normalized_col for keyword in station_id_keywords):
            station_id_col = col
        elif any(normalize_string(keyword) in normalized_col for keyword in station_name_keywords):
            station_name_col = col
        elif any(normalize_string(keyword) in normalized_col for keyword in date_keywords):
            date_col = col
        elif any(normalize_string(keyword) in normalized_col for keyword in latitude_keywords):
            lat_col = col
        elif any(normalize_string(keyword) in normalized_col for keyword in longitude_keywords):
            lon_col = col
        elif data_type == "Cross section" and any(normalize_string(keyword) in normalized_col for keyword in distance_keywords):
            distance_col = col
        elif data_type == "Cross section" and any(normalize_string(keyword) in normalized_col for keyword in rl_keywords):
            rl_col = col
        elif col in data_column_keywords.get(data_type, []):
            data_columns.append(col)

    return river_col, station_id_col, station_name_col, date_col, data_columns, station_type_col, lat_col, lon_col, distance_col, rl_col
def process_excel_file(file_path, data_type):
    try:
        if file_path.endswith(('.xlsx', '.xls')):
            # Automatically detect the correct engine for .xlsx or .xls files
            sheets_data = pd.read_excel(file_path, sheet_name=None, engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd')  # sheet_name=None loads all sheets
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

        all_data = []

        for sheet_name, data in sheets_data.items():
            print(f"[DEBUG] Processing sheet: {sheet_name}")
            
            # Get matching columns based on the data type
            cols = find_matching_columns(data.columns, data_type)
            (
                river_col, station_id_col, station_name_col, date_col, data_columns, 
                station_type_col, lat_col, lon_col, distance_col, rl_col
            ) = cols

            # Handle general time-series data
            if data_type != "Cross section":
                critical_columns = [river_col, station_id_col, station_name_col, date_col]
                if any(col is None for col in critical_columns):
                    print(f"[DEBUG] Skipping sheet {sheet_name} in file {file_path}: Missing critical columns")
                    continue  # Skip this sheet if critical columns are missing

                selected_columns = [river_col, station_id_col, station_name_col, date_col] + data_columns

                # Add Latitude and Longitude columns only if they exist (optional for Time Series)
                if lat_col:
                    selected_columns.append(lat_col)
                if lon_col:
                    selected_columns.append(lon_col)

                if station_type_col:
                    selected_columns.append(station_type_col)  # Add Station_Type if available

            # Handle Cross-Section data
            else:
                if not all([river_col, station_id_col, date_col, distance_col, rl_col]):
                    print(f"[DEBUG] Skipping sheet {sheet_name} in file {file_path}: Missing critical columns")
                    continue  # Skip this sheet if critical columns are missing

                selected_columns = [river_col, station_id_col, date_col, distance_col, rl_col]
                if lat_col and lon_col:
                    selected_columns += [lat_col, lon_col]

            filtered_data = data[selected_columns].dropna(subset=[date_col])

            # Convert to datetime and remove rows with invalid dates
            filtered_data[date_col] = pd.to_datetime(filtered_data[date_col], errors="coerce")
            filtered_data.dropna(subset=[date_col], inplace=True)

            column_mapping = {
                river_col: "River",
                station_id_col: "Station_ID",
                date_col: "Date",
                distance_col: "Distance" if data_type == "Cross section" else None,
                rl_col: "RL" if data_type == "Cross section" else None
            }

            # Add Latitude and Longitude if present
            if lat_col:
                column_mapping[lat_col] = "Latitude"
            if lon_col:
                column_mapping[lon_col] = "Longitude"

            if station_name_col:
                column_mapping[station_name_col] = "Station_Name"
            if station_type_col:
                column_mapping[station_type_col] = "Station_Type"  # Add the Station_Type column to mapping

            filtered_data.rename(columns={k: v for k, v in column_mapping.items() if v is not None}, inplace=True)

            # Append the data from this sheet
            all_data.append(filtered_data)

        # Concatenate data from all sheets
        if all_data:
            full_data = pd.concat(all_data, ignore_index=True)
            print(f"[DEBUG] Successfully processed file: {file_path}")
            return full_data
        else:
            print(f"[DEBUG] No valid data found in any sheet of file: {file_path}")
            return pd.DataFrame()  # Return an empty DataFrame if no valid data was found
    except Exception as e:
        print(f"[DEBUG] Error processing file {file_path}: {e}")
        return pd.DataFrame()
    
@app.route('/load_data', methods=['GET'])
def load_data():
    global preloaded_data

    data_type = request.args.get('data_type')
    if not data_type:
        return jsonify({"error": "No data type provided."}), 400

    print(f"[DEBUG] Requested data type: {data_type}")

    # For Water level, check for water_level_type and adjust the folder path accordingly.
    if data_type == "Water level":
        water_level_type = request.args.get('water_level_type')
        if water_level_type:
            folder_path = os.path.join(BASE_FOLDER, data_type, water_level_type)
        else:
            folder_path = os.path.join(BASE_FOLDER, data_type)
    else:
        folder_path = os.path.join(BASE_FOLDER, data_type)

    if not os.path.exists(folder_path):
        return jsonify({"error": f"Folder for '{data_type}' does not exist."}), 404

    files = [os.path.join(folder_path, file) for file in os.listdir(folder_path) if file.endswith(('.xlsx', '.xls'))]
    print(f"[DEBUG] Total files found: {len(files)}")

    if not files:
        return jsonify({"error": "No files found in the folder."}), 404

    data_frames = []
    skipped_files = []
    try:
        with ThreadPoolExecutor() as executor:
            results = executor.map(lambda f: process_excel_file(f, data_type), files)
            for file, result in zip(files, results):
                if result.empty:
                    skipped_files.append(file)
                else:
                    data_frames.append(result)

        print(f"[DEBUG] Files processed: {len(data_frames)}, Files skipped: {len(skipped_files)}")
        if skipped_files:
            print(f"[DEBUG] Skipped files: {skipped_files}")

        if data_frames:
            preloaded_data = pd.concat(data_frames, ignore_index=True)

            # Replace NaN values with None explicitly
            preloaded_data = preloaded_data.fillna(value=np.nan).infer_objects().replace({np.nan: None})

            # Debug: Preview the DataFrame with replaced None values
            print("[DEBUG] Preview of the DataFrame with replaced None values:")
            print(preloaded_data.head())

            if not preloaded_data.empty:
                rivers = preloaded_data["River"].unique().tolist()
                response = {
                    "data": preloaded_data.to_dict(orient="records"),
                    "rivers": rivers
                }
                # If the data type is Sediment, also include sediment columns.
                if data_type == "Sediment":
                    possible_columns = data_column_keywords.get("Sediment", [])
                    sediment_columns = [col for col in preloaded_data.columns if col in possible_columns]
                    response["sediment_columns"] = sediment_columns

                print(f"[DEBUG] JSON Response prepared. Number of records: {len(preloaded_data)}")
                return jsonify(response)

        return jsonify({"error": "No valid data found in the loaded files."}), 404
    except Exception as e:
        print(f"[DEBUG] Exception in load_data: {e}")
        return jsonify({"error": "Server error while loading data."}), 500

@app.route('/stations', methods=['GET'])
def get_stations():
    global preloaded_data

    selected_river = request.args.get('river')
    selected_data_type = request.args.get('data_type')  # Ensure this is passed from frontend

    if selected_river == "None" or not selected_river:
        # If 'None' is selected, return all stations
        filtered_data = preloaded_data
    else:
        # Filter by selected river
        filtered_data = preloaded_data[preloaded_data["River"] == selected_river]
    
    if filtered_data.empty:
        return jsonify({"error": f"No stations found for river '{selected_river}'."}), 404

    # Use Station_ID for Cross Section, Station_Name for others
    if selected_data_type == "Cross section":
        station_list = ["Station_ID", "Latitude", "Longitude", "River"]  # Add River
    else:
        station_list = ["Station_Name", "Latitude", "Longitude", "Station_ID", "River"]  # Add River for other data types

    # Include Station_Type only if it exists
    if "Station_Type" in filtered_data.columns:
        station_list.append("Station_Type")

    try:
        stations = (
            filtered_data[station_list]
            .drop_duplicates()
            .dropna(subset=["Latitude", "Longitude"])
            .to_dict(orient="records")
        )
        return jsonify({"stations": stations})
    except KeyError as e:
        return jsonify({"error": f"Missing expected column: {str(e)}"}), 500

@app.route('/available_years', methods=['GET'])
def get_available_years():
    global preloaded_data

    station_id = request.args.get('station_id')
    if not station_id:
        return jsonify({"error": "No station ID provided."}), 400

    # Filter by Station_ID
    if "Station_Name" in preloaded_data.columns:
        filtered_data = preloaded_data[
            (preloaded_data["Station_ID"] == station_id) | (preloaded_data["Station_Name"] == station_id)
        ]
    else:
        filtered_data = preloaded_data[preloaded_data["Station_ID"] == station_id]

    if filtered_data.empty:
        return jsonify({"error": "No data found for the selected station."}), 404

    # Get available years for Cross Section
    if "Date" in filtered_data.columns:
        years = sorted(filtered_data["Date"].dt.year.dropna().unique().tolist())
    else:
        return jsonify({"error": "No 'Date' column found in data."}), 500

    return jsonify({"years": years})

@app.route('/plot_time_series', methods=['GET'])
def get_time_series_plot():
    global preloaded_data

    station = request.args.get('station')
    year = request.args.get('year')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    data_type = request.args.get('data_type')  # Include data type to determine the column
    selected_column = request.args.get('column')  # For sediment-specific column selection

    if not station:
        return jsonify({"error": "Station not provided."}), 400

    try:
        # Filter data for the selected station
        filtered_data = preloaded_data[preloaded_data['Station_Name'] == station]

        if year and year != "None":
            filtered_data = filtered_data[filtered_data['Date'].dt.year == int(year)]

        if start_date:
            filtered_data = filtered_data[filtered_data['Date'] >= pd.to_datetime(start_date)]

        if end_date:
            filtered_data = filtered_data[filtered_data['Date'] <= pd.to_datetime(end_date)]

        if filtered_data.empty:
            return jsonify({"error": "No data found for the selected station and date range."}), 404

        # Determine the data column dynamically based on the data type
        if data_type == "Sediment" and selected_column:
            y_axis_column = selected_column
        else:
            # Get the first matching column for the data type from data_column_keywords
            y_axis_column = next(
                (col for col in filtered_data.columns if col in data_column_keywords.get(data_type, [])), None
            )
            if not y_axis_column:
                return jsonify({"error": f"No valid data column found for data type '{data_type}'."}), 404

        # Prepare plot data
        plot_data = filtered_data[['Date', y_axis_column]].sort_values(by='Date').to_dict(orient='records')

        return jsonify({"plot_data": plot_data})
    except Exception as e:
        print(f"[DEBUG] Error in get_time_series_plot: {e}")
        return jsonify({"error": "Failed to retrieve plot data."}), 500

@app.route('/plot_cross_section', methods=['GET'])
def get_cross_section_plot():
    global preloaded_data

    station_id = request.args.get('station_id')
    year1 = request.args.get('year1')
    year2 = request.args.get('year2')

    if not station_id:
        return jsonify({"error": "Station ID not provided."}), 400

    # Filter data for the station
    filtered_data = preloaded_data[preloaded_data["Station_ID"] == station_id]

    data_year1 = pd.DataFrame()
    data_year2 = pd.DataFrame()

    # Handle year1 if provided
    if year1 and year1 != "None":
        try:
            data_year1 = filtered_data[filtered_data["Date"].dt.year == int(year1)]
        except ValueError:
            return jsonify({"error": f"Invalid year1 value: {year1}"}), 400

    # Handle year2 if provided
    if year2 and year2 != "None":
        try:
            data_year2 = filtered_data[filtered_data["Date"].dt.year == int(year2)]
        except ValueError:
            return jsonify({"error": f"Invalid year2 value: {year2}"}), 400

    if data_year1.empty and data_year2.empty:
        return jsonify({"error": "No data found for the selected years."}), 404

    # Prepare response
    response = {}
    if not data_year1.empty:
        response["year1"] = data_year1[["Distance", "RL"]].sort_values(by="Distance").to_dict(orient="records")
    if not data_year2.empty:
        response["year2"] = data_year2[["Distance", "RL"]].sort_values(by="Distance").to_dict(orient="records")

    return jsonify(response)


@app.route('/download_data', methods=['GET'])
def download_data():
    global preloaded_data

    selectedStation = request.args.get('station') or request.args.get('station_id')
    if not selectedStation:
        return jsonify({"error": "No station selected."}), 400

    # For filtering: if Station_Name exists, we use it; otherwise, use Station_ID.
    if "Station_Name" in preloaded_data.columns:
        station_data = preloaded_data[preloaded_data["Station_Name"] == selectedStation]
    else:
        station_data = preloaded_data[preloaded_data["Station_ID"] == selectedStation]

    if station_data.empty:
        return jsonify({"error": "No data found for the selected station."}), 404

    # Apply filtering for Time Series (year, start_date, end_date)
    year = request.args.get('year')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # If a specific year is selected, filter by that year
    if year and year != "None":
        try:
            station_data = station_data[station_data["Date"].dt.year == int(year)]
        except ValueError:
            return jsonify({"error": "Invalid year format."}), 400

    # If start_date and end_date are provided, filter by the date range
    if start_date and end_date:
        try:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            station_data = station_data[(station_data["Date"] >= start_date) & (station_data["Date"] <= end_date)]
        except Exception as e:
            return jsonify({"error": "Invalid date format."}), 400

    # If no filtering criteria are met, return all data for the station
    if station_data.empty:
        return jsonify({"error": "No data available for the selected criteria."}), 404

    # Prepare the CSV data for download
    csv_data = station_data.to_csv(index=False)
    response = app.response_class(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=plot_data.csv"}
    )
    return response

@app.route('/')
def index():
    return render_template('index.html')

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == '__main__':
    Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)
