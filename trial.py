import streamlit as st  
import pandas as pd 
import plotly.express as px 
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import io
import difflib
import os
import logging
import calendar
import uuid

# Configure logging
logging.basicConfig(filename='debug.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Set page config
st.set_page_config(page_title="Maple vs Cashify Analytics", layout="wide")

# Initialize session state
if 'maple_data' not in st.session_state:
    st.session_state.maple_data = None
if 'cashify_data' not in st.session_state:
    st.session_state.cashify_data = None
if 'spoc_data' not in st.session_state:
    st.session_state.spoc_data = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'column_mappings' not in st.session_state:
    st.session_state.column_mappings = {'Maple': {}, 'Cashify': {}, 'SPOC': {}}
if 'spoc_mapping_complete' not in st.session_state:
    st.session_state.spoc_mapping_complete = False
if 'spoc_ids' not in st.session_state:
    st.session_state.spoc_ids = {}

# User credentials
users = {
    "mahesh_shetty": {"password": "Maple2025!", "name": "Mahesh Shetty"},
    "sandesh_kadam": {"password": "TradeIn@2025", "name": "Sandesh Kadam"},
    "vishwa_sanghavi": {"password": "Analytics#2025", "name": "Vishwa Sanghavi"},
    "kavish_shah": {"password": "Cashify2025$", "name": "Kavish Shah"},
    "hardik_shah": {"password": "Hardik@2025", "name": "Hardik Shah"},
    "manil_shetty": {"password": "Manil@2025", "name": "Manil Shetty"},
}

# Expected columns
MAPLE_REQUIRED_COLUMNS = [
    'Service Number', 'Status', 'Old IMEI No', 'Created Date', 'Month', 'Year',
    'Store Name', 'Vendor Name', 'Payment Amount', 'Partner / Source',
    'Product Category', 'Product Type', 'Old Product Name', 'New Product Name', 'Maple Bid'
]
CASHIFY_REQUIRED_COLUMNS = [
    'Order Id', 'Order Date', 'Month', 'Year', 'Order Status', 'Partner Name',
    'Store Name', 'Pickup Type', 'Old Device IMEI', 'Product Type', 'Product Category',
    'Old Device Name', 'New Device IMEI', 'New Device Name', 'Initial Device Amount'
]
SPOC_REQUIRED_COLUMNS = ['Spoc Name', 'Store State', 'Zone', 'Weekoff Day', 'Store Name']

# Enhanced state name normalization
STATE_MAPPING = {
    'ap': 'Andhra Pradesh', 'andhra pradesh': 'Andhra Pradesh', 
    'andhra Pradesh': 'Andhra Pradesh', 'Andhra Pardesh': 'Andhra Pradesh',
    'telangana': 'Telangana', 'telengana': 'Telangana', 'tg': 'Telangana',
    'karnataka': 'Karnataka', 'ka': 'Karnataka',
    'tamil nadu': 'Tamil Nadu', 'tn': 'Tamil Nadu',
    'kerala': 'Kerala', 'kl': 'Kerala',
    'pondicherry': 'Puducherry', 'puducherry': 'Puducherry', 
    'py': 'Puducherry'
}

# File paths
BASE_PATH = "/Users/maple/Desktop/SPOC Review file/"
MAPLE_FILE_PATH = os.path.join(BASE_PATH, "Actual Data Sheet.xlsx")
CASHIFY_FILE_PATH = os.path.join(BASE_PATH, "Cashify Trade-in Sept'24 to 12th May'25.xlsx")
SPOC_FILE_PATH = os.path.join(BASE_PATH, "SPOC Master Data Sheet.xlsx")

def standardize_state_names(df, state_col='Store State'):
    if state_col in df.columns:
        df[state_col] = df[state_col].str.strip().str.title()
        df[state_col] = df[state_col].replace({
            'Pondicherry': 'Puducherry',
            'Puducherry': 'Puducherry'
        })
        df[state_col] = df[state_col].map(lambda x: STATE_MAPPING.get(x.lower(), x) if pd.notna(x) else x)
    return df

def find_similar_columns(df_columns, expected_col):
    return difflib.get_close_matches(expected_col, df_columns, n=3, cutoff=0.6)

def validate_and_map_columns(df, required_columns, df_name):
    if df.empty or df.columns.empty:
        st.error(f"{df_name} dataset is empty or has no columns. Please check the file at {BASE_PATH}.")
        return None, {}
    
    df_columns = df.columns.tolist()
    missing_columns = [col for col in required_columns if col not in df_columns]
    column_mapping = st.session_state.column_mappings.get(df_name, {})
    
    logging.info(f"{df_name} Available Columns: {', '.join(df_columns)}")
    
    if missing_columns:
        st.warning(f"Missing columns in {df_name} data: {', '.join(missing_columns)}")
        st.subheader(f"Map Columns for {df_name}")
        for col in missing_columns:
            similar_cols = find_similar_columns(df_columns, col)
            st.write(f"Mapping for '{col}':")
            options = similar_cols + ["Enter custom column name"]
            if df_name == "SPOC" and col in ['Store Name', 'Spoc Name']:
                st.error(f"{col} is mandatory for SPOC data. Please select or enter a valid column.")
            else:
                options = ["None"] + options
            default_value = column_mapping.get(col, options[0])
            if default_value not in options:
                default_value = options[0]
            selected_col = st.selectbox(
                f"Select column for '{col}'",
                options=options,
                key=f"{df_name}_{col}_mapping",
                index=options.index(default_value)
            )
            if selected_col == "Enter custom column name":
                selected_col = st.text_input(
                    f"Enter column name for '{col}'",
                    key=f"{df_name}_{col}_custom",
                    value=column_mapping.get(col, "") if col in column_mapping else ""
                )
            if selected_col != "None" and selected_col in df_columns:
                column_mapping[col] = selected_col
            elif selected_col != "None" and selected_col:
                st.error(f"Column '{selected_col}' not found in {df_name} data. Please select a valid column.")
                return None, column_mapping
            elif selected_col == "None" and df_name == "SPOC" and col in ['Store Name', 'Spoc Name']:
                st.error(f"{col} cannot be set to None for SPOC data.")
                return None, column_mapping
            else:
                column_mapping[col] = None
        
        st.session_state.column_mappings[df_name] = column_mapping
    
    rename_dict = {v: k for k, v in column_mapping.items() if v and v != "None"}
    if rename_dict:
        df = df.rename(columns=rename_dict)
    
    critical_cols = ['Store Name']
    if df_name == "SPOC":
        critical_cols.append('Spoc Name')
    missing_critical = [col for col in critical_cols if col not in df.columns and col in required_columns]
    if missing_critical:
        st.error(f"Critical columns missing in {df_name} after mapping: {', '.join(missing_critical)}.")
        return None, column_mapping
    
    if df_name == "Cashify" and 'Spoc Name' not in df.columns and ' Partner Name' in df.columns:
        df['Spoc Name'] = df[' Partner Name']

    logging.info(f"{df_name} Columns After Mapping: {', '.join(df.columns.tolist())}")
    
    return df, column_mapping

def standardize_month(df, month_col='Month'):
    if month_col not in df.columns:
        logging.warning(f"'{month_col}' column not found in dataset. Skipping month standardization.")
        return df
    month_mapping = {
        1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
        7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
        "jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June",
        "jul": "July", "aug": "August", "sep": "September", "oct": "October", "nov": "November", "dec": "December"
    }
    def parse_month(x):
        if pd.isna(x):
            return x
        x_str = str(x).strip().lower()
        try:
            month_num = int(float(x_str))
            return month_mapping.get(month_num, x_str.title())
        except (ValueError, TypeError):
            return month_mapping.get(x_str, x_str.title())
    
    df[month_col] = df[month_col].apply(parse_month)
    return df

def standardize_names(df, store_col='Store Name', spoc_col='Spoc Name', state_col='Store State', product_col=None):
    for col in [store_col, spoc_col, state_col, product_col]:
        if col and col in df.columns:
            df[col] = df[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    df = standardize_state_names(df, state_col)
    return df

def map_store_names_and_states(df, spoc_data, is_maple=True):
    if spoc_data.empty or 'Store Name' not in spoc_data.columns:
        logging.warning("SPOC data is empty or missing Store Name. Setting Store State and Zone to 'Unknown'.")
        df['Store State'] = 'Unknown'
        df['Zone'] = 'Unknown'
        return df
    
    required_spoc_cols = ['Store Name']
    optional_spoc_cols = [col for col in ['Store State', 'Zone', 'Spoc Name'] if col in spoc_data.columns]
    logging.info(f"SPOC Columns Before Merge: {', '.join(spoc_data.columns.tolist())}")
    store_mapping = spoc_data[required_spoc_cols + optional_spoc_cols].drop_duplicates()
    
    for col in required_spoc_cols + optional_spoc_cols:
        store_mapping[col] = store_mapping[col].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
        if col == 'Store State':
            store_mapping[col] = store_mapping[col].map(lambda x: STATE_MAPPING.get(x.lower(), x) if pd.notna(x) else x)
    
    if 'Store Name' not in df.columns:
        st.error(f"Store Name column missing in {'Maple' if is_maple else 'Cashify'} dataset.")
        df['Store State'] = 'Unknown'
        df['Zone'] = 'Unknown'
        return df
    
    df['Store Name'] = df['Store Name'].apply(lambda x: str(x).strip().title() if pd.notna(x) else x)
    
    unmatched_stores = set(df['Store Name'].dropna()) - set(store_mapping['Store Name'].dropna())
    if unmatched_stores:
        logging.warning(f"Unmatched Store Names in {'Maple' if is_maple else 'Cashify'}: {', '.join(unmatched_stores)}")
    
    df = df.merge(store_mapping, on=['Store Name'], how='left', suffixes=('', '_spoc'))
    
    for col in ['Store State', 'Zone']:
        if f'{col}_spoc' in df.columns:
            df[col] = df[f'{col}_spoc'].combine_first(df.get(col))
    df = df.drop(columns=[col for col in df.columns if col.endswith('_spoc')], errors='ignore')
    
    if 'Store State' not in df.columns:
        df['Store State'] = 'Unknown'
    if 'Zone' not in df.columns:
        df['Zone'] = 'Unknown'

    logging.info(f"Store States in {'Maple' if is_maple else 'Cashify'} after merge: {', '.join(sorted(set(df['Store State'].dropna())))}")

    return df

def filter_by_date(df, year, month, day=None, is_maple=True):
    date_column = 'Created Date' if is_maple else 'Order Date'
    if date_column not in df.columns:
        st.error(f"Column '{date_column}' not found in {'Maple' if is_maple else 'Cashify'} data.")
        return pd.DataFrame()
    try:
        required_cols = ['Year', 'Month', date_column, 'Store Name']
        optional_cols = ['Store State', 'Zone']
        if is_maple:
            required_cols.extend(['Maple Bid', 'Old IMEI No', 'Product Category', 'Product Type', 'Old Product Name'])
        else:
            required_cols.extend(['Initial Device Amount', 'Old Device IMEI', 'Product Category', 'Product Type', 'Old Device Name'])
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in {'Maple' if is_maple else 'Cashify'} data: {', '.join(missing_cols)}")
            return pd.DataFrame()
        
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce', dayfirst=True)
        df = df[df['Year'] == year]
        if month and month != "All":
            df = df[df['Month'] == month]
        if day and day != "All":
            df = df[df[date_column].dt.day == day]
        return df
    except Exception as e:
        st.error(f"Error processing dates in {'Maple' if is_maple else 'Cashify'} data: {str(e)}")
        return pd.DataFrame()

def calculate_market_share(spoc_achievement, total_trade_ins):
    return (spoc_achievement / total_trade_ins * 100) if total_trade_ins > 0 else 0

def calculate_target_achievement(spoc_achievement, target):
    return (spoc_achievement / target * 100) if target > 0 else 0

def get_weekoffs(year, month, weekoff_day):
    if weekoff_day == "Vacant" or pd.isna(weekoff_day):
        return []
    month_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                 "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    first_day = date(year, month_num[month], 1)
    last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    return [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1) if (first_day + timedelta(days=i)).strftime('%A') == weekoff_day]

def create_excel_buffer(df, sheet_name):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()

def create_csv_buffer(df, sheet_name=None):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()

def get_weeks_in_month(year, month):
    month_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                 "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    first_day = date(year, month_num[month], 1)
    last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    weeks = []
    current_date = first_day
    week_num = 1
    while current_date <= last_day:
        week_end = min(current_date + timedelta(days=6), last_day)
        weeks.append((f"Week {week_num}", current_date, week_end))
        current_date = week_end + timedelta(days=1)
        week_num += 1
    return weeks

def get_last_n_months(current_month, current_year, n=3):
    month_num = {
        "January": 1, "February": 2, "March": 3, "April": 4, 
        "May": 5, "June": 6, "July": 7, "August": 8, 
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    
    if current_month == "All":
        current_month = datetime.now().strftime("%B")
    
    if current_month not in month_num:
        raise ValueError(f"Invalid month: {current_month}. Must be one of {list(month_num.keys())}")
    
    reverse_month = {v: k for k, v in month_num.items()}
    current_month_num = month_num[current_month]
    months = []
    
    for i in range(n):
        month = (current_month_num - i) % 12 or 12
        year_adjust = current_year - ((current_month_num - i) // 12)
        months.append((reverse_month[month], year_adjust))
    
    return sorted(months, key=lambda x: (x[1], month_num[x[0]]))

def get_last_n_weeks(selected_month, selected_year, spoc, n=4):
    month_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                 "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    if selected_month not in month_num:
        return []
    first_day = date(selected_year, month_num[selected_month], 1)
    last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    weeks = []
    current_date = first_day
    week_num = 1
    while current_date <= last_day:
        week_end = min(current_date + timedelta(days=6), last_day)
        weeks.append((f"Week {week_num}", current_date, week_end))
        current_date = week_end + timedelta(days=1)
        week_num += 1
    return weeks[-n:] if n <= len(weeks) else weeks

def categorize_product_type(product_type):
    if pd.isna(product_type):
        return 'Other'
    
    product_type = str(product_type).lower().strip()
    
    if any(x in product_type for x in ['mobile', 'phone']):
        return 'Mobile Phone'
    elif 'laptop' in product_type:
        return 'Laptop'
    elif 'tablet' in product_type:
        return 'Tablet'
    elif any(x in product_type for x in ['smartwatch', 'watch']):
        if 'apple' in product_type:
            return 'SmartWatch (Apple)'
        return 'SmartWatch (Android)'
    return 'Other'

def generate_spoc_id(spoc_name, store_name, store_state):
    spoc_key = f"{spoc_name}_{store_state}"
    if spoc_key not in st.session_state.spoc_ids:
        st.session_state.spoc_ids[spoc_key] = str(uuid.uuid4())
    return st.session_state.spoc_ids[spoc_key]

def update_spoc_id(spoc_name, old_store, new_store, store_state):
    old_key = f"{spoc_name}_{store_state}"
    new_key = f"{spoc_name}_{store_state}"
    if old_key in st.session_state.spoc_ids:
        spoc_id = st.session_state.spoc_ids[old_key]
        st.session_state.spoc_ids[new_key] = spoc_id
        if old_key != new_key:
            del st.session_state.spoc_ids[old_key]

def login():
    st.sidebar.header("Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    
    if st.sidebar.button("Login"):
        if username in users and users[username]["password"] == password:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.sidebar.success(f"Welcome, {users[username]['name']}!")
        else:
            st.sidebar.error("Invalid username or password")

def logout():
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.column_mappings = {'Maple': {}, 'Cashify': {}, 'SPOC': {}}
        st.session_state.spoc_mapping_complete = False
        st.session_state.spoc_ids = {}
        st.sidebar.success("Logged out successfully")

def get_last_n_months_for_page(n):
    current_date = date.today()
    months = []
    for i in range(n):
        month = current_date.month - i
        year = current_date.year
        if month <= 0:
            month += 12
            year -= 1
        months.append((calendar.month_name[month], year))
    return sorted(months, key=lambda x: (x[1], list(calendar.month_name).index(x[0])))

def process_spoc_weekoffs(spoc_df, selected_year, selected_month):
    if 'Weekoff Day' not in spoc_df.columns or selected_month == "All":
        return {}
    
    spoc_weekoffs = {}
    for _, row in spoc_df.iterrows():
        if pd.notna(row['Weekoff Day']) and row['Weekoff Day'] != "Vacant":
            spoc_weekoffs[row['Spoc Name']] = get_weekoffs(selected_year, selected_month, row['Weekoff Day'])
    
    logging.info(f"Processed weekoffs for {len(spoc_weekoffs)} SPOCs")
    return spoc_weekoffs

def process_devices_lost_section(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month, selected_day):
    st.header("5. Devices Lost on SPOC Weekoff Days")
    
    if selected_month == "All":
        st.warning("Please select a specific month for weekoff analysis")
        return
    
    spoc_weekoffs = process_spoc_weekoffs(spoc_df, selected_year, selected_month)
    
    if not spoc_weekoffs:
        st.info("No devices lost on weekoff days (no weekoff data available)")
        return
    
    # Get all SPOCs with weekoff data
    spoc_list = list(spoc_weekoffs.keys())
    selected_spoc = st.selectbox("Select SPOC", spoc_list, key="spoc_weekoff_select")
    
    if selected_spoc not in spoc_weekoffs:
        st.info("No weekoff days for selected SPOC")
        return
    
    weekoff_dates = spoc_weekoffs[selected_spoc]
    if not weekoff_dates:
        st.info(f"No weekoff days for {selected_spoc} in {selected_month}")
        return
    
    # Get stores for this SPOC
    spoc_stores = maple_filtered[maple_filtered['Spoc Name'] == selected_spoc]['Store Name'].unique()
    if not spoc_stores:
        st.info(f"No stores found for SPOC {selected_spoc}")
        return
    
    store = spoc_stores[0]  # Assuming one store per SPOC
    
    # Get Cashify devices lost on weekoff days
    cashify_losses = cashify_filtered[
        (cashify_filtered['Store Name'] == store) &
        (cashify_filtered['Order Date'].dt.date.isin(weekoff_dates))
    ]
    
    if cashify_losses.empty:
        st.info(f"No devices lost on weekoff days for {selected_spoc} at {store}")
        return
    
    # Group by product category
    losses_by_category = cashify_losses.groupby('Product Category').size().reset_index(name='Count')
    
    st.write(f"**Devices lost on {selected_spoc}'s weekoff days at {store}:**")
    st.dataframe(losses_by_category)
    
    if not losses_by_category.empty:
        fig = px.bar(
            losses_by_category,
            x='Product Category',
            y='Count',
            text='Count',
            title=f"Devices Lost on {selected_spoc}'s Weekoff Days"
        )
        st.plotly_chart(fig, use_container_width=True)

def process_working_day_losses(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month):
    st.header("6. Working Day Losses")
    
    if selected_month == "All":
        st.warning("Please select a specific month for working day analysis")
        return
    
    spoc_weekoffs = process_spoc_weekoffs(spoc_df, selected_year, selected_month)
    
    if not spoc_weekoffs:
        st.info("No working day losses data available (no weekoff data for comparison)")
        return
    
    spoc_list = list(spoc_weekoffs.keys())
    selected_spoc = st.selectbox("Select SPOC", spoc_list, key="spoc_working_select")
    
    if selected_spoc not in spoc_weekoffs:
        st.info("No data for selected SPOC")
        return
    
    weekoff_dates = spoc_weekoffs[selected_spoc]
    spoc_stores = maple_filtered[maple_filtered['Spoc Name'] == selected_spoc]['Store Name'].unique()
    
    if not spoc_stores:
        st.info(f"No stores found for SPOC {selected_spoc}")
        return
    
    store = spoc_stores[0]
    
    # Get all dates in the month that aren't weekoff days
    month_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                 "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
    first_day = date(selected_year, month_num[selected_month], 1)
    last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    
    all_dates = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
    working_dates = [d for d in all_dates if d not in weekoff_dates]
    
    # Get Cashify devices lost on working days
    cashify_losses = cashify_filtered[
        (cashify_filtered['Store Name'] == store) &
        (cashify_filtered['Order Date'].dt.date.isin(working_dates))
    ]
    
    if cashify_losses.empty:
        st.info(f"No working day losses for {selected_spoc} at {store}")
        return
    
    # Group by product category
    losses_by_category = cashify_losses.groupby('Product Category').size().reset_index(name='Count')
    
    st.write(f"**Working day losses for {selected_spoc} at {store}:**")
    st.dataframe(losses_by_category)
    
    if not losses_by_category.empty:
        fig = px.bar(
            losses_by_category,
            x='Product Category',
            y='Count',
            text='Count',
            title=f"Working Day Losses for {selected_spoc}"
        )
        st.plotly_chart(fig, use_container_width=True)

def process_tradein_losses(cashify_filtered, selected_year, selected_month):
    st.header("7. Trade-ins Lost to Cashify by State")
    
    south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
    
    if selected_month == "All":
        st.warning("Please select a specific month for trade-in analysis")
        return
    
    # Standardize state names
    cashify_filtered = standardize_state_names(cashify_filtered)
    
    # Filter for south states and completed orders
    status_filter = cashify_filtered['Order Status'] == 'Completed' if 'Order Status' in cashify_filtered.columns else pd.Series([True] * len(cashify_filtered))
    
    tradein_losses = cashify_filtered[
        (cashify_filtered['Store State'].isin(south_states)) &
        (cashify_filtered['Month'] == selected_month) &
        (cashify_filtered['Year'] == selected_year) &
        status_filter
    ]
    
    if tradein_losses.empty:
        st.info("No trade-in losses data available for selected period")
        return
    
    # Enhanced product categorization
    tradein_losses['Product Category'] = tradein_losses['Product Type'].apply(categorize_product_type)
    
    # 1. Trade-in Losses by State
    losses_by_state = tradein_losses.groupby('Store State').size().reset_index(name='Count')
    
    if not losses_by_state.empty:
        st.subheader("Trade-in Losses by State")
        fig_state = px.bar(
            losses_by_state,
            x='Store State',
            y='Count',
            text='Count',
            title=f"Trade-ins Lost to Cashify by State ({selected_month} {selected_year})"
        )
        st.plotly_chart(fig_state, use_container_width=True)
    
    # 2. Trade-in Losses by Category
    losses_by_category = tradein_losses.groupby('Product Category').size().reset_index(name='Count')
    
    if not losses_by_category.empty:
        st.subheader("Trade-in Losses by Product Category")
        fig_category = px.bar(
            losses_by_category,
            x='Product Category',
            y='Count',
            color='Product Category',
            text='Count',
            title=f"Trade-ins Lost by Product Category ({selected_month} {selected_year})"
        )
        st.plotly_chart(fig_category, use_container_width=True)
    
    # 3. Combined view
    losses_by_state_category = tradein_losses.groupby(['Store State', 'Product Category']).size().reset_index(name='Count')
    
    if not losses_by_state_category.empty:
        st.subheader("Trade-in Losses by State and Category")
        fig_combined = px.bar(
            losses_by_state_category,
            x='Store State',
            y='Count',
            color='Product Category',
            barmode='stack',
            text='Count',
            title=f"Trade-ins Lost by State and Category ({selected_month} {selected_year})"
        )
        st.plotly_chart(fig_combined, use_container_width=True)

def process_pricing_comparison(maple_filtered, cashify_filtered, selected_year, selected_month):
    st.header("8. Device Loss to Cashify with Pricing Comparison")
    
    if selected_month == "All":
        st.warning("Please select a specific month for pricing comparison")
        return
    
    south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
    
    # Standardize state names
    cashify_filtered = standardize_state_names(cashify_filtered)
    maple_filtered = standardize_state_names(maple_filtered)
    
    # Filter for south states and current month
    cashify_prices = cashify_filtered[
        (cashify_filtered['Store State'].isin(south_states)) &
        (cashify_filtered['Month'] == selected_month) &
        (cashify_filtered['Year'] == selected_year)
    ]
    
    maple_prices = maple_filtered[
        (maple_filtered['Store State'].isin(south_states)) &
        (maple_filtered['Month'] == selected_month) &
        (maple_filtered['Year'] == selected_year)
    ]
    
    if cashify_prices.empty or maple_prices.empty:
        st.warning("Insufficient data for pricing comparison")
        return
    
    # Enhanced product categorization
    cashify_prices['Product Category'] = cashify_prices['Product Type'].apply(categorize_product_type)
    maple_prices['Product Category'] = maple_prices['Product Type'].apply(categorize_product_type)
    
    # Filter for valid categories
    valid_categories = ['Mobile Phone', 'Laptop', 'Tablet', 'SmartWatch (Apple)', 'SmartWatch (Android)']
    cashify_prices = cashify_prices[cashify_prices['Product Category'].isin(valid_categories)]
    maple_prices = maple_prices[maple_prices['Product Category'].isin(valid_categories)]
    
    if cashify_prices.empty or maple_prices.empty:
        st.warning("No valid product categories for pricing comparison")
        return
    
    # Calculate average prices
    cashify_avg = cashify_prices.groupby('Product Category')['Initial Device Amount'].mean().reset_index()
    maple_avg = maple_prices.groupby('Product Category')['Maple Bid'].mean().reset_index()
    
    pricing_comparison = pd.merge(
        cashify_avg,
        maple_avg,
        on='Product Category',
        how='outer'
    ).fillna(0)
    
    pricing_comparison['Price Difference'] = pricing_comparison['Initial Device Amount'] - pricing_comparison['Maple Bid']
    pricing_comparison['Price Difference %'] = (pricing_comparison['Price Difference'] / pricing_comparison['Maple Bid']) * 100
    
    # Format for display
    pricing_comparison = pricing_comparison.round(2)
    pricing_comparison.columns = [
        'Product Category', 
        'Avg Cashify Price (₹)', 
        'Avg Maple Price (₹)', 
        'Price Difference (₹)', 
        'Price Difference (%)'
    ]
    
    st.write(f"**Pricing Comparison for {selected_month} {selected_year}**")
    st.dataframe(pricing_comparison)
    
    # Visualization
    fig = px.bar(
        pricing_comparison.melt(id_vars=['Product Category'], 
                              value_vars=['Avg Cashify Price (₹)', 'Avg Maple Price (₹)']),
        x='Product Category',
        y='value',
        color='variable',
        barmode='group',
        text='value',
        title=f"Average Pricing Comparison ({selected_month} {selected_year})",
        labels={'value': 'Price (₹)', 'variable': 'Price Source'}
    )
    st.plotly_chart(fig, use_container_width=True)

def base_analysis(maple_df, cashify_df, spoc_df):
    st.title("Maple vs Cashify Analytics Dashboard")

    st.header("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        years = sorted(set(maple_df['Year'].dropna()) & set(cashify_df['Year'].dropna()))
        years = [int(year) for year in years]
        selected_year = st.selectbox("Select Year", years if years else [2025], key="year_filter")

    with col2:
        maple_months = set(maple_df['Month'].dropna())
        cashify_months = set(cashify_df['Month'].dropna())
        common_months = sorted(maple_months & cashify_months)
        selected_month = st.selectbox("Select Month", ["All"] + common_months, key="month_filter")

    with col3:
        if selected_month != "All":
            days = []
            if not maple_df.empty and 'Created Date' in maple_df.columns:
                maple_days = maple_df[maple_df['Month'] == selected_month]['Created Date'].dt.day.dropna()
                days.extend(maple_days)
            if not cashify_df.empty and 'Order Date' in cashify_df.columns:
                cashify_days = cashify_df[cashify_df['Month'] == selected_month]['Order Date'].dt.day.dropna()
                days.extend(cashify_days)
            days = sorted(set(map(int, days)))
            selected_day = st.selectbox("Select Day", ["All"] + list(days), key="day_filter")
        else:
            selected_day = "All"

    # Filter data
    maple_filtered = filter_by_date(maple_df, selected_year, selected_month, selected_day)
    cashify_filtered = filter_by_date(cashify_df, selected_year, selected_month, selected_day, is_maple=False)

    if maple_filtered.empty or cashify_filtered.empty:
        st.warning("No data available after applying filters. Please check your data or adjust the filters.")
        return

    # Apply product categorization
    maple_filtered['Product Category'] = maple_filtered['Product Type'].apply(categorize_product_type)
    cashify_filtered['Product Category'] = cashify_filtered['Product Type'].apply(categorize_product_type)

    # Process each section
    process_devices_lost_section(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month)
    process_working_day_losses(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month)
    process_tradein_losses(cashify_filtered, selected_year, selected_month)
    process_pricing_comparison(maple_filtered, cashify_filtered, selected_year, selected_month)

def main():
    if not st.session_state.authenticated:
        login()
        return

    st.sidebar.write(f"Logged in as: {users[st.session_state.username]['name']}")
    logout()

    # Sidebar for reset and sample download
    st.sidebar.header("Options")
    if st.sidebar.button("Reset Column Mappings"):
        st.session_state.column_mappings = {'Maple': {}, 'Cashify': {}, 'SPOC': {}}
        st.session_state.spoc_mapping_complete = False
        st.sidebar.success("Column mappings reset. Please reload the app to re-map columns.")

    # Load data from fixed paths
    try:
        if os.path.exists(MAPLE_FILE_PATH):
            st.session_state.maple_data = pd.read_excel(MAPLE_FILE_PATH)
            st.session_state.column_mappings['Maple'] = {}
        else:
            st.error(f"Maple file not found at {MAPLE_FILE_PATH}. Please ensure the file exists.")
            raise FileNotFoundError
        
        if os.path.exists(CASHIFY_FILE_PATH):
            st.session_state.cashify_data = pd.read_excel(CASHIFY_FILE_PATH)
            st.session_state.column_mappings['Cashify'] = {}
        else:
            st.error(f"Cashify file not found at {CASHIFY_FILE_PATH}. Please ensure the file exists.")
            raise FileNotFoundError
        
        if os.path.exists(SPOC_FILE_PATH):
            st.session_state.spoc_data = pd.read_excel(SPOC_FILE_PATH)
            st.session_state.column_mappings['SPOC'] = {}
            st.session_state.spoc_mapping_complete = False
        else:
            st.error(f"SPOC file not found at {SPOC_FILE_PATH}. Please ensure the file exists.")
            raise FileNotFoundError
    except Exception as e:
        st.error(f"Error loading files: {str(e)}. Please check the Excel files at {BASE_PATH}.")
        st.stop()

    # Validate and process data
    with st.spinner("Processing data..."):
        if st.session_state.maple_data is not None and st.session_state.cashify_data is not None and st.session_state.spoc_data is not None:
            maple_df, maple_mapping = validate_and_map_columns(st.session_state.maple_data.copy(), MAPLE_REQUIRED_COLUMNS, "Maple")
            cashify_df, cashify_mapping = validate_and_map_columns(st.session_state.cashify_data.copy(), CASHIFY_REQUIRED_COLUMNS, "Cashify")
            spoc_df, spoc_mapping = validate_and_map_columns(st.session_state.spoc_data.copy(), SPOC_REQUIRED_COLUMNS, "SPOC")
            
            if maple_df is None or cashify_df is None or spoc_df is None:
                st.error("Please complete column mappings for all datasets. Ensure SPOC 'Store Name' and 'Spoc Name' are mapped to valid columns.")
                st.stop()
            
            if 'Store Name' not in spoc_df.columns or 'Spoc Name' not in spoc_df.columns:
                st.error("SPOC mapping incomplete: Store Name or Spoc Name not found after mapping. Please map these columns.")
                st.stop()
            st.session_state.spoc_mapping_complete = True

            # Standardize data
            maple_df = standardize_month(maple_df)
            cashify_df = standardize_month(cashify_df)
            
            maple_df = standardize_names(maple_df, product_col='Old Product Name')
            cashify_df = standardize_names(cashify_df, product_col='Old Device Name')
            spoc_df = standardize_names(spoc_df)

            maple_df = map_store_names_and_states(maple_df, spoc_df, is_maple=True)
            cashify_df = map_store_names_and_states(cashify_df, spoc_df, is_maple=False)

            maple_df['Created Date'] = pd.to_datetime(maple_df['Created Date'], errors='coerce')
            cashify_df['Order Date'] = pd.to_datetime(cashify_df['Order Date'], errors='coerce')

            # Generate SPOC IDs
            if 'Spoc Name' in maple_df.columns and 'Store Name' in maple_df.columns and 'Store State' in maple_df.columns:
                maple_df['SPOC_ID'] = maple_df.apply(
                    lambda x: generate_spoc_id(x['Spoc Name'], x['Store Name'], x['Store State']) 
                    if pd.notna(x['Spoc Name']) and pd.notna(x['Store Name']) and pd.notna(x['Store State']) else 'Unknown', 
                    axis=1
                )
            if 'Spoc Name' in cashify_df.columns and 'Store Name' in cashify_df.columns and 'Store State' in cashify_df.columns:
                cashify_df['SPOC_ID'] = cashify_df.apply(
                    lambda x: generate_spoc_id(x['Spoc Name'], x['Store Name'], x['Store State']) 
                    if pd.notna(x['Spoc Name']) and pd.notna(x['Store Name']) and pd.notna(x['Store State']) else 'Unknown', 
                    axis=1
                )
            if 'Spoc Name' in spoc_df.columns and 'Store Name' in spoc_df.columns and 'Store State' in spoc_df.columns:
                spoc_df['SPOC_ID'] = spoc_df.apply(
                    lambda x: generate_spoc_id(x['Spoc Name'], x['Store Name'], x['Store State']) 
                    if pd.notna(x['Spoc Name']) and pd.notna(x['Store Name']) and pd.notna(x['Store State']) else 'Unknown', 
                    axis=1
                )

    # Navigation
    page = st.sidebar.radio("Select Page", ["Base Analysis", "Advanced Analytics"])

    if page == "Base Analysis":
        base_analysis(maple_df, cashify_df, spoc_df)
    elif page == "Advanced Analytics":
        advanced_analytics(maple_df, cashify_df, spoc_df)

def base_analysis(maple_df, cashify_df, spoc_df):
    st.title("Maple vs Cashify Analytics Dashboard")

    st.header("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        years = sorted(set(maple_df['Year'].dropna()) & set(cashify_df['Year'].dropna()))
        years = [int(year) for year in years]
        selected_year = st.selectbox("Select Year", years if years else [2025], key="year_filter")

    with col2:
        maple_months = set(maple_df['Month'].dropna())
        cashify_months = set(cashify_df['Month'].dropna())
        common_months = sorted(maple_months & cashify_months)
        selected_month = st.selectbox("Select Month", ["All"] + common_months, key="month_filter")

    with col3:
        if selected_month != "All":
            days = []
            if not maple_df.empty and 'Created Date' in maple_df.columns:
                maple_days = maple_df[maple_df['Month'] == selected_month]['Created Date'].dt.day.dropna()
                days.extend(maple_days)
            if not cashify_df.empty and 'Order Date' in cashify_df.columns:
                cashify_days = cashify_df[cashify_df['Month'] == selected_month]['Order Date'].dt.day.dropna()
                days.extend(cashify_days)
            days = sorted(set(map(int, days)))
            selected_day = st.selectbox("Select Day", ["All"] + list(days), key="day_filter")
        else:
            selected_day = "All"

    # Dynamically determine target column based on selected month
    target_column = f"{selected_month} Target" if selected_month != "All" else "May Target"
    if selected_month != "All" and target_column not in spoc_df.columns:
        st.error(f"Target column '{target_column}' not found in SPOC data. Please ensure the SPOC Master Data Sheet includes this column.")
        st.stop()

    # Define spoc_weekoffs
    if 'Spoc Name' in spoc_df.columns and 'Weekoff Day' in spoc_df.columns and selected_month != "All":
        spoc_weekoffs = {row['Spoc Name']: get_weekoffs(selected_year, selected_month, row['Weekoff Day']) for _, row in spoc_df.iterrows()}
    else:
        st.warning("Spoc Name, Weekoff Day, or specific month selection missing in SPOC data. Weekoff analysis will be skipped.")
        spoc_weekoffs = {}

    maple_filtered = filter_by_date(maple_df, selected_year, selected_month, selected_day)
    cashify_filtered = filter_by_date(cashify_df, selected_year, selected_month, selected_day, is_maple=False)

    if maple_filtered.empty or cashify_filtered.empty:
        st.warning("No data available after applying filters. Please check your data or adjust the filters.")
        st.stop()

    # Apply product category standardization
    maple_filtered['Product Category'] = maple_filtered['Product Type'].apply(categorize_product_type)
    cashify_filtered['Product Category'] = cashify_filtered['Product Type'].apply(categorize_product_type)

    # 1. Average Devices Acquired
    st.header("1. Average Devices Acquired")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Maple")
        maple_daily = maple_filtered.groupby(maple_filtered['Created Date'].dt.date).size().mean() if not maple_filtered.empty else 0
        maple_weekly = maple_filtered.groupby(maple_filtered['Created Date'].dt.isocalendar().week).size().mean() if not maple_filtered.empty else 0
        maple_monthly = len(maple_filtered) if selected_month != "All" else 0
        maple_south = maple_filtered[maple_filtered['Zone'] == 'South']
        maple_west = maple_filtered[maple_filtered['Zone'] == 'West']
        st.write(f"Daily Avg: {maple_daily:.2f}")
        st.write(f"Weekly Avg: {maple_weekly:.2f}")
        st.write(f"Monthly Total: {maple_monthly}")
        st.write(f"South Zone Total: {len(maple_south)}")
        st.write(f"West Zone Total: {len(maple_west)}")


    with col2:
        st.subheader("Cashify")
    
        # Calculate daily average
        cashify_daily = cashify_filtered.groupby(cashify_filtered['Order Date'].dt.date).size().mean() if not cashify_filtered.empty else 0
    
        # Calculate weekly average
        cashify_weekly = cashify_filtered.groupby(cashify_filtered['Order Date'].dt.isocalendar().week).size().mean() if not cashify_filtered.empty else 0
    
    # Calculate monthly total (only if specific month is selected)
        cashify_monthly = len(cashify_filtered) if selected_month != "All" else 0
    
    # Calculate zone totals - with improved filtering
    # First check what zone column exists in the data
        zone_col = 'Zone' if 'Zone' in cashify_filtered.columns else 'Store Zone' if 'Store Zone' in cashify_filtered.columns else None
    
        if zone_col:
            # Clean zone names by stripping whitespace and standardizing case
            cashify_filtered[zone_col] = cashify_filtered[zone_col].str.strip().str.title()
        
            # Filter for South zone (handling different possible names)
            south_zone_filters = [
            cashify_filtered[zone_col].str.contains('South', case=False, na=False),
            cashify_filtered[zone_col].str.contains('S Zone', case=False, na=False),
            cashify_filtered[zone_col].str.contains('South Zone', case=False, na=False)
            ]
        
            # Combine filters with OR condition
            south_filter = pd.Series(False, index=cashify_filtered.index)
            for f in south_zone_filters:
                south_filter = south_filter | f
        
            cashify_south = cashify_filtered[south_filter]
        
            # Filter for West zone
            west_zone_filters = [
                cashify_filtered[zone_col].str.contains('West', case=False, na=False),
                cashify_filtered[zone_col].str.contains('W Zone', case=False, na=False),
                cashify_filtered[zone_col].str.contains('West Zone', case=False, na=False)
            ]
        
            # Combine filters with OR condition
            west_filter = pd.Series(False, index=cashify_filtered.index)
            for f in west_zone_filters:
                west_filter = west_filter | f
        
            cashify_west = cashify_filtered[west_filter]
        else:
            st.warning("Zone column not found in Cashify data")
            cashify_south = pd.DataFrame()
            cashify_west = pd.DataFrame()
    
            # Display the metrics
        st.write(f"Daily Avg: {cashify_daily:.2f}")
        st.write(f"Weekly Avg: {cashify_weekly:.2f}")
        st.write(f"Monthly Total: {cashify_monthly}")
        st.write(f"South Zone Total: {len(cashify_south)}")
        st.write(f"West Zone Total: {len(cashify_west)}")

    # Weekly Market Share Overview
    st.header("1.1 Weekly Market Share Overview")
    if selected_month != "All" and 'Zone' in maple_filtered.columns and 'Store State' in maple_filtered.columns:
        weeks = get_weeks_in_month(selected_year, selected_month)
        weekly_ms_data = []
        south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
        for state in south_states:
            for week_name, start_date, end_date in weeks:
                maple_week = maple_filtered[
                    (maple_filtered['Store State'] == state) &
                    (maple_filtered['Created Date'].dt.date >= start_date) &
                    (maple_filtered['Created Date'].dt.date <= end_date)
                ]
                cashify_week = cashify_filtered[
                    (cashify_filtered['Store State'] == state) &
                    (cashify_filtered['Order Date'].dt.date >= start_date) &
                    (cashify_filtered['Order Date'].dt.date <= end_date)
                ]
                maple_count = len(maple_week)
                total_count = maple_count + len(cashify_week)
                ms = calculate_market_share(maple_count, total_count)
                weekly_ms_data.append({
                    'Store State': state,
                    'Week': week_name,
                    'Market Share (%)': round(ms, 2)
                })
        
        weekly_ms_df = pd.DataFrame(weekly_ms_data)
        if not weekly_ms_df.empty:
            weekly_ms_pivot = weekly_ms_df.pivot(index='Store State', columns='Week', values='Market Share (%)').fillna(0)
            st.write("**Weekly Market Share by State:**")
            st.dataframe(weekly_ms_pivot)
            
            st.download_button(
                label="Download Weekly Market Share as Excel",
                data=create_excel_buffer(weekly_ms_pivot.reset_index(), 'Weekly Market Share'),
                file_name="weekly_market_share.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("No data available for weekly market share analysis.")
    else:
        st.warning("Please select a specific month for weekly market share analysis.")

    # 2. Monthly Market Share Overview for South Zone
    st.header("2. Monthly Market Share Overview for South Zone")
    if 'Zone' in maple_df.columns and 'Store State' in maple_df.columns and 'Month' in maple_df.columns:
        south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
        if selected_month != "All":
            last_n_months = get_last_n_months(selected_month, selected_year, 3)
            monthly_ms_data = []
            for month, year in last_n_months:
                maple_ms = maple_df[
                    (maple_df['Zone'] == 'South') &
                    (maple_df['Store State'].isin(south_states)) &
                    (maple_df['Month'] == month) &
                    (maple_df['Year'] == year)
                ].groupby(['Store State']).size().reset_index(name='Maple Count')
                cashify_ms = cashify_df[
                    (cashify_df['Zone'] == 'South') &
                    (cashify_df['Store State'].isin(south_states)) &
                    (cashify_df['Month'] == month) &
                    (cashify_df['Year'] == year)
                ].groupby(['Store State']).size().reset_index(name='Cashify Count')
                
                monthly_ms = pd.merge(
                    maple_ms,
                    cashify_ms,
                    on=['Store State'],
                    how='outer'
                ).fillna({'Maple Count': 0, 'Cashify Count': 0})
                monthly_ms['Total Trade-ins'] = monthly_ms['Maple Count'] + monthly_ms['Cashify Count']
                monthly_ms['Market Share (%)'] = monthly_ms.apply(
                    lambda row: calculate_market_share(row['Maple Count'], row['Total Trade-ins']), axis=1
                ).round(2)
                monthly_ms['Month'] = month
                monthly_ms_data.append(monthly_ms[['Store State', 'Month', 'Market Share (%)']])
            
            monthly_ms_df = pd.concat(monthly_ms_data, ignore_index=True)
            monthly_ms_pivot = monthly_ms_df.pivot(index='Store State', columns='Month', values='Market Share (%)').fillna(0)
            
            st.write("**Monthly Market Share by State:**")
            st.dataframe(monthly_ms_pivot)
            
            fig_ms = px.bar(
                monthly_ms_df,
                x='Store State',
                y='Market Share (%)',
                color='Month',
                title=f"Monthly Market Share by South Zone States (Current and Last 3 Months)",
                text='Market Share (%)',
                height=600,
                barmode='group'
            )
            fig_ms.update_traces(texttemplate='%{text:.1f}', textposition='auto', textfont=dict(size=14, weight='bold'))
            fig_ms.update_layout(
                showlegend=True,
                xaxis_tickangle=45,
                margin=dict(t=150)
            )
            st.plotly_chart(fig_ms, use_container_width=True)
            
            st.download_button(
                label="Download Monthly Market Share as Excel",
                data=create_excel_buffer(monthly_ms_pivot.reset_index(), 'Monthly Market Share'),
                file_name="monthly_market_share.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Please select a specific month to view current and last 3 months' market share.")
    else:
        st.warning("Required columns (Zone, Store State, Month) missing for monthly market share analysis.")

    # 2.1 Overall Market Share of South Zone (>50%)
    st.header("2.1 Overall Market Share of South Zone (>50%)")
    south_market_data = []
    south_zone = "South"
    south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
    state_dropdown = st.selectbox("Select South Zone State", south_states, key="state_select_2_1")
    if south_zone in set(maple_filtered['Zone'].dropna()) if 'Zone' in maple_filtered.columns else []:
        south_stores = maple_filtered[maple_filtered['Zone'] == south_zone]['Store Name'].unique()
        last_n_months = get_last_n_months(selected_month, selected_year, 2) if selected_month != "All" else [(selected_month, selected_year)]
        last_n_months = [(selected_month, selected_year)] + last_n_months
        for month, year in last_n_months:
            maple_ms = maple_df[
                (maple_df['Zone'] == south_zone) &
                (maple_df['Store State'] == state_dropdown) &
                (maple_df['Month'] == month) &
                (maple_df['Year'] == year)
            ]
            cashify_ms = cashify_df[
                (cashify_df['Zone'] == south_zone) &
                (cashify_df['Store State'] == state_dropdown) &
                (cashify_df['Month'] == month) &
                (cashify_df['Year'] == year)
            ]
            if maple_ms.empty:
                logging.info(f"No Maple data for South Zone in {month} {year}. Skipping.")
                continue
            valid_stores = maple_ms['Store Name'].unique()
            for store in south_stores:
                if store not in valid_stores:
                    continue
                store_spocs = maple_ms[maple_ms['Store Name'] == store]['Spoc Name'].unique() if 'Spoc Name' in maple_ms.columns else ["No Spoc"]
                store_state = maple_ms[maple_ms['Store Name'] == store]['Store State'].iloc[0] if not maple_ms[maple_ms['Store Name'] == store].empty and 'Store State' in maple_ms.columns else "Unknown"
                for store_spoc in store_spocs:
                    maple_count = len(maple_ms[(maple_ms['Store Name'] == store) & (maple_ms['Spoc Name'] == store_spoc)]) if store_spoc != "No Spoc" else len(maple_ms[maple_ms['Store Name'] == store])
                    total_count = maple_count + len(cashify_ms[cashify_ms['Store Name'] == store])
                    ms = calculate_market_share(maple_count, total_count)
                    if ms > 50:
                        south_market_data.append({
                            'Zone': south_zone,
                            'Store State': store_state,
                            'Store Name': store,
                            'Spoc Name': store_spoc,
                            'Month': month,
                            'Market Share (%)': round(ms, 2)
                        })
    
    if south_market_data:
        south_ms_df = pd.DataFrame(south_market_data)
        south_ms_df['Store_SPOC'] = south_ms_df['Store Name'] + ' (' + south_ms_df['Spoc Name'] + ')'
        fig_south_ms = px.bar(
            south_ms_df,
            x='Store_SPOC',
            y='Market Share (%)',
            color='Month',
            text='Market Share (%)',
            title=f"Market Share (>50%) in {state_dropdown} by Store and SPOC",
            height=600,
            barmode='group'
        )
        fig_south_ms.update_traces(texttemplate='%{text:.1f}%', textposition='auto')
        fig_south_ms.update_layout(
            showlegend=True,
            xaxis_title="Store Name (SPOC)",
            xaxis_tickangle=45
        )
        st.plotly_chart(fig_south_ms, use_container_width=True)
    else:
        st.write(f"No data available for {state_dropdown} with market share above 50%.")

    # 2.2 Zone-wise Market Share
    st.header("2.2 Zone-wise Market Share")
    if selected_month != "All":
        last_n_months = get_last_n_months(selected_month, selected_year, 4)
        zone_market_data = []
        all_zones = sorted(set(maple_df['Zone'].dropna())) if 'Zone' in maple_df.columns else ['Unknown']
        for month, year in last_n_months:
            for zn in all_zones:
                if zn in ['South', 'West']:
                    zone_maple = len(maple_df[(maple_df['Zone'] == zn) & (maple_df['Month'] == month) & (maple_df['Year'] == year)])
                    zone_total = zone_maple + len(cashify_df[(cashify_df['Zone'] == zn) & (cashify_df['Month'] == month) & (cashify_df['Year'] == year)]) if 'Zone' in cashify_df.columns else 0
                    zone_ms = calculate_market_share(zone_maple, zone_total)
                    zone_market_data.append({
                        'Zone': zn,
                        'Month': month,
                        'Market Share (%)': round(zone_ms, 2)
                    })
        
        if zone_market_data:
            zone_ms_df = pd.DataFrame(zone_market_data)
            zone_ms_pivot = zone_ms_df.pivot(index='Zone', columns='Month', values='Market Share (%)').fillna(0)
            st.write("**Market Share by Zone (South and West):**")
            st.dataframe(zone_ms_df)
            
            fig_zone_ms = px.bar(
                zone_ms_df,
                x='Zone',
                y='Market Share (%)',
                color='Month',
                text='Market Share (%)',
                title=f"Zone-wise Market Share (Current and Last Month)",
                barmode='group'
            )
            fig_zone_ms.update_traces(texttemplate='%{text:.1f}', textposition='auto')
            fig_zone_ms.update_layout(showlegend=True)
            st.plotly_chart(fig_zone_ms, use_container_width=True)
        else:
            st.write("No zone-wise market share data available.")
    else:
        st.write("Please select a specific month to view current and last 3 months.")

    # 2.3 Low Market Share Stores
    st.header("2.3 Stores with Market Share Below 50% in Selected Zone")
    zones = sorted(set(maple_df['Zone'].dropna())) if 'Zone' in maple_df.columns else ['Unknown']
    zone = st.selectbox("Select Zone", zones, key="zone_select_2_3")
    stores_in_zone = maple_filtered[maple_filtered['Zone'] == zone]['Store Name'].unique() if 'Zone' in maple_filtered.columns else []
    low_market_data = []
    
    for store in stores_in_zone:
        store_spocs = maple_filtered[maple_filtered['Store Name'] == store]['Spoc Name'].unique() if 'Spoc Name' in maple_filtered.columns else ["No Spoc"]
        for store_spoc in store_spocs:
            maple_count = len(maple_filtered[(maple_filtered['Store Name'] == store) & (maple_filtered['Spoc Name'] == store_spoc)]) if store_spoc != "No Spoc" else len(maple_filtered[maple_filtered['Store Name'] == store])
            total_count = maple_count + len(cashify_filtered[cashify_filtered['Store Name'] == store])
            ms = calculate_market_share(maple_count, total_count)
            if ms < 50:
                low_market_data.append({
                    'Store Name': store,
                    'Spoc Name': store_spoc,
                    'Maple Devices': maple_count,
                    'Market Share (%)': ms
                })
    
    if low_market_data:
        low_ms_df = pd.DataFrame(low_market_data)
        st.write("**Stores with Market Share Below 50%**")
        st.dataframe(low_ms_df)

        fig = px.bar(
            low_ms_df,
            x='Market Share (%)',
            y='Store Name',
            color='Spoc Name',
            text='Maple Devices',
            title=f"Stores in {zone} with Market Share Below 50%",
            orientation='h'
        )
        fig.update_traces(textposition='inside')
        st.plotly_chart(fig)

        st.download_button(
            label="Download Low Market Share Stores as Excel",
            data=create_excel_buffer(low_ms_df, 'Low Market Share Stores'),
            file_name="low_ms_stores.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.write(f"No stores in {zone} have a market share below 50%.")

    # 2.4 State-wise Device Counts and Top Performer SPOCs
    st.header("2.4 State-wise Device Counts and Top Performer SPOCs")
    south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
    if 'Store State' in maple_filtered.columns and 'Store State' in cashify_filtered.columns:
        st.write("**Device Counts per State (South Zone)**")
        maple_state_counts = maple_filtered[maple_filtered['Store State'].isin(south_states)].groupby('Store State').size().reset_index(name='Maple Device Count')
        cashify_state_counts = cashify_filtered[cashify_filtered['Store State'].isin(south_states)].groupby('Store State').size().reset_index(name='Cashify Device Count')
        state_counts = pd.merge(maple_state_counts, cashify_state_counts, on='Store State', how='outer').fillna(0)
        state_counts_melted = pd.melt(
            state_counts,
            id_vars=['Store State'],
            value_vars=['Maple Device Count', 'Cashify Device Count'],
            var_name='Source',
            value_name='Device Count'
        )

        logging.info(f"State-wise Device Counts: {state_counts[['Store State', 'Maple Device Count', 'Cashify Device Count']].to_dict('records')}")

        if not state_counts_melted.empty:
            fig_state = px.bar(
                state_counts_melted,
                x='Store State',
                y='Device Count',
                color='Source',
                text='Device Count',
                title=f"Device Counts per State (South Zone, Year: {selected_year}, Month: {selected_month})",
                barmode='group',
                color_discrete_map={'Maple Device Count': '#636EFA', 'Cashify Device Count': '#EF553B'}
            )
            fig_state.update_traces(texttemplate='%{text:.0f}', textposition='auto')
            fig_state.update_layout(showlegend=True)
            st.plotly_chart(fig_state, use_container_width=True)
        else:
            st.write("No device data available for state-wise analysis in South Zone.")
    
    # Top Performer SPOCs
    #st.write("**Top Performing SPOCs (Target Achievement >50%)**")
    #if 'Spoc Name' in maple_filtered.columns and all(col in spoc_df.columns for col in ['Spoc Name', 'Store State', 'Store Name']):
        #last_n_months = get_last_n_months(selected_month, selected_year, 2) if selected_month != "All" else [(selected_month, selected_year)]
        #spoc_achievements = []
        #for month, year in last_n_months:
         #  temp_maple = maple_df[(maple_df['Month'] == month) & (maple_df['Year'] == year) & (maple_df['Store State'].isin(south_states))]
            #temp_ach = temp_maple.groupby(['Spoc Name', 'Store Name', 'Month']).size().reset_index(name='Achievement')
            #temp_ach['Year'] = year
            #spoc_achievements.append(temp_ach)
        #spoc_achievements = pd.concat(spoc_achievements, ignore_index=True)
        
        #target_columns = [col for col in spoc_df.columns if col.endswith('Target')]
        #spoc_targets = spoc_df[['Spoc Name', 'Store Name', 'Store State'] + target_columns]
        #top_spoc_df = pd.merge(
        #   spoc_achievements,
        #   spoc_targets,
        #   on=['Spoc Name', 'Store Name'],
        #   how='inner'
        #)
        #top_spoc_df = top_spoc_df[top_spoc_df['Store State'].isin(south_states)]
        
        #for month in ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']:
            #target_col = f"{month} Target"
            #if target_col in top_spoc_df.columns:
                #top_spoc_df[f'% {month} Target Achieved'] = top_spoc_df.apply(
                #   lambda x: calculate_target_achievement(x['Achievement'], x[target_col]) if x['Month'] == month and pd.notna(x[target_col]) else pd.NA, axis=1
                #).round(2)

        #top_spoc_df = top_spoc_df[top_spoc_df['Month'].isin(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])]
        #)

        # Split into two groups: 50-75% and >75%
        #spoc_50_75 = top_spoc_df[top_spoc_df[f'% {selected_month} Target Achieved'].between(50, 75)]
        #spoc_above_75 = top_spoc_df[top_spoc_df[f'% {selected_month} Target Achieved'] > 75]
        
        #display_cols = ['Spoc Name', 'Store State', 'Store Name', 'Month', 'Achievement'] + [col for col in top_spoc_df.columns if col.endswith('Target') or col.startswith('%')]
        
        # Display 50-75%
        #if not spoc_50_75.empty:
            #st.subheader("SPOCs with Target Achievement 50-75%")
            #st.dataframe(spoc_50_75[display_cols])

            #spoc_50_75['Spoc_Display'] = spoc_50_75['Spoc Name'] + ' (' + spoc_50_75['Store State'] + ')'
            #fig_spoc_50_75 = px.bar(
            #    spoc_50_75,
                #x='Spoc_Display',
                #y=f'% {selected_month} Target Achieved',
                #color='Month',
                #text=f'% {selected_month} Target Achieved',
                #title=f"SPOCs with 50-75% Target Achievement (South Zone)",
                #height=600
            #)
            #fig_spoc_50_75.update_traces(texttemplate='%{text:.1f}%', textposition='auto')
            #fig_spoc_50_75.update_layout(xaxis_title="SPOC Name (State)", xaxis_tickangle=45, showlegend=True)
            #st.plotly_chart(fig_spoc_50_75, use_container_width=True)
        
        # Display >75%
        #if not spoc_above_75.empty:
            #st.subheader("SPOCs with Target Achievement >75%")
            #st.dataframe(spoc_above_75[display_cols])
            
            #spoc_above_75['Spoc_Display'] = spoc_above_75['Spoc Name'] + ' (' + spoc_above_75['Store State'] + ')'
            #fig_spoc_above_75 = px.bar(
            #   spoc_above_75,
            #    x='Spoc_Display',
            #    y=f'% {selected_month} Target Achieved',
            #    color='Month',
            #    text=f'% {selected_month} Target Achieved',
                #title=f"SPOCs with >75% Target Achievement (South Zone)",
                #height=600
            #)
            #fig_spoc_above_75.update_traces(texttemplate='%{text:.1f}%', textposition='auto')
            #fig_spoc_above_75.update_layout(xaxis_title="SPOC Name (State)", xaxis_tickangle=45, showlegend=True)
            #st.plotly_chart(fig_spoc_above_75, use_container_width=True)

            #st.download_button(
            #    label="Download Top Performing SPOCs as Excel",
            #    data=create_excel_buffer(spoc_above_75[display_cols], 'Top SPOCs'),
            #    file_name="top_spocs.xlsx",
            #    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            #)
        #else:
            #st.write("No SPOCs have target achievement above 50% for the selected period.")
    #else:
        #st.warning("Required columns missing for SPOC performance analysis (Spoc Name, Store State, or Target columns).")

    # 2.5 Market Share Analysis
    st.header("2.5 Market Share Analysis")
    zones = sorted(set(maple_df['Zone'].dropna())) if 'Zone' in maple_df.columns else ['Unknown']
    zone = st.selectbox("Select Zone", zones, key="zone_select_2_5")
    store_states = sorted(set(maple_df[maple_df['Zone'] == zone]['Store State'].dropna()) | {'Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry'}) if 'Zone' in maple_df.columns else ['Unknown']
    if not store_states:
        store_states = sorted(set(spoc_df['Store State'].dropna()) | {'Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry'}) if 'Store State' in spoc_df.columns else ['Unknown']
    store_state = st.selectbox("Select Store State", store_states, key="state_select_2_5")
    store_names = sorted(set(maple_filtered[maple_filtered['Store State'] == store_state]['Store Name'].dropna()))
    if not store_names:
        st.warning("No store names available for the selected store state.")
        st.stop()
    store_name = st.selectbox("Select Store Name", store_names, key="store_select_2_5")
    spocs = sorted(set(maple_filtered[maple_filtered['Store Name'] == store_name]['Spoc Name'].dropna())) if 'Spoc Name' in maple_filtered.columns else []
    if not spocs:
        st.info("No SPOCs available for the selected store. Using store-level data.")
        spoc = "No Spoc"
    else:
        spoc = st.selectbox("Select SPOC", spocs, key="spoc_select_2_5")

    if spoc == "No Spoc":
        spoc_achievement = len(maple_filtered[maple_filtered['Store Name'] == store_name])
        total_trades = spoc_achievement + len(cashify_filtered[cashify_filtered['Store Name'] == store_name])
        cashify_count = len(cashify_filtered[(cashify_filtered['Store State'] == store_state) & (cashify_filtered['Store Name'] == store_name)])
    else:
        spoc_achievement = len(maple_filtered[(maple_filtered['Store Name'] == store_name) & (maple_filtered['Spoc Name'] == spoc)])
        total_trades = spoc_achievement + len(cashify_filtered[cashify_filtered['Store Name'] == store_name])
        cashify_count = len(cashify_filtered[(cashify_filtered['Store State'] == store_state) & (cashify_filtered['Store Name'] == store_name)])

    market_share = calculate_market_share(spoc_achievement, total_trades)
    target = spoc_df[spoc_df['Spoc Name'] == spoc][target_column].iloc[0] if spoc != "No Spoc" and not spoc_df[spoc_df['Spoc Name'] == spoc].empty and target_column in spoc_df.columns else 0
    target_achievement_percent = calculate_target_achievement(spoc_achievement, target)
    shortfall = target - spoc_achievement

    st.write(f"Market Share: {market_share:.2f}%")
    st.markdown(f"SPOC Target ({selected_month}): {target}")
    st.write(f"SPOC Achievement: {spoc_achievement}")
    st.write(f"Target Achieved MTD: {target_achievement_percent:.2f}%")
    st.markdown(f"SPOC Shortfall: {shortfall}")
    st.write(f"Total Trade-ins at Store (Maple + Cashify): {total_trades}")
    st.write(f"Total Trade-ins in Cashify (Selected State and Store): {cashify_count}")

    # 3. SPOC Performance in Selected Month
    st.header("3. SPOC Performance in Selected Month")
    if selected_month != "All" and 'Spoc Name' in maple_filtered.columns:
        st.subheader(f"{spoc}'s Performance in {selected_month} {selected_year}")
        spoc_count = len(maple_filtered[maple_filtered['Spoc Name'] == spoc]) if spoc != 'No Spoc' else 0
        st.write(f"Devices Acquired: {spoc_count}")

        last_n_months = get_last_n_months(selected_month, selected_year, 2)
        spoc_perf_data = []
        for month, year in last_n_months:
            temp_maple = maple_df[(maple_df['Month'] == month) & (maple_df['Year'] == year)]
            if spoc != 'No Spoc':
                spoc_cat = temp_maple[temp_maple['Spoc Name'] == spoc].groupby('Product Category').size().reset_index(name='Count')
            else:
                spoc_cat = temp_maple[temp_maple['Store Name'] == store_name].groupby('Product Category').size().reset_index(name='Count')
            spoc_cat['Month'] = month
            spoc_perf_data.append(spoc_cat)

        if spoc_perf_data:
            spoc_perf_df = pd.concat(spoc_perf_data, ignore_index=True)
            valid_categories = ['Mobile Phone', 'Laptop', 'Tablet', 'SmartWatch (Apple)', 'SmartWatch (Android)']
            spoc_perf_df = spoc_perf_df[spoc_perf_df['Product Category'].isin(valid_categories)]
            
            if not spoc_perf_df.empty:
                fig_spoc_perf = px.bar(
                    spoc_perf_df,
                    x='Product Category',
                    y='Count',
                    color='Month',
                    text='Count',
                    title=f"{spoc}'s Devices Acquired by Category (Current and Last Month)",
                    barmode='group'
                )
                fig_spoc_perf.update_traces(texttemplate='%{text:.0f}', textposition='auto')
                fig_spoc_perf.update_layout(showlegend=True)
                st.plotly_chart(fig_spoc_perf)
            else:
                st.write("No spoc-wise performance data available for spoc.")
        else:
            st.write("No performance data available for spoc.")
    else:
        st.write("Please select a specific month to view spoc performance.")

    # 4. Category-wise Contribution in Selected Zone
    st.header("4. Category-wise Contribution in Selected Zone")

    # First ensure we have proper product categorization
    def categorize_products(df):
        if 'Product Category' not in df.columns and 'Product Type' in df.columns:
            df['Product Category'] = df['Product Type'].apply(categorize_product_type)
        elif 'Product Category' not in df.columns:
            df['Product Category'] = 'Other'
        return df

    # Apply categorization to both datasets
    maple_filtered = categorize_products(maple_filtered)
    cashify_filtered = categorize_products(cashify_filtered)

    if 'Zone' not in maple_filtered.columns or 'Zone' not in cashify_filtered.columns:
        st.error("Zone column missing in Maple or Cashify data. Please ensure it is mapped correctly.")
    else:
        maple_zone = maple_filtered[maple_filtered['Zone'] == zone] if zone in maple_filtered['Zone'].values else maple_filtered
        cashify_zone = cashify_filtered[cashify_filtered['Zone'] == zone] if zone in cashify_filtered['Zone'].values else cashify_filtered
    
        if 'Product Category' not in maple_zone.columns or 'Product Category' not in cashify_zone.columns:
            st.error("Product Category column missing in filtered data.")
        else:
            # Get counts by category
            maple_cat = maple_zone.groupby('Product Category').size().reset_index(name='Maple Device Count')
            cashify_cat = cashify_zone.groupby('Product Category').size().reset_index(name='Cashify Device Count')
        
            # Merge the counts
            cat_df = pd.merge(maple_cat, cashify_cat, on='Product Category', how='outer').fillna(0)

            if not cat_df.empty:
                # Prepare data for visualization
                cat_df_melted = pd.melt(
                cat_df,
                id_vars=['Product Category'],
                value_vars=['Maple Device Count', 'Cashify Device Count'],
                var_name='Source',
                value_name='Device Count'
                )
                # Define our valid categories (including 'Other' for visualization)
                valid_categories = ['Mobile Phone', 'Laptop', 'Tablet',
                                    'SmartWatch (Apple)', 'SmartWatch (Android)', 'Other']

                # Filter and sort categories
                cat_df_melted = cat_df_melted[cat_df_melted['Product Category'].isin(valid_categories)]
                cat_df_melted['Product Category'] = pd.Categorical(
                    cat_df_melted['Product Category'],
                    categories=valid_categories,
                    ordered=True
                    )
                cat_df_melted = cat_df_melted.sort_values('Product Category')
            
                if not cat_df_melted.empty:
                    # Create visualization
                    fig = px.bar(
                    cat_df_melted,
                    x='Product Category',
                    y='Device Count',
                    color='Source',
                    text='Device Count',
                    title=f"Category-wise Device Counts in {zone} Zone",
                    category_orders={"Product Category": valid_categories}
                    )
                    fig.update_traces(texttemplate='%{text:.0f}', textposition='auto')
                    fig.update_layout(
                    barmode='group', 
                    showlegend=True,
                    xaxis_title="Product Category",
                    yaxis_title="Number of Devices"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                    # Show raw data as well
                    st.subheader("Detailed Category Breakdown")
                    st.dataframe(cat_df.sort_values('Maple Device Count', ascending=False))
                else:
                    st.warning(f"No valid category data for {zone}. Available categories: {cat_df['Product Category'].unique().tolist()}")
            else:
                st.warning(f"No category data available for {zone} zone.")


# Assuming these are defined earlier:
# maple_filtered, cashify_filtered, spoc_df, spoc, spoc_weekoffs,
# selected_month, selected_year, store_name, store_state
# and helper function create_csv_buffer(), calculate_market_share()

    def process_devices_lost_section(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month, selected_day):
        st.header("5. Devices Lost on SPOC Weekoff Days at Their Store")
    
        if selected_month == "All":
            st.warning("Please select a specific month for weekoff analysis")
            return
    
        # Get SPOC weekoff days
        spoc_weekoffs = {}
        if 'Weekoff Day' in spoc_df.columns and 'Spoc Name' in spoc_df.columns:
            for _, row in spoc_df.iterrows():
                if pd.notna(row['Weekoff Day']) and row['Weekoff Day'] != "Vacant":
                    spoc_weekoffs[row['Spoc Name']] = get_weekoffs(selected_year, selected_month, row['Weekoff Day'])
    
        if not spoc_weekoffs:
            st.info("No weekoff data available in SPOC data")
            return
    
        # Get SPOCs with weekoff data
        spoc_list = list(spoc_weekoffs.keys())
        if not spoc_list:
            st.info("No SPOCs with weekoff days found")
            return
    
        selected_spoc = st.selectbox("Select SPOC", spoc_list, key="spoc_weekoff_select")
        weekoff_dates = spoc_weekoffs.get(selected_spoc, [])
    
        if not weekoff_dates:
            st.info(f"No weekoff days for {selected_spoc} in {selected_month}")
            return
    
        # Get stores for this SPOC
        spoc_stores = spoc_df[spoc_df['Spoc Name'] == selected_spoc]['Store Name'].unique()
        if not spoc_stores:
            st.info(f"No stores found for SPOC {selected_spoc}")
            return
    
        # Get Cashify devices lost on weekoff days
        weekoff_dates_set = set([d if isinstance(d, date) else d.date() for d in weekoff_dates])
        cashify_losses = cashify_filtered[
            (cashify_filtered['Store Name'].isin(spoc_stores)) &
            (cashify_filtered['Order Date'].dt.date.isin(weekoff_dates_set))
        ]
    
        if cashify_losses.empty:
            st.info(f"No devices lost on weekoff days for {selected_spoc}")
            return
    
    # Group by store and product category
        losses_by_store = cashify_losses.groupby(['Store Name', 'Product Category']).size().reset_index(name='Count')
    
        st.write(f"**Devices lost on {selected_spoc}'s weekoff days:**")
        st.dataframe(losses_by_store)
    
        if not losses_by_store.empty:
            fig = px.bar(
            losses_by_store,
            x='Store Name',
            y='Count',
            color='Product Category',
            text='Count',
            title=f"Devices Lost on {selected_spoc}'s Weekoff Days by Store",
            barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

    def process_working_day_losses(maple_filtered, cashify_filtered, spoc_df, selected_year, selected_month):
        st.header("6. Working Day Losses")
    
        if selected_month == "All":
            st.warning("Please select a specific month for working day analysis")
            return
    
            # Get SPOC weekoff days
        spoc_weekoffs = {}
        if 'Weekoff Day' in spoc_df.columns and 'Spoc Name' in spoc_df.columns:
            for _, row in spoc_df.iterrows():
                if pd.notna(row['Weekoff Day']) and row['Weekoff Day'] != "Vacant":
                    spoc_weekoffs[row['Spoc Name']] = get_weekoffs(selected_year, selected_month, row['Weekoff Day'])

        if not spoc_weekoffs:
            st.info("No weekoff data available in SPOC data")
            return
    
        spoc_list = list(spoc_weekoffs.keys())
        if not spoc_list:
            st.info("No SPOCs with weekoff days found")
            return
    
        selected_spoc = st.selectbox("Select SPOC", spoc_list, key="spoc_working_select")
        weekoff_dates = spoc_weekoffs.get(selected_spoc, [])
    
        if not weekoff_dates:
            st.info(f"No weekoff days for {selected_spoc} in {selected_month}")
            return
    
        # Get stores for this SPOC
        spoc_stores = spoc_df[spoc_df['Spoc Name'] == selected_spoc]['Store Name'].unique()
        if not spoc_stores:
            st.info(f"No stores found for SPOC {selected_spoc}")
            return
    
        # Get working days (all dates in month minus weekoff days)
        month_num = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
                 "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}
        first_day = date(selected_year, month_num[selected_month], 1)
        last_day = (first_day + timedelta(days=31)).replace(day=1) - timedelta(days=1)
        all_dates = [first_day + timedelta(days=i) for i in range((last_day - first_day).days + 1)]
        working_dates = [d for d in all_dates if d not in [wd.date() for wd in weekoff_dates]]
    
        # Get Cashify devices lost on working days
        cashify_losses = cashify_filtered[
            (cashify_filtered['Store Name'].isin(spoc_stores)) &
        (cashify_filtered['Order Date'].dt.date.isin(working_dates))
    ]
    
        if cashify_losses.empty:
            st.info(f"No working day losses for {selected_spoc}")
            return
    
        # Group by store and product category
        losses_by_store = cashify_losses.groupby(['Store Name', 'Product Category']).size().reset_index(name='Count')
    
        st.write(f"**Working day losses for {selected_spoc}:**")
        st.dataframe(losses_by_store)
    
        if not losses_by_store.empty:
            fig = px.bar(
            losses_by_store,
            x='Store Name',
            y='Count',
            color='Product Category',
            text='Count',
            title=f"Working Day Losses for {selected_spoc} by Store",
            barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)

    def process_tradein_losses(cashify_filtered, selected_year, selected_month):
        st.header("7. Trade-ins Lost to Cashify by State and Store")
    
        if selected_month == "All":
            st.warning("Please select a specific month for trade-in analysis")
            return
    
        # Filter for south states and completed orders
        south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
        status_filter = cashify_filtered['Order Status'] == 'Completed' if 'Order Status' in cashify_filtered.columns else pd.Series([True] * len(cashify_filtered))
    
        tradein_losses = cashify_filtered[
            (cashify_filtered['Store State'].isin(south_states)) &
            (cashify_filtered['Month'] == selected_month) &
            (cashify_filtered['Year'] == selected_year) &
            status_filter
        ]
    
        if tradein_losses.empty:
            st.info("No trade-in losses data available for selected period")
            return
    
    # Enhanced product categorization
        tradein_losses['Product Category'] = tradein_losses['Product Type'].apply(categorize_product_type)
    
    # Create detailed table
        st.subheader("Detailed Trade-in Losses by State, Store and SPOC")
    
    # Get required columns (check if they exist first)
        required_cols = ['Store State', 'Store Name', 'Spoc Name', 'Product Category', 
                    'Product Type', 'Old Device Name', 'Initial Device Amount']
        available_cols = [col for col in required_cols if col in tradein_losses.columns]
    
        if not available_cols:
            st.error("Required columns not found in Cashify data")
            return
    
        detailed_losses = tradein_losses[available_cols].copy()
    
    # Add count column
        detailed_losses['Count'] = 1
    
    # Create pivot table for visualization
        pivot_data = detailed_losses.groupby(['Store State', 'Store Name', 'Spoc Name', 'Product Category']).agg({
        'Count': 'sum',
        'Initial Device Amount': 'mean'
        }).reset_index()
    
    # Display the detailed data
        st.dataframe(detailed_losses)
    
    # Visualization 1: State-wise losses
        st.subheader("Trade-in Losses by State")
        state_losses = detailed_losses.groupby('Store State')['Count'].sum().reset_index()
        fig_state = px.bar(
        state_losses,
        x='Store State',
        y='Count',
        text='Count',
        title=f"Total Trade-ins Lost to Cashify by State ({selected_month} {selected_year})",
        color='Store State'
        )
        st.plotly_chart(fig_state, use_container_width=True)
    
    # Visualization 2: Store-wise losses within each state
        st.subheader("Trade-in Losses by Store (Within Each State)")
    
    # Create a selectbox to choose state
        selected_state = st.selectbox(
        "Select State to View Store-wise Losses",
            sorted(detailed_losses['Store State'].unique()),
            key="state_select_tradein"
        )
    
        state_store_losses = detailed_losses[detailed_losses['Store State'] == selected_state]
        store_summary = state_store_losses.groupby(['Store Name', 'Spoc Name'])['Count'].sum().reset_index()
    
        fig_store = px.bar(
            store_summary,
            x='Store Name',
        y='Count',
        color='Spoc Name',
        text='Count',
        title=f"Trade-in Losses by Store in {selected_state}",
        barmode='group'
        )
        fig_store.update_layout(xaxis_tickangle=45)
        st.plotly_chart(fig_store, use_container_width=True)
    
    # Visualization 3: Product category distribution for selected state
        st.subheader(f"Product Category Distribution in {selected_state}")
        state_category_losses = state_store_losses.groupby('Product Category')['Count'].sum().reset_index()
    
        fig_category = px.pie(
        state_category_losses,
        names='Product Category',
        values='Count',
        title=f"Product Categories Lost in {selected_state}"
        )
        st.plotly_chart(fig_category, use_container_width=True)
    
    # Download buttons
        st.download_button(
        label="Download Detailed Trade-in Losses as CSV",
        data=create_csv_buffer(detailed_losses, 'Trade-in Losses'),
        file_name=f"tradein_losses_{selected_month}_{selected_year}.csv",
        mime="text/csv"
        )
    
        st.download_button(
        label="Download Summary Data as CSV",
        data=create_csv_buffer(pivot_data, 'Trade-in Summary'),
        file_name=f"tradein_summary_{selected_month}_{selected_year}.csv",
        mime="text/csv"
        )

    def process_pricing_comparison(maple_filtered, cashify_filtered, selected_year, selected_month):
        st.header("8. Device Loss to Cashify with Pricing Comparison")
    
        if selected_month == "All":
            st.warning("Please select a specific month for pricing comparison")
            return
    
        south_states = ['Andhra Pradesh', 'Telangana', 'Karnataka', 'Tamil Nadu', 'Kerala', 'Puducherry']
    
        # Filter for south states and current month
        cashify_prices = cashify_filtered[
            (cashify_filtered['Store State'].isin(south_states)) &
            (cashify_filtered['Month'] == selected_month) &
            (cashify_filtered['Year'] == selected_year)
        ]
    
        maple_prices = maple_filtered[
         (maple_filtered['Store State'].isin(south_states)) &
         (maple_filtered['Month'] == selected_month) &
         (maple_filtered['Year'] == selected_year)
        ]
    
        if cashify_prices.empty or maple_prices.empty:
            st.warning("Insufficient data for pricing comparison")
            return
    
    # Enhanced product categorization
    cashify_prices['Product Category'] = cashify_prices['Product Type'].apply(categorize_product_type)
    maple_prices['Product Category'] = maple_prices['Product Type'].apply(categorize_product_type)
    
    # Filter for valid categories
    valid_categories = ['Mobile Phone', 'Laptop', 'Tablet', 'SmartWatch (Apple)', 'SmartWatch (Android)']
    cashify_prices = cashify_prices[cashify_prices['Product Category'].isin(valid_categories)]
    maple_prices = maple_prices[maple_prices['Product Category'].isin(valid_categories)]
    
    if cashify_prices.empty or maple_prices.empty:
        st.warning("No valid product categories for pricing comparison")
        return
    
    # Calculate average prices by category and program type
    cashify_avg = cashify_prices.groupby(['Product Category', 'Product Type'])['Initial Device Amount'].mean().reset_index()
    maple_avg = maple_prices.groupby(['Product Category', 'Product Type'])['Maple Bid'].mean().reset_index()
    
    pricing_comparison = pd.merge(
        cashify_avg,
        maple_avg,
        on=['Product Category', 'Product Type'],
        how='outer',
        suffixes=('_Cashify', '_Maple')
    ).fillna(0)
    
    pricing_comparison['Price Difference (₹)'] = pricing_comparison['Initial Device Amount'] - pricing_comparison['Maple Bid']
    pricing_comparison['Price Difference (%)'] = (pricing_comparison['Price Difference (₹)'] / pricing_comparison['Maple Bid']) * 100
    
    # Format for display
    pricing_comparison = pricing_comparison.round(2)
    pricing_comparison.columns = [
        'Product Category', 
        'Program Type',
        'Avg Cashify Price (₹)', 
        'Avg Maple Price (₹)', 
        'Price Difference (₹)', 
        'Price Difference (%)'
    ]
    
    st.write(f"**Pricing Comparison for {selected_month} {selected_year}**")
    st.dataframe(pricing_comparison)
    
    # Visualization - Price Difference by Category and Program Type
    fig = px.bar(
        pricing_comparison,
        x='Product Category',
        y='Price Difference (₹)',
        color='Program Type',
        barmode='group',
        text='Price Difference (₹)',
        title=f"Price Difference (Cashify - Maple) by Category ({selected_month} {selected_year})",
        labels={'value': 'Price Difference (₹)', 'variable': 'Price Source'}
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)
    
    # Visualization - Average Prices Comparison
    fig_prices = px.bar(
        pricing_comparison.melt(id_vars=['Product Category', 'Program Type'], 
                              value_vars=['Avg Cashify Price (₹)', 'Avg Maple Price (₹)']),
        x='Product Category',
        y='value',
        color='variable',
        facet_col='Program Type',
        text='value',
        title=f"Average Pricing Comparison by Program Type ({selected_month} {selected_year})",
        labels={'value': 'Price (₹)', 'variable': 'Price Source'}
    )
    fig_prices.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig_prices.update_layout(showlegend=True)
    st.plotly_chart(fig_prices, use_container_width=True)

def advanced_analytics(maple_df, cashify_df, spoc_df):
    st.title("Advanced Analytics & SPOC Performance")
    
    # 1. Zonal Market Share Trend with Hourly Data Points
    st.header("1. Zonal Market Share Trend")
    zone_options = [z for z in maple_df['Zone'].unique() if z in ['South', 'West']]
    selected_zone_adv = st.selectbox("Select Zone", zone_options, key="adv_zone")
    timeframe_options = [7, 15, 30, 60, 90]
    default_timeframe = 30
    timeframe_days = st.sidebar.radio("Select Timeframe (Days)", options=timeframe_options, index=timeframe_options.index(default_timeframe))

    if selected_zone_adv:
        end_date = maple_df['Created Date'].max()
        start_date = end_date - timedelta(days=timeframe_days)
    
        if timeframe_days == 1:  # Special handling for 1-day view
            date_range_index = pd.date_range(start_date, end_date, freq='H')
            maple_daily = maple_df[maple_df['Zone'] == selected_zone_adv].set_index('Created Date').resample('H').size().reindex(date_range_index, fill_value=0)
            cashify_daily = cashify_df[cashify_df['Zone'] == selected_zone_adv].set_index('Order Date').resample('H').size().reindex(date_range_index, fill_value=0)
        else:
            date_range_index = pd.date_range(start_date, end_date, freq='D')
            maple_daily = maple_df[maple_df['Zone'] == selected_zone_adv].set_index('Created Date').resample('D').size().reindex(date_range_index, fill_value=0)
            cashify_daily = cashify_df[cashify_df['Zone'] == selected_zone_adv].set_index('Order Date').resample('D').size().reindex(date_range_index, fill_value=0)
    
        daily_ms = pd.DataFrame({'Maple': maple_daily, 'Cashify': cashify_daily})
        daily_ms['Market Share'] = daily_ms.apply(lambda r: calculate_market_share(r['Maple'], r['Maple'] + r['Cashify']), axis=1)
        daily_ms['Delta'] = daily_ms['Market Share'].diff()
    
    # Create figure with colored markers
    fig_trend = go.Figure()
    
    # Add the main line
    fig_trend.add_trace(go.Scatter(
        x=daily_ms.index, 
        y=daily_ms['Market Share'], 
        name='Market Share', 
        mode='lines',
        line=dict(color='royalblue'),
        showlegend=False
    ))
    
    # Add increasing points (green)
    increasing = daily_ms[daily_ms['Delta'] > 0]
    if not increasing.empty:
        fig_trend.add_trace(go.Scatter(
            x=increasing.index,
            y=increasing['Market Share'],
            mode='markers',
            marker=dict(color='green', size=8),
            name='Increasing',
            showlegend=False
        ))
    
    # Add decreasing points (red)
    decreasing = daily_ms[daily_ms['Delta'] < 0]
    if not decreasing.empty:
        fig_trend.add_trace(go.Scatter(
            x=decreasing.index,
            y=decreasing['Market Share'],
            mode='markers',
            marker=dict(color='red', size=8),
            name='Decreasing',
            showlegend=False
        ))
    
    # Add neutral points (grey) - only if we want to show them
    neutral = daily_ms[daily_ms['Delta'] == 0]
    if not neutral.empty:
        fig_trend.add_trace(go.Scatter(
            x=neutral.index,
            y=neutral['Market Share'],
            mode='markers',
            marker=dict(color='grey', size=6),
            name='Neutral',
            showlegend=False
        ))
    
    fig_trend.update_layout(
        title=f"Market Share Trend for {selected_zone_adv} Zone (Last {timeframe_days} Days{' - Hourly View' if timeframe_days == 1 else ''})",
        yaxis_title="Market Share (%)",
        xaxis_title="Time (Hourly)" if timeframe_days == 1 else "Date",
        hovermode="x unified"
    )
    
    # Add data table below the chart
    st.plotly_chart(fig_trend, use_container_width=True)
    
    # Display data containers
    with st.expander("View Raw Data"):
        st.write("### Market Share Trend Data")
        st.dataframe(daily_ms)
        
        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                label="Average Market Share",
                value=f"{daily_ms['Market Share'].mean():.1f}%",
                delta=f"{daily_ms['Market Share'].iloc[-1] - daily_ms['Market Share'].iloc[0]:.1f}%",
                delta_color="normal"
            )
        with col2:
            st.metric(
                label="Highest Market Share",
                value=f"{daily_ms['Market Share'].max():.1f}%",
                delta=f"on {daily_ms['Market Share'].idxmax().strftime('%b %d')}"
            )
        with col3:
            st.metric(
                label="Lowest Market Share",
                value=f"{daily_ms['Market Share'].min():.1f}%",
                delta=f"on {daily_ms['Market Share'].idxmin().strftime('%b %d')}"
            )
    
    # Download button
    csv = daily_ms.to_csv(index=True).encode('utf-8')
    st.download_button(
        label="Download Market Share Data as CSV",
        data=csv,
        file_name=f"market_share_trend_{selected_zone_adv}_{timeframe_days}days.csv",
        mime="text/csv"
    )

    # 2. State Performance in Zone
    st.header(f"2. State Performance in {selected_zone_adv} Zone (Last 30 Days)")
    states_in_zone = maple_df[maple_df['Zone'] == selected_zone_adv]['Store State'].dropna().unique()
    state_perf_data = []
    if len(states_in_zone) > 0:
        end_date = maple_df['Created Date'].max()
        for state in states_in_zone:
            maple_state = len(maple_df[(maple_df['Store State'] == state) & (maple_df['Created Date'] >= end_date - timedelta(days=30))])
            cashify_state = len(cashify_df[(cashify_df['Store State'] == state) & (cashify_df['Order Date'] >= end_date - timedelta(days=30))])
            state_ms = calculate_market_share(maple_state, maple_state + cashify_state)
            state_perf_data.append({'State': state, 'Market Share (%)': state_ms, 'Maple Volume': maple_state})
        
        state_perf_df = pd.DataFrame(state_perf_data)
        col1, col2 = st.columns(2)
        with col1:
            st.write("📈 **Growing States (MS > 50%)**")
            st.dataframe(state_perf_df[state_perf_df['Market Share (%)'] > 50].sort_values('Market Share (%)', ascending=False))
        with col2:
            st.write("📉 **De-growing States (MS < 20%)**")
            st.dataframe(state_perf_df[state_perf_df['Market Share (%)'] < 20].sort_values('Market Share (%)'))

    # 3. SPOC Performance Profile
    st.header("3. SPOC Performance Profile")
    if 'SPOC_ID' in spoc_df.columns:
        spoc_list = spoc_df.sort_values('Spoc Name')[['Spoc Name', 'SPOC_ID']].dropna().drop_duplicates()
        selected_spoc_id_adv = st.selectbox("Select SPOC", spoc_list['SPOC_ID'], format_func=lambda x: spoc_list[spoc_list['SPOC_ID']==x]['Spoc Name'].iloc[0], key="adv_spoc_select")
        if selected_spoc_id_adv:
            start_date_sep = pd.Timestamp('2024-09-01')
            spoc_history = maple_df[(maple_df['SPOC_ID'] == selected_spoc_id_adv) & (maple_df['Created Date'] >= start_date_sep)]
            st.metric(f"Total Trade-ins Since Sep '24", len(spoc_history))
            if not spoc_history.empty:
                monthly_perf = spoc_history.set_index('Created Date').resample('ME').size().reset_index()
                monthly_perf.columns = ['Month', 'Count']
                monthly_perf['Month'] = monthly_perf['Month'].dt.strftime('%b %Y')
                fig_spoc_hist = px.bar(monthly_perf, x='Month', y='Count', text_auto=True, title="Monthly Trade-in Performance")
                st.plotly_chart(fig_spoc_hist)
    
    # 4. Trade-in Loss Analysis
    st.header("4. Trade-in Loss Analysis (Last 6 Months)")
    last_6_months = get_last_n_months_for_page(6)
    cashify_last_6m = cashify_df.merge(pd.DataFrame(last_6_months, columns=['Month', 'Year']), on=['Month', 'Year'], how='inner')
    if not cashify_last_6m.empty:
        st.subheader("Loss by Product Category (LOB)")
        lob_loss = cashify_last_6m.groupby(['Month', 'Product Category']).size().reset_index(name='Count')
        
        # Create a larger, clearer visualization
        fig_lob_loss = px.bar(
            lob_loss, 
            x='Month', 
            y='Count', 
            color='Product Category',
            barmode='group',
            title='Monthly Device Losses by Category',
            height=600,
            text='Count'
        )
        fig_lob_loss.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Devices Lost",
            legend_title="Product Category",
            hovermode="x unified"
        )
        fig_lob_loss.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig_lob_loss, use_container_width=True)

        st.subheader("Top 10 Stores with Highest Losses (and Top Lost Devices)")
        # Get top 10 stores by total losses
        store_loss_total = cashify_last_6m.groupby(['Store Name', 'Store State']).size().reset_index(name='Total Losses').sort_values('Total Losses', ascending=False).head(10)
        
        if not store_loss_total.empty:
            # Get top lost devices for each store
            top_device_loss = cashify_last_6m[cashify_last_6m['Store Name'].isin(store_loss_total['Store Name'])]
            top_device_loss = top_device_loss.groupby(['Store Name', 'Old Device Name']).size().reset_index(name='Device Count')
            top_device_loss = top_device_loss.loc[top_device_loss.groupby('Store Name')['Device Count'].idxmax()]
            
            # Merge with total losses
            store_loss_final = pd.merge(
                store_loss_total,
                top_device_loss[['Store Name', 'Old Device Name', 'Device Count']],
                on='Store Name',
                how='left'
            )
            
            # Rename columns for clarity
            store_loss_final.rename(columns={
                'Old Device Name': 'Top Lost Device',
                'Device Count': 'Top Device Loss Count'
            }, inplace=True)
            
            # Add SPOC information
            store_loss_final = pd.merge(
                store_loss_final,
                spoc_df[['Store Name', 'Spoc Name']].drop_duplicates(),
                on='Store Name',
                how='left'
            )
            
            # Reorder columns
            store_loss_final = store_loss_final[['Store Name', 'Store State', 'Spoc Name', 'Total Losses', 'Top Lost Device', 'Top Device Loss Count']]
            
            st.dataframe(store_loss_final)
            
            # Download button
            st.download_button(
                label="Download Top Loss Stores as Excel",
                data=create_excel_buffer(store_loss_final, 'Top Loss Stores'),
                file_name="top_loss_stores.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # 5. Highest Productive Stores
    st.header("5. Highest Productive Stores (Last 6 Months)")
    last_6_months = get_last_n_months_for_page(6)
    
    # Add zone filter
    zone_filter = st.selectbox("Select Zone for Store Productivity", ['South', 'West'], key="store_prod_zone")
    
    maple_last_6m = maple_df[
        (maple_df['Zone'] == zone_filter) &
        (maple_df['Month'].isin([m[0] for m in last_6_months])) &
        (maple_df['Year'].isin([m[1] for m in last_6_months]))
    ]
    
    if not maple_last_6m.empty:
        # Get top 6 stores in the selected zone
        top_6_stores = maple_last_6m.groupby('Store Name').size().nlargest(6).index

        # Prepare data for visualization
        top_stores_monthly = maple_last_6m[maple_last_6m['Store Name'].isin(top_6_stores)].groupby(['Store Name', 'Month']).size().reset_index(name='Count')

        # Ensure correct month ordering
        month_order = [m[0] for m in last_6_months]
        top_stores_monthly['Month'] = pd.Categorical(top_stores_monthly['Month'], categories=month_order, ordered=False)
        
        # Create visualization
        fig_prod = px.line(
            top_stores_monthly, 
            x='Month', 
            y='Count', 
            color='Store Name', 
            markers=True, 
            text='Count', 
            title=f"Monthly Productivity of Top 15 Maple Stores in {zone_filter} Zone",
            height=600
        )
        fig_prod.update_traces(textposition="top center")
        fig_prod.update_layout(
            xaxis_title="Month",
            yaxis_title="Number of Trade-ins",
            legend_title="Store Name"
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.warning(f"No data available for {zone_filter} zone in the last 6 months")


    # 6. Monthly SPOC Target Performance
    st.header("6. SPOC Target Performance (Current vs. Previous Month)")
    if not spoc_df.empty and 'SPOC_ID' in spoc_df.columns:
        months_to_compare = get_last_n_months_for_page(2)
        if len(months_to_compare) == 2:
            prev_month, prev_year = months_to_compare[0]
            curr_month, curr_year = months_to_compare[1]
            
            perf_df = spoc_df[['SPOC_ID', 'Spoc Name', 'Store Name', 'Store State']].copy().dropna(subset=['SPOC_ID'])
            
            for m, y, suffix in [(curr_month, curr_year, '_curr'), (prev_month, prev_year, '_prev')]:
                target_col = f"{m} Target"
                if target_col in spoc_df.columns:
                    perf_df = pd.merge(perf_df, spoc_df[['SPOC_ID', target_col]], on='SPOC_ID', how='left')
                    perf_df.rename(columns={target_col: f'Target{suffix}'}, inplace=True)
                    ach_df = maple_df[(maple_df['Month'] == m) & (maple_df['Year'] == y)].groupby('SPOC_ID').size().reset_index(name=f'Achieved{suffix}')
                    perf_df = pd.merge(perf_df, ach_df, on='SPOC_ID', how='left')
                    perf_df[f'% Achieved{suffix}'] = perf_df.apply(lambda r: calculate_target_achievement(r.get(f'Achieved{suffix}', 0), r.get(f'Target{suffix}', 0)), axis=1).round(1)

            perf_df = perf_df.fillna(0)
            display_cols = ['Spoc Name', 'Store Name', 'Store State']
            for suffix, month_name in [('_curr', curr_month), ('_prev', prev_month)]:
                for prefix in ['% Achieved', 'Achieved', 'Target']:
                    col_name = f"{prefix}{suffix}"
                    if col_name in perf_df.columns:
                        display_cols.append(col_name)
            
            perf_display_df = perf_df[display_cols]
            perf_display_df.columns = perf_display_df.columns.str.replace('_curr', f' ({curr_month})').str.replace('_prev', f' ({prev_month})')
            st.dataframe(perf_display_df.sort_values(by=f'% Achieved ({curr_month})', ascending=False))

    # 7. Store Performance Ranking & Analysis
    st.header("7. Store Performance Ranking & Analysis")
    min_date, max_date = maple_df['Created Date'].min().date(), maple_df['Created Date'].max().date()
    date_range = st.date_input("Select Date Range", (max_date - timedelta(days=30), max_date), min_date, max_date, key="perf_date_range_adv")
    
    if len(date_range) == 2:
        start, end = date_range
        maple_perf = maple_df[maple_df['Created Date'].dt.date.between(start, end)]
        cashify_perf = cashify_df[cashify_df['Order Date'].dt.date.between(start, end)]
        
        maple_counts = maple_perf.groupby(['Store Name', 'Store State', 'Zone']).size().reset_index(name='Maple Count')
        cashify_counts = cashify_perf.groupby(['Store Name', 'Store State', 'Zone']).size().reset_index(name='Cashify Count')
        
        store_perf_df = pd.merge(maple_counts, cashify_counts, on=['Store Name', 'Store State', 'Zone'], how='outer').fillna(0)
        store_perf_df['Market Share (%)'] = store_perf_df.apply(
            lambda r: calculate_market_share(r['Maple Count'], r['Maple Count'] + r['Cashify Count']), 
            axis=1
        ).round(2)
        
        # Add SPOC information
        store_perf_df = pd.merge(
            store_perf_df,
            spoc_df[['Store Name', 'Spoc Name']].drop_duplicates(),
            on='Store Name',
            how='left'
        )
        
        st.subheader("State-wise Contribution to Maple Trade-ins")
        state_contrib = store_perf_df.groupby('Store State')['Maple Count'].sum().reset_index()
        fig_state_pie = px.pie(state_contrib, names='Store State', values='Maple Count', title="Maple Trade-in Volume by State")
        st.plotly_chart(fig_state_pie)
        st.subheader("Store Performance Ranking")
        st.dataframe(store_perf_df.sort_values('Maple Count', ascending=False).reset_index(drop=True))

        st.subheader("Stores where Cashify Outperforms Maple")
        st.dataframe(store_perf_df[store_perf_df['Cashify Count'] > store_perf_df['Maple Count']].sort_values('Cashify Count', ascending=False))

if __name__ == "__main__":
    main()