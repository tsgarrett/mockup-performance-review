import streamlit as st
import pandas as pd
from datetime import date
import io
from openpyxl.styles import PatternFill

# UPDATED Recommendations mapping based on new stage logic
recommendations_by_stage = {
    "Mockup": {
        "High CPC": "CPC is at or above threshold after $5 spend. Visual may not be appealing enough. Test new mockups.",
        "Keep": "CPC is below threshold ($1 target) after $5 spend. Good candidate visual.",
        # "Insufficient Data" handled separately
    },
    "Cycle 1": {
        "High CPC": "CPC is at or above threshold after $5 spend. Ad may not resonate broadly. Consider pausing or testing different angles.",
        "Keep": "CPC is below threshold ($1 target) after $5 spend. Good signal for broad appeal.",
        # "Insufficient Data" handled separately
    },
    "Cycle 2": {
        "No Purchases": "Spent over $15 but no purchases recorded (ROAS <= 0). Ad is not converting. Pause this ad.",
        "High CPC (Converting)": "Ad is converting (ROAS > 0), but CPC is high. Monitor profitability closely or test optimizations.",
        "Keep": "Ad is converting (ROAS > 0) with acceptable CPC. Strong performer.",
        # "Insufficient Data" handled separately
    }
}

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Ad Performance Review", layout="centered")
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

st.title("📊 Ad Performance Review")
st.markdown("A stage-aware review tool adapting recommendations based on the WeScale testing methodology.")

# --- Disclaimer ---
st.info(
    """
    **Disclaimer:** This tool is intended as an **aid** to your ad review process and should complement, **not replace**, your own judgment and analysis.
    It was created by a member for members and is **not an official product of, nor endorsed by, the WeScale Group Founders.**
    Always consider the full context of your campaigns when making decisions.
    """,
    icon="ℹ️"
)
# --- END DISCLAIMER ---


# --- User Inputs ---

# Step 0: Choose Ad Stage
ad_stage = st.radio(
    "Select Ad Stage:",
    ["Mockup", "Cycle 1", "Cycle 2"],
    horizontal=True
)

st.subheader("Step 1: Define Evaluation Thresholds")

# Use columns for better layout
col1, col2 = st.columns(2)

with col1:
    # CPC threshold selector - Defaulting to $1.00 as per Mockup/C1 rules
    cpc_threshold = st.selectbox(
        "Maximum Acceptable CPC ($)",
        [0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 5.00],
        index=2, # Default to 1.00
        help="Mockup & Cycle 1 typically aim for sub-$1 CPC. Cycle 2 considers this alongside conversions."
    )
    # Spend threshold for Cycle 2 ROAS evaluation
    cycle2_spend_threshold = st.number_input(
        "Spend threshold for Cycle 2 eval ($)",
        min_value=0.0,
        value=15.0, # Default based on previous logic, aligns with needing spend for purchase data
        step=1.00,
        format="%.2f",
        help="Minimum spend before evaluating Cycle 2 ads for purchase performance (ROAS)."
    )

with col2:
    # Spend threshold for initial evaluation (Mockup, Cycle 1)
    initial_spend_threshold = st.number_input(
        "Spend threshold for Mockup/Cycle 1 eval ($)",
        min_value=0.0,
        value=5.0, # Default based on rules
        step=0.50,
        format="%.2f",
        help="Minimum spend before evaluating Mockup & Cycle 1 ads for CPC."
    )


st.subheader("Step 2: Upload Your File")
# Updated note about required columns
st.markdown(
    """
    **Core Required Columns:** `Ad name`, `Amount spent (USD)`, `CPC (cost per link click) (USD)`, `Purchase ROAS (return on ad spend)`.

    *Note: `Link clicks` and `CTR (link click-through rate)` are included in the output table for informational context if present in your file, but are not used in the primary decision logic based on the current rules.*
    """
)
uploaded_file = st.file_uploader(
    "Upload your Facebook Ads Excel export (.xlsx)",
    type=["xlsx"],
    key=st.session_state.upload_key
)

