import streamlit as st

# Title
st.set_page_config(page_title="Opportunity Risk Score Calculator", page_icon="📊")
st.title("📊 Opportunity Risk Score (ORS) Calculator")
st.markdown("A dynamic risk engine for CPQ approval routing. Adjust inputs to see real-time risk scoring.")

# Sidebar for inputs
st.sidebar.header("🔷 Deal Inputs")

deal_type = st.sidebar.selectbox(
    "Deal Type",
    ["Net New", "Upsell", "Downsell", "Cross-Sell", "Cancellation"]
)

revenue_types = st.sidebar.multiselect(
    "Revenue Types",
    ["Time & Material", "Project", "License", "Managed Service"],
    default=["Project", "License"]
)

# ACV inputs
if deal_type in ["Cancellation", "Downsell"]:
    current_acv = st.sidebar.number_input("Current ACV ($)", min_value=0, value=200000, step=10000)
    acv_for_multiplier = current_acv
    acv_for_base = current_acv
else:
    acv = st.sidebar.number_input("ACV ($)", min_value=0, value=180000, step=10000)
    growth_acv = 0
    if deal_type == "Upsell":
        growth_acv = st.sidebar.number_input("Growth ACV ($)", min_value=0, value=25000, step=5000)
        acv_for_multiplier = growth_acv
    else:
        acv_for_multiplier = acv
    acv_for_base = acv

discount_pct = st.sidebar.slider("Discount (%)", 0, 100, 25) / 100.0
tcv_term = st.sidebar.slider("TCV Term (Years)", 1, 5, 2)
project_duration = st.sidebar.slider("Project Duration (Months)", 1, 24, 14)
ps_value = st.sidebar.number_input("PS Value ($)", min_value=0, value=90000, step=10000)
payment_days = st.sidebar.selectbox("Payment Terms (Days)", [30, 45, 60, 90], index=2)

# Risk flags
col1, col2 = st.sidebar.columns(2)
strategic = col1.checkbox("Strategic Account?")
min_term_met = col2.checkbox("Min Term Met?", value=True)
bundle_compat = st.sidebar.checkbox("Bundle Compatible?", value=False)
non_standard = st.sidebar.checkbox("Non-Standard Contract?")
break_no_penalty = st.sidebar.checkbox("Break Clause + No Penalty?")

customer_health = st.sidebar.slider("Customer Health Score", 0, 100, 65)

# === CALCULATION LOGIC ===
base_ors = 0

# Base risk by deal type
if deal_type == "Cancellation":
    base_ors = 80
    if customer_health < 50:
        base_ors += 10
    if strategic:
        base_ors += 15
    if not min_term_met:
        base_ors += 20  # early termination
    else:
        base_ors += 5
elif deal_type == "Downsell":
    base_ors = 40
    if discount_pct < -0.25:  # Note: discount_pct is positive; use ACV delta logic if available
        base_ors += 30
    # Simplified: assume 30% downsell if discount > 25%
    if discount_pct > 0.25:
        base_ors += 30
    if acv_for_base / (acv_for_base / (1 - discount_pct) if discount_pct < 1 else 1) < 0.5:
        base_ors += 20
    if "License" in revenue_types or "Managed Service" in revenue_types:
        base_ors += 15
    else:
        base_ors += 5
elif deal_type == "Upsell":
    base_ors = 20
    if "License" in revenue_types:
        if discount_pct > 0.5:
            base_ors += 25
        elif discount_pct > 0.15:
            base_ors += 10
    if "Time & Material" in revenue_types and discount_pct > 0.2:
        base_ors += 10
elif deal_type == "Cross-Sell":
    base_ors = 25 + 15  # new revenue to existing
    if len(revenue_types) > 1:
        base_ors += 10  # hybrid
    if not bundle_compat:
        base_ors += 20
    if acv_for_base > 150000:
        base_ors += 25
    elif acv_for_base > 50000:
        base_ors += 10
elif deal_type == "Net New":
    base_ors = 35
    if len(revenue_types) > 1:
        base_ors += 15
    if "Project" in revenue_types:
        base_ors += 10
    if acv_for_base > 500000:
        base_ors += 30
    elif acv_for_base > 150000:
        base_ors += 15
    if not bundle_compat:
        base_ors += 25

# Add risk adders
if discount_pct < 0.1:
    disc_risk = 0
elif discount_pct <= 0.2:
    disc_risk = 10
else:
    disc_risk = 20

term_risk = 20 if (deal_type == "Net New" and tcv_term < 3) else 0
proj_risk = 15 if ("Project" in revenue_types and project_duration > 12) else 0
ps_risk = 10 if ps_value > 75000 else 0

pay_risk = 0
if payment_days == 45:
    pay_risk = 5
elif payment_days == 60:
    pay_risk = 10
elif payment_days >= 90:
    pay_risk = 20

base_ors += disc_risk + term_risk + proj_risk + ps_risk + pay_risk
base_ors = min(100, max(0, base_ors))

# ACV Multiplier
if acv_for_multiplier <= 50000:
    multiplier = 0.8
elif acv_for_multiplier <= 150000:
    multiplier = 1.0
elif acv_for_multiplier <= 500000:
    multiplier = 1.3
elif acv_for_multiplier <= 1000000:
    multiplier = 1.6
else:
    multiplier = 2.0

pre_override = min(100, base_ors * multiplier)

# Overrides
final_ors = pre_override
if non_standard:
    final_ors = max(final_ors, 50)
if break_no_penalty:
    final_ors = 95
final_ors = min(100, final_ors)

# === DISPLAY RESULTS ===
st.subheader("🎯 Risk Assessment")

col1, col2, col3 = st.columns(3)
col1.metric("Base ORS", f"{base_ors:.0f}")
col2.metric("ACV Multiplier", f"×{multiplier:.1f}")
col3.metric("Final ORS", f"{final_ors:.0f}", delta=None)

# Risk tier
if final_ors <= 30:
    tier = "✅ Low Risk – Auto-Approve"
    color = "#4CAF50"
elif final_ors <= 60:
    tier = "👥 Medium Risk – Tier 1 Approval"
    color = "#FFC107"
else:
    tier = "🚨 High Risk – Tier 2 Approval"
    color = "#F44336"

st.markdown(f"<h3 style='color:{color};'>{tier}</h3>", unsafe_allow_html=True)

# Approvers
approvers = []
if final_ors > 30:
    approvers.append("Sales Ops")
if final_ors > 60:
    approvers += ["RevOps", "Finance"]
    if "License" in revenue_types or break_no_penalty:
        approvers.append("Legal")
    if "Project" in revenue_types:
        approvers.append("Delivery Lead")
if deal_type in ["Downsell", "Cancellation"]:
    approvers.append("CSM")

if approvers:
    st.write("**Approvers:** " + ", ".join(set(approvers)))

# Footer
st.markdown("---")
st.caption("Opportunity Risk Score Framework v1.0 • For CPQ Approval Routing")
