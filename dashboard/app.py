
import streamlit as st
import pandas as pd
import plotly.express as px
import joblib
import requests
from pathlib import Path

st.set_page_config(
    page_title="4F ShockRadar AI",
    page_icon="🌍",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "commodity_monthly_changes.csv"
MODEL_DIR = BASE_DIR / "models"

st.title("🌍 4F ShockRadar AI")
st.caption("AI-powered commodity price risk monitoring")

@st.cache_data
def load_data():
    data = pd.read_csv(DATA_PATH)
    data["observation_date"] = pd.to_datetime(data["observation_date"])
    return data

@st.cache_resource
def load_models():
    logistic = joblib.load(MODEL_DIR / "logistic_shock_model.pkl")
    forest = joblib.load(MODEL_DIR / "random_forest_shock_model.pkl")
    thresholds = joblib.load(MODEL_DIR / "model_thresholds.pkl")
    return logistic, forest, thresholds

try:
    df = load_data()
    logistic_model, rf_model, thresholds = load_models()
except Exception as error:
    st.error(f"Could not load project data or models: {error}")
    st.stop()

# Prepare latest features for each commodity
def get_predictions(data):
    data = data.sort_values(
        ["commodity_name", "observation_date"]
    ).copy()

    data["monthly_change_pct"] = (
        data.groupby("commodity_name")["price"].pct_change() * 100
    )

    data["previous_month_change_pct"] = (
        data.groupby("commodity_name")["monthly_change_pct"].shift(1)
    )

    data["three_month_avg_change_pct"] = (
        data.groupby("commodity_name")["monthly_change_pct"]
        .transform(lambda x: x.rolling(3, min_periods=3).mean())
    )

    latest = (
        data.groupby("commodity_name", group_keys=False)
        .tail(1)
        .dropna(subset=[
            "monthly_change_pct",
            "previous_month_change_pct",
            "three_month_avg_change_pct"
        ]).copy()
    )

    features = [
        "monthly_change_pct",
        "previous_month_change_pct",
        "three_month_avg_change_pct",
        "commodity_name"
    ]

    latest["logistic_probability"] = (
        logistic_model.predict_proba(latest[features])[:, 1]
    )

    latest["random_forest_probability"] = (
        rf_model.predict_proba(latest[features])[:, 1]
    )

    latest["logistic_warning"] = (
        latest["logistic_probability"] >= thresholds["logistic"]
    )

    latest["random_forest_warning"] = (
        latest["random_forest_probability"] >= thresholds["random_forest"]
    )

    return latest

predictions = get_predictions(df)

latest_date = df["observation_date"].max()

# Summary metrics
c1, c2, c3, c4 = st.columns(4)

c1.metric("Commodities tracked", df["commodity_name"].nunique())
c2.metric("Historical records", f"{len(df):,}")
c3.metric("Latest data", latest_date.strftime("%b %Y"))
c4.metric(
    "Flagged by both models",
    int((predictions["logistic_warning"] &
         predictions["random_forest_warning"]).sum())
)

st.divider()

# Navigation
page = st.sidebar.radio(
    "Dashboard sections",
    [
        "Overview",
        "Price Trends",
        "ML Risk Predictions",
        "AI Business Report"
    ]
)

if page == "Overview":
    st.subheader("Commodity Risk Overview")

    st.write(
        "Monitor historical international commodity prices and "
        "experimental machine learning warnings."
    )

    summary = predictions[[
        "commodity_name",
        "price",
        "monthly_change_pct",
        "logistic_probability",
        "random_forest_probability"
    ]].copy()

    summary["logistic_probability"] *= 100
    summary["random_forest_probability"] *= 100

    summary = summary.rename(columns={
        "commodity_name": "Commodity",
        "price": "Latest price",
        "monthly_change_pct": "Monthly change (%)",
        "logistic_probability": "Logistic probability (%)",
        "random_forest_probability": "Random Forest probability (%)"
    })

    st.dataframe(
        summary.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "The model estimates the probability of a price increase of "
        "10% or more in the following month. Warnings are not guarantees."
    )

elif page == "Price Trends":
    st.subheader("Historical Commodity Price Analysis")

    commodity = st.selectbox(
        "Choose a commodity",
        sorted(df["commodity_name"].unique())
    )

    selected = df[df["commodity_name"] == commodity].sort_values(
        "observation_date"
    )

    price_chart = px.line(
        selected,
        x="observation_date",
        y="price",
        title=f"{commodity} – Historical Price Trend"
    )

    st.plotly_chart(price_chart, use_container_width=True)

    change_chart = px.bar(
        selected,
        x="observation_date",
        y="monthly_change_pct",
        title="Monthly Percentage Change"
    )

    st.plotly_chart(change_chart, use_container_width=True)

elif page == "ML Risk Predictions":
    st.subheader("Machine Learning Risk Predictions")

    result = predictions.copy()

    def classify(row):
        if row["logistic_warning"] and row["random_forest_warning"]:
            return "Both models"
        if row["logistic_warning"]:
            return "Logistic only"
        if row["random_forest_warning"]:
            return "Random Forest only"
        return "Neither model"

    result["risk_category"] = result.apply(classify, axis=1)

    st.dataframe(
        result[[
            "commodity_name",
            "price",
            "monthly_change_pct",
            "logistic_probability",
            "random_forest_probability",
            "risk_category"
        ]].round(3),
        use_container_width=True,
        hide_index=True
    )

    chart_data = result.melt(
        id_vars="commodity_name",
        value_vars=[
            "logistic_probability",
            "random_forest_probability"
        ],
        var_name="Model",
        value_name="Probability"
    )

    chart_data["Probability"] *= 100

    fig = px.bar(
        chart_data,
        x="commodity_name",
        y="Probability",
        color="Model",
        barmode="group",
        title="Estimated Probability of Next-Month Price Shock",
        labels={"Probability": "Probability (%)"}
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Thresholds: Logistic Regression = 0.50; "
        "Random Forest = 0.40. These are experimental model thresholds."
    )


elif page == "AI Business Report":
    st.subheader("AI-Generated Business Risk Report")

    st.write(
        "Python calculates the model classifications. "
        "Llama generates the business interpretation."
    )

    # Classification is performed deterministically in Python
    result = predictions.copy()

    both = result[
        result["logistic_warning"] &
        result["random_forest_warning"]
    ]["commodity_name"].tolist()

    logistic_only = result[
        result["logistic_warning"] &
        ~result["random_forest_warning"]
    ]["commodity_name"].tolist()

    rf_only = result[
        ~result["logistic_warning"] &
        result["random_forest_warning"]
    ]["commodity_name"].tolist()

    neither = result[
        ~result["logistic_warning"] &
        ~result["random_forest_warning"]
    ]["commodity_name"].tolist()

    st.markdown("### Verified model classifications")

    classification = pd.DataFrame({
        "Category": [
            "Both models",
            "Logistic Regression only",
            "Random Forest only",
            "Neither model"
        ],
        "Commodities": [
            ", ".join(both) or "None",
            ", ".join(logistic_only) or "None",
            ", ".join(rf_only) or "None",
            ", ".join(neither) or "None"
        ]
    })

    st.dataframe(
        classification,
        use_container_width=True,
        hide_index=True
    )

    if st.button("Generate AI Business Report"):

        prompt = f"""
        You are a professional commodity risk analyst.

        Write a concise business risk report using these
        VERIFIED classifications calculated by Python.

        Commodities flagged by both models: {both}

        Flagged only by Logistic Regression: {logistic_only}

        Flagged only by Random Forest: {rf_only}

        Not flagged by either model: {neither}

        Latest data date: {latest_date.date()}

        Prediction target: price increase of 10% or more
        in the following month.

        Rules:
        1. Do not change or recalculate the classifications.
        2. Do not move commodities between categories.
        3. Do not describe unflagged commodities as high risk.
        4. Explain that probabilities are estimates, not guarantees.
        5. Recommend monitoring, not guaranteed price increases.
        6. Mention that the dataset contains international
           commodity prices, not Indian retail prices.

        Write these sections:
        - Executive Summary
        - Key Business Risks
        - Recommended Monitoring Actions
        - Limitations
        - Conclusion

        Use professional, concise business language.
        """

        try:
            with st.spinner("Generating report using local Llama AI..."):

                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2:1b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 450
                        }
                    },
                    timeout=(10, 180)
                )

                response.raise_for_status()
                report = response.json()["response"]

            st.markdown("### AI-Generated Report")
            st.markdown(report)

        except requests.exceptions.RequestException as error:
            st.error(f"Ollama connection error: {error}")


st.divider()

st.caption(
    "Data source: World Bank Commodity Markets. "
    "Historical international prices, not Indian retail prices. "
    "Experimental decision-support system."
)
