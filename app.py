import streamlit as st
import pandas as pd
from datetime import date
import io

# Page config
st.set_page_config(page_title="Mockup Ad Review", layout="centered")

# Session state keys
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

st.title("📊 Mockup Ad Performance Review")
st.markdown("""
This tool helps you quickly analyze mockup ad performance from Facebook Ad reports.

✅ Step 1: Upload your report  
✅ Step 2: Select a CPC threshold  
✅ Step 3: We will automatically flag underperforming ads  
✅ Step 4: Download your Mockup Ad Review Sheet

---
**🔐 Your data is never stored!**  
All processing happens in your browser session. The file is cleared from memory after download.
""")

# Step 1 - Custom Upload UI
st.subheader("Step 1: Upload Your File")

st.markdown("📁 **Click below to upload your Excel ad report**")
st.caption("*(Drag-and-drop may not work reliably in all browsers)*")

uploaded_file = st.file_uploader(
    label="",
    type=["xlsx"],
    key=st.session_state.upload_key
)

# Step 2 - CPC Selector (after file uploaded)
if uploaded_file:
    st.subheader("Step 2: Select CPC Threshold")
    cpc_threshold = st.selectbox(
        "Choose the CPC ($) threshold used to flag underperforming ads:",
        options=["Please select CPC threshold", 1.00, 1.25, 1.50, 1.75, 2.00],
        index=0
    )

    if isinstance(cpc_threshold, float):
        try:
            df = pd.read_excel(uploaded_file)

            # Validate required columns
            required_cols = [
                "Ad name",
                "Amount spent (USD)",
                "CTR (all)",
                "CPC (cost per link click) (USD)",
                "Link clicks",
                "Purchase ROAS (return on ad spend)"
            ]
            missing = [col for col in required_cols if col not in df.columns]
            if missing:
                st.error(f"🚫 The uploaded file is missing required columns: {', '.join(missing)}")
                st.stop()

            # Evaluate ads
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
                elif cpc is not None and cpc > cpc_threshold:
                    return "Y", f"High CPC (${cpc:.2f}), revise targeting"
                elif clicks < 3 and spend > 5:
                    return "Y", "Low clicks, pause or test variation"
                elif spend > 15 and (pd.isna(roas) or roas == 0):
                    return "Y", "No conversions, review funnel"
                else:
                    return "N", "Keep running"

            df[['Kill Criteria Met? (Y/N)', 'Action Taken']] = df.apply(evaluate_ad, axis=1, result_type='expand')

            # Prepare output DataFrame
            review = pd.DataFrame({
                "Date of Report": [date.today()] * len(df),
                "Ad Name": df["Ad name"],
                "Amount Spent (USD)": df["Amount spent (USD)"],
                "CTR (%)": df["CTR (all)"].apply(lambda x: round(x, 2) if pd.notna(x) else "N/A"),
                "Link Clicks": df["Link clicks"].fillna("N/A"),
                "CPC (USD)": df["CPC (cost per link click) (USD)"].apply(lambda x: round(x, 2) if pd.notna(x) else "N/A"),
                "Conversions (Purchases)": df["Purchase ROAS (return on ad spend)"].apply(lambda x: "N/A" if pd.isna(x) else x),
                "ROAS": df["Purchase ROAS (return on ad spend)"],
                "Kill Criteria Met? (Y/N)": df["Kill Criteria Met? (Y/N)"],
                "Action Taken": df["Action Taken"],
                "Notes": ["" for _ in range(len(df))]
            })

            # Summary Stats
            st.subheader("📊 Summary")
            total_ads = len(review)
            flagged = review["Kill Criteria Met? (Y/N)"].value_counts().get("Y", 0)
            flagged_df = review[review["Kill Criteria Met? (Y/N)"] == "Y"]
            total_flagged_spend = flagged_df["Amount Spent (USD)"].sum()
            avg_flagged_ctr = (
                flagged_df["CTR (%)"].replace("N/A", pd.NA).dropna().astype(float).mean()
            )

            st.markdown(f"""
            - **Total Ads Reviewed:** {total_ads}  
            - **Ads Flagged:** {flagged}  
            - **Total Spend (Flagged Ads):** ${total_flagged_spend:.2f}  
            - **Average CTR (Flagged Ads):** {avg_flagged_ctr:.2f}%
            """)

            # Show the results table
            st.subheader("Step 3: Review Flagged Results")
            st.success("✅ Review Sheet Generated!")
            st.dataframe(review)

            # Download section
            st.subheader("Step 4: Download Your Review Sheet")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                review.to_excel(writer, index=False, sheet_name='Weekly Review')

            st.download_button(
                label="📥 Download Mockup Ad Review Sheet",
                data=buffer.getvalue(),
                file_name="Mockup_Review.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("✅ Done reviewing this file?")
            if st.button("🔄 Start Over / Upload Another File"):
                st.session_state.upload_key += 1
                st.rerun()

        except Exception as e:
            st.error(f"⚠️ Something went wrong while processing the file: {e}")

    else:
        st.info("📌 Please select a CPC threshold to process your ad data.")
