# car_tracker.py
import streamlit as st
import pandas as pd
import datetime as dt
import os

st.set_page_config(page_title="🚗 Car Booking & Tracking", layout="wide")

# ---------- Data Loaders ----------
@st.cache_data
def load_data(filename, columns):
    if os.path.exists(filename):
        try:
            df = pd.read_csv(filename)
            # Ensure all expected columns exist
            for col in columns:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception:
            return pd.DataFrame(columns=columns)
    else:
        return pd.DataFrame(columns=columns)

# Initialize session state for data persistence
if 'data_loaded' not in st.session_state:
    st.session_state.cars = load_data("cars.csv", ["id", "car_name", "plate_number", "model", "status", "last_service_date", "next_service_date"])
    st.session_state.bookings = load_data("bookings.csv", ["id", "car_id", "client_name", "start_date", "end_date", "amount_paid", "status"])
    st.session_state.expenses = load_data("expenses.csv", ["id", "car_id", "date", "description", "amount", "type"])
    st.session_state.data_loaded = True

cars = st.session_state.cars
bookings = st.session_state.bookings
expenses = st.session_state.expenses

# ---------- Navigation ----------
menu = st.sidebar.radio("Menu", ["Dashboard", "Cars", "Bookings", "Expenses", "Maintenance"])

# ---------- Dashboard ----------
if menu == "Dashboard":
    # Handle empty DataFrames safely
    total_income = 0
    total_expenses = 0
    
    if not bookings.empty and "amount_paid" in bookings.columns:
        total_income = pd.to_numeric(bookings["amount_paid"], errors='coerce').fillna(0).sum()
    
    if not expenses.empty and "amount" in expenses.columns:
        total_expenses = pd.to_numeric(expenses["amount"], errors='coerce').fillna(0).sum()
    
    profit = total_income - total_expenses

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💰 Total Income", f"UGX {total_income:,.0f}")
    with col2:
        st.metric("🧾 Total Expenses", f"UGX {total_expenses:,.0f}")
    with col3:
        st.metric("📊 Profit", f"UGX {profit:,.0f}")

    st.write("### Recent Bookings")
    if not bookings.empty:
        st.dataframe(bookings.tail(5), use_container_width=True)
    else:
        st.info("No bookings recorded yet.")

# ---------- Cars ----------
elif menu == "Cars":
    st.write("### Manage Cars")
    if not cars.empty:
        st.dataframe(cars, use_container_width=True)
    else:
        st.info("No cars registered yet.")

    with st.form("add_car"):
        st.write("#### Add New Car")
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
                st.session_state.cars.to_csv("cars.csv", index=False)
                st.success("Car added successfully!")
                st.rerun()
            else:
                st.error("Please fill in all fields.")

# ---------- Bookings ----------
elif menu == "Bookings":
    st.write("### Booking Management")
    
    if cars.empty:
        st.warning("Please add cars first before creating bookings.")
    else:
        # Display existing bookings
        if not bookings.empty:
            st.write("#### Existing Bookings")
            st.dataframe(bookings, use_container_width=True)
        
        st.write("#### Add New Booking")
        with st.form("add_booking"):
            available_cars = cars[cars["status"] == "Available"] if not cars.empty else pd.DataFrame()
            
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
                    st.session_state.bookings.to_csv("bookings.csv", index=False)
                    st.session_state.cars.to_csv("cars.csv", index=False)
                    st.success("Booking added and car marked as booked!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields correctly.")

# ---------- Expenses ----------
elif menu == "Expenses":
    st.write("### Expense Management")
    
    if cars.empty:
        st.warning("Please add cars first before recording expenses.")
    else:
        # Display existing expenses
        if not expenses.empty:
            st.write("#### Existing Expenses")
            st.dataframe(expenses, use_container_width=True)
        
        st.write("#### Add New Expense")
        with st.form("add_expense"):
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
                etype = st.selectbox("Type", ["Fuel", "Maintenance", "Other"])
            
            if st.form_submit_button("Add Expense"):
                if car_id and desc and amt > 0:
                    new_exp = {
                        "id": len(expenses)+1, "car_id": car_id, "date": dt.date.today().strftime("%Y-%m-%d"), 
                        "description": desc, "amount": amt, "type": etype
                    }
                    st.session_state.expenses = pd.concat([expenses, pd.DataFrame([new_exp])], ignore_index=True)
                    st.session_state.expenses.to_csv("expenses.csv", index=False)
                    st.success("Expense added successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields correctly.")

# ---------- Maintenance ----------
elif menu == "Maintenance":
    st.write("### Maintenance Schedule")
    if not cars.empty:
        maintenance_data = cars[["car_name", "last_service_date", "next_service_date"]]
        st.dataframe(maintenance_data, use_container_width=True)
    else:
        st.info("No cars registered yet.")
