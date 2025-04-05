import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Mockup Ad Review", layout="centered")

st.title("📊 Weekly Mockup Ad Performance Review")
st.markdown("Upload your Facebook Ad report and choose the start of the week to generate your Weekly Review Sheet.")

uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])
week_start = st.date_input("Week Start Date")

if uploaded_file and week_start:
    df = pd.read_excel(uploaded_file)

    # Apply kill criteria logic
    def evaluate_ad(row):
        spend = row['Amount spent (USD)']
        ctr = row['CTR (all)']
        cpc = row['CPC (cost per link click) (USD)']
        clicks = row['Link clicks'] if not pd.isna(row['Link clicks']) else 0
        roas = row['Purchase ROAS (return on ad spend)']
        if spend > 5 and (pd.isna(ctr) or ctr < 0.005):
            return "Y", "Pause ad, no engagement"
        elif ctr is not None and ctr < 0.0075 and spend > 5:
            return "Y", "Low CTR, rework creative"
        elif cpc is not None and cpc > 3.00:
            return "Y", "High CPC, revise targeting"
        elif clicks < 3 and spend > 5:
            return "Y", "Low clicks, pause or test variation"
        elif spend > 15 and (pd.isna(roas) or roas == 0):
            return "Y", "No conversions, review funnel"
        else:
            return "N", "Keep running"

    df[['Kill Criteria Met? (Y/N)', 'Action Taken']] = df.apply(evaluate_ad, axis=1, result_type='expand')

    weekly_review = pd.DataFrame({
        "Week Start": [week_start] * len(df),
        "Ad Name": df["Ad name"],
        "Amount Spent (USD)": df["Amount spent (USD)"],
        "CTR (%)": df["CTR (all)"],
        "Link Clicks": df["Link clicks"],
        "CPC (USD)": df["CPC (cost per link click) (USD)"],
        "Conversions (Purchases)": df["Purchase ROAS (return on ad spend)"].apply(lambda x: "N/A" if pd.isna(x) else x),
        "ROAS": df["Purchase ROAS (return on ad spend)"],
        "Kill Criteria Met? (Y/N)": df["Kill Criteria Met? (Y/N)"],
        "Action Taken": df["Action Taken"],
        "Notes": ["" for _ in range(len(df))]
    })

    st.success("✅ Review Sheet Generated!")
    st.dataframe(weekly_review)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        weekly_review.to_excel(writer, index=False, sheet_name='Weekly Review')
    st.download_button("📥 Download Weekly Review Sheet", data=buffer.getvalue(), file_name="Weekly_Review.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
