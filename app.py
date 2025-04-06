import streamlit as st
import pandas as pd
from datetime import date
import io
from openpyxl.styles import PatternFill

# Recommendations mapping - reflecting the default formula outcomes
recommendations_by_stage = {
    "Mockup": {
        "Fail": "Did not meet criteria based on thresholds set (Default: Spend ≥ $5 AND CPC < $1).",
        "Keep": "✅ Meets criteria based on thresholds set (Default: Spend ≥ $5 AND CPC < $1). Good candidate visual.",
        "Insufficient Data": "Spend is below the minimum threshold for evaluation.",
    },
    "Cycle 1": {
        "Fail": "Did not meet criteria based on thresholds set (Default: Spend ≥ $5 AND CPC < $1).",
        "Keep": "✅ Meets criteria based on thresholds set (Default: Spend ≥ $5 AND CPC < $1). Good signal for broad appeal.",
        "Insufficient Data": "Spend is below the minimum threshold for evaluation.",
    },
    "Cycle 2": {
        "Fail": "Did not meet criteria based on thresholds set (Default: Spend ≥ $10 AND CPC < $1 AND Purchases ≥ 1).",
        "Keep": "✅ Meets criteria based on thresholds set (Default: Spend ≥ $10 AND CPC < $1 AND Purchases ≥ 1). Potential winner.",
        "Insufficient Data": "Spend is below the minimum threshold for evaluation.",
    }
}

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Ad Performance Review", layout="centered")
if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

st.title("📊 Ad Performance Review")
st.markdown("Applies the WeScale testing formulas with stage-specific defaults, allowing adjustments.")

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
    horizontal=True,
    help="Select the stage corresponding to the ads in your uploaded file. Defaults will adjust below."
)

st.subheader("Step 1: Adjust Evaluation Criteria (Defaults Set by Stage)")

# --- Determine Defaults Based on Stage ---
if ad_stage == "Mockup" or ad_stage == "Cycle 1":
    default_cpc_index = 2 # Index for $1.00
    default_initial_spend = 5.0
    default_cycle2_spend = 10.0 # Keep a sensible default even if not primary
elif ad_stage == "Cycle 2":
    default_cpc_index = 2 # Index for $1.00
    default_initial_spend = 5.0 # Keep a sensible default
    default_cycle2_spend = 10.0
else: # Fallback (shouldn't happen)
    default_cpc_index = 2
    default_initial_spend = 5.0
    default_cycle2_spend = 10.0

# --- Input Widgets with Dynamic Defaults ---
col1, col2 = st.columns(2)

with col1:
    cpc_threshold = st.selectbox(
        "CPC Threshold (< $)",
        options=[0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00, 2.50, 3.00, 5.00],
        index=default_cpc_index, # Set default based on stage
        help="Ad CPC must be STRICTLY LESS THAN this value. Default is $1.00."
    )
    # Purchase check explanation (no widget needed, uses ROAS > 0)
    if ad_stage == "Cycle 2":
         st.caption("Purchase check requires ROAS > 0 in data.")
         # Placeholder to balance columns
         st.container()


with col2:
    # Separate spend thresholds for clarity, using stage-based defaults
    initial_spend_threshold = st.number_input(
        "Min Spend Mockup/Cycle 1 ($)",
        min_value=0.0,
        value=default_initial_spend, # Set default based on stage logic
        step=0.50,
        format="%.2f",
        help="Minimum spend before evaluating Mockup & Cycle 1 ads. Default: $5.00"
    )
    cycle2_spend_threshold = st.number_input(
        "Min Spend Cycle 2 ($)",
        min_value=0.0,
        value=default_cycle2_spend, # Set default based on stage logic
        step=1.00,
        format="%.2f",
        help="Minimum spend before evaluating Cycle 2 ads. Default: $10.00"
    )


