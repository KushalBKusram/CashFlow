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
st.sidebar.caption("🔒 Your data stays in your browser and is never sent to any server.")

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
    st.sidebar.success(f"Loaded {len(df)} transactions")
except Exception as e:
    st.error(f"Error loading CSV file: {e}")
    st.stop()

# Sidebar controls
st.sidebar.header("Filters")

# Date range selector
date_range_option = st.sidebar.selectbox(
    "Date Range",
    ["All Time", "Last Week", "Last Month", "Last 60 Days", "Last 90 Days", "Last 6 Months", "Last Year"],
    index=2  # Default to "Last Month"
)

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

# Separate income and expenses
# Income: only transactions tagged as 'income'
income_df = filtered_df[filtered_df['type'] == 'income']

# Expenses: all non-income transactions with valid categories (positive = expense, negative = refund)
expenses_df = filtered_df[
    (filtered_df['type'] != 'income') & 
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

# Add savings if positive
if savings > 0:
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
if savings > 0:
    node_colors.append("rgba(59, 130, 246, 0.8)")  # Blue for Savings

# Add colors for expense categories
for idx in range(len(category_totals)):
    node_colors.append(f"rgba({(idx * 50) % 255}, {(idx * 100) % 255}, {(idx * 150) % 255}, 0.8)")

# Create custom hover text for labels
node_labels = []
for i, label in enumerate(labels):
    if i == 0:  # Income
        node_labels.append("Income")
    elif label == "Savings":
        node_labels.append(f"Savings ({savings/total_income*100:.2f}%)")
    else:
        cat_amount = category_totals.get(label, 0)
        node_labels.append(f"{label} ({cat_amount/total_income*100:.2f}%)")

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

fig.update_layout(
    title="Income Flow to Savings and Expense Categories",
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
legend_df = pd.DataFrame({
    'Category': category_totals.head(10).index,
    'Amount': category_totals.head(10).values,
    'Percentage': (category_totals.head(10).values / total_income * 100)
})
legend_df['Amount'] = legend_df['Amount'].apply(lambda x: f"${x:,.2f}")
legend_df['Percentage'] = legend_df['Percentage'].apply(lambda x: f"{x:.2f}%")
st.dataframe(legend_df, hide_index=True, use_container_width=True)
