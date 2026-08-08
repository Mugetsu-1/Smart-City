"""Demand forecasting on the REAL published DOR series.

Trains a per-station trend model on the actual multi-year AADT series
published by the Department of Roads (2011/12 .. latest) and projects the
next count window. Everything is computed from real observed counts: no
synthetic training data exists anywhere.

The model is deliberately simple (linear trend via scikit-learn) because
the ground truth is a real but sparse yearly series; it generalises
honestly and its uncertainty is reported on every output.
"""

import sys
import os

import pandas as pd
from sklearn.linear_model import LinearRegression

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.data_feeds import load_demand_feed

MIN_YEARS_FOR_TREND = 4


def _next_window_label(last_year_int):
    """DOR fiscal label for the window after the latest published one.
    Example: last published 2024/25 (end 2025) -> '2025/26'."""
    return f"{last_year_int}/{format((last_year_int + 1) % 100, '02d')}"


def forecast_next_window(demand_df):
    """Forecast each station's next published count window.

    For every station with at least MIN_YEARS_FOR_TREND observed yearly
    AADT points, fits a linear trend (year -> aadt_pcu) and predicts the
    next fiscal window. Stations with too few published years are carried
    forward at their latest observed value (marked 'carry-forward').

    Returns (station_forecast_df, next_window_label).
    """
    stations = (
        demand_df[["stop_id", "stop_name", "route_id"]]
        .drop_duplicates("stop_id")
        .copy()
    )
    series = demand_df[["stop_id", "timestamp", "aadt_pcu"]].copy()
    series["year_num"] = series["timestamp"].dt.year

    next_window_year = int(series["year_num"].max()) + 1
    label = _next_window_label(next_window_year)
    next_window_dt = pd.Timestamp(year=next_window_year, month=1, day=1)

    records = []
    for stop_id, grp in series.groupby("stop_id"):
        grp = grp.sort_values("year_num").drop_duplicates("year_num")
        years = grp["year_num"].astype(float).values
        values = grp["aadt_pcu"].astype(float).values
        n_obs = len(grp)

        if n_obs >= MIN_YEARS_FOR_TREND:
            model = LinearRegression()
            model.fit(years.reshape(-1, 1), values)
            fitted = model.predict(years.reshape(-1, 1))
            forecast = float(model.predict([[next_window_year]])[0])
            sigma = float((values - fitted).std(ddof=1)) if n_obs > 2 else 0.0
            method = "trend"
        else:
            forecast = float(values[-1])
            sigma = 0.0
            method = "carry-forward"

        records.append(
            {
                "stop_id": stop_id,
                "forecast_aadt_pcu": max(0.0, float(round(forecast))),
                "forecast_sigma_pcu": float(round(sigma)),
                "forecast_method": method,
                "n_observed_years": int(n_obs),
                "forecast_year": label,
                "forecast_timestamp": next_window_dt,
            }
        )

    fore = pd.DataFrame(records)
    fore = stations.merge(fore, on="stop_id", how="left")

    latest = series.sort_values("timestamp").groupby("stop_id").tail(1)
    fore = fore.merge(
        latest[["stop_id", "aadt_pcu", "timestamp"]].rename(
            columns={"aadt_pcu": "latest_aadt_pcu", "timestamp": "latest_year_ts"}
        ),
        on="stop_id",
        how="left",
    )
    fore["latest_aadt_pcu"] = fore["latest_aadt_pcu"].fillna(fore["forecast_aadt_pcu"])
    fore["pct_change"] = (
        (fore["forecast_aadt_pcu"] - fore["latest_aadt_pcu"])
        / fore["latest_aadt_pcu"].clip(lower=1.0)
        * 100
    ).round(1)
    return fore, label


def main():
    print("Fetching live DOR data for forecasting...")
    demand_df = load_demand_feed(live=True)
    latest_year = demand_df["traffic_year"].max()
    fore, label = forecast_next_window(demand_df)

    print(f"\n--- Demand Forecast ({latest_year} -> {label}) ---")
    view = (
        fore[
            ["stop_name", "route_id", "latest_aadt_pcu", "forecast_aadt_pcu",
             "pct_change", "forecast_method", "n_observed_years"]
        ]
        .sort_values("forecast_aadt_pcu", ascending=False)
        .copy()
    )
    view.columns = ["Station", "Corridor", f"Latest ({latest_year})",
                    f"Forecast ({label})", "Delta %", "Method", "Obs Years"]
    print(view.to_string(index=False))

    total_latest = int(fore["latest_aadt_pcu"].sum())
    total_forecast = int(fore["forecast_aadt_pcu"].sum())
    print(
        f"\nSystem total   : {total_latest:,} -> {total_forecast:,} PCU/day "
        f"({(total_forecast - total_latest) / total_latest * 100:+.1f}%)"
    )


if __name__ == "__main__":
    main()