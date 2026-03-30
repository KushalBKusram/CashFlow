import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="CashFlow",
    page_icon="💰",
    layout="wide"
)

# Title
st.title("CashFlow - Fund    Visualizer")
st.markdown("Visualize your financial transactions as an interactive Sankey diagram")

# Sidebar - File Upload
st.sidebar.header("Data Upload")
uploaded_file = st.sidebar.file_uploader("Upload your transactions CSV", type=['csv'])
st.sidebar.caption("Currently works with Copilot Money CSV exports")

if uploaded_file is None:
    st.info("Please upload your transaction CSV file (currently supports Copilot Money export format)")

    st.markdown("""
    ### Expected CSV Format

    Your CSV file should include these columns:
    - `date`: Transaction date (YYYY-MM-DD)
    - `name`: Merchant/payee name
    - `amount`: Transaction amount (negative for income/refunds, positive for expenses)
    - `type`: Transaction type (`income`, `regular`, etc.)
    - `category`: Expense category
    - `account`: Account name
    - `excluded`: Whether to exclude (true/false)

    #### Sample format:
    ```csv
    date,name,amount,status,category,type,account,excluded
    2026-01-01,Salary,-5000.00,cleared,Salary,income,Checking,false
    2026-01-02,Grocery Store,85.50,cleared,Food & Dining,regular,Credit Card,false
    ```
    """)
    st.stop()

# Load data from uploaded file
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    df['date'] = pd.to_datetime(df['date'])
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    return df

try:
    df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Error loading CSV file: {e}")
    st.stop()

# Filter excluded non-income transactions (credit card payments, transfers, etc.)
# Income rows are kept even if marked excluded, since Copilot Money marks income as excluded by default
if 'excluded' in df.columns:
    excl_mask = df['excluded'].astype(str).str.strip().str.lower().isin(['true', '1', 'yes'])
    df = df[~excl_mask | (df['type'] == 'income')]

st.sidebar.success(f"Loaded {len(df)} transactions")

# Sidebar controls
st.sidebar.header("Filters")

# Date range selector
date_range_option = st.sidebar.selectbox(
    "Date Range",
    ["All Time", "Last Week", "Last Month", "Last 60 Days", "Last 90 Days", "Last 6 Months", "Last Year"],
    index=2  # Default to "Last Month"
)

# Tag filter selector
# Extract unique tags (excluding empty/NaN values)
if 'tags' in df.columns:
    unique_tags = df['tags'].dropna()
    unique_tags = unique_tags[unique_tags != ''].unique()
    unique_tags = sorted(unique_tags.tolist())

    tag_options = ["All Tags"] + unique_tags
    selected_tag = st.sidebar.selectbox(
        "Filter by Tag",
        tag_options,
        index=0
    )
else:
    selected_tag = "All Tags"

# Calculate date range
end_date = datetime.now()
if date_range_option == "Last Week":
    start_date = end_date - timedelta(days=7)
elif date_range_option == "Last Month":
    start_date = end_date - timedelta(days=30)
elif date_range_option == "Last 60 Days":
    start_date = end_date - timedelta(days=60)
elif date_range_option == "Last 90 Days":
    start_date = end_date - timedelta(days=90)
elif date_range_option == "Last 6 Months":
    start_date = end_date - timedelta(days=180)
elif date_range_option == "Last Year":
    start_date = end_date - timedelta(days=365)
else:  # All Time
    start_date = df['date'].min()

# Filter data
filtered_df = df.copy()

# Apply date filter
if date_range_option != "All Time":
    filtered_df = filtered_df[(filtered_df['date'] >= start_date) & (filtered_df['date'] <= end_date)]

# Apply tag filter
if selected_tag != "All Tags" and 'tags' in df.columns:
    filtered_df = filtered_df[filtered_df['tags'] == selected_tag]

tab1, tab2 = st.tabs(["💰 Spending Tracker", "📈 Year-end Projections"])

