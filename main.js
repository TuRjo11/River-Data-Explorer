document.addEventListener('DOMContentLoaded', () => {
    const dataTypeDropdown = document.getElementById('data-type');
    const riverDropdown = document.getElementById('river');
    const stationDropdown = document.getElementById('station');
    const yearDropdown = document.getElementById('year');
    const year1Dropdown = document.getElementById('year1');
    const year2Dropdown = document.getElementById('year2');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const columnContainer = document.getElementById('column-container');
    const columnDropdown = document.getElementById('column');
    const mapDiv = document.getElementById('map');
    const chartCanvas = document.getElementById('chart');
    const loadingMessage = document.getElementById('loading-message');
    let mapInstance = null;
    let chartInstance = null;

    const showLoading = (message) => {
        loadingMessage.textContent = message;
        loadingMessage.style.display = 'block';
    };

    const hideLoading = () => {
        loadingMessage.style.display = 'none';
    };

    document.getElementById('load-data').addEventListener('click', async () => {
        const dataType = dataTypeDropdown.value;
    
        if (!dataType) {
            alert("Please select a data type!");
            return;
        }
    
        showLoading("Loading data...");
        try {
            let url = `/load_data?data_type=${encodeURIComponent(dataType)}`;
            // If Water level, include water_level_type from the new dropdown.
            if (dataType === "Water level") {
                const waterLevelType = document.getElementById('water-level-type').value;
                if (waterLevelType) {
                    url += `&water_level_type=${encodeURIComponent(waterLevelType)}`;
                }
            }
            const response = await fetch(url);    
    
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
    
            const rawResponse = await response.text();
            console.log("[DEBUG] Raw response:", rawResponse);
    
            let result;
            try {
                result = JSON.parse(rawResponse);
            } catch (error) {
                console.error("Failed to parse JSON:", rawResponse);
                throw new Error("Invalid JSON response from server.");
            }
    
            if (result.error) {
                alert(result.error);
                return;
            }
    
            // Populate the river dropdown
            riverDropdown.innerHTML = `<option value="None" selected>None</option>` + 
                                  result.rivers.map(r => `<option value="${r}">${r}</option>`).join('');
    
            // If Sediment data type, populate the sediment column dropdown as well.
            if (dataType === "Sediment" && result.sediment_columns) {
                columnDropdown.innerHTML = `<option value="" disabled selected>Choose a column</option>` +
                    result.sediment_columns.map(col => `<option value="${col}">${col}</option>`).join('');
            }
    
            alert("Data loaded successfully!");
        } catch (error) {
            console.error("Error loading data:", error);
            alert("Failed to load data. Please check the server and try again.");
        } finally {
            hideLoading();
        }
    });
    
    dataTypeDropdown.addEventListener('change', () => {
        const dataType = dataTypeDropdown.value;

        // Reset dependent dropdowns to default state
        riverDropdown.innerHTML = `<option value="" disabled selected>Choose a river</option>`;
        stationDropdown.innerHTML = `<option value="" disabled selected>Choose a station</option>`;
        yearDropdown.innerHTML = `<option value="None" selected>None</option>`;
        year1Dropdown.innerHTML = `<option value="None" selected>None</option>`;
        year2Dropdown.innerHTML = `<option value="None" selected>None</option>`;
        // Also reset the sediment column dropdown if present.
        columnDropdown.innerHTML = `<option value="" disabled selected>Choose a column</option>`;

        // Show water level type dropdown only for Water level datatype.
        const waterLevelTypeContainer = document.getElementById('water-level-type-container');
        if (dataType === "Water level") {
            waterLevelTypeContainer.style.display = "block";
        } else {
            waterLevelTypeContainer.style.display = "none";
        }
        
        // Reset the map if it exists
        if (mapInstance) {
            mapInstance.remove();
            mapInstance = null;
        }
        
        // Reset the chart if it exists
        if (chartInstance) {
            chartInstance.destroy();
            chartInstance = null;
        }        

        if (dataType === "Sediment") {
            columnContainer.style.display = "block";
        } else {
            columnContainer.style.display = "none";
            columnDropdown.innerHTML = `<option value="" disabled selected>Choose a column</option>`;
        }

        if (dataType === "Cross section") {
            document.getElementById('cross-section-options').style.display = "block";
            document.getElementById('time-series-options').style.display = "none";
        } else {
            document.getElementById('cross-section-options').style.display = "none";
            document.getElementById('time-series-options').style.display = "block";
        }
    });

    riverDropdown.addEventListener('change', async () => {
        const selectedRiver = riverDropdown.value;
        const selectedDataType = dataTypeDropdown.value;
    
        if (!selectedRiver) return;
    
        showLoading("Loading stations...");
        try {
            const response = await fetch(`/stations?river=${encodeURIComponent(selectedRiver)}&data_type=${encodeURIComponent(selectedDataType)}`);
            const result = await response.json();
    
            if (result.error) {
                alert(result.error);
                return;
            }
    
            console.log("[DEBUG] Loaded Stations:", result.stations);
    
            // Adjust station selection dropdown based on data type
            if (selectedDataType === "Cross section") {
                stationDropdown.innerHTML = `<option value="" disabled selected>Choose a station</option>` +
                    result.stations.map(station => `<option value="${station.Station_ID}">${station.Station_ID}</option>`).join('');
            } else {
                stationDropdown.innerHTML = `<option value="" disabled selected>Choose a station</option>` +
                    result.stations.map(station => station.Station_Name ? `<option value="${station.Station_Name}">${station.Station_Name}</option>` : '').join('');
            }
        } catch (error) {
            console.error("[DEBUG] Error loading stations:", error);
            alert("Failed to load stations.");
        } finally {
            hideLoading();
        }
    });
        
    stationDropdown.addEventListener('change', async () => {
        const selectedStation = stationDropdown.value;
        const selectedDataType = dataTypeDropdown.value;
    
        if (!selectedStation) return;
    
        showLoading("Fetching available years...");
        try {
            const response = await fetch(`/available_years?station_id=${encodeURIComponent(selectedStation)}`);
            const result = await response.json();
    
            if (result.error) {
                alert(result.error);
                return;
            }
    
            console.log("[DEBUG] Available Years:", result.years);
    
            const yearOptions = `<option value="None" selected>None</option>` +
                result.years.map(year => `<option value="${year}">${year}</option>`).join('');
    
            if (selectedDataType === "Cross section") {
                // Populate both XS comparison dropdowns
                year1Dropdown.innerHTML = yearOptions;
                year2Dropdown.innerHTML = yearOptions;
            } else {
                // Populate the single available years dropdown
                yearDropdown.innerHTML = yearOptions;
            }
        } catch (error) {
            console.error("[DEBUG] Error fetching available years:", error);
            alert("Failed to fetch available years.");
        } finally {
            hideLoading();
        }
    });
        
    document.getElementById('plot-data').addEventListener('click', async () => {
        const dataType = dataTypeDropdown.value;
        const selectedStation = stationDropdown.value;
    
        if (!selectedStation) {
            alert("Please select a station!");
            return;
        }
    
        showLoading("Plotting data...");
        try {
            let response;
            const params = new URLSearchParams();
    
            if (dataType === "Cross section") {
                // For cross-section plots, we use station_id and compare two years.
                const year1 = year1Dropdown.value;
                const year2 = year2Dropdown.value;
                params.set("station_id", selectedStation);
                if (year1 !== "None") params.append("year1", year1);
                if (year2 !== "None") params.append("year2", year2);
                response = await fetch(`/plot_cross_section?${params}`);
            } else {
                // For time series plots, we use station name along with date filters.
                params.append("station", selectedStation);
                params.append("data_type", dataType);
                const year = yearDropdown.value;
                if (year && year !== "None") {
                    params.append("year", year);
                } else {
                    const startDate = startDateInput.value;
                    const endDate = endDateInput.value;
                    params.append("start_date", startDate);
                    params.append("end_date", endDate);
                }
                // If the data type is Sediment, include the selected sediment column.
                if (dataType === "Sediment") {
                    const selectedColumn = columnDropdown.value;
                    if (selectedColumn) {
                        params.append("column", selectedColumn);
                    }
                }
                response = await fetch(`/plot_time_series?${params}`);
            }
    
            const result = await response.json();
    
            if (result.error) {
                alert(result.error);
                return;
            }
    
            // Check if there is no valid data (non-None) for the selected column
            if (dataType === "Sediment" && result.plot_data) {
                const selectedColumn = columnDropdown.value;
                const isValidDataAvailable = result.plot_data.some(point => point[selectedColumn] !== null && point[selectedColumn] !== undefined);
    
                if (!isValidDataAvailable) {
                    alert(`No data available for the selected sediment type: ${selectedColumn}`);
                    return;
                }
            }
    
            // Destroy any existing chart instance before creating a new one.
            if (chartInstance) chartInstance.destroy();
            const ctx = chartCanvas.getContext('2d');
            const datasets = [];
            let yAxisLabel = "Value";  // default for time series if not determined
    
            if (dataType === "Cross section") {
                // Build datasets for cross-section: x-axis is Distance, y-axis is RL.
                if (result.year1) {
                    datasets.push({
                        label: `Cross-Section ${year1Dropdown.value}`,
                        data: result.year1.map(point => ({ x: point.Distance, y: point.RL })),
                        borderColor: 'blue',
                        borderWidth: 2,
                        fill: false,
                    });
                }
                if (result.year2) {
                    datasets.push({
                        label: `Cross-Section ${year2Dropdown.value}`,
                        data: result.year2.map(point => ({ x: point.Distance, y: point.RL })),
                        borderColor: 'red',
                        borderWidth: 2,
                        fill: false,
                    });
                }
            } else {
                // Build dataset for time series: x-axis is Date, y-axis is the selected data value.
                if (!result.plot_data || result.plot_data.length === 0) {
                    alert("No time series data available.");
                    return;
                }
                // Determine the y-axis key (assumes the returned objects have a "Date" key and one other key)
                const sampleRecord = result.plot_data[0];
                const dataValueKey = Object.keys(sampleRecord).find(key => key !== "Date");
                yAxisLabel = dataValueKey || "Value";
                datasets.push({
                    label: `${dataType} - ${selectedStation}`,
                    data: result.plot_data.map(point => ({
                        x: new Date(point.Date),
                        y: point[dataValueKey]
                    })),
                    borderColor: 'blue',
                    borderWidth: 2,
                    fill: false,
                });
            }
    
            // Configure chart options.
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: dataType === "Cross section" ? "Distance (m)" : "Date"
                        },
                        type: dataType === "Cross section" ? 'linear' : 'time',
                        ...(dataType === "Cross section"
                            ? {
                                  ticks: {
                                      autoSkip: false, // show all tick intervals for Distance
                                  },
                                  offset: true, // extra space at the edges
                              }
                            : (dataType === "Water level" &&
                               document.getElementById('water-level-type').value === '3 or 6 Hourly Data')
                                ? {
                                      time: {
                                          unit: 'hour',
                                          tooltipFormat: 'MMM D, YYYY, HH:mm',
                                          displayFormats: {
                                              hour: 'MMM D, YYYY, HH:mm'
                                          }
                                      }
                                  }
                                : {
                                      time: {
                                          tooltipFormat: 'll'
                                      }
                                  })
                    },
                    y: {
                        title: {
                            display: true,
                            text: dataType === "Cross section" ? "RL (Elevation)" : yAxisLabel
                        }
                    }
                },
                layout: {
                    padding: dataType === "Cross section" ? { left: 20, right: 20 } : {}
                }
            };
    
            chartInstance = new Chart(ctx, {
                type: 'line',
                data: { datasets },
                options: chartOptions,
            });
        } catch (error) {
            console.error("[DEBUG] Error plotting data:", error);
            alert("Failed to plot data.");
        } finally {
            hideLoading();
        }
    });
                
    document.getElementById('download-data').addEventListener('click', async () => {
        const dataType = dataTypeDropdown.value;
        const selectedStation = stationDropdown.value;
        let queryParams;
    
        if (dataType === "Cross section") {
            const year1 = year1Dropdown.value;
            const year2 = year2Dropdown.value;
            queryParams = new URLSearchParams({
                station_id: selectedStation
            });
    
            if (year1 && year1 !== "None") {
                queryParams.append("year1", year1);
            }
            if (year2 && year2 !== "None") {
                queryParams.append("year2", year2);
            }
        } else {
            const selectedYear = yearDropdown.value;
            const startDate = startDateInput.value;
            const endDate = endDateInput.value;
    
            queryParams = new URLSearchParams({
                station: selectedStation,
                year: selectedYear,
                start_date: startDate,
                end_date: endDate,
            });
        }
    
        try {
            const response = await fetch(`/download_data?${queryParams}`);
            if (!response.ok) {
                throw new Error(`Failed to download data: ${response.statusText}`);
            }
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", "plot_data.csv");
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error("Error downloading data:", error);
            alert("Failed to download data. Please try again.");
        }
    });
                            
    document.getElementById('show-map').addEventListener('click', async () => {
        const selectedRiver = riverDropdown.value;
        const selectedDataType = dataTypeDropdown.value;
        if (!selectedRiver) {
            alert("Please select a river!");
            return;
        }
    
        try {
            // Include data_type so that the /stations endpoint knows which columns to return.
            const response = await fetch(`/stations?river=${encodeURIComponent(selectedRiver)}&data_type=${encodeURIComponent(selectedDataType)}`);
            const result = await response.json();
    
            if (result.error) {
                alert(result.error);
                return;
            }
    
            if (result.stations.length === 0) {
                alert("No station data available for the selected river.");
                return;
            }
    
            if (mapInstance) {
                mapInstance.remove();
            }
    
            // Use the first station's coordinates to center the map.
            const firstStation = result.stations[0];
            const lat = firstStation.Latitude;
            const lon = firstStation.Longitude;
            mapInstance = L.map(mapDiv).setView([lat, lon], 8);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(mapInstance);
    
            result.stations.forEach(station => {
                // Build popup content based on data type.
                let popupContent = '';
                const stationId = station.Station_ID || "No ID available"; // Ensure Station_ID is available
                const riverName = station.River || "No River available";  // Display River name
                const stationType = station.Station_Type || "No Type available";  // Display Station Type (Tidal or Non-Tidal)
    
                if (selectedDataType === "Cross section") {
                    // Cross section: only Station_ID is available.
                    popupContent = `<b>Station ID:</b> ${stationId}<br>
                                    <b>River:</b> ${riverName}<br>  <!-- Add River to popup -->
                                    <b>Station Type:</b> ${stationType}<br> <!-- Add Station_Type to popup -->
                                    <b>Latitude:</b> ${station.Latitude.toFixed(5)}<br>
                                    <b>Longitude:</b> ${station.Longitude.toFixed(5)}`;
                } else {
                    // Other datatypes: Station_Name is available.
                    popupContent = `<b>Station Name:</b> ${station.Station_Name || "No name available"}<br>
                                    <b>Station ID:</b> ${stationId}<br>
                                    <b>River:</b> ${riverName}<br>  <!-- Add River to popup -->
                                    <b>Station Type:</b> ${stationType}<br>  <!-- Add Station_Type to popup -->
                                    <b>Latitude:</b> ${station.Latitude.toFixed(5)}<br>
                                    <b>Longitude:</b> ${station.Longitude.toFixed(5)}`;
                }
    
                L.marker([station.Latitude, station.Longitude])
                    .addTo(mapInstance)
                    .bindPopup(popupContent);
            });
        } catch (error) {
            console.error("Error loading map data:", error);
            alert("Failed to load map data.");
        }
    });
    
    
});