# --- Main Processing Logic ---
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        # UPDATED required_cols list based on new logic
        # Core columns needed for logic:
        core_required_cols = [
            "Ad name", "Amount spent (USD)",
            "CPC (cost per link click) (USD)",
            "Purchase ROAS (return on ad spend)"
        ]
        # Optional columns for display:
        optional_cols = ["Link clicks", "CTR (link click-through rate)"]
        all_expected_cols = core_required_cols + optional_cols

        # Check for core required columns
        missing_core = [col for col in core_required_cols if col not in df.columns]
        if missing_core:
            st.error(f"Missing CORE required columns needed for logic: {', '.join(missing_core)}")
            st.stop()

        # Check for optional columns and note if missing (won't stop execution)
        missing_optional = [col for col in optional_cols if col not in df.columns]
        if missing_optional:
            st.caption(f"Note: Optional columns for display not found: {', '.join(missing_optional)}. They won't appear in the output table.")

        # Identify columns to convert to numeric (only those present)
        cols_to_convert = [
            "Amount spent (USD)", "CPC (cost per link click) (USD)", "Purchase ROAS (return on ad spend)"
        ]
        # Add optional numeric columns if they exist
        if "Link clicks" in df.columns:
            cols_to_convert.append("Link clicks")
        if "CTR (link click-through rate)" in df.columns:
            cols_to_convert.append("CTR (link click-through rate)")

        # Ensure numeric types where necessary, coerce errors to NaN
        for col in cols_to_convert:
            df[col] = pd.to_numeric(df[col], errors='coerce')


        # --- UPDATED Evaluation Function (Based on New Stage Rules) ---
        def evaluate(row):
            spend = row["Amount spent (USD)"]
            cpc = row["CPC (cost per link click) (USD)"]
            roas = row["Purchase ROAS (return on ad spend)"]
            # Clicks and CTR are not used in logic but available if needed later
            # clicks = row.get("Link clicks", None) # Use .get for optional cols
            # ctr = row.get("CTR (link click-through rate)", None)

            if ad_stage == "Mockup":
                # 1. Check Spend Validity
                if spend < initial_spend_threshold:
                    return "N", "Insufficient Data"
                # 2. Check Primary Metric: CPC
                # Treat NaN CPC as failing the threshold
                if pd.isna(cpc) or cpc >= cpc_threshold:
                    return "Y", "High CPC"
                # 3. Else (Spend >= threshold AND CPC < threshold)
                else:
                    return "N", "Keep"

            elif ad_stage == "Cycle 1":
                # Logic is identical to Mockup based on description
                # 1. Check Spend Validity
                if spend < initial_spend_threshold:
                    return "N", "Insufficient Data"
                # 2. Check Primary Metric: CPC
                if pd.isna(cpc) or cpc >= cpc_threshold:
                    return "Y", "High CPC"
                # 3. Else (Spend >= threshold AND CPC < threshold)
                else:
                    return "N", "Keep"

            elif ad_stage == "Cycle 2":
                # 1. Check Spend Validity
                if spend < cycle2_spend_threshold:
                    return "N", "Insufficient Data"
                # 2. Check Primary Metric: Conversions (ROAS > 0)
                if pd.isna(roas) or roas <= 0:
                    # Hasn't converted after enough spend
                    return "Y", "No Purchases"
                # 3. Else (Has Converted - ROAS > 0)
                else:
                    # Check Secondary Metric: CPC
                    if pd.isna(cpc) or cpc >= cpc_threshold:
                         # Converting, but CPC is high
                        return "Y", "High CPC (Converting)"
                    else:
                        # Converting and CPC is acceptable
                        return "N", "Keep"

            # Fallback (should not be reached)
            return "N", "Review Manually"

        # Apply the evaluation function
        df[["Kill Criteria Met? (Y/N)", "Flag Reason"]] = df.apply(evaluate, axis=1, result_type="expand")

        # Define UPDATED Action mapping based on new flags
        action_mapping = {
            "Keep": "Keep Running",
            "Insufficient Data": "Keep Running (Monitor)",
            "High CPC": "Pause/Review", # Flagged in Mockup/C1
            "No Purchases": "Pause/Kill", # Flagged in C2
            "High CPC (Converting)": "Optimize/Review", # Flagged in C2 but converting
            "Review Manually": "Review Manually"
        }

        # --- Prepare Output DataFrame ---
        # Build the dict dynamically based on available columns
        review_data = {
            "Date of Report": [date.today().strftime("%Y-%m-%d")] * len(df),
            "Ad Name": df["Ad name"],
            "Amount Spent (USD)": df["Amount spent (USD)"].round(2),
            # Optional: Link CTR
            "Link CTR (%)": df["CTR (link click-through rate)"].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A") if "CTR (link click-through rate)" in df.columns else ["N/A"] * len(df),
            # Optional: Link Clicks
            "Link Clicks": df["Link clicks"].apply(lambda x: int(x) if pd.notna(x) else "N/A") if "Link clicks" in df.columns else ["N/A"] * len(df),
            # Core Metrics for Logic
            "CPC (USD)": df["CPC (cost per link click) (USD)"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"),
            "ROAS": df["Purchase ROAS (return on ad spend)"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"),
            # Evaluation Results
            "Kill Criteria Met? (Y/N)": df["Kill Criteria Met? (Y/N)"],
            "Flag Reason": df["Flag Reason"],
            "Action to Take": df["Flag Reason"].map(action_mapping).fillna("Review Manually"),
            "Detailed Recommendation": df["Flag Reason"].apply(
                lambda r: recommendations_by_stage[ad_stage].get(r, "Check metrics manually based on flag reason.")
            ),
            "Notes": "" # Add empty Notes column
        }
        review = pd.DataFrame(review_data)


        # --- Display Results in Streamlit ---
        st.subheader("📊 Summary")
        flagged_count = (review['Kill Criteria Met? (Y/N)'] == 'Y').sum()
        st.write(f"**Total Ads Processed:** {len(review)}")
        st.write(f"**Ads Flagged for Action (Y):** {flagged_count}")

        # Highlighting function (adapted slightly for new flags)
        def highlight_rows(row):
            if row['Kill Criteria Met? (Y/N)'] == 'Y':
                 # Distinguish between hard fails and 'review' flags
                if row['Flag Reason'] in ["No Purchases", "High CPC"]: # Mockup/C1 High CPC might lead to kill
                    color = '#ffe6e6' # Light Red (Pause/Kill)
                elif row['Flag Reason'] == "High CPC (Converting)":
                    color = '#ffffe0' # Light Yellow (Optimize/Review - different from Insufficient Data)
                else:
                    color = '#ffe6e6' # Default Red for other Y flags
            elif row['Flag Reason'] == 'Insufficient Data':
                color = '#e6f7ff' # Light Blue (Monitor - distinct from green/red/yellow)
            else: # Keep
                color = '#e6ffe6' # Light green
            return [f'background-color: {color}'] * len(row)

        st.subheader("Step 3: Review Results")
        st.dataframe(review.style.apply(highlight_rows, axis=1), height=400)

        # --- Download Functionality ---
        st.subheader("Step 4: Download Report")
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            review.to_excel(writer, index=False, sheet_name="Ad Review")
            worksheet = writer.sheets["Ad Review"]

            # Define fills for Excel conditional formatting
            red_fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid") # Light Red
            green_fill = PatternFill(start_color="E6FFE6", end_color="E6FFE6", fill_type="solid") # Light Green
            yellow_fill = PatternFill(start_color="FFFFE0", end_color="FFFFE0", fill_type="solid") # Light Yellow (Optimize/Review)
            blue_fill = PatternFill(start_color="E6F7FF", end_color="E6F7FF", fill_type="solid") # Light Blue (Insufficient Data)


            kill_col_idx = review.columns.get_loc("Kill Criteria Met? (Y/N)") + 1
            reason_col_idx = review.columns.get_loc("Flag Reason") + 1

            for row_idx in range(2, len(review) + 2):
                kill_val = worksheet.cell(row=row_idx, column=kill_col_idx).value
                reason_val = worksheet.cell(row=row_idx, column=reason_col_idx).value

                fill_to_apply = None # Default no fill
                if reason_val == 'Insufficient Data':
                    fill_to_apply = blue_fill
                elif kill_val == 'Y':
                    if reason_val in ["No Purchases", "High CPC"]:
                         fill_to_apply = red_fill
                    elif reason_val == "High CPC (Converting)":
                         fill_to_apply = yellow_fill
                    else: # Default for any other Y flag
                        fill_to_apply = red_fill
                elif kill_val == 'N' and reason_val == 'Keep':
                    fill_to_apply = green_fill
                # else: Keep default fill (None)

                if fill_to_apply:
                    for col_idx in range(1, len(review.columns) + 1):
                        worksheet.cell(row=row_idx, column=col_idx).fill = fill_to_apply

            # Auto-adjust column widths
            for col in worksheet.columns:
                max_length = 0
                column = col[0].column_letter
                header_cell = worksheet[f"{column}1"]
                if header_cell.value:
                     max_length = len(str(header_cell.value))
                for cell in col:
                    if cell.row == 1: continue
                    try:
                        if cell.value:
                            cell_len = len(str(cell.value))
                            if cell_len > max_length: max_length = cell_len
                    except: pass
                adjusted_width = (max_length + 2) * 1.2
                if adjusted_width > 50: adjusted_width = 50
                worksheet.column_dimensions[column].width = adjusted_width

        st.download_button(
            label="📥 Download Formatted Ad Review Sheet (.xlsx)",
            data=buffer.getvalue(),
            file_name=f"Ad_Review_{ad_stage}_{date.today().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except FileNotFoundError:
        st.error("Uploaded file not found. Please ensure the file was uploaded correctly.")
    except KeyError as e:
         st.error(f"Missing CORE required column in the uploaded file: {e}. Please ensure your file includes all required columns for the logic.")
         st.info(f"Core required columns are: {', '.join(core_required_cols)}")
    except Exception as e:
        st.error(f"An error occurred during processing: {e}")
        st.exception(e)

# --- Start Over Button ---
st.divider()
if st.button("🔄 Start Over / Upload New File"):
    st.session_state.upload_key += 1
    st.rerun()