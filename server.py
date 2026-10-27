"""Local Distribution Analysis web app (Python stdlib + pandas + matplotlib)."""
from __future__ import annotations

import base64
import io
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8000
MAX_BODY = 10 * 1024 * 1024


def json_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")


def read_dataframe(csv_text: str) -> pd.DataFrame:
    if not isinstance(csv_text, str) or not csv_text.strip():
        raise ValueError("The CSV file is empty. Please upload a CSV with a header row and data.")
    try:
        frame = pd.read_csv(io.StringIO(csv_text))
    except Exception as exc:
        raise ValueError(f"Could not read this CSV: {exc}") from exc
    if frame.empty:
        raise ValueError("The CSV has a header but no data rows.")
    if len(frame.columns) == 0:
        raise ValueError("No columns were found. Make sure the first row contains column names.")
    frame.columns = [str(column).strip() or f"Column {i + 1}" for i, column in enumerate(frame.columns)]
    return frame


def numeric_columns(frame: pd.DataFrame) -> list[str]:
    result: list[str] = []
    for column in frame.columns:
        series = frame[column]
        if pd.api.types.is_numeric_dtype(series):
            converted = pd.to_numeric(series, errors="coerce")
        else:
            converted = pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False), errors="coerce")
        valid = int(converted.notna().sum())
        # Include columns that are truly numeric or are mostly numeric strings.
        if valid >= 2 and valid / max(len(series), 1) >= 0.8:
            result.append(str(column))
    return result


def clean_preview(frame: pd.DataFrame) -> list[dict]:
    preview_json = frame.head(5).to_json(orient="records", date_format="iso")
    return json.loads(preview_json)


