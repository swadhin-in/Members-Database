import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from PIL import Image
import io
import os

# --- CONFIGURATION ---
# In a real app, use st.secrets for passwords
ADMIN_PASSWORD = "admin" 
DB_FILE = "employee_db.sqlite"
IMAGE_FOLDER = "employee_photos"

# Ensure image folder exists
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# --- DATABASE FUNCTIONS ---
def init_db():
    """Initialize the SQLite database if it doesn't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            domain TEXT,
            linkedin TEXT,
            photo_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_employee(name, email, phone, domain, linkedin, photo_path):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO employees (name, email, phone, domain, linkedin, photo_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, email, phone, domain, linkedin, photo_path))
    conn.commit()
    conn.close()

def delete_employee(emp_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Get photo path to delete file from storage
    c.execute("SELECT photo_path FROM employees WHERE id=?", (emp_id,))
    result = c.fetchone()
    if result and result[0] and os.path.exists(result[0]):
        try:
            os.remove(result[0])
        except Exception as e:
            st.warning(f"Could not delete image file: {e}")
    
    c.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()

def get_all_employees():
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT * FROM employees", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# --- HELPER FUNCTIONS ---
def generate_qr(data):
    """Generates a QR code image from a string."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

# --- MAIN APP ---
def main():
    st.set_page_config(page_title="Employee Directory", layout="wide")
    
    # Initialize DB on load
    init_db()

    st.title("🏢 Corporate Employee Database")

    # Sidebar for Navigation
    menu = st.sidebar.selectbox("Menu", ["Public View", "Admin Portal"])

    # --- PUBLIC VIEW (Read Only) ---
    if menu == "Public View":
        st.header("Employee Directory")
        
        df = get_all_employees()
        
        if df.empty:
            st.info("No employees found in the database. Please ask an Admin to add records.")
        else:
            # Search bar
            search = st.text_input("🔍 Search by Name or Domain", placeholder="e.g. John or Marketing")
            
            # Filter logic
            if search:
                mask = df['name'].str.contains(search, case=False, na=False) | \
                       df['domain'].str.contains(search, case=False, na=False)
                df = df[mask]

            st.write(f"Showing {len(df)} employees")
            st.markdown("---")

            # Display Cards
            for index, row in df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    # Col 1: Photo
                    with col1:
                        if row['photo_path'] and os.path.exists(row['photo_path']):
                            try:
                                image = Image.open(row['photo_path'])
                                st.image(image, width=150, caption="Employee Photo")
                            except:
                                st.error("Error loading image")
                        else:
                            st.image("https://via.placeholder.com/150", width=150, caption="No Image")

                    # Col 2: Details
                    with col2:
                        st.subheader(f"{row['name']}")
                        st.caption(f"**{row['domain']}**")
                        st.text(f"📧 {row['email']}")
                        st.text(f"📞 {row['phone']}")
                        if row['linkedin']:
                            st.markdown(f"🔗 [LinkedIn Profile]({row['linkedin']})")

                    # Col 3: QR Code
                    with col3:
                        # Constructing data string for QR
                        qr_info = (
                            f"Name: {row['name']}\n"
                            f"Title: {row['domain']}\n"
                            f"Email: {row['email']}\n"
                            f"Phone: {row['phone']}"
                        )
                        qr_img = generate_qr(qr_info)
                        
                        # Convert PIL image to bytes for display
                        buf = io.BytesIO()
                        qr_img.save(buf)
                        st.image(buf, caption="Scan for Contact Info", width=150)
                    
                    st.markdown("---")

    # --- ADMIN PORTAL (Add/Delete) ---
    elif menu == "Admin Portal":
        st.header("Admin Portal")
        password = st.sidebar.text_input("Enter Admin Password", type="password")
        
        if password == ADMIN_PASSWORD:
            st.sidebar.success("Authentication Successful")
            
            tab1, tab2 = st.tabs(["➕ Add Employee", "❌ Remove Employee"])
            
            # Tab 1: Add Employee
            with tab1:
                st.subheader("Add New Employee")
                with st.form("add_form", clear_on_submit=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        name = st.text_input("Full Name")
                        email = st.text_input("Email")
                        phone = st.text_input("Phone Number")
                    with col_b:
                        domain = st.text_input("Domain (e.g., IT, HR)")
                        linkedin = st.text_input("LinkedIn URL")
                        photo = st.file_uploader("Upload Passport Photo", type=['jpg', 'png', 'jpeg'])
                    
                    submitted = st.form_submit_button("Save Record")
                    
                    if submitted:
                        if name and email and photo:
                            # Save Image Locally
                            file_ext = photo.name.split(".")[-1]
                            # Sanitize filename
                            safe_name = "".join([c for c in name if c.isalpha() or c.isdigit()]).rstrip()
                            save_path = os.path.join(IMAGE_FOLDER, f"{safe_name}_{phone}.{file_ext}")
                            
                            with open(save_path, "wb") as f:
                                f.write(photo.getbuffer())
                            
                            add_employee(name, email, phone, domain, linkedin, save_path)
                            st.success(f"Employee '{name}' added successfully!")
                            st.rerun()
                        else:
                            st.error("Name, Email, and Photo are required.")

            # Tab 2: Delete Employee
            with tab2:
                st.subheader("Remove Employee")
                df = get_all_employees()
                if not df.empty:
                    # Create a dictionary for the selectbox: "Name (Email)" -> ID
                    emp_options = {f"{row['name']} | {row['domain']}": row['id'] for index, row in df.iterrows()}
                    selected_emp_label = st.selectbox("Select Employee to Delete", list(emp_options.keys()))
                    
                    if st.button("Delete Selected Employee", type="primary"):
                        emp_id = emp_options[selected_emp_label]
                        delete_employee(emp_id)
                        st.success("Employee record deleted.")
                        st.rerun()
                else:
                    st.info("Database is empty.")
                    
        elif password:
            st.error("Incorrect Password")
        else:
            st.info("Please enter the password in the sidebar to access admin features.")

if __name__ == "__main__":
    main()