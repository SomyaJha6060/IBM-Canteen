from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
from supabase import create_client
import json
import secrets
from flask import session

SUPABASE_URL= 'Place your Supabase url here'
SUPABASE_KEY = 'Place your Supabase key here'

app = Flask(__name__)
# SQLite database setup
app.secret_key = secrets.token_hex(16)  # Generates a random 32-character hex key
DATABASE = 'users.db'
SEATS_DB = 'seats.db'
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_seats_db():
    conn = sqlite3.connect(SEATS_DB)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Supabase client
def connect_to_supabase():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase

# not use this function
def init_db():
    try:
        conn = sqlite3.connect(SEATS_DB)
        cursor = conn.cursor()
        # Create tables for seats and time slots if they don't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_slot TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time_slot_id INTEGER,
                seat_number INTEGER,
                available BOOLEAN,
                FOREIGN KEY (time_slot_id) REFERENCES time_slots (id)
            )
        ''')
        # Insert time slots and seats if they are not present
        cursor.execute('SELECT COUNT(*) FROM time_slots')
        if cursor.fetchone()[0] == 0:
            time_slots = [
                ('9:00 AM',),
                ('10:00 AM',),
                ('11:00 AM',),
                ('12:00 PM',),
                ('1:00 PM',),
                ('2:00 PM',),
                ('3:00 PM',),
                ('4:00 PM',),
                ('5:00 PM',),
                ('6:00 PM',),
                ('7:00 PM',),
                ('8:00 PM',)
            ]
            cursor.executemany('INSERT INTO time_slots (time_slot) VALUES (?)', time_slots)
            # Insert 10 seats for each time slot
            cursor.execute('SELECT id FROM time_slots')
            time_slot_ids = cursor.fetchall()
            for time_slot_id in time_slot_ids:
                for seat_number in range(1, 11):  # 10 seats per time slot
                    cursor.execute('''
                        INSERT INTO seats (time_slot_id, seat_number, available)
                        VALUES (?, ?, ?)
                    ''', (time_slot_id[0], seat_number, True))  # Set all seats as available initially
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {e}")
# Run the initialization function when the app starts
#init_db()

# Main page (login or sign up)
@app.route('/')
def main_page():
    return render_template('main_page.html')

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    conn = connect_to_supabase()
    if request.method == 'POST':
        # Get form data
        full_name = request.form['fullName']
        w3id = request.form['w3id']
        manager_email = request.form['managerEmail']
        password = request.form['newPassword']
        
        # Validate IBM email addresses
        if not w3id.endswith('@ibm.com'):
            return render_template('signup.html', error_message="Please enter a valid IBM email address (@ibm.com)")
        
        if not manager_email.endswith('@ibm.com'):
            return render_template('signup.html', error_message="Please enter a valid IBM manager email address (@ibm.com)")
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        try:
            # Insert new employee with all required fields
            response = conn.table("employee").insert({
                "full_name": full_name,
                "w3id": w3id,
                "manager_email": manager_email,
                "password": hashed_password
            }).execute()
            
            return redirect(url_for('login'))
        except Exception as e:
            # Handle any database errors (like duplicate w3id)
            return render_template('signup.html', error_message="Registration failed. Email might already be registered.")
            
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = connect_to_supabase()
    if request.method == 'POST':
        w3id = request.form['w3id']
        password = request.form['password']
        
        # Validate IBM email address
        if not w3id.endswith('@ibm.com'):
            return render_template('login.html', error_message="Please enter a valid IBM email address (@ibm.com)")
        
        try:
            # Query using w3id instead of username
            response = conn.table('employee').select("*").eq("w3id", w3id).execute()
            user_data = response.data
            
            if user_data and check_password_hash(user_data[0]['password'], password):
                session['e_id'] = user_data[0]['e_id']
                return redirect(url_for('homepage'))
            else:
                return render_template('login.html', error_message="Invalid IBM w3id or password.")
                
        except Exception as e:
            return render_template('login.html', error_message="Login failed. Please try again.")
            
    return render_template('login.html')


# Homepage
@app.route('/homepage')
def homepage():
    return render_template('homepage.html')

# Logout
@app.route('/logout')
def logout():
    return redirect(url_for('login'))

# Route to display available time slots for booking seats
@app.route('/book-seats', methods=['GET', 'POST'])
def book_seats():
    conn = connect_to_supabase()
    if 'e_id' not in session:
        return redirect(url_for('login'))

    e_id = session['e_id']

    if request.method == 'GET':
        try:
            # Fetch all time slots from the time_slot table
            response = conn.table("time_slot").select("*").execute()
            if response.data:
                return render_template('book_seats.html', time_slots=response.data, seats=None)
            else:
                return render_template('book_seats.html', error_message="No time slots available")
        except Exception as e:
            print(f"Error fetching time slots: {e}")
            return render_template('book_seats.html', error_message="Error loading time slots")

    if request.method == 'POST' and 'time_slot_id' in request.form:
        time_slot_id = request.form['time_slot_id']
        
        if 'seat_number' not in request.form:
            try:
                # Get already booked seats for this time slot
                booked_seats = conn.table("seat").select("seat_number").eq("t_id", time_slot_id).execute()
                booked_seat_numbers = {seat['seat_number'] for seat in booked_seats.data}
                
                # Generate all possible seats (1-36)
                all_seats = []
                for seat_num in range(1, 37):
                    all_seats.append({
                        "s_id": f"{time_slot_id}_{seat_num}",  # temporary ID for display
                        "seat_number": seat_num,
                        "seat_status": seat_num in booked_seat_numbers  # True if booked, False if available
                    })
                
                time_slot_response = conn.table("time_slot").select("*").eq("t_id", time_slot_id).single().execute()
                
                return render_template('book_seats.html', 
                                    seats=all_seats,
                                    time_slot_id=time_slot_id,
                                    time_slot=time_slot_response.data['timeslot'] if time_slot_response.data else None)
            except Exception as e:
                print(f"Error fetching seats: {e}")
                return render_template('book_seats.html', error_message=f"Error loading seats: {str(e)}")
        else:
            # Handle seat booking
            seat_number = int(request.form['seat_number'].split('_')[1])  # Extract seat number from temporary ID
            try:
                # if seat is already booked
                seat_check = conn.table("seat").select("*").eq("t_id", time_slot_id).eq("seat_number", seat_number).execute()
                
                if not seat_check.data:
                    # Create new seat entry
                    seat_data = {
                        "t_id": time_slot_id,
                        "seat_number": seat_number,
                        "booking_time": datetime.now().isoformat(),
                        "e_id": e_id
                    }
                    seat_response = conn.table("seat").insert(seat_data).execute()
                    
                    # Store booking details in session for thank you page
                    time_slot_info = conn.table("time_slot").select("timeslot").eq("t_id", time_slot_id).single().execute()
                    
                    session['booked_seat_number'] = seat_number
                    session['booked_time_slot'] = time_slot_info.data['timeslot']
                    
                    return redirect(url_for('thank_you'))
                else:
                    return render_template('book_seats.html', error_message="Seat is already booked")
            except Exception as e:
                print(f"Error booking seat: {e}")
                return render_template('book_seats.html', error_message="Error booking seat")

    return render_template('book_seats.html', error_message="Invalid request")

@app.route('/available-seats', methods=['POST'])
def available_seats():
    time_slot_id = request.form['time_slot_id']
    conn = sqlite3.connect('seats.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT seat_number, available
        FROM seats
        WHERE time_slot_id = ?
    ''', (time_slot_id,))
    seats = cursor.fetchall()
    conn.close()
    return render_template('available_seats.html', seats=seats, time_slot_id=time_slot_id)
