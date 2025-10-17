# car_tracker.py
import streamlit as st
import pandas as pd
import datetime as dt
import os
import hashlib
import plotly.express as px
import plotly.graph_objects as go

# ---------- Dark Theme Configuration ----------
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }
    .stSidebar {
        background-color: #262730;
    }
    .stMetric {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #464646;
    }
    .stDataFrame {
        background-color: #262730;
    }
    </style>
    """, unsafe_allow_html=True)

st.set_page_config(page_title="🚗 Car Booking & Tracking", layout="wide")
apply_dark_theme()

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

# ---------- Data Management Functions ----------
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

def update_car_status(car_id, new_status, user_prefix):
    """Update car status without affecting other data"""
    cars = st.session_state.cars.copy()
    cars.loc[cars["id"] == car_id, "status"] = new_status
    st.session_state.cars = cars
    save_data(cars, "cars.csv", user_prefix)

def complete_booking(booking_id, user_prefix):
    """Mark booking as completed and make car available"""
    bookings = st.session_state.bookings.copy()
    booking_row = bookings[bookings["id"] == booking_id]
    if not booking_row.empty:
        car_id = booking_row.iloc[0]["car_id"]
        bookings.loc[bookings["id"] == booking_id, "status"] = "Completed"
        st.session_state.bookings = bookings
        save_data(bookings, "bookings.csv", user_prefix)
        update_car_status(car_id, "Available", user_prefix)
        return True
    return False

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

# ---------- Main App with Enhanced Features ----------
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

    # ---------- Enhanced Sidebar ----------
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.full_name}! 👋")
        
        if st.button("🚪 Logout"):
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

        # Status Overview with Quick Actions
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
            st.markdown("### ⚡ Quick Actions")
            active_bookings = bookings[bookings['status'] == 'Booked'] if not bookings.empty else pd.DataFrame()
            
            if not active_bookings.empty:
                st.markdown("**Complete Bookings:**")
                for _, booking in active_bookings.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"📅 {booking['client_name']} - {booking['start_date']}")
                    with col_b:
                        if st.button("✅", key=f"complete_{booking['id']}", help="Complete booking"):
                            if complete_booking(booking['id'], user_prefix):
                                st.success("Booking completed!")
                                st.rerun()
            else:
                st.info("No active bookings")

    # ---------- Enhanced Cars Section ----------
    elif menu == "🚗 Cars":
        st.markdown("# 🚗 Car Management")
        
        # Edit Mode Toggle
        edit_mode = st.toggle("✏️ Edit Mode", key="car_edit_mode")
        
        if not cars.empty:
            if edit_mode:
                st.markdown("### Edit Car Details")
                selected_car_id = st.selectbox("Select Car to Edit", 
                                             cars['id'].values,
                                             format_func=lambda x: f"{cars[cars['id']==x].iloc[0]['car_name']} ({cars[cars['id']==x].iloc[0]['plate_number']})")
                
                if selected_car_id:
                    car_data = cars[cars['id'] == selected_car_id].iloc[0]
                    
                    with st.form("edit_car"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            new_name = st.text_input("Car Name", value=car_data['car_name'])
                        with col2:
                            new_plate = st.text_input("Plate Number", value=car_data['plate_number'])
                        with col3:
                            new_model = st.text_input("Model", value=car_data['model'])
                        
                        new_status = st.selectbox("Status", ["Available", "Booked", "Maintenance"], 
                                                index=["Available", "Booked", "Maintenance"].index(car_data['status']))
                        
                        if st.form_submit_button("💾 Update Car"):
                            if new_name and new_plate and new_model:
                                st.session_state.cars.loc[st.session_state.cars['id'] == selected_car_id, 'car_name'] = new_name
                                st.session_state.cars.loc[st.session_state.cars['id'] == selected_car_id, 'plate_number'] = new_plate
                                st.session_state.cars.loc[st.session_state.cars['id'] == selected_car_id, 'model'] = new_model
                                st.session_state.cars.loc[st.session_state.cars['id'] == selected_car_id, 'status'] = new_status
                                save_data(st.session_state.cars, "cars.csv", user_prefix)
                                st.success("Car updated successfully!")
                                st.rerun()
            
            st.markdown("### Current Fleet")
            st.dataframe(cars, use_container_width=True)
        else:
            st.info("No cars registered yet.")

        # Add new car form (unchanged)
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

    # ---------- Enhanced Bookings Section ----------
    elif menu == "📅 Bookings":
        st.markdown("# 📅 Booking Management")
        
        if cars.empty:
            st.warning("Please add cars first before creating bookings.")
        else:
            # Edit Mode Toggle
            edit_mode = st.toggle("✏️ Edit Mode", key="booking_edit_mode")
            
            if not bookings.empty:
                if edit_mode:
                    st.markdown("### Edit Booking")
                    selected_booking_id = st.selectbox("Select Booking to Edit", 
                                                     bookings['id'].values,
                                                     format_func=lambda x: f"{bookings[bookings['id']==x].iloc[0]['client_name']} - {bookings[bookings['id']==x].iloc[0]['start_date']}")
                    
                    if selected_booking_id:
                        booking_data = bookings[bookings['id'] == selected_booking_id].iloc[0]
                        
                        with st.form("edit_booking"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_client = st.text_input("Client Name", value=booking_data['client_name'])
                                new_amount = st.number_input("Amount", value=float(booking_data['amount_paid']))
                            with col2:
                                new_status = st.selectbox("Status", ["Booked", "Completed", "Cancelled"], 
                                                        index=["Booked", "Completed", "Cancelled"].index(booking_data['status']))
                            
                            if st.form_submit_button("💾 Update Booking"):
                                if new_client and new_amount > 0:
                                    st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'client_name'] = new_client
                                    st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'amount_paid'] = new_amount
                                    st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'status'] = new_status
                                    save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                                    st.success("Booking updated successfully!")
                                    st.rerun()
                
                st.markdown("### Current Bookings")
                st.dataframe(bookings, use_container_width=True)
            
            # Add new booking form (unchanged from previous version)
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
                        update_car_status(car_id, "Booked", user_prefix)
                        save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                        st.success("Booking added successfully!")
                        st.rerun()
                    else:
                        st.error("Please fill in all fields correctly.")

    # ---------- Enhanced Expenses Section ----------
    elif menu == "💰 Expenses":
        st.markdown("# 💰 Expense Management")
        
        if cars.empty:
            st.warning("Please add cars first before recording expenses.")
        else:
            # Edit Mode Toggle
            edit_mode = st.toggle("✏️ Edit Mode", key="expense_edit_mode")
            
            if not expenses.empty:
                if edit_mode:
                    st.markdown("### Edit Expense")
                    selected_expense_id = st.selectbox("Select Expense to Edit", 
                                                     expenses['id'].values,
                                                     format_func=lambda x: f"{expenses[expenses['id']==x].iloc[0]['description']} - UGX {expenses[expenses['id']==x].iloc[0]['amount']}")
                    
                    if selected_expense_id:
                        expense_data = expenses[expenses['id'] == selected_expense_id].iloc[0]
                        
                        with st.form("edit_expense"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                new_desc = st.text_input("Description", value=expense_data['description'])
                            with col2:
                                new_amount = st.number_input("Amount", value=float(expense_data['amount']))
                            with col3:
                                new_type = st.selectbox("Type", ["Fuel", "Maintenance", "Insurance", "Repairs", "Other"],
                                                       index=["Fuel", "Maintenance", "Insurance", "Repairs", "Other"].index(expense_data['type']))
                            
                            if st.form_submit_button("💾 Update Expense"):
                                if new_desc and new_amount > 0:
                                    st.session_state.expenses.loc[st.session_state.expenses['id'] == selected_expense_id, 'description'] = new_desc
                                    st.session_state.expenses.loc[st.session_state.expenses['id'] == selected_expense_id, 'amount'] = new_amount
                                    st.session_state.expenses.loc[st.session_state.expenses['id'] == selected_expense_id, 'type'] = new_type
                                    save_data(st.session_state.expenses, "expenses.csv", user_prefix)
                                    st.success("Expense updated successfully!")
                                    st.rerun()
                
                st.markdown("### Expense History")
                st.dataframe(expenses, use_container_width=True)
            
            # Add new expense form (unchanged from previous version)
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

    # ---------- Maintenance Section (unchanged) ----------
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
