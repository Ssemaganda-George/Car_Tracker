# 🚗 Car Booking & Tracking System

A Streamlit web application for managing car rentals, bookings, expenses, and maintenance with multi-user support.

## Features

- **🔐 Multi-User Authentication**: Secure login system with user isolation
- **📊 Enhanced Dashboard**: Interactive charts, metrics, and quick actions
- **🚗 Car Management**: Add, edit, and track vehicle inventory with status management
- **📅 Advanced Booking System**: 
  - Record client bookings with conflict detection
  - Support for overlapping bookings (rebooking)
  - Real-time availability checking
- **💰 Expense Tracking**: Monitor fuel, maintenance, insurance, and other costs
- **🔧 Maintenance Schedule**: Track service dates and maintenance status
- **✏️ Edit Mode**: Modify existing records without data loss
- **🌙 Dark Mode**: Modern dark theme interface

## Data Persistence

⚠️ **Important**: When deploying to cloud platforms, CSV data files are ephemeral and will be lost on redeployment.

### For Production Use (Recommended):

#### Option 1: Database Integration
Replace CSV storage with a persistent database:

```python
# Example: Using SQLite
import sqlite3
import pandas as pd

def save_to_db(df, table_name, user_id):
    conn = sqlite3.connect('car_tracker.db')
    df.to_sql(f"{user_id}_{table_name}", conn, if_exists='replace', index=False)
    conn.close()

def load_from_db(table_name, user_id):
    conn = sqlite3.connect('car_tracker.db')
    try:
        df = pd.read_sql(f"SELECT * FROM {user_id}_{table_name}", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df
```

#### Option 2: Cloud Storage Integration
Use cloud storage services:

```python
# Example: Using Google Sheets API or AWS S3
import streamlit as st

# Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="cars", usecols=list(range(7)))

# AWS S3
import boto3
s3 = boto3.client('s3')
```

#### Option 3: Streamlit Secrets + GitHub
Store data in repository with proper gitignore management:

1. Add to `.gitignore`:
```
# User data files
*_cars.csv
*_bookings.csv
*_expenses.csv
users.csv
```

2. Use Streamlit secrets for sensitive data
3. Implement data backup/restore functionality

### For Development/Demo:

The current CSV-based system works perfectly for local development and testing.

## Local Setup

1. **Clone the repository:**
```bash
git clone <your-repo-url>
cd Car_Tracker
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
streamlit run car_tracker.py
```

4. **Default Login:**
   - Username: `admin`
   - Password: `admin123`

## Deployment

### Streamlit Cloud Deployment

1. **Push code to GitHub** (data files will be lost on redeployment)
2. **Connect repository to Streamlit Cloud**
3. **Set main file path**: `car_tracker.py`
4. **Deploy with one click**

⚠️ **Note**: For production deployment, implement database integration (see Data Persistence section above).

### Environment Variables

For production deployments, set these in your cloud platform:

```bash
# Optional: Database URLs, API keys, etc.
DATABASE_URL=your_database_url
SECRET_KEY=your_secret_key
```

## File Structure

```
Car_Tracker/
├── car_tracker.py          # Main application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitignore            # Git ignore rules
├── users.csv             # User accounts (ephemeral in cloud)
└── *_cars.csv            # User car data (ephemeral in cloud)
└── *_bookings.csv        # User booking data (ephemeral in cloud)
└── *_expenses.csv        # User expense data (ephemeral in cloud)
```

## Usage

1. **Login/Register**: Create an account or use default admin credentials
2. **Dashboard**: View business metrics, charts, and quick actions
3. **Cars**: Add and manage your vehicle fleet
4. **Bookings**: Create bookings with conflict detection and rebooking support
5. **Expenses**: Track all car-related expenses
6. **Maintenance**: Monitor service schedules

### Key Features:

- **Data Isolation**: Each user has separate data files
- **Edit Mode**: Toggle edit mode to modify existing records
- **Conflict Detection**: Booking system warns about date conflicts
- **Rebooking**: Allow overlapping bookings for the same car
- **Quick Actions**: Complete bookings directly from dashboard

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and feature requests, please create an issue in the GitHub repository.
