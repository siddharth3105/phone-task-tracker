import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# Page configuration
st.set_page_config(
    page_title="Phone Task Tracker",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database initialization
def init_db():
    conn = sqlite3.connect('phone_tracker.db', check_same_thread=False)
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS persons
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  person_id TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  currently_has_phones INTEGER DEFAULT 0,
                  current_session_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS phone_sets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  iphone_name TEXT NOT NULL,
                  samsung_name TEXT NOT NULL,
                  power_bank_name TEXT NOT NULL,
                  is_available INTEGER DEFAULT 1,
                  current_session_id INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  person_id INTEGER NOT NULL,
                  phone_set_id INTEGER NOT NULL,
                  assigned_at TEXT NOT NULL,
                  returned_at TEXT,
                  iphone_seconds INTEGER,
                  samsung_seconds INTEGER,
                  status TEXT DEFAULT 'in_progress',
                  entry_method TEXT,
                  FOREIGN KEY (person_id) REFERENCES persons (id),
                  FOREIGN KEY (phone_set_id) REFERENCES phone_sets (id))''')
    
    conn.commit()
    return conn

# Helper functions
def format_duration(seconds):
    if seconds is None:
        return "00:00"
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"

def parse_duration(duration_str):
    """Parse MM:SS format to total seconds"""
    try:
        parts = duration_str.split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
    except:
        pass
    return 0

# Initialize database
conn = init_db()

# Sidebar navigation
st.sidebar.title("📱 Phone Task Tracker")
page = st.sidebar.radio("Navigation", 
                        ["🏠 Active Tasks", 
                         "👥 Assignments", 
                         "⏱️ Time Entry", 
                         "📊 Reports",
                         "⚙️ Setup"])

# Page: Setup
if page == "⚙️ Setup":
    st.title("⚙️ Setup Device Sets")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Add New Device Set")
        with st.form("add_device_set"):
            iphone_name = st.text_input("iPhone Name", placeholder="e.g., iPhone #1")
            samsung_name = st.text_input("Samsung Name", placeholder="e.g., Samsung #1")
            power_bank_name = st.text_input("Power Bank Name", placeholder="e.g., Power Bank #1")
            
            if st.form_submit_button("➕ Add Device Set"):
                if iphone_name and samsung_name and power_bank_name:
                    c = conn.cursor()
                    c.execute('''INSERT INTO phone_sets (iphone_name, samsung_name, power_bank_name)
                                 VALUES (?, ?, ?)''', (iphone_name, samsung_name, power_bank_name))
                    conn.commit()
                    st.success(f"✅ Added device set: {iphone_name} + {samsung_name} + {power_bank_name}")
                    st.rerun()
                else:
                    st.error("Please fill all fields")
    
    with col2:
        st.subheader("Configured Device Sets")
        c = conn.cursor()
        phone_sets = c.execute('SELECT * FROM phone_sets').fetchall()
        
        if phone_sets:
            for ps in phone_sets:
                status = "🟢 Available" if ps[4] == 1 else "🔴 In Use"
                st.info(f"""
                **{ps[1]} + {ps[2]}**  
                Power Bank: {ps[3]}  
                Status: {status}
                """)
        else:
            st.warning("No device sets configured yet")

# Page: Assignments
elif page == "👥 Assignments":
    st.title("👥 Assignment Dashboard")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Add New Person")
        with st.form("add_person"):
            person_name = st.text_input("Name", placeholder="e.g., Rahul Kumar")
            person_id = st.text_input("Person ID", placeholder="e.g., 101")
            
            if st.form_submit_button("➕ Add Person"):
                if person_name and person_id:
                    c = conn.cursor()
                    try:
                        c.execute('INSERT INTO persons (name, person_id) VALUES (?, ?)', 
                                 (person_name, person_id))
                        conn.commit()
                        st.success(f"✅ Added {person_name}")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Person ID already exists")
                else:
                    st.error("Please fill all fields")
        
        st.subheader("Assign Devices")
        c = conn.cursor()
        available_persons = c.execute('''SELECT id, name, person_id FROM persons 
                                         WHERE currently_has_phones = 0''').fetchall()
        available_sets = c.execute('''SELECT id, iphone_name, samsung_name, power_bank_name 
                                      FROM phone_sets WHERE is_available = 1''').fetchall()
        
        if available_persons and available_sets:
            with st.form("assign_devices"):
                person_options = {f"{p[1]} ({p[2]})": p[0] for p in available_persons}
                selected_person = st.selectbox("Select Person", list(person_options.keys()))
                
                set_options = {f"{s[1]} + {s[2]} (PB: {s[3]})": s[0] for s in available_sets}
                selected_set = st.selectbox("Select Device Set", list(set_options.keys()))
                
                if st.form_submit_button("📱 Assign Devices"):
                    person_id = person_options[selected_person]
                    set_id = set_options[selected_set]
                    
                    # Create session
                    c.execute('''INSERT INTO sessions (person_id, phone_set_id, assigned_at, status)
                                 VALUES (?, ?, ?, 'in_progress')''',
                             (person_id, set_id, datetime.now().isoformat()))
                    session_id = c.lastrowid
                    
                    # Update person
                    c.execute('UPDATE persons SET currently_has_phones = 1, current_session_id = ? WHERE id = ?',
                             (session_id, person_id))
                    
                    # Update phone set
                    c.execute('UPDATE phone_sets SET is_available = 0, current_session_id = ? WHERE id = ?',
                             (session_id, set_id))
                    
                    conn.commit()
                    st.success("✅ Devices assigned successfully!")
                    st.rerun()
        else:
            if not available_persons:
                st.warning("No available persons (all have devices or none added)")
            if not available_sets:
                st.warning("No available device sets")
    
    with col2:
        st.subheader("All Persons")
        c = conn.cursor()
        persons = c.execute('SELECT * FROM persons ORDER BY name').fetchall()
        
        if persons:
            for person in persons:
                status = "🔴 Has Devices" if person[3] == 1 else "🟢 Available"
                st.info(f"""
                **{person[2]}** (ID: {person[1]})  
                Status: {status}
                """)
        else:
            st.warning("No persons added yet")

# Page: Active Tasks
elif page == "🏠 Active Tasks":
    st.title("🏠 Active Tasks Monitor")
    
    c = conn.cursor()
    active_sessions = c.execute('''
        SELECT s.id, p.name, p.person_id, ps.iphone_name, ps.samsung_name, ps.power_bank_name, s.assigned_at
        FROM sessions s
        JOIN persons p ON s.person_id = p.id
        JOIN phone_sets ps ON s.phone_set_id = ps.id
        WHERE s.status = 'in_progress'
        ORDER BY s.assigned_at DESC
    ''').fetchall()
    
    st.subheader(f"Currently Working ({len(active_sessions)})")
    
    if active_sessions:
        for session in active_sessions:
            assigned_time = datetime.fromisoformat(session[6])
            duration = datetime.now() - assigned_time
            minutes = int(duration.total_seconds() / 60)
            
            # Color coding
            if minutes < 30:
                color = "🟢"
            elif minutes < 60:
                color = "🟡"
            else:
                color = "🔴"
            
            st.success(f"""
            {color} **{session[1]}** (ID: {session[2]})  
            📱 {session[3]} + {session[4]}  
            🔋 Power Bank: {session[5]}  
            ⏱️ Working for: {minutes} minutes  
            🕐 Assigned: {assigned_time.strftime('%I:%M %p')}
            """)
    else:
        st.info("No active tasks")
    
    st.subheader("Available Device Sets")
    available_sets = c.execute('''SELECT iphone_name, samsung_name, power_bank_name 
                                  FROM phone_sets WHERE is_available = 1''').fetchall()
    
    if available_sets:
        cols = st.columns(3)
        for idx, ps in enumerate(available_sets):
            with cols[idx % 3]:
                st.info(f"""
                ✅ **{ps[0]} + {ps[1]}**  
                🔋 {ps[2]}  
                Ready to assign
                """)
    else:
        st.warning("No device sets available")

# Page: Time Entry
elif page == "⏱️ Time Entry":
    st.title("⏱️ Time Entry")
    
    c = conn.cursor()
    active_sessions = c.execute('''
        SELECT s.id, p.name, p.person_id, ps.iphone_name, ps.samsung_name, ps.power_bank_name, p.id, ps.id
        FROM sessions s
        JOIN persons p ON s.person_id = p.id
        JOIN phone_sets ps ON s.phone_set_id = ps.id
        WHERE s.status = 'in_progress'
        ORDER BY p.name
    ''').fetchall()
    
    if active_sessions:
        st.subheader("Select Person to Record Time")
        
        session_options = {f"{s[1]} ({s[2]}) - {s[3]} + {s[4]}": s for s in active_sessions}
        selected_session_key = st.selectbox("Person", list(session_options.keys()))
        
        if selected_session_key:
            session = session_options[selected_session_key]
            
            st.info(f"""
            **Person:** {session[1]} (ID: {session[2]})  
            **Devices:** {session[3]} + {session[4]}  
            **Power Bank:** {session[5]}
            """)
            
            entry_method = st.radio("Entry Method", ["Manual", "Auto (OCR)"])
            
            if entry_method == "Manual":
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📱 iPhone Duration")
                    iphone_duration = st.text_input("Format: MM:SS", placeholder="15:30", key="iphone")
                
                with col2:
                    st.subheader("📱 Samsung Duration")
                    samsung_duration = st.text_input("Format: MM:SS", placeholder="20:45", key="samsung")
                
                if st.button("💾 Save Time Entry"):
                    iphone_seconds = parse_duration(iphone_duration)
                    samsung_seconds = parse_duration(samsung_duration)
                    
                    if iphone_seconds > 0 and samsung_seconds > 0:
                        # Update session
                        c.execute('''UPDATE sessions 
                                    SET returned_at = ?, iphone_seconds = ?, samsung_seconds = ?, 
                                        status = 'completed', entry_method = 'manual'
                                    WHERE id = ?''',
                                 (datetime.now().isoformat(), iphone_seconds, samsung_seconds, session[0]))
                        
                        # Update person
                        c.execute('UPDATE persons SET currently_has_phones = 0, current_session_id = NULL WHERE id = ?',
                                 (session[6],))
                        
                        # Update phone set
                        c.execute('UPDATE phone_sets SET is_available = 1, current_session_id = NULL WHERE id = ?',
                                 (session[7],))
                        
                        conn.commit()
                        st.success(f"✅ Time recorded for {session[1]}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter valid durations in MM:SS format")
            
            else:  # OCR mode
                st.info("📸 OCR Feature: Upload screenshots of recording durations")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("📱 iPhone Screenshot")
                    iphone_file = st.file_uploader("Upload iPhone screenshot", type=['png', 'jpg', 'jpeg'], key="iphone_ocr")
                    iphone_duration_ocr = st.text_input("Extracted/Manual Duration (MM:SS)", placeholder="15:30", key="iphone_extracted")
                
                with col2:
                    st.subheader("📱 Samsung Screenshot")
                    samsung_file = st.file_uploader("Upload Samsung screenshot", type=['png', 'jpg', 'jpeg'], key="samsung_ocr")
                    samsung_duration_ocr = st.text_input("Extracted/Manual Duration (MM:SS)", placeholder="20:45", key="samsung_extracted")
                
                st.info("💡 Tip: After uploading, enter the duration you see in the screenshot")
                
                if st.button("💾 Save Time Entry (OCR)"):
                    iphone_seconds = parse_duration(iphone_duration_ocr)
                    samsung_seconds = parse_duration(samsung_duration_ocr)
                    
                    if iphone_seconds > 0 and samsung_seconds > 0:
                        # Update session
                        c.execute('''UPDATE sessions 
                                    SET returned_at = ?, iphone_seconds = ?, samsung_seconds = ?, 
                                        status = 'completed', entry_method = 'automatic'
                                    WHERE id = ?''',
                                 (datetime.now().isoformat(), iphone_seconds, samsung_seconds, session[0]))
                        
                        # Update person
                        c.execute('UPDATE persons SET currently_has_phones = 0, current_session_id = NULL WHERE id = ?',
                                 (session[6],))
                        
                        # Update phone set
                        c.execute('UPDATE phone_sets SET is_available = 1, current_session_id = NULL WHERE id = ?',
                                 (session[7],))
                        
                        conn.commit()
                        st.success(f"✅ Time recorded for {session[1]} (OCR method)")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Please enter valid durations in MM:SS format")
    else:
        st.info("No active sessions to record")

# Page: Reports
elif page == "📊 Reports":
    st.title("📊 Reports")
    
    c = conn.cursor()
    completed_sessions = c.execute('''
        SELECT p.name, p.person_id, s.iphone_seconds, s.samsung_seconds, 
               s.assigned_at, s.returned_at, s.entry_method
        FROM sessions s
        JOIN persons p ON s.person_id = p.id
        WHERE s.status = 'completed'
        ORDER BY s.returned_at DESC
    ''').fetchall()
    
    if completed_sessions:
        st.subheader(f"Completed Sessions ({len(completed_sessions)})")
        
        # Create DataFrame
        data = []
        for session in completed_sessions:
            data.append({
                'Person Name': session[0],
                'Person ID': session[1],
                'iPhone Duration': format_duration(session[2]),
                'Samsung Duration': format_duration(session[3]),
                'Assigned': datetime.fromisoformat(session[4]).strftime('%Y-%m-%d %I:%M %p'),
                'Returned': datetime.fromisoformat(session[5]).strftime('%Y-%m-%d %I:%M %p'),
                'Method': session[6] or 'manual'
            })
        
        df = pd.DataFrame(data)
        
        # Display table
        st.dataframe(df, use_container_width=True)
        
        # Export to CSV
        st.subheader("📥 Export Data")
        
        # Create CSV for export (simplified format)
        export_data = []
        for session in completed_sessions:
            export_data.append({
                'Person Name': session[0],
                'Person ID': session[1],
                'iPhone Duration': format_duration(session[2]),
                'Samsung Duration': format_duration(session[3])
            })
        
        export_df = pd.DataFrame(export_data)
        
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"phone_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        # Statistics
        st.subheader("📈 Statistics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Sessions", len(completed_sessions))
        
        with col2:
            total_iphone = sum(s[2] for s in completed_sessions if s[2])
            st.metric("Total iPhone Time", format_duration(total_iphone))
        
        with col3:
            total_samsung = sum(s[3] for s in completed_sessions if s[3])
            st.metric("Total Samsung Time", format_duration(total_samsung))
    else:
        st.info("No completed sessions yet")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("""
**Phone Task Tracker**  
Version 1.1.0  
Built with Streamlit
""")