def analyze(csv_text: str, column: str, bins: int) -> dict:
    frame = read_dataframe(csv_text)
    candidates = numeric_columns(frame)
    if column not in candidates:
        raise ValueError("Choose a numeric column from the list before generating the histogram.")
    series = pd.to_numeric(
        frame[column].astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    )
    missing = int(series.isna().sum())
    values = series.dropna().astype(float)
    if len(values) < 2:
        raise ValueError("This column needs at least two valid numeric values to build a histogram.")

    bins = max(4, min(int(bins), 24))
    count = int(values.count())
    mean = float(values.mean())
    median = float(values.median())
    std = float(values.std(ddof=1)) if count > 1 else 0.0
    minimum = float(values.min())
    maximum = float(values.max())
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    skew_val = float(values.skew()) if count >= 3 and pd.notna(values.skew()) else 0.0
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    outliers = int(((values < lower_fence) | (values > upper_fence)).sum())
    value_range = maximum - minimum

    if abs(skew_val) < 0.5:
        shape = "roughly symmetric"
        shape_detail = "The values are fairly balanced around the centre."
    elif skew_val >= 0.5:
        shape = "right-skewed"
        shape_detail = "A longer tail extends toward higher values."
    else:
        shape = "left-skewed"
        shape_detail = "A longer tail extends toward lower values."

    if mean > median:
        centre_detail = "The mean is above the median, so higher observations pull the average upward."
    elif mean < median:
        centre_detail = "The mean is below the median, so lower observations pull the average downward."
    else:
        centre_detail = "The mean and median are equal, indicating the centre measures agree closely."

    observations = [
        {
            "title": "Shape & skewness",
            "text": f"The distribution is {shape} (skewness {skew_val:.2f}). {shape_detail}",
        },
        {
            "title": "Centre & spread",
            "text": f"Mean: {mean:.2f}; median: {median:.2f}. {centre_detail} The values span {minimum:.2f} to {maximum:.2f}, with an IQR of {iqr:.2f}.",
        },
        {
            "title": "Potential outliers & coverage",
            "text": f"The IQR rule flags {outliers} potential outlier(s). {count} numeric values were analyzed; {missing} blank or non-numeric value(s) were skipped. Review flagged values in context rather than removing them automatically.",
        },
    ]

    # Matplotlib creates a real histogram image for the report/dashboard.
    fig, ax = plt.subplots(figsize=(9.2, 4.6), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fbfcfe")
    n, edges, patches = ax.hist(values, bins=bins, color="#ee8354", edgecolor="#ffffff", linewidth=1.4, alpha=0.95)
    ax.axvline(mean, color="#243b53", linewidth=2.0, linestyle="--", label=f"Mean {mean:.2f}")
    ax.axvline(median, color="#1c8c8c", linewidth=2.0, linestyle="-", label=f"Median {median:.2f}")
    ax.set_title(f"Distribution of {column}", loc="left", fontsize=15, fontweight="bold", color="#182b49", pad=16)
    ax.set_xlabel(column, fontsize=10, color="#52637a", labelpad=9)
    ax.set_ylabel("Frequency", fontsize=10, color="#52637a", labelpad=9)
    ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.23, color="#8190a5")
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#d9e0e8")
    ax.spines["bottom"].set_color("#d9e0e8")
    ax.tick_params(colors="#65758b", labelsize=9)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    fig.tight_layout(pad=1.5)
    output = io.BytesIO()
    fig.savefig(output, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    histogram = "data:image/png;base64," + base64.b64encode(output.getvalue()).decode("ascii")

    return {
        "filename": "uploaded CSV",
        "column": column,
        "bins": bins,
        "rows": int(len(frame)),
        "count": count,
        "missing": missing,
        "stats": [
            {"label": "Valid values", "value": f"{count:,}", "detail": f"of {len(frame):,} rows"},
            {"label": "Mean", "value": f"{mean:,.2f}", "detail": "arithmetic average"},
            {"label": "Median", "value": f"{median:,.2f}", "detail": "middle value"},
            {"label": "Std. deviation", "value": f"{std:,.2f}", "detail": "sample spread"},
            {"label": "Range", "value": f"{value_range:,.2f}", "detail": f"{minimum:,.2f}–{maximum:,.2f}"},
            {"label": "Skewness", "value": f"{skew_val:,.2f}", "detail": shape},
        ],
        "observations": observations,
        "histogram": histogram,
        "preview": clean_preview(frame),
        "all_columns": [str(c) for c in frame.columns],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "DistributionStudio/1.0"

    def send_bytes(self, data: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: int = 200) -> None:
        self.send_bytes(json_bytes(payload), "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            path = "/index.html"
        candidate = (ROOT / path.lstrip("/")).resolve()
        if ROOT not in candidate.parents and candidate != ROOT:
            self.send_json({"error": "Invalid path."}, 403)
            return
        if not candidate.is_file():
            self.send_json({"error": "File not found."}, 404)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or candidate.suffix in {".js", ".json"}:
            content_type += "; charset=utf-8"
        try:
            self.send_bytes(candidate.read_bytes(), content_type)
        except OSError:
            self.send_json({"error": "Could not read the requested file."}, 500)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                self.send_json({"error": "Request must contain CSV text under 10 MB."}, 413)
                return
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            csv_text = payload.get("csv", "")
            if path == "/api/inspect":
                frame = read_dataframe(csv_text)
                numeric = numeric_columns(frame)
                if not numeric:
                    raise ValueError("No numeric columns were detected. Try a CSV with numerical values such as marks, sales, prices, or hours.")
                self.send_json({
                    "columns": numeric,
                    "rows": int(len(frame)),
                    "column_count": int(len(frame.columns)),
                    "preview": clean_preview(frame),
                    "all_columns": [str(c) for c in frame.columns],
                })
                return
            if path == "/api/analyze":
                result = analyze(csv_text, str(payload.get("column", "")), int(payload.get("bins", 10)))
                result["filename"] = str(payload.get("filename", "uploaded CSV"))[:150]
                self.send_json(result)
                return
            self.send_json({"error": "Endpoint not found."}, 404)
        except (ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            self.send_json({"error": str(exc)}, 400)
        except Exception as exc:  # Keep the local interface readable when a file is malformed.
            self.send_json({"error": f"Analysis failed: {exc}"}, 500)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        print(f"[{self.log_date_time_string()}] {args[0] if args else ''}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 58)
    print("  DISTRIBUTION STUDIO — Local analysis server")
    print(f"  Open this address in your browser: http://{HOST}:{PORT}")
    print("  Keep this terminal open while using the app.")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 58)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Distribution Studio...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
