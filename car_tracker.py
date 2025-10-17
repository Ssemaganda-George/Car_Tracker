# car_tracker.py
import streamlit as st
import pandas as pd
import datetime as dt
import os
import hashlib
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="🚗 Car Booking & Tracking", layout="wide")

# ---------- Authentication Functions ----------
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_users():
    if os.path.exists("users.csv"):
        return pd.read_csv("users.csv")
    else:
        # Create default admin user
        default_user = pd.DataFrame({
            "username": ["admin"], 
            "password": [hash_password("admin123")], 
            "full_name": ["System Administrator"],
            "created_date": [dt.date.today().strftime("%Y-%m-%d")]
        })
        default_user.to_csv("users.csv", index=False)
        return default_user

def authenticate(username, password):
    users = load_users()
    hashed_password = hash_password(password)
    user = users[(users["username"] == username) & (users["password"] == hashed_password)]
    return not user.empty, user.iloc[0]["full_name"] if not user.empty else ""

def register_user(username, password, full_name):
    users = load_users()
    if username in users["username"].values:
        return False, "Username already exists"
    
    new_user = pd.DataFrame({
        "username": [username],
        "password": [hash_password(password)],
        "full_name": [full_name],
        "created_date": [dt.date.today().strftime("%Y-%m-%d")]
    })
    users = pd.concat([users, new_user], ignore_index=True)
    users.to_csv("users.csv", index=False)
    return True, "User registered successfully"

# ---------- Data Loaders ----------
@st.cache_data
def load_data(filename, columns, user_prefix=""):
    full_filename = f"{user_prefix}_{filename}" if user_prefix else filename
    if os.path.exists(full_filename):
        try:
            df = pd.read_csv(full_filename)
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, filename, user_prefix=""):
    full_filename = f"{user_prefix}_{filename}" if user_prefix else filename
    df.to_csv(full_filename, index=False)

# ---------- Login/Registration UI ----------
def show_login():
    st.markdown("# 🚗 Car Booking & Tracking System")
    st.markdown("### Please login to continue")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                is_valid, full_name = authenticate(username, password)
                if is_valid:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.full_name = full_name
                    st.success(f"Welcome back, {full_name}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            
            if st.form_submit_button("Register"):
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif not all([new_username, new_password, full_name]):
                    st.error("Please fill all fields")
                else:
                    success, message = register_user(new_username, new_password, full_name)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

# ---------- Main App ----------
def main_app():
    # Initialize user-specific data
    user_prefix = st.session_state.username
    
    if 'data_loaded' not in st.session_state or st.session_state.get('current_user') != user_prefix:
        st.session_state.cars = load_data("cars.csv", ["id", "car_name", "plate_number", "model", "status", "last_service_date", "next_service_date"], user_prefix)
        st.session_state.bookings = load_data("bookings.csv", ["id", "car_id", "client_name", "start_date", "end_date", "amount_paid", "status"], user_prefix)
        st.session_state.expenses = load_data("expenses.csv", ["id", "car_id", "date", "description", "amount", "type"], user_prefix)
        st.session_state.data_loaded = True
        st.session_state.current_user = user_prefix

    cars = st.session_state.cars
    bookings = st.session_state.bookings
    expenses = st.session_state.expenses

    # ---------- Sidebar ----------
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.full_name}! 👋")
        if st.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        menu = st.radio("Navigation", ["📊 Dashboard", "🚗 Cars", "📅 Bookings", "💰 Expenses", "🔧 Maintenance"])

    # ---------- Enhanced Dashboard ----------
    if menu == "📊 Dashboard":
        st.markdown("# 📊 Business Dashboard")
        
        # Key Metrics
        total_income = 0
        total_expenses = 0
        
        if not bookings.empty and "amount_paid" in bookings.columns:
            total_income = pd.to_numeric(bookings["amount_paid"], errors='coerce').fillna(0).sum()
        
        if not expenses.empty and "amount" in expenses.columns:
            total_expenses = pd.to_numeric(expenses["amount"], errors='coerce').fillna(0).sum()
        
        profit = total_income - total_expenses
        
        # Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 Total Income", f"UGX {total_income:,.0f}")
        with col2:
            st.metric("🧾 Total Expenses", f"UGX {total_expenses:,.0f}")
        with col3:
            st.metric("📊 Net Profit", f"UGX {profit:,.0f}", delta=f"{((profit/total_income)*100) if total_income > 0 else 0:.1f}%")
        with col4:
            st.metric("🚗 Total Cars", len(cars))

        # Charts Row
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Monthly Income Trend")
            if not bookings.empty:
                bookings_copy = bookings.copy()
                bookings_copy['start_date'] = pd.to_datetime(bookings_copy['start_date'])
                bookings_copy['month'] = bookings_copy['start_date'].dt.to_period('M').astype(str)
                monthly_income = bookings_copy.groupby('month')['amount_paid'].sum().reset_index()
                
                fig = px.line(monthly_income, x='month', y='amount_paid', 
                             title="Monthly Income", markers=True)
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No booking data available")

        with col2:
            st.markdown("### 🥧 Expense Breakdown")
            if not expenses.empty:
                expense_by_type = expenses.groupby('type')['amount'].sum().reset_index()
                fig = px.pie(expense_by_type, values='amount', names='type', 
                           title="Expenses by Type")
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expense data available")

        # Status Overview
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🚗 Car Status Overview")
            if not cars.empty:
                status_counts = cars['status'].value_counts()
                fig = px.bar(x=status_counts.index, y=status_counts.values, 
                           title="Cars by Status", color=status_counts.index)
                fig.update_layout(height=300)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No cars registered")

        with col2:
            st.markdown("### 📋 Recent Activity")
            if not bookings.empty:
                recent_bookings = bookings.tail(5)[['client_name', 'start_date', 'amount_paid']]
                st.dataframe(recent_bookings, use_container_width=True)
            else:
                st.info("No recent bookings")

    # ---------- Cars Section ----------
    elif menu == "🚗 Cars":
        st.markdown("# 🚗 Car Management")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if not cars.empty:
                st.dataframe(cars, use_container_width=True)
            else:
                st.info("No cars registered yet.")
        
        with col2:
            st.markdown("### Quick Stats")
            if not cars.empty:
                available_cars = len(cars[cars['status'] == 'Available'])
                booked_cars = len(cars[cars['status'] == 'Booked'])
                st.metric("Available", available_cars)
                st.metric("Booked", booked_cars)

        with st.form("add_car"):
            st.markdown("#### ➕ Add New Car")
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input("Car Name")
            with col2:
                plate = st.text_input("Plate Number")
            with col3:
                model = st.text_input("Model")
            
            if st.form_submit_button("Add Car"):
                if name and plate and model:
                    new_car = {
                        "id": len(cars)+1, "car_name": name, "plate_number": plate, "model": model,
                        "status": "Available", "last_service_date": dt.date.today().strftime("%Y-%m-%d"), "next_service_date": ""
                    }
                    st.session_state.cars = pd.concat([cars, pd.DataFrame([new_car])], ignore_index=True)
                    save_data(st.session_state.cars, "cars.csv", user_prefix)
                    st.success("Car added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields.")

    # ---------- Bookings Section ----------
    elif menu == "📅 Bookings":
        st.markdown("# 📅 Booking Management")
        
        if cars.empty:
            st.warning("Please add cars first before creating bookings.")
        else:
            if not bookings.empty:
                st.markdown("### Current Bookings")
                st.dataframe(bookings, use_container_width=True)
            
            with st.form("add_booking"):
                st.markdown("#### ➕ New Booking")
                available_cars = cars[cars["status"] == "Available"]
                
                if available_cars.empty:
                    st.warning("No available cars for booking.")
                    car_id = None
                else:
                    car_display = available_cars.apply(lambda x: f"{x['car_name']} ({x['plate_number']})", axis=1)
                    selected_idx = st.selectbox("Select Car", range(len(available_cars)), 
                                               format_func=lambda x: car_display.iloc[x])
                    car_id = available_cars.iloc[selected_idx]["id"] if selected_idx is not None else None
                
                col1, col2 = st.columns(2)
                with col1:
                    client = st.text_input("Client Name")
                    start = st.date_input("Start Date")
                with col2:
                    amount = st.number_input("Amount Paid (UGX)", min_value=0)
                    end = st.date_input("End Date")
                
                if st.form_submit_button("Add Booking"):
                    if car_id and client and start and end and amount > 0:
                        new_booking = {
                            "id": len(bookings)+1, "car_id": car_id, "client_name": client,
                            "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d"), 
                            "amount_paid": amount, "status": "Booked"
                        }
                        st.session_state.bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                        st.session_state.cars.loc[st.session_state.cars["id"] == car_id, "status"] = "Booked"
                        save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                        save_data(st.session_state.cars, "cars.csv", user_prefix)
                        st.success("Booking added successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in all fields correctly.")

    # ---------- Expenses Section ----------
    elif menu == "💰 Expenses":
        st.markdown("# 💰 Expense Management")
        
        if cars.empty:
            st.warning("Please add cars first before recording expenses.")
        else:
            if not expenses.empty:
                st.markdown("### Expense History")
                st.dataframe(expenses, use_container_width=True)
            
            with st.form("add_expense"):
                st.markdown("#### ➕ Record Expense")
                car_display = cars.apply(lambda x: f"{x['car_name']} ({x['plate_number']})", axis=1)
                selected_idx = st.selectbox("Select Car", range(len(cars)), 
                                           format_func=lambda x: car_display.iloc[x])
                car_id = cars.iloc[selected_idx]["id"] if selected_idx is not None else None
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    desc = st.text_input("Description")
                with col2:
                    amt = st.number_input("Amount (UGX)", min_value=0)
                with col3:
                    etype = st.selectbox("Type", ["Fuel", "Maintenance", "Insurance", "Repairs", "Other"])
                
                if st.form_submit_button("Add Expense"):
                    if car_id and desc and amt > 0:
                        new_exp = {
                            "id": len(expenses)+1, "car_id": car_id, "date": dt.date.today().strftime("%Y-%m-%d"), 
                            "description": desc, "amount": amt, "type": etype
                        }
                        st.session_state.expenses = pd.concat([expenses, pd.DataFrame([new_exp])], ignore_index=True)
                        save_data(st.session_state.expenses, "expenses.csv", user_prefix)
                        st.success("Expense recorded successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in all fields correctly.")

    # ---------- Maintenance Section ----------
    elif menu == "🔧 Maintenance":
        st.markdown("# 🔧 Maintenance Schedule")
        if not cars.empty:
            maintenance_data = cars[["car_name", "last_service_date", "next_service_date", "status"]]
            st.dataframe(maintenance_data, use_container_width=True)
        else:
            st.info("No cars registered yet.")

# ---------- App Entry Point ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    main_app()
else:
    show_login()
