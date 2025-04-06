import streamlit as st
import pandas as pd
from datetime import date
import io
from openpyxl.styles import PatternFill

# Recommendations mapping per ad stage
recommendations_by_stage = {
    "Mockup": {
        "Low CTR": "CTR is under 0.75%. Test radically different visuals or curiosity-driven headlines. [Ref: Stage 3 – 03:45:10]",
        "High CPC": "CPC above threshold in mockup phase. Consider stronger hooks or clearer visual cues. [Ref: Stage 3 – 03:52:10]",
        "No engagement": "No engagement after $5. Kill ad and test a fresh creative angle. [Ref: Stage 3 – 03:49:22]",
        "Keep": "CTR is strong. Consider moving into Cycle 1 to test targeting. [Ref: Stage 3 – 03:58:00]"
    },
    "Cycle 1": {
        "Low CTR": "CTR under 0.75%. Try tightening your hook or using more urgency. [Ref: Stage 4 – 04:20:03]",
        "High CPC": "CPC is above your threshold. Adjust targeting or test broader audiences. [Ref: Stage 4 – 04:31:50]",
        "No engagement": "No CTR after $5. Kill ad or duplicate with bold creative shift. [Ref: Stage 4 – 04:12:45]",
        "Keep": "Good signals. Let it run and monitor CPC/CTR closely. [Ref: Stage 4 – 04:40:00]"
    },
    "Cycle 2": {
        "Low CTR": "CTR is under expected scaling performance. Consider fatigue or ad set saturation. [Ref: Stage 5 – 05:01:00]",
        "High CPC": "CPC too high. Restructure ad set or test budget split. [Ref: Stage 5 – 05:06:12]",
        "No ROAS": "No ROAS after $15. Review funnel, page load time, and offer clarity. [Ref: Stage 5 – 05:02:17]",
        "Keep": "Strong performer. Consider scaling or cloning into new audience segments. [Ref: Stage 5 – 05:14:03]"
    }
}

# Streamlit setup
st.set_page_config(page_title="Ad Performance Review", layout="centered")
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

st.title("📊 Ad Performance Review")
st.markdown("A stage-aware review tool that adapts recommendations based on your campaign phase.")

# Step 0: Choose Ad Stage
ad_stage = st.radio("What type of ads are you reviewing?", ["Mockup", "Cycle 1", "Cycle 2"])

st.subheader("Step 1: Upload Your File")
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"], key=st.session_state.upload_key)

# CPC threshold selector (now for all stages)
cpc_threshold = st.selectbox(
    "Select your CPC threshold ($)",
    [0.75, 1.00, 1.25, 1.50, 1.75, 2.00]
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    required_cols = [
        "Ad name", "Amount spent (USD)", "CTR (all)",
        "CPC (cost per link click) (USD)", "Link clicks",
        "Purchase ROAS (return on ad spend)"
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        st.stop()

    def evaluate(row):
        spend = row["Amount spent (USD)"]
        ctr = row["CTR (all)"]
        cpc = row["CPC (cost per link click) (USD)"]
        clicks = row["Link clicks"]
        roas = row["Purchase ROAS (return on ad spend)"]

        if ad_stage == "Mockup":
            if not (spend > 5 and pd.notna(clicks) and clicks >= 5):
                return "N", "Keep"
            if pd.isna(ctr) or ctr < 0.0075:
                return "Y", "Low CTR"
            elif cpc_threshold and cpc > cpc_threshold:
                return "Y", "High CPC"
            else:
                return "N", "Keep"

        elif ad_stage == "Cycle 1":
            if spend > 5 and (pd.isna(ctr) or ctr < 0.0075):
                return "Y", "Low CTR"
            elif cpc_threshold and cpc > cpc_threshold:
                return "Y", "High CPC"
            else:
                return "N", "Keep"

        elif ad_stage == "Cycle 2":
            if spend > 5 and (pd.isna(ctr) or ctr < 0.0075):
                return "Y", "Low CTR"
            elif cpc_threshold and cpc > cpc_threshold:
                return "Y", "High CPC"
            elif spend > 15 and (pd.isna(roas) or roas == 0):
                return "Y", "No ROAS"
            else:
                return "N", "Keep"

        return "N", "Keep"

    df[["Kill Criteria Met? (Y/N)", "Flag Reason"]] = df.apply(evaluate, axis=1, result_type="expand")

    review = pd.DataFrame({
        "Date of Report": [date.today()] * len(df),
        "Ad Name": df["Ad name"],
        "Amount Spent (USD)": df["Amount spent (USD)"],
        "CTR (%)": df["CTR (all)"].apply(lambda x: round(x, 2) if pd.notna(x) else "N/A"),
        "Link Clicks": df["Link clicks"].fillna("N/A"),
        "CPC (USD)": df["CPC (cost per link click) (USD)"].apply(lambda x: round(x, 2) if pd.notna(x) else "N/A"),
        "ROAS": df["Purchase ROAS (return on ad spend)"],
        "Kill Criteria Met? (Y/N)": df["Kill Criteria Met? (Y/N)"],
        "Action to Take": df["Flag Reason"].apply(lambda r: "Pause" if r != "Keep" else "Keep Running"),
        "Detailed Recommendation": df["Flag Reason"].apply(lambda r: recommendations_by_stage[ad_stage].get(r, "Review manually.")),
    })

    review["Notes"] = ""

    st.subheader("📊 Summary")
    st.write(f"**Total Ads:** {len(review)}")
    st.write(f"**Flagged for Action:** {(review['Kill Criteria Met? (Y/N)'] == 'Y').sum()}")

    def highlight(row):
        return ['background-color: #ffe6e6'] * len(row) if row['Kill Criteria Met? (Y/N)'] == 'Y' else ['background-color: #e6ffe6'] * len(row)

    st.subheader("Step 2: Review Results")
    st.dataframe(review.style.apply(highlight, axis=1))

    st.subheader("Step 3: Download")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        review.to_excel(writer, index=False, sheet_name="Ad Review")
        worksheet = writer.sheets["Ad Review"]
        red = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid")
        green = PatternFill(start_color="E6FFE6", end_color="E6FFE6", fill_type="solid")
        for idx, val in enumerate(review["Kill Criteria Met? (Y/N)"], start=2):
            fill = red if val == "Y" else green
            for col in range(1, len(review.columns)+1):
                worksheet.cell(row=idx, column=col).fill = fill

    st.download_button(
        label="📥 Download Ad Review Sheet",
        data=buffer.getvalue(),
        file_name="Ad_Review.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if st.button("🔄 Start Over"):
        st.session_state.upload_key += 1
        st.rerun()