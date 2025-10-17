# car_tracker.py
import streamlit as st
import pandas as pd
import datetime as dt
import os
import hashlib
import plotly.express as px
import plotly.graph_objects as go
import json

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

# ---------- Persistent Storage Functions ----------
def init_persistent_storage():
    """Initialize persistent data storage across sessions"""
    if 'persistent_data' not in st.session_state:
        st.session_state.persistent_data = {
            'users': {},
            'cars': {},
            'bookings': {},
            'expenses': {},
            'pending_bookings': {}  # Add pending_bookings to initial storage
        }

def save_to_persistent_storage(data_type, user_id, data):
    """Save data to persistent storage"""
    if 'persistent_data' not in st.session_state:
        init_persistent_storage()
    
    # Ensure the data_type key exists
    if data_type not in st.session_state.persistent_data:
        st.session_state.persistent_data[data_type] = {}
    
    key = f"{user_id}_{data_type}" if user_id else data_type
    
    if hasattr(data, 'to_dict'):
        st.session_state.persistent_data[data_type][key] = data.to_dict('records')
    elif isinstance(data, dict):
        st.session_state.persistent_data[data_type][key] = [data]
    else:
        st.session_state.persistent_data[data_type][key] = data

def load_from_persistent_storage(data_type, user_id, columns):
    """Load data from persistent storage"""
    if 'persistent_data' not in st.session_state:
        init_persistent_storage()
    
    key = f"{user_id}_{data_type}" if user_id else data_type
    
    if key in st.session_state.persistent_data.get(data_type, {}):
        data = st.session_state.persistent_data[data_type][key]
        if isinstance(data, list) and data:
            return pd.DataFrame(data)
    
    return pd.DataFrame(columns=columns)

# Initialize persistent storage on app start
init_persistent_storage()

# ---------- Authentication Functions ----------
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_users():
    # First try persistent storage
    users_df = load_from_persistent_storage('users', None, ["username", "password", "full_name", "created_date"])
    
    if not users_df.empty:
        return users_df
    
    # Fall back to CSV file
    if os.path.exists("users.csv"):
        users_df = pd.read_csv("users.csv")
        # Save to persistent storage
        save_to_persistent_storage('users', None, users_df)
        return users_df
    else:
        # Create default admin user
        default_user = pd.DataFrame({
            "username": ["admin"], 
            "password": [hash_password("admin123")], 
            "full_name": ["System Administrator"],
            "created_date": [dt.date.today().strftime("%Y-%m-%d")]
        })
        save_to_persistent_storage('users', None, default_user)
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
    save_to_persistent_storage('users', None, users)
    users.to_csv("users.csv", index=False)
    return True, "User registered successfully"

# ---------- Enhanced Data Management Functions ----------
def load_data(filename, columns, user_prefix=""):
    """Load data with persistent storage priority"""
    data_type = filename.replace('.csv', '')
    
    # First try persistent storage
    df = load_from_persistent_storage(data_type, user_prefix, columns)
    if not df.empty:
        return df
    
    # Fall back to CSV file
    full_filename = f"{user_prefix}_{filename}" if user_prefix else filename
    if os.path.exists(full_filename):
        try:
            df = pd.read_csv(full_filename)
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            # Save to persistent storage for next time
            save_to_persistent_storage(data_type, user_prefix, df)
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

def save_data(df, filename, user_prefix=""):
    """Save data to both persistent storage and CSV"""
    data_type = filename.replace('.csv', '')
    
    # Save to persistent storage (primary)
    save_to_persistent_storage(data_type, user_prefix, df)
    
    # Also save to CSV file for backup
    full_filename = f"{user_prefix}_{filename}" if user_prefix else filename
    try:
        df.to_csv(full_filename, index=False)
    except Exception:
        pass  # Don't fail if CSV write fails

def update_car_status(car_id, new_status, user_prefix):
    """Update car status without affecting other data"""
    cars = st.session_state.cars.copy()
    cars.loc[cars["id"] == car_id, "status"] = new_status
    st.session_state.cars = cars
    save_data(cars, "cars.csv", user_prefix)

def check_date_overlap(car_id, start_date, end_date, exclude_booking_id=None):
    """Check if booking dates overlap with existing bookings for the same car"""
    bookings = st.session_state.bookings
    car_bookings = bookings[bookings["car_id"] == car_id]
    
    # Exclude current booking if editing
    if exclude_booking_id:
        car_bookings = car_bookings[car_bookings["id"] != exclude_booking_id]
    
    # Only check active bookings (not completed or cancelled)
    active_bookings = car_bookings[car_bookings["status"] == "Booked"]
    
    if active_bookings.empty:
        return False, []
    
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    
    overlapping_bookings = []
    
    for _, booking in active_bookings.iterrows():
        booking_start = pd.to_datetime(booking['start_date'])
        booking_end = pd.to_datetime(booking['end_date'])
        
        # Check for overlap
        if (start_date <= booking_end) and (end_date >= booking_start):
            overlapping_bookings.append({
                'client': booking['client_name'],
                'start': booking['start_date'],
                'end': booking['end_date']
            })
    
    return len(overlapping_bookings) > 0, overlapping_bookings