st.subheader("Step 2: Upload Your File")
st.markdown(
    """
    **Core Required Columns:** `Ad name`, `Amount spent (USD)`, `CPC (cost per link click) (USD)`, `Purchase ROAS (return on ad spend)`.

    *Note: `Link clicks` and `CTR (link click-through rate)` can be included for informational context.*
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
        # Core columns needed for logic:
        core_required_cols = [
            "Ad name", "Amount spent (USD)",
            "CPC (cost per link click) (USD)",
            "Purchase ROAS (return on ad spend)" # Used for Purchase check in Cycle 2
        ]
        # Optional columns for display:
        optional_cols = ["Link clicks", "CTR (link click-through rate)"]

        # Check for core required columns
        missing_core = [col for col in core_required_cols if col not in df.columns]
        if missing_core:
            st.error(f"Missing CORE required columns needed for logic: {', '.join(missing_core)}")
            st.stop()

        # Check for optional columns
        missing_optional = [col for col in optional_cols if col not in df.columns]
        if missing_optional:
            st.caption(f"Note: Optional columns for display not found: {', '.join(missing_optional)}.")

        # Identify columns to convert to numeric
        cols_to_convert = core_required_cols[1:] # Skip 'Ad name'
        if "Link clicks" in df.columns: cols_to_convert.append("Link clicks")
        if "CTR (link click-through rate)" in df.columns: cols_to_convert.append("CTR (link click-through rate)")

        # Ensure numeric types
        for col in cols_to_convert:
             if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')


        # --- Evaluation Function (Using Widget Values) ---
        def evaluate(row):
            spend = row["Amount spent (USD)"]
            cpc = row["CPC (cost per link click) (USD)"]
            roas = row["Purchase ROAS (return on ad spend)"]

            # Conditions based on WIDGET values
            # Note: Using the user-selected CPC threshold from the selectbox
            is_cpc_valid = pd.notna(cpc) and cpc < cpc_threshold
            has_purchase = pd.notna(roas) and roas > 0

            if ad_stage == "Mockup":
                # Using the user-selected initial_spend_threshold from number_input
                if spend < initial_spend_threshold:
                    return "N", "Insufficient Data"
                if is_cpc_valid: # Pass if CPC is valid
                    return "N", "Keep"
                else: # Fail if CPC is invalid
                    return "Y", "Fail"

            elif ad_stage == "Cycle 1":
                 # Using the user-selected initial_spend_threshold
                if spend < initial_spend_threshold:
                    return "N", "Insufficient Data"
                if is_cpc_valid: # Pass if CPC is valid
                    return "N", "Keep"
                else: # Fail if CPC is invalid
                    return "Y", "Fail"

            elif ad_stage == "Cycle 2":
                 # Using the user-selected cycle2_spend_threshold
                if spend < cycle2_spend_threshold:
                    return "N", "Insufficient Data"
                # Check winner condition: Spend OK, CPC OK, Purchase OK
                if is_cpc_valid and has_purchase:
                    return "N", "Keep"
                else: # Fail if any condition not met
                    return "Y", "Fail"

            # Fallback
            return "N", "Review Manually"

        # Apply the evaluation function
        df[["Flagged? (Y/N)", "Result"]] = df.apply(evaluate, axis=1, result_type="expand")

        # Define Action mapping
        action_mapping = {
            "Keep": "Keep Running (Pass)",
            "Insufficient Data": "Keep Running (Monitor)",
            "Fail": "Pause/Review (Fail)",
            "Review Manually": "Review Manually"
        }

        # --- Prepare Output DataFrame ---
        review_data = {
            "Date of Report": [date.today().strftime("%Y-%m-%d")] * len(df),
            "Ad Name": df["Ad name"],
            "Amount Spent (USD)": df["Amount spent (USD)"].round(2),
            # Optional Columns
            "Link CTR (%)": df["CTR (link click-through rate)"].apply(lambda x: f"{x*100:.2f}%" if pd.notna(x) else "N/A") if "CTR (link click-through rate)" in df.columns else ["N/A"] * len(df),
            "Link Clicks": df["Link clicks"].apply(lambda x: int(x) if pd.notna(x) else "N/A") if "Link clicks" in df.columns else ["N/A"] * len(df),
            # Core Metrics
            "CPC (USD)": df["CPC (cost per link click) (USD)"].apply(lambda x: f"${x:.2f}" if pd.notna(x) else "N/A"),
            "ROAS": df["Purchase ROAS (return on ad spend)"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"),
            # Evaluation Results
            "Flagged? (Y/N)": df["Flagged? (Y/N)"], # Y = Failed Criteria / Needs Action
            "Result": df["Result"], # Keep, Fail, Insufficient Data
            "Action to Take": df["Result"].map(action_mapping).fillna("Review Manually"),
            "Recommendation": df["Result"].apply(
                lambda r: recommendations_by_stage[ad_stage].get(r, "Check metrics manually.")
            ),
            "Notes": ""
        }
        review = pd.DataFrame(review_data)


        # --- Display Results in Streamlit ---
        st.subheader("📊 Summary")
        flagged_count = (review['Flagged? (Y/N)'] == 'Y').sum()
        passed_count = (review['Result'] == 'Keep').sum()
        st.write(f"**Total Ads Processed:** {len(review)}")
        st.write(f"**✅ Ads Passing Criteria ('Keep'):** {passed_count}")
        st.write(f"**❌ Ads Failing Criteria ('Fail'):** {flagged_count}")

        # Highlighting function - Simplified
        def highlight_rows(row):
            if row['Flagged? (Y/N)'] == 'Y': # Failed Criteria
                color = '#ffe6e6' # Light Red
            elif row['Result'] == 'Insufficient Data':
                color = '#e6f7ff' # Light Blue
            else: # Keep (Passed Criteria)
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

            # Define fills for Excel
            red_fill = PatternFill(start_color="FFE6E6", end_color="FFE6E6", fill_type="solid") # Fail
            green_fill = PatternFill(start_color="E6FFE6", end_color="E6FFE6", fill_type="solid") # Keep/Pass
            blue_fill = PatternFill(start_color="E6F7FF", end_color="E6F7FF", fill_type="solid") # Insufficient Data

            flagged_col_idx = review.columns.get_loc("Flagged? (Y/N)") + 1
            result_col_idx = review.columns.get_loc("Result") + 1

            for row_idx in range(2, len(review) + 2):
                flagged_val = worksheet.cell(row=row_idx, column=flagged_col_idx).value
                result_val = worksheet.cell(row=row_idx, column=result_col_idx).value

                fill_to_apply = None
                if result_val == 'Insufficient Data': fill_to_apply = blue_fill
                elif flagged_val == 'Y': fill_to_apply = red_fill
                elif flagged_val == 'N' and result_val == 'Keep': fill_to_apply = green_fill

                if fill_to_apply:
                    for col_idx in range(1, len(review.columns) + 1):
                        worksheet.cell(row=row_idx, column=col_idx).fill = fill_to_apply

            # Auto-adjust column widths
            for col in worksheet.columns:
                max_length = 0; column = col[0].column_letter
                header_cell = worksheet[f"{column}1"]
                if header_cell.value: max_length = len(str(header_cell.value))
                for cell in col:
                    if cell.row == 1: continue
                    try:
                        if cell.value:
                            cell_len = len(str(cell.value))
                            if cell_len > max_length: max_length = cell_len
                    except: pass
                adjusted_width = (max_length + 2) * 1.2
                if adjusted_width > 60: adjusted_width = 60 # Slightly wider max width
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