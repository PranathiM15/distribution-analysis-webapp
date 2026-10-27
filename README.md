# Distribution Studio — Task 27

A polished, local web app for **Distribution Analysis**. Upload a CSV, select a numeric variable, adjust the histogram bins, and inspect summary statistics plus three data-led observations.

## Tools used

- **Python** — local server and data analysis
- **Pandas** — CSV loading, numeric cleaning, descriptive statistics, quartiles and outlier checks
- **Matplotlib** — histogram image with mean and median reference lines
- HTML, CSS and JavaScript — responsive web interface

No Jupyter Notebook, Flask, Streamlit, database, or account/login is required. The app listens only on `127.0.0.1` and is intended for local use.

## Quick start (Windows)

1. Extract `distribution-analysis-webapp.zip`.
2. Open the extracted `distribution-analysis-webapp` folder.
3. Double-click **`run_app.bat`**. It checks for Python dependencies and installs Pandas/Matplotlib if needed.
4. Open **http://127.0.0.1:8000** in Chrome or Edge.
5. The student-performance sample loads automatically. Choose `Math_Score`, `Science_Score`, `English_Score`, `Study_Hours`, or `Attendance_Percent`; adjust bins; click **Generate analysis**.
6. To use your own data, choose **Drop your CSV file here**. Your CSV should have column headers and at least one numeric column.
7. When finished, return to the terminal and press **Ctrl+C**.

## Run from terminal instead

Open Command Prompt or PowerShell in the extracted folder, then run:

```powershell
py -m pip install -r requirements.txt
py server.py
```

Then open `http://127.0.0.1:8000` in your browser. Keep the terminal running while the app is open.

## Analysis delivered

- Histogram for a selected numeric variable; adjustable from 4 to 24 bins
- Valid observation count, mean, median, sample standard deviation, range and skewness
- At least three observations: distribution shape, centre/spread, and potential outliers/data coverage
- First-five-row CSV preview to verify the source data
- A built-in student-performance CSV so the app works immediately after launch

The IQR rule flags potential outliers for review; it does not delete them automatically. Blank or non-numeric values in the selected column are skipped for calculations and counted in the observations.

## GitHub upload

Create a **Public** repository named `distribution-analysis-webapp` at https://github.com/new. Do not initialise it with a README, `.gitignore`, or licence because this folder already includes a README and `.gitignore`. Follow the terminal push instructions provided with the task handoff.