def get_car_availability_status(car_id):
    """Get detailed availability status for a car"""
    bookings = st.session_state.bookings
    car_bookings = bookings[(bookings["car_id"] == car_id) & (bookings["status"] == "Booked")]
    
    if car_bookings.empty:
        return "Available", []
    
    current_date = pd.to_datetime(dt.date.today())
    active_bookings = []
    
    for _, booking in car_bookings.iterrows():
        booking_start = pd.to_datetime(booking['start_date'])
        booking_end = pd.to_datetime(booking['end_date'])
        
        if booking_end >= current_date:  # Future or ongoing bookings
            active_bookings.append({
                'client': booking['client_name'],
                'start': booking['start_date'],
                'end': booking['end_date']
            })
    
    if active_bookings:
        return "Partially Booked", active_bookings
    else:
        return "Available", []

def complete_booking(booking_id, user_prefix):
    """Mark booking as completed and update car status if no other active bookings"""
    bookings = st.session_state.bookings.copy()
    booking_row = bookings[bookings["id"] == booking_id]
    if not booking_row.empty:
        car_id = booking_row.iloc[0]["car_id"]
        bookings.loc[bookings["id"] == booking_id, "status"] = "Completed"
        st.session_state.bookings = bookings
        save_data(bookings, "bookings.csv", user_prefix)
        
        # Check if car has other active bookings
        other_active_bookings = bookings[
            (bookings["car_id"] == car_id) & 
            (bookings["status"] == "Booked") & 
            (bookings["id"] != booking_id)
        ]
        
        if other_active_bookings.empty:
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

# ---------- Main App with Enhanced Data Persistence ----------
def main_app():
    # Initialize user-specific data with persistent storage priority
    user_prefix = st.session_state.username
    
    # Always reload data to ensure persistence works
    if 'current_user' not in st.session_state or st.session_state.get('current_user') != user_prefix:
        # Clear any cached data first
        st.cache_data.clear()
        
        # Load user-specific data
        st.session_state.cars = load_data("cars.csv", ["id", "car_name", "plate_number", "model", "status", "last_service_date", "next_service_date"], user_prefix)
        st.session_state.bookings = load_data("bookings.csv", ["id", "car_id", "client_name", "start_date", "end_date", "amount_paid", "status"], user_prefix)
        st.session_state.expenses = load_data("expenses.csv", ["id", "car_id", "date", "description", "amount", "type"], user_prefix)
        st.session_state.current_user = user_prefix

    cars = st.session_state.cars
    bookings = st.session_state.bookings
    expenses = st.session_state.expenses

    # Load pending bookings FIRST - before sidebar
    pending_bookings = load_pending_bookings()
    user_pending = [b for b in pending_bookings if b.get('owner') == user_prefix and b.get('status') == 'Pending']

    # ---------- Enhanced Sidebar ----------
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.full_name}! 👋")
        
        # ALWAYS show notification area (even if empty) to test
        st.markdown("---")
        st.markdown("### 🔔 Notifications")
        
        # Debug: Always show this first
        st.write(f"Debug: Found {len(pending_bookings)} total pending bookings")
        st.write(f"Debug: Found {len(user_pending)} for user '{user_prefix}'")
        
        # Notification icon for pending bookings - ENHANCED
        if user_pending:
            st.markdown(f"""
            <div style="
                background: linear-gradient(90deg, #ff6b6b, #ee5a52);
                color: white;
                padding: 15px 15px;
                border-radius: 12px;
                margin: 15px 0;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
                box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
                animation: pulse-notification 2s infinite;
                border: 2px solid rgba(255, 255, 255, 0.3);
            ">
                🔔 {len(user_pending)} NEW BOOKING REQUEST{"S" if len(user_pending) > 1 else ""}!
            </div>
            <style>
            @keyframes pulse-notification {{
                0% {{ 
                    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
                    transform: scale(1);
                }}
                50% {{ 
                    box-shadow: 0 6px 25px rgba(255, 107, 107, 0.7);
                    transform: scale(1.02);
                }}
                100% {{ 
                    box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
                    transform: scale(1);
                }}
            }}
            </style>
            """, unsafe_allow_html=True)
            
            # Make the button more prominent
            if st.button("🚨 VIEW URGENT REQUESTS 🚨", key="notification_btn", use_container_width=True, type="primary"):
                # Force navigation to Dashboard
                st.session_state.force_dashboard = True
                st.rerun()
                
            # Show preview of requests
            st.markdown("**Quick Preview:**")
            for i, booking in enumerate(user_pending[:2]):  # Show first 2
                st.markdown(f"• **{booking['client_name']}** - {booking.get('car_name', 'Unknown Car')}")
                st.caption(f"📅 {booking['start_date']} to {booking['end_date']}")
            
            if len(user_pending) > 2:
                st.caption(f"... and {len(user_pending) - 2} more requests")
        else:
            # Show when no notifications
            st.info("🔕 No pending requests")
            if pending_bookings:
                st.caption(f"({len(pending_bookings)} total system requests)")
        
        # Show data summary with pending bookings
        st.markdown("---")
        st.markdown("### 📈 Your Data Summary")
        st.write(f"🚗 Cars: {len(cars)}")
        st.write(f"📅 Bookings: {len(bookings)}")
        st.write(f"💰 Expenses: {len(expenses)}")
        if user_pending:
            st.write(f"🔥 **URGENT: {len(user_pending)} Pending Requests**")
        
        # Enhanced Public booking link section
        st.markdown("---")
        st.markdown("### 🌐 Your Booking Link")
        
        # Generate user-specific booking URL
        base_url = "https://motoka.streamlit.app"  # Replace with your actual URL
        user_booking_url = f"{base_url}/?page=booking&owner={user_prefix}"
        
        st.code(user_booking_url, language="text")
        st.caption("🔗 Share this unique link with your customers")
        
        # Copy button simulation
        if st.button("📋 Copy Link"):
            st.success("✅ Link copied! Share it with your customers.")
            st.balloons()
        
        # QR Code suggestion
        st.markdown("💡 **Tip:** Create a QR code with this URL for easy sharing!")
        
        # ---------- Test Button to Create Fake Booking ----------
        st.markdown("---")
        st.markdown("### 🧪 Testing")
        if st.button("🧪 Create Test Booking", help="Create a fake booking for testing"):
            test_booking = {
                'owner': user_prefix,
                'car_id': 1,
                'car_name': 'Test Car',
                'car_model': 'Test Model',
                'plate_number': 'TEST123',
                'client_name': 'Test Customer',
                'client_phone': '+256700000000',
                'client_email': 'test@example.com',
                'start_date': '2024-01-15',
                'end_date': '2024-01-20',
                'purpose': 'Testing',
                'additional_notes': 'This is a test booking'
            }
            save_public_booking(test_booking)
            st.success("Test booking created!")
            st.rerun()
        
        # ---------- Logout ----------
        if st.button("🚪 Logout"):
            # Clear user session but keep persistent data
            keys_to_remove = ['logged_in', 'username', 'full_name', 'current_user', 'cars', 'bookings', 'expenses']
            for key in keys_to_remove:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        st.markdown("---")
        
        # Force dashboard selection if notification clicked
        if st.session_state.get('force_dashboard', False):
            menu = "📊 Dashboard"
            st.session_state.force_dashboard = False
        else:
            menu = st.radio("Navigation", ["📊 Dashboard", "🚗 Cars", "📅 Bookings", "💰 Expenses", "🔧 Maintenance"])
        
        # Add notification badge to Dashboard option - ENHANCED
        if user_pending:
            st.markdown(f"""
            <div style="
                background: linear-gradient(45deg, #ff6b6b, #ff4757);
                color: white;
                border-radius: 50%;
                width: 25px;
                height: 25px;
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                line-height: 25px;
                position: fixed;
                margin-top: -45px;
                margin-left: 130px;
                z-index: 9999;
                box-shadow: 0 2px 10px rgba(255, 107, 107, 0.5);
                animation: bounce-badge 1s infinite;
            ">
                {len(user_pending)}
            </div>
            <style>
            @keyframes bounce-badge {{
                0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                40% {{ transform: translateY(-5px); }}
                60% {{ transform: translateY(-2px); }}
            }}
            </style>
            """, unsafe_allow_html=True)
        
        # Add data management section
        show_data_management_section()

    # ---------- Enhanced Dashboard ----------
    if menu == "📊 Dashboard":
        st.markdown("# 📊 Business Dashboard")
        
        # Load pending bookings for current user
        pending_bookings = load_pending_bookings()
        user_pending = [b for b in pending_bookings if b.get('owner') == user_prefix and b.get('status') == 'Pending']
        
        # Debug info (remove in production)
        if st.sidebar.checkbox("🔍 Debug Info"):
            st.sidebar.write(f"Total pending bookings: {len(pending_bookings)}")
            st.sidebar.write(f"User pending bookings: {len(user_pending)}")
            st.sidebar.write(f"Current user: {user_prefix}")
            if pending_bookings:
                st.sidebar.write("Sample booking owners:", [b.get('owner', 'No owner') for b in pending_bookings[:3]])
                st.sidebar.write("All pending bookings:", pending_bookings)
        
        # Prominent pending bookings notification at top
        if user_pending:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                color: white;
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
                text-align: center;
                font-size: 18px;
                font-weight: bold;
                box-shadow: 0 4px 20px rgba(255, 107, 107, 0.3);
                border-left: 5px solid #fff;
            ">
                🔔 URGENT: You have {len(user_pending)} pending booking request{"s" if len(user_pending) > 1 else ""} waiting for your attention!
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("📋 Pending Booking Requests", expanded=True):
                for booking in user_pending:
                    # Add visual emphasis for each pending booking
                    st.markdown(f"""
                    <div style="
                        background: rgba(255, 107, 107, 0.1);
                        padding: 15px;
                        border-radius: 10px;
                        margin: 10px 0;
                        border-left: 4px solid #ff6b6b;
                    ">
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.write(f"**{booking['client_name']}** - {booking.get('car_name', 'Unknown Car')}")
                        st.write(f"📅 {booking['start_date']} to {booking['end_date']}")
                        st.write(f"📞 {booking['client_phone']}")
                        if booking.get('client_email'):
                            st.write(f"📧 {booking['client_email']}")
                        if booking.get('purpose'):
                            st.write(f"📝 Purpose: {booking['purpose']}")
                        
                        # Show time since submission
                        try:
                            submission_time = pd.to_datetime(booking.get('submission_date', ''))
                            time_diff = dt.datetime.now() - submission_time
                            hours_ago = int(time_diff.total_seconds() / 3600)
                            if hours_ago < 1:
                                minutes_ago = int(time_diff.total_seconds() / 60)
                                st.caption(f"⏰ Submitted {minutes_ago} minutes ago")
                            else:
                                st.caption(f"⏰ Submitted {hours_ago} hours ago")
                        except:
                            st.caption("⏰ Recently submitted")
                    
                    with col2:
                        if st.button("✅ Approve", key=f"approve_{booking['id']}"):
                            # Create confirmed booking
                            new_booking_id = 1 if bookings.empty else int(bookings['id'].max()) + 1
                            new_booking = {
                                "id": new_booking_id,
                                "car_id": booking['car_id'],
                                "client_name": booking['client_name'],
                                "start_date": booking['start_date'],
                                "end_date": booking['end_date'],
                                "amount_paid": 0,  # Can be updated later
                                "status": "Confirmed"
                            }
                            
                            # Add to bookings
                            st.session_state.bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                            
                            # Update car status
                            update_car_status(booking['car_id'], "Booked", user_prefix)
                            
                            # Save bookings
                            save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                            
                            # Update pending booking status
                            for i, pb in enumerate(st.session_state.pending_bookings):
                                if pb['id'] == booking['id']:
                                    st.session_state.pending_bookings[i]['status'] = 'Approved'
                            
                            # Save updated pending bookings
                            st.session_state.persistent_data['pending_bookings']['pending_bookings'] = st.session_state.pending_bookings
                            
                            st.success("✅ Booking approved and added to your system!")
                            st.rerun()
                    
                    with col3:
                        if st.button("✏️ Edit", key=f"edit_{booking['id']}"):
                            st.session_state[f"edit_booking_{booking['id']}"] = True
                            st.rerun()
                    
                    with col4:
                        if st.button("❌ Reject", key=f"reject_{booking['id']}"):
                            # Update pending booking status
                            for i, pb in enumerate(st.session_state.pending_bookings):
                                if pb['id'] == booking['id']:
                                    st.session_state.pending_bookings[i]['status'] = 'Rejected'
                            
                            # Save updated pending bookings
                            st.session_state.persistent_data['pending_bookings']['pending_bookings'] = st.session_state.pending_bookings
                            
                            st.success("❌ Booking rejected!")
                            st.rerun()
                    
                    # Edit form for pending booking
                    if st.session_state.get(f"edit_booking_{booking['id']}", False):
                        with st.form(f"edit_pending_{booking['id']}"):
                            st.markdown("##### Edit Booking Request")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                new_client_name = st.text_input("Client Name", value=booking['client_name'])
                                new_start = st.date_input("Start Date", value=pd.to_datetime(booking['start_date']).date())
                                estimated_amount = st.number_input("Estimated Amount (UGX)", min_value=0)
                            with col_b:
                                new_phone = st.text_input("Phone", value=booking['client_phone'])
                                new_end = st.date_input("End Date", value=pd.to_datetime(booking['end_date']).date())
                            
                            col_x, col_y = st.columns(2)
                            with col_x:
                                if st.form_submit_button("💾 Save & Approve"):
                                    # Create booking with edited details
                                    new_booking_id = 1 if bookings.empty else int(bookings['id'].max()) + 1
                                    new_booking = {
                                        "id": new_booking_id,
                                        "car_id": booking['car_id'],
                                        "client_name": new_client_name,
                                        "start_date": new_start.strftime('%Y-%m-%d'),
                                        "end_date": new_end.strftime('%Y-%m-%d'),
                                        "amount_paid": estimated_amount,
                                        "status": "Confirmed"
                                    }
                                    
                                    # Add to bookings
                                    st.session_state.bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                                    
                                    # Update car status and save
                                    update_car_status(booking['car_id'], "Booked", user_prefix)
                                    save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                                    
                                    # Update pending booking
                                    for i, pb in enumerate(st.session_state.pending_bookings):
                                        if pb['id'] == booking['id']:
                                            st.session_state.pending_bookings[i]['status'] = 'Approved'
                                    
                                    # Save updated pending bookings
                                    st.session_state.persistent_data['pending_bookings']['pending_bookings'] = st.session_state.pending_bookings
                                    
                                    del st.session_state[f"edit_booking_{booking['id']}"]
                                    st.success("✅ Booking edited and approved!")
                                    st.rerun()
                            
                            with col_y:
                                if st.form_submit_button("❌ Cancel Edit"):
                                    del st.session_state[f"edit_booking_{booking['id']}"]
                                    st.rerun()
                    
                    st.divider()

        # Key Metrics Section - Always show regardless of pending bookings
        st.markdown("---")
        
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
        
        # Show message about pending bookings if none exist
        if not user_pending:
            if len(pending_bookings) > 0:
                st.info(f"ℹ️ No pending booking requests for you. Total system bookings: {len(pending_bookings)}")
            else:
                st.info("ℹ️ No pending booking requests. Share your booking link to receive requests!")

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
                                st.success("✅ Car updated and saved!")
                                st.rerun()
            
            st.markdown("### Current Fleet")
            st.dataframe(cars, use_container_width=True)
        else:
            st.info("No cars registered yet. Add your first car below!")

        # Add new car form with enhanced feedback
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
                    # Generate proper ID
                    new_id = 1 if cars.empty else int(cars['id'].max()) + 1
                    
                    new_car = {
                        "id": new_id, 
                        "car_name": name, 
                        "plate_number": plate, 
                        "model": model,
                        "status": "Available", 
                        "last_service_date": dt.date.today().strftime("%Y-%m-%d"), 
                        "next_service_date": ""
                    }
                    
                    # Update session state
                    st.session_state.cars = pd.concat([cars, pd.DataFrame([new_car])], ignore_index=True)
                    
                    # Save to persistent storage
                    save_data(st.session_state.cars, "cars.csv", user_prefix)
                    
                    st.success(f"✅ Car '{name}' added successfully and saved to your account!")
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
                                new_start = st.date_input("Start Date", value=pd.to_datetime(booking_data['start_date']).date())
                                new_amount = st.number_input("Amount", value=float(booking_data['amount_paid']))
                            with col2:
                                new_end = st.date_input("End Date", value=pd.to_datetime(booking_data['end_date']).date())
                                new_status = st.selectbox("Status", ["Booked", "Completed", "Cancelled"], 
                                                        index=["Booked", "Completed", "Cancelled"].index(booking_data['status']))
                            
                            # Check for date conflicts when editing
                            if new_start and new_end:
                                has_conflict, conflicts = check_date_overlap(booking_data['car_id'], new_start, new_end, selected_booking_id)
                                if has_conflict:
                                    st.warning("⚠️ Date conflict detected with existing bookings:")
                                    for conflict in conflicts:
                                        st.write(f"• {conflict['client']} ({conflict['start']} to {conflict['end']})")
                            
                            if st.form_submit_button("💾 Update Booking"):
                                if new_client and new_amount > 0 and new_start and new_end:
                                    # Check conflicts again before saving
                                    has_conflict, conflicts = check_date_overlap(booking_data['car_id'], new_start, new_end, selected_booking_id)
                                    
                                    if has_conflict and new_status == "Booked":
                                        st.error("Cannot update booking due to date conflicts with existing bookings.")
                                    else:
                                        st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'client_name'] = new_client
                                        st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'start_date'] = new_start.strftime("%Y-%m-%d")
                                        st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'end_date'] = new_end.strftime("%Y-%m-%d")
                                        st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'amount_paid'] = new_amount
                                        st.session_state.bookings.loc[st.session_state.bookings['id'] == selected_booking_id, 'status'] = new_status
                                        save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                                        st.success("Booking updated successfully!")
                                        st.rerun()
                                else:
                                    st.error("Please fill in all fields correctly.")
                
                st.markdown("### Current Bookings")
                # Enhanced booking display with status and conflict info
                display_bookings = bookings.copy()
                if not display_bookings.empty:
                    # Add car names to booking display
                    display_bookings = display_bookings.merge(
                        cars[['id', 'car_name']], 
                        left_on='car_id', 
                        right_on='id', 
                        suffixes=('', '_car')
                    ).drop('id_car', axis=1)
                    
                st.dataframe(display_bookings, use_container_width=True)
            
            # Enhanced booking form with availability check
            with st.form("add_booking"):
                st.markdown("#### ➕ New Booking")
                
                # Show all cars, not just available ones
                if cars.empty:
                    st.warning("No cars available for booking.")
                    car_id = None
                else:
                    car_display = cars.apply(lambda x: f"{x['car_name']} ({x['plate_number']})", axis=1)
                    selected_idx = st.selectbox("Select Car", range(len(cars)), 
                                               format_func=lambda x: car_display.iloc[x])
                    car_id = cars.iloc[selected_idx]["id"] if selected_idx is not None else None
                    
                    # Show car availability status
                    if car_id:
                        status, active_bookings = get_car_availability_status(car_id)
                        if status == "Available":
                            st.success("✅ Car is fully available")
                        elif status == "Partially Booked":
                            st.info("ℹ️ Car has existing bookings:")
                            for booking in active_bookings:
                                st.write(f"• {booking['client']} ({booking['start']} to {booking['end']})")
                
                col1, col2 = st.columns(2)
                with col1:
                    client = st.text_input("Client Name")
                    start = st.date_input("Start Date", min_value=dt.date.today())
                with col2:
                    amount = st.number_input("Amount Paid (UGX)", min_value=0)
                    end = st.date_input("End Date", min_value=dt.date.today())
                
                # Real-time conflict checking
                if car_id and start and end and start <= end:
                    has_conflict, conflicts = check_date_overlap(car_id, start, end)
                    if has_conflict:
                        st.warning("⚠️ Date conflict detected with existing bookings:")
                        for conflict in conflicts:
                            st.write(f"• {conflict['client']} ({conflict['start']} to {conflict['end']})")
                        st.info("💡 Consider choosing different dates or proceed if this is intentional (rebooking)")
                
                allow_conflicts = st.checkbox("Allow overlapping bookings (for rebooking)", 
                                            help="Check this to allow booking even when dates overlap with existing bookings")
                
                if st.form_submit_button("Add Booking"):
                    if car_id and client and start and end and amount > 0:
                        # Check for conflicts
                        has_conflict, conflicts = check_date_overlap(car_id, start, end)
                        
                        if has_conflict and not allow_conflicts:
                            st.error("Cannot create booking due to date conflicts. Enable 'Allow overlapping bookings' if this is intentional.")
                        else:
                            new_booking = {
                                "id": len(bookings)+1, "car_id": car_id, "client_name": client,
                                "start_date": start.strftime("%Y-%m-%d"), "end_date": end.strftime("%Y-%m-%d"), 
                                "amount_paid": amount, "status": "Booked"
                            }
                            st.session_state.bookings = pd.concat([bookings, pd.DataFrame([new_booking])], ignore_index=True)
                            
                            # Update car status to "Booked" if not already
                            current_car = cars[cars['id'] == car_id].iloc[0]
                            if current_car['status'] != "Booked":
                                update_car_status(car_id, "Booked", user_prefix)
                            
                            save_data(st.session_state.bookings, "bookings.csv", user_prefix)
                            
                            if has_conflict:
                                st.success("Booking added successfully! ⚠️ Note: This booking overlaps with existing bookings.")
                            else:
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

# ---------- Public Booking Functions ----------
def save_public_booking(booking_data):
    """Save public booking to pending bookings"""
    # Initialize persistent storage if not exists
    if 'persistent_data' not in st.session_state:
        init_persistent_storage()
    
    # Ensure pending_bookings key exists in persistent storage
    if 'pending_bookings' not in st.session_state.persistent_data:
        st.session_state.persistent_data['pending_bookings'] = {}
    
    if 'pending_bookings' not in st.session_state:
        st.session_state.pending_bookings = []
    
    # Generate unique ID based on existing pending bookings
    existing_ids = [pb.get('id', 0) for pb in st.session_state.pending_bookings]
    booking_data['id'] = max(existing_ids) + 1 if existing_ids else 1
    booking_data['submission_date'] = dt.datetime.now().isoformat()
    booking_data['status'] = 'Pending'
    
    st.session_state.pending_bookings.append(booking_data)
    
    # Save to persistent storage - use 'pending_bookings' as key directly
    try:
        st.session_state.persistent_data['pending_bookings']['pending_bookings'] = st.session_state.pending_bookings
    except Exception:
        # Fallback initialization
        st.session_state.persistent_data['pending_bookings'] = {'pending_bookings': st.session_state.pending_bookings}

def load_pending_bookings():
    """Load pending bookings from storage"""
    if 'pending_bookings' not in st.session_state:
        # Try to load from persistent storage
        try:
            if ('pending_bookings' in st.session_state.persistent_data and 
                'pending_bookings' in st.session_state.persistent_data['pending_bookings']):
                stored_data = st.session_state.persistent_data['pending_bookings']['pending_bookings']
                st.session_state.pending_bookings = stored_data if isinstance(stored_data, list) else []
            else:
                st.session_state.pending_bookings = []
        except Exception:
            st.session_state.pending_bookings = []
    
    return st.session_state.pending_bookings

def get_owner_cars(owner_username):
    """Get cars for a specific owner only"""
    owner_cars = load_data("cars.csv", ["id", "car_name", "plate_number", "model", "status", "last_service_date", "next_service_date"], owner_username)
    if not owner_cars.empty:
        owner_cars['owner'] = owner_username
    return owner_cars

# ---------- User-Specific Public Booking Page ----------
def show_public_booking():
    st.markdown("# 🚗 Car Rental Booking")
    
    # Get owner from URL parameters
    try:
        query_params = dict(st.query_params)
        owner_username = query_params.get("owner")
    except Exception:
        owner_username = None
    
    if not owner_username:
        st.error("❌ Invalid booking link. Please contact the car owner for the correct link.")
        st.markdown("""
        ### For Car Owners:
        To generate your booking link:
        1. Login to your dashboard
        2. Go to the Public Booking section in the sidebar
        3. Copy your unique booking URL
        """)
        return
    
    # Verify owner exists
    users = load_users()
    if owner_username not in users['username'].values:
        st.error("❌ Car owner not found. Please check the booking link.")
        return
    
    owner_name = users[users['username'] == owner_username]['full_name'].iloc[0]
    
    st.markdown(f"### 🏢 Booking with **{owner_name}**")
    
    # Get owner's cars
    owner_cars = get_owner_cars(owner_username)
    
    if owner_cars.empty:
        st.error(f"❌ {owner_name} has no cars available for booking at the moment.")
        st.info("Please contact them directly or try again later.")
        return
    
    available_cars = owner_cars[owner_cars['status'] == 'Available']
    
    if available_cars.empty:
        st.warning(f"⚠️ All of {owner_name}'s cars are currently booked.")
        st.markdown("### All Cars (Check availability)")
        display_cars = owner_cars[['car_name', 'model', 'plate_number', 'status']].copy()
        st.dataframe(display_cars, use_container_width=True)
        st.info("Please contact the owner directly or choose different dates.")
        return
    
    # Show available cars
    st.markdown("### 🚗 Available Cars")
    display_cars = available_cars[['car_name', 'model', 'plate_number']].copy()
    st.dataframe(display_cars, use_container_width=True)
    
    # Initialize session state for form reset
    if 'booking_submitted' not in st.session_state:
        st.session_state.booking_submitted = False
    
    # Show success message if booking was just submitted
    if st.session_state.booking_submitted:
        st.success("🎉 Booking request submitted successfully!")
        st.info(f"Your booking request has been sent to {owner_name}. You will be contacted soon for confirmation.")
        
        # Show booking summary from session state
        if 'last_booking_summary' in st.session_state:
            summary = st.session_state.last_booking_summary
            st.markdown("#### 📋 Booking Summary")
            st.write(f"**Car:** {summary['car_name']} - {summary['car_model']}")
            st.write(f"**Owner:** {summary['owner_name']}")
            st.write(f"**Dates:** {summary['start_date']} to {summary['end_date']}")
            st.write(f"**Duration:** {summary['duration']} days")
            st.write(f"**Customer:** {summary['client_name']}")
            st.write(f"**Phone:** {summary['client_phone']}")
        
        # Reset button outside the form
        if st.button("📝 Submit Another Booking", type="primary"):
            st.session_state.booking_submitted = False
            if 'last_booking_summary' in st.session_state:
                del st.session_state.last_booking_summary
            st.rerun()
        
        return
    
    # Booking form
    with st.form("public_booking"):
        st.markdown("#### 📝 Booking Details")
        
        # Car selection
        car_options = available_cars.apply(lambda x: f"{x['car_name']} - {x['model']} ({x['plate_number']})", axis=1)
        if len(available_cars) == 1:
            st.info(f"**Selected Car:** {car_options.iloc[0]}")
            selected_car = available_cars.iloc[0]
        else:
            selected_car_idx = st.selectbox("Select Car", range(len(available_cars)), 
                                           format_func=lambda x: car_options.iloc[x])
            selected_car = available_cars.iloc[selected_car_idx] if selected_car_idx is not None else None
        
        # Customer details
        col1, col2 = st.columns(2)
        with col1:
            client_name = st.text_input("Your Full Name *", placeholder="John Doe")
            client_phone = st.text_input("Phone Number *", placeholder="+256 XXX XXX XXX")
            start_date = st.date_input("Start Date *", min_value=dt.date.today())
        
        with col2:
            client_email = st.text_input("Email Address", placeholder="john@example.com")
            purpose = st.text_input("Purpose of Rental", placeholder="Business trip, vacation, etc.")
            end_date = st.date_input("End Date *", min_value=dt.date.today())
        
        # Additional info
        additional_notes = st.text_area("Additional Notes", placeholder="Any special requirements or questions...")
        
        # Contact info
        st.markdown("---")
        st.markdown(f"**Owner Contact:** For immediate assistance, contact {owner_name}")
        
        # Terms and conditions
        agree_terms = st.checkbox("I agree to the terms and conditions *")
        
        if st.form_submit_button("🚀 Submit Booking Request", type="primary"):
            if not all([client_name, client_phone, start_date, end_date, agree_terms]):
                st.error("Please fill in all required fields (*) and agree to terms.")
            elif end_date < start_date:
                st.error("End date must be after start date.")
            elif selected_car is None:
                st.error("Please select a car.")
            else:
                # Create booking request
                booking_request = {
                    'owner': owner_username,
                    'car_id': selected_car['id'],
                    'car_name': selected_car['car_name'],
                    'car_model': selected_car['model'],
                    'plate_number': selected_car['plate_number'],
                    'client_name': client_name,
                    'client_phone': client_phone,
                    'client_email': client_email,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'purpose': purpose,
                    'additional_notes': additional_notes
                }
                
                save_public_booking(booking_request)
                
                # Store booking summary for display
                st.session_state.last_booking_summary = {
                    'car_name': selected_car['car_name'],
                    'car_model': selected_car['model'],
                    'owner_name': owner_name,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'duration': (end_date - start_date).days + 1,
                    'client_name': client_name,
                    'client_phone': client_phone
                }
                
                # Set flag to show success message
                st.session_state.booking_submitted = True
                st.rerun()

# ---------- Enhanced Sidebar with Data Management ----------
def show_data_management_section():
    """Show data management options in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Data Management")
    
    # Export data
    if st.sidebar.button("📤 Export Data"):
        user_prefix = st.session_state.username
        export_data = {
            'cars': st.session_state.cars.to_dict('records') if not st.session_state.cars.empty else [],
            'bookings': st.session_state.bookings.to_dict('records') if not st.session_state.bookings.empty else [],
            'expenses': st.session_state.expenses.to_dict('records') if not st.session_state.expenses.empty else [],
            'export_date': dt.datetime.now().isoformat(),
            'user': user_prefix
        }
        
        st.sidebar.download_button(
            label="💾 Download Backup",
            data=json.dumps(export_data, indent=2),
            file_name=f"{user_prefix}_backup_{dt.date.today().strftime('%Y%m%d')}.json",
            mime="application/json"
        )
    
    # Import data
    uploaded_file = st.sidebar.file_uploader("📥 Import Backup", type=['json'])
    if uploaded_file is not None:
        try:
            import_data = json.load(uploaded_file)
            user_prefix = st.session_state.username
            
            # Restore data with validation
            if 'cars' in import_data and import_data['cars']:
                st.session_state.cars = pd.DataFrame(import_data['cars'])
                save_data(st.session_state.cars, "cars.csv", user_prefix)
            
            if 'bookings' in import_data and import_data['bookings']:
                st.session_state.bookings = pd.DataFrame(import_data['bookings'])
                save_data(st.session_state.bookings, "bookings.csv", user_prefix)
            
            if 'expenses' in import_data and import_data['expenses']:
                st.session_state.expenses = pd.DataFrame(import_data['expenses'])
                save_data(st.session_state.expenses, "expenses.csv", user_prefix)
            
            st.sidebar.success("✅ Data imported and saved successfully!")
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"❌ Import failed: {str(e)}")

# ---------- App Entry Point with Fixed URL Handling ----------
def main():
    # Check URL parameters for public booking
    try:
        query_params = dict(st.query_params)
    except Exception:
        query_params = {}
    
    if query_params.get("page") == "booking":
        show_public_booking()
    else:
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False

        if st.session_state.logged_in:
            main_app()
        else:
            show_login()

# Run the app
if __name__ == "__main__":
    main()
else:
    # When running in Streamlit, call main directly
    main()
