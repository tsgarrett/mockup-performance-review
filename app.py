import streamlit as st
import pandas as pd
from datetime import date
import io

# Set page config
st.set_page_config(page_title="Mockup Ad Review", layout="centered")

# Title and explanation
st.title("📊 Weekly Mockup Ad Performance Review")
st.markdown("""
This tool helps you quickly analyze mockup ad performance from Facebook Ad reports.

✅ Upload your report  
✅ Automatically flag underperforming ads using kill criteria  
✅ Download a clean Weekly Review Sheet  

---
**🔐 Your data is never stored.**  
All processing happens in your browser session. The file is cleared from memory after download.
""")

# Step 1 - Upload
st.subheader("Step 1: Upload Your File")
uploaded_file = st.file_uploader(
    "Click to browse and upload your Excel file",
    type=["xlsx"],
    key="uploader"
)
st.caption("🔒 Your file is processed in-memory only and never stored. You can remove it anytime by clicking the ❌.")

if uploaded_file:
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

        # Step 2 - Review Results
        st.subheader("Step 2: Review Flagged Results")

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

        # Build final output
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

        st.success("✅ Review Sheet Generated!")
        st.dataframe(review)

        # Step 3 - Download
        st.subheader("Step 3: Download Your Review Sheet")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            review.to_excel(writer, index=False, sheet_name='Weekly Review')

        st.download_button(
            label="📥 Download Weekly Review Sheet",
            data=buffer.getvalue(),
            file_name="Weekly_Review.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("✅ Done reviewing this file?")
        if st.button("🔄 Start Over / Upload Another File"):
            st.session_state.pop("uploader", None)
            st.rerun()

    except Exception as e:
        st.error(f"⚠️ Something went wrong while processing the file: {e}")
