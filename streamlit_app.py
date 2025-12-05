import streamlit as st
import sqlite3
import pandas as pd
import qrcode
from PIL import Image
import io
import os

# --- CONFIGURATION ---
ADMIN_PASSWORD = "Admin#1520"  # Simple password for demonstration
DB_FILE = "employee_db.sqlite"
IMAGE_FOLDER = "employee_photos"

# Ensure image folder exists
if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)

# --- DATABASE FUNCTIONS ---
def init_db():
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
    # Get photo path to delete file
    c.execute("SELECT photo_path FROM employees WHERE id=?", (emp_id,))
    result = c.fetchone()
    if result and os.path.exists(result[0]):
        os.remove(result[0])
    
    c.execute("DELETE FROM employees WHERE id=?", (emp_id,))
    conn.commit()
    conn.close()

def get_all_employees():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM employees", conn)
    conn.close()
    return df

# --- HELPER FUNCTIONS ---
def generate_qr(data):
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
    init_db()

    st.title("🏢 SuperX Members Database")

    # Sidebar for Navigation
    menu = st.sidebar.selectbox("Menu", ["Public View", "Admin Portal"])

    # --- PUBLIC VIEW (Read Only) ---
    if menu == "Public View":
        st.subheader("Employee Directory")
        
        df = get_all_employees()
        
        if df.empty:
            st.info("No employees found in the database.")
        else:
            # Search bar
            search = st.text_input("Search Employee by Name or Domain")
            if search:
                df = df[df['name'].str.contains(search, case=False) | df['domain'].str.contains(search, case=False)]

            # Display Cards
            for index, row in df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 2, 1])
                    
                    # Col 1: Photo
                    with col1:
                        if os.path.exists(row['photo_path']):
                            image = Image.open(row['photo_path'])
                            st.image(image, width=150)
                        else:
                            st.write("No Image")

                    # Col 2: Details
                    with col2:
                        st.markdown(f"### {row['name']}")
                        st.write(f"**Domain:** {row['domain']}")
                        st.write(f"**Email:** {row['email']}")
                        st.write(f"**Phone:** {row['phone']}")
                        st.markdown(f"[LinkedIn Profile]({row['linkedin']})")

                    # Col 3: QR Code
                    with col3:
                        # Constructing data string for QR
                        qr_data = f"Name: {row['name']}\nEmail: {row['email']}\nPhone: {row['phone']}\nDomain: {row['domain']}\nLinkedIn: {row['linkedin']}"
                        qr_img = generate_qr(qr_data)
                        
                        # Convert PIL image to bytes for display
                        buf = io.BytesIO()
                        qr_img.save(buf)
                        st.image(buf, caption="Scan for Details", width=150)
                    
                    st.markdown("---")

    # --- ADMIN PORTAL (Add/Delete) ---
    elif menu == "Admin Portal":
        password = st.sidebar.text_input("Enter Admin Password", type="password")
        
        if password == ADMIN_PASSWORD:
            st.sidebar.success("Logged In")
            
            tab1, tab2 = st.tabs(["Add Employee", "Manage Employees"])
            
            # Tab 1: Add Employee
            with tab1:
                st.subheader("Add New Employee")
                with st.form("add_form", clear_on_submit=True):
                    name = st.text_input("Full Name")
                    email = st.text_input("Email")
                    phone = st.text_input("Phone Number")
                    domain = st.text_input("Domain (e.g., IT, HR, Sales)")
                    linkedin = st.text_input("LinkedIn URL")
                    photo = st.file_uploader("Upload Passport Photo", type=['jpg', 'png', 'jpeg'])
                    
                    submitted = st.form_submit_button("Add Employee")
                    
                    if submitted:
                        if name and email and photo:
                            # Save Image Locally
                            file_ext = photo.name.split(".")[-1]
                            save_path = os.path.join(IMAGE_FOLDER, f"{name}_{phone}.{file_ext}")
                            
                            with open(save_path, "wb") as f:
                                f.write(photo.getbuffer())
                            
                            add_employee(name, email, phone, domain, linkedin, save_path)
                            st.success(f"Employee {name} added successfully!")
                        else:
                            st.error("Please fill required fields and upload a photo.")

            # Tab 2: Delete Employee
            with tab2:
                st.subheader("Remove Employee")
                df = get_all_employees()
                if not df.empty:
                    # Create a dictionary for the selectbox to show names but use ID
                    emp_dict = {f"{row['name']} ({row['email']})": row['id'] for index, row in df.iterrows()}
                    selected_emp = st.selectbox("Select Employee to Delete", list(emp_dict.keys()))
                    
                    if st.button("Delete Selected Employee"):
                        emp_id = emp_dict[selected_emp]
                        delete_employee(emp_id)
                        st.warning("Employee Deleted. Refresh the page to see changes.")
                        st.rerun()
                else:
                    st.info("Database is empty.")
                    
        elif password:
            st.sidebar.error("Incorrect Password")

if __name__ == "__main__":
    main()