# ── TAB 1: Sankey Flow ─────────────────────────────────────────────────────────
with tab1:
    # Separate income and expenses
    # Income: only transactions tagged as 'income'
    income_df = filtered_df[filtered_df['type'] == 'income']

    # Expenses: non-income, non-transfer transactions with valid categories
    expenses_df = filtered_df[
        (filtered_df['type'] != 'income') &
        (filtered_df['type'] != 'transfer') &
        (filtered_df['category'].notna()) &
        (filtered_df['category'] != '')
    ]

    # Calculate totals
    total_income = income_df['amount'].abs().sum()

    # Group expenses by category (positive = expense, negative = refund/credit)
    category_totals = expenses_df.groupby('category')['amount'].sum().sort_values(ascending=False)
    total_expenses = category_totals.sum()
    savings = total_income - total_expenses

    # Display metrics
    # When a tag is selected, hide savings metrics (they don't make sense for filtered data)
    if selected_tag != "All Tags" and 'tags' in df.columns:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Expenses", f"${total_expenses:,.2f}", delta=None, delta_color="inverse")
        with col2:
            num_transactions = len(filtered_df)
            st.metric("Transactions", f"{num_transactions:,}", delta=None)
    else:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Income", f"${total_income:,.2f}", delta=None)
        with col2:
            st.metric("Expenses", f"${total_expenses:,.2f}", delta=None, delta_color="inverse")
        with col3:
            st.metric("Savings", f"${savings:,.2f}", delta=None)
        with col4:
            savings_rate = (savings / total_income * 100) if total_income > 0 else 0
            st.metric("Savings Rate", f"{savings_rate:.2f}%", delta=None)

    # Create Sankey diagram
    labels = ["Income"]
    source = []
    target = []
    values = []
    colors = []

    # Add savings if positive (but only when viewing all tags)
    tag_is_selected = selected_tag != "All Tags" and 'tags' in df.columns
    if savings > 0 and not tag_is_selected:
        labels.append("Savings")
        source.append(0)  # Income
        target.append(1)  # Savings
        values.append(savings)
        colors.append("rgba(59, 130, 246, 0.4)")  # Blue for savings

    # Add expense categories
    start_idx = len(labels)
    for idx, (category, amount) in enumerate(category_totals.items()):
        labels.append(f"{category}")
        source.append(0)  # Income
        target.append(start_idx + idx)
        values.append(amount)
        colors.append(f"rgba({(idx * 50) % 255}, {(idx * 100) % 255}, {(idx * 150) % 255}, 0.4)")

    # Create node colors
    node_colors = ["rgba(16, 185, 129, 0.8)"]  # Green for Income
    if savings > 0 and not tag_is_selected:
        node_colors.append("rgba(59, 130, 246, 0.8)")  # Blue for Savings

    # Add colors for expense categories
    for idx in range(len(category_totals)):
        node_colors.append(f"rgba({(idx * 50) % 255}, {(idx * 100) % 255}, {(idx * 150) % 255}, 0.8)")

    # Create custom hover text for labels
    # When a tag is selected, show percentages relative to total expenses
    # When "All Tags" is selected, show percentages relative to total income
    percentage_base = total_expenses if (selected_tag != "All Tags" and 'tags' in df.columns) else total_income

    node_labels = []
    for i, label in enumerate(labels):
        if i == 0:  # Income
            node_labels.append("Income")
        elif label == "Savings":
            node_labels.append(f"Savings ({savings/total_income*100:.2f}%)")
        else:
            cat_amount = category_totals.get(label, 0)
            if percentage_base > 0:
                node_labels.append(f"{label} ({cat_amount/percentage_base*100:.2f}%)")
            else:
                node_labels.append(f"{label}")

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=node_labels,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=values,
            color=colors
        ),
        arrangement='snap',
        orientation='h'
    )])

    # Update title based on whether a tag is selected
    if tag_is_selected:
        diagram_title = f"Expense Breakdown for '{selected_tag}'"
    else:
        diagram_title = "Income Flow to Savings and Expense Categories"

    fig.update_layout(
        title=diagram_title,
        font=dict(size=12),
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # Category drill-down section
    st.markdown("---")
    st.subheader("Category Breakdown")

    # Category selector
    all_categories = sorted(category_totals.index.tolist())
    selected_category = st.selectbox("Select a category to see detailed breakdown:", ["None"] + all_categories, index=0)

    if selected_category != "None":
        # Filter transactions for selected category
        category_transactions = expenses_df[expenses_df['category'] == selected_category]

        st.markdown(f"### {selected_category}")

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            category_total = category_transactions['amount'].sum()
            st.metric("Total Spent", f"${category_total:,.2f}")
        with col2:
            st.metric("Transactions", len(category_transactions))
        with col3:
            avg_transaction = category_total / len(category_transactions) if len(category_transactions) > 0 else 0
            st.metric("Avg Transaction", f"${avg_transaction:,.2f}")

        # Pie chart by merchant/name (exclude negative refunds)
        positive_transactions = category_transactions[category_transactions['amount'] > 0]
        merchant_totals = positive_transactions.groupby('name')['amount'].sum().sort_values(ascending=False).head(10)

        if len(merchant_totals) > 0:
            # Create pie chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=merchant_totals.index,
                values=merchant_totals.values,
                hole=0.3,
                textposition='auto',
                textinfo='label+percent'
            )])

            fig_pie.update_layout(
                title=f"Top Merchants/Payees in {selected_category}",
                height=500,
                showlegend=True
            )

            st.plotly_chart(fig_pie, use_container_width=True)

            # Detailed transaction table
            st.markdown("### Recent Transactions")
            transaction_display = category_transactions[['date', 'name', 'amount', 'account']].copy()
            transaction_display['date'] = pd.to_datetime(transaction_display['date']).dt.strftime('%Y-%m-%d')
            transaction_display['amount'] = transaction_display['amount'].apply(lambda x: f"${x:,.2f}")
            transaction_display = transaction_display.sort_values('date', ascending=False).head(20)
            st.dataframe(transaction_display, hide_index=True, use_container_width=True)

    # Additional stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Transactions", f"{len(filtered_df):,}")
    with col2:
        categories = filtered_df['category'].dropna().nunique()
        st.metric("Categories", categories)
    with col3:
        accounts = filtered_df['account'].dropna().nunique()
        st.metric("Accounts", accounts)

    # Top categories legend
    st.subheader("Top Expense Categories")

    # Use total expenses for percentage when tag is selected, otherwise use total income
    legend_percentage_base = total_expenses if (selected_tag != "All Tags" and 'tags' in df.columns) else total_income

    if legend_percentage_base > 0:
        legend_df = pd.DataFrame({
            'Category': category_totals.head(10).index,
            'Amount': category_totals.head(10).values,
            'Percentage': (category_totals.head(10).values / legend_percentage_base * 100)
        })
        legend_df['Amount'] = legend_df['Amount'].apply(lambda x: f"${x:,.2f}")
        legend_df['Percentage'] = legend_df['Percentage'].apply(lambda x: f"{x:.2f}%")
        st.dataframe(legend_df, hide_index=True, use_container_width=True)
    else:
        st.info("No expense data available for the selected filters.")

# ── TAB 2: Year-end Projections ────────────────────────────────────────────────
with tab2:
    if len(filtered_df) == 0:
        st.info("No data in the selected date range.")
        st.stop()

    # ── Months elapsed in the filtered window ──────────────────────────────────
    date_min = filtered_df['date'].min()
    date_max = filtered_df['date'].max()
    months_elapsed = max((date_max - date_min).days / 30.44, 1)

    if months_elapsed < 1.5:
        st.warning(f"Only {months_elapsed:.1f} month(s) of data in the selected range — projections may be less reliable.")

    # ── Income detection ───────────────────────────────────────────────────────
    income_rows_proj = filtered_df[filtered_df['type'] == 'income']
    annual_income_auto = income_rows_proj['amount'].abs().sum() / months_elapsed * 12
    monthly_income_auto = annual_income_auto / 12

    st.subheader("Income")
    inc_col1, inc_col2 = st.columns([1, 2])
    with inc_col1:
        inc_mode = st.radio(
            "Income source",
            ["Auto-detect from CSV", "Manual override"],
            horizontal=True,
            key="proj_income_mode"
        )
    with inc_col2:
        if inc_mode == "Auto-detect from CSV":
            annual_income = annual_income_auto
            if annual_income_auto == 0:
                st.warning("No income transactions found in the selected range. Switch to manual override or broaden your date filter.")
            else:
                st.write(f"Detected: ${annual_income_auto:,.0f}/year (${monthly_income_auto:,.0f}/mo) from {months_elapsed:.1f} months of data")
        else:
            annual_income = st.number_input(
                "Annual income ($)",
                min_value=0.0,
                value=float(annual_income_auto) if annual_income_auto > 0 else 60000.0,
                step=1000.0,
                key="proj_income_manual"
            )

    st.markdown("---")

    # ── Projection calculations ────────────────────────────────────────────────
    expenses_proj = filtered_df[
        (filtered_df['type'] != 'income') &
        (filtered_df['type'] != 'transfer') &
        (filtered_df['category'].notna()) &
        (filtered_df['category'] != '')
    ]
    cat_totals_proj = expenses_proj.groupby('category')['amount'].sum()
    cat_totals_proj = cat_totals_proj[cat_totals_proj > 0]

    if len(cat_totals_proj) == 0:
        st.info("No expense categories found in the selected date range.")
        st.stop()

    monthly_rates = cat_totals_proj / months_elapsed
    projected_annual = monthly_rates * 12

    today = datetime.now()
    year_end = datetime(today.year, 12, 31)
    months_remaining = max((year_end - today).days / 30.44, 0)

    categories_list = sorted(cat_totals_proj.index.tolist())

    # ── Initialize per-category targets as % of income (once per category) ──────
    for cat in categories_list:
        key = f"target_pct_{cat}"
        if key not in st.session_state:
            default_pct = (projected_annual[cat] / annual_income * 100) if annual_income > 0 else 0.0
            st.session_state[key] = round(default_pct, 1)

    def target_dollars(cat):
        return st.session_state[f"target_pct_{cat}"] / 100 * annual_income if annual_income > 0 else 0.0

    # ── Summary metrics ────────────────────────────────────────────────────────
    on_pace = [c for c in categories_list if projected_annual[c] <= target_dollars(c)]
    over_budget = [c for c in categories_list if projected_annual[c] > target_dollars(c)]
    total_projected = projected_annual.sum()
    pct_of_income = (total_projected / annual_income * 100) if annual_income > 0 else 0

    st.subheader("Summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("On Pace", len(on_pace))
    m2.metric("Over Budget", len(over_budget))
    m3.metric("Total Projected Annual", f"${total_projected:,.0f}")
    m4.metric("% of Annual Income", f"{pct_of_income:.1f}%" if annual_income > 0 else "N/A")

    st.markdown("---")

    # ── Visualization: projected vs target ────────────────────────────────────
    st.subheader("Projected Annual Spend vs. Target")

    bar_colors = [
        "rgba(16, 185, 129, 0.85)" if projected_annual[c] <= target_dollars(c)
        else "rgba(239, 68, 68, 0.85)"
        for c in categories_list
    ]

    fig_proj = go.Figure()
    fig_proj.add_trace(go.Bar(
        name="Target",
        y=categories_list,
        x=[target_dollars(c) for c in categories_list],
        orientation='h',
        marker_color="rgba(100, 116, 139, 0.3)"
    ))
    fig_proj.add_trace(go.Bar(
        name="Projected Annual",
        y=categories_list,
        x=[float(projected_annual[c]) for c in categories_list],
        orientation='h',
        marker_color=bar_colors
    ))
    fig_proj.update_layout(
        barmode='overlay',
        xaxis_title="Amount ($)",
        height=max(400, len(categories_list) * 32),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_proj, use_container_width=True)

    st.markdown("---")

    # ── Per-category table with editable targets ───────────────────────────────
    st.subheader("Category Targets & Projections")

    reset_col, _ = st.columns([1, 4])
    with reset_col:
        if st.button("Reset targets to projected values"):
            for cat in categories_list:
                default_pct = (projected_annual[cat] / annual_income * 100) if annual_income > 0 else 0.0
                st.session_state[f"target_pct_{cat}"] = round(default_pct, 1)
            st.rerun()

    # Header row
    h_cols = st.columns([2, 1.2, 1.5, 1, 1.5, 1.2, 1.2])
    for col, header in zip(h_cols, ["Category", "Monthly Rate", "Projected Annual", "% Income", "Target (% income)", "Gap", "Status"]):
        col.markdown(f"**{header}**")
    st.divider()

    for cat in categories_list:
        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1.2, 1.5, 1, 1.5, 1.2, 1.2])
        proj = float(projected_annual[cat])
        monthly = float(monthly_rates[cat])
        pct = (proj / annual_income * 100) if annual_income > 0 else 0

        c1.write(cat)
        c2.write(f"${monthly:,.0f}")
        c3.write(f"${proj:,.0f}")
        c4.write(f"{pct:.1f}%")
        with c5:
            st.number_input(
                "",
                min_value=0.0,
                max_value=100.0,
                step=0.5,
                format="%.1f",
                key=f"target_pct_{cat}",
                label_visibility="collapsed"
            )
        t_dollars = target_dollars(cat)
        gap = proj - t_dollars
        c6.markdown(f"{'🟢' if gap <= 0 else '🔴'} ${gap:+,.0f}")
        c7.markdown("On Pace" if gap <= 0 else f"Over by ${gap:,.0f}")