# Route for 'my bookings' page (empty for now)
@app.route('/thank_you')
def thank_you():
    # booking details from the session or database
    seat_number = session.get('booked_seat_number')
    time_slot = session.get('booked_time_slot')
    booking_date = datetime.now().strftime("%B %d, %Y")
    
    return render_template('thank_you.html', 
                         seat_number=seat_number,
                         time_slot=time_slot,
                         booking_date=booking_date)


@app.route('/my-bookings', methods=['GET'])
def my_bookings():
    e_id = session.get('e_id')
    
    if e_id:
        conn = connect_to_supabase()
        try:
            # fetch bookings from seat table along with time slot information
            response = conn.table('seat').select(
                "s_id",
                "seat_number",
                "booking_time",
                "time_slot(timeslot)"  # Join with time_slot table
            ).eq("e_id", e_id).execute()

            bookings = []
            for booking in response.data:
                # Convert ISO timestamp to datetime object
                booking_datetime = datetime.fromisoformat(booking['booking_time'].replace('Z', '+00:00'))
                
                bookings.append({
                    'booking_date': booking_datetime.strftime('%B %d, %Y'),
                    'booking_time': booking_datetime.strftime('%I:%M %p'),
                    'seat_number': booking['seat_number'],
                    'time_slot': booking['time_slot']['timeslot'] if booking['time_slot'] else 'N/A'
                })

            return render_template('my_bookings.html', bookings=bookings)
            
        except Exception as e:
            print(f"Error fetching bookings: {e}")
            return render_template('my_bookings.html', error_message="Error fetching bookings")
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)