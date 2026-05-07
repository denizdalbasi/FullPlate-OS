from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import os
import sqlite3

# --- App Configuration ---
app = Flask(__name__)
# Secret key is essential for signing session cookies to prevent tampering
app.secret_key = 'menemen_secret' 

# --- Database Setup ---
# Dynamically locate the database file regardless of which OS/folder the app runs in
basedir = os.path.abspath(os.path.dirname(__file__))

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    db_path = os.path.join(basedir, 'kitchen.db')
    conn = sqlite3.connect(db_path)
    # Allows accessing columns by name (like row['item_name']) instead of index (row[0])
    conn.row_factory = sqlite3.Row
    return conn

# --- Authentication Middleware ---
def login_required(f):
    """
    Custom decorator to protect routes.
    If a user isn't logged in, they are booted back to the login page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes & Controllers ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles both displaying the login form and processing the login logic."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Simple Hardcoded Authentication 
        # (Note: In a production app, you'd check hashed passwords in a database)
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True  # Create a session cookie for the user
            return redirect(url_for('manager_dashboard'))
        else:
            return "Invalid Credentials. Please try again.", 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Clears the session and returns the user to the home page."""
    session.pop('logged_in', None)
    return redirect(url_for('index'))

# --- Manager Dashboard: Data Aggregation & Logic ---
@app.route('/manager')
@login_required  # Protects the route from unauthorized access
def manager_dashboard():
    conn = get_db_connection()
    
    # Fetch core metrics: finances, current stock levels, and recent activity
    finances = conn.execute('SELECT * FROM finances WHERE id = 1').fetchone()
    ingredients = conn.execute('SELECT * FROM ingredient_list').fetchall()
    logs = conn.execute('SELECT * FROM activity_logs ORDER BY id DESC LIMIT 50').fetchall()
    
    # 1. DATA FETCHING: Retrieve raw feedback entries
    raw_feedback = conn.execute('SELECT user, ans FROM feedback ORDER BY id DESC').fetchall()
    
    # 2. GROUPING LOGIC: Organizes multiple feedback entries under each unique user
    grouped_feedback = {}
    for row in raw_feedback:
        user = row['user']
        ans = row['ans']
        
        # CLEANING: Only process if the answer isn't empty, null, or the string 'none'
        if ans and str(ans).strip() and str(ans).lower() != 'none': 
            if user not in grouped_feedback:
                grouped_feedback[user] = []
            grouped_feedback[user].append(str(ans).strip())

    # 3. STRING FORMATTING: Convert lists of answers into a single readable string per user
    # Example: {'Hasan': ['Too spicy', 'Great eggs']} -> {'Hasan': 'Too spicy, Great eggs'}
    final_feedback = {user: ", ".join(answers) for user, answers in grouped_feedback.items()}

    conn.close()
    
    # Pass all processed data to the manager template
    return render_template('manager.html', 
                           finances=finances, 
                           ingredients=ingredients, 
                           logs=logs, 
                           feedbacks=final_feedback)


# --- Inventory Management: Restocking & Financial Impact ---
@app.route('/restock_item/<item_name>', methods=['POST'])
@login_required
def restock_item(item_name):
    refill_cost = 10.00  # Fixed cost for inventory purchase
    conn = get_db_connection()

    # Increase stock count by a bulk amount (10 units)
    conn.execute('UPDATE ingredient_list SET stock_count = stock_count + 10 WHERE item = ?', (item_name,))

    # FINANCIAL UPDATE: Log the expense and recalculate profit in real-time
    conn.execute('''
        UPDATE finances
        SET total_costs = total_costs + ?,
            profit = total_revenue - (total_costs + ?)
        WHERE id = 1
    ''', (refill_cost, refill_cost))

    # AUDIT LOG: Record this transaction in the activity history
    conn.execute('''
        INSERT INTO activity_logs (activity_text, amount, type)
        VALUES (?, ?, ?)
    ''', (f"Restocked {item_name}", -refill_cost, "expense"))

    conn.commit()
    conn.close()
    return redirect(url_for('manager_dashboard'))


# --- Public Interface: Stock Availability & Order Validation ---
@app.route('/')
def index():
    """Home page: Clears old cook sessions and shows current ingredient availability."""
    session.pop('step', None)
    session.pop('needs_onion', None)

    conn = get_db_connection()
    ingredients = conn.execute('SELECT * FROM ingredient_list').fetchall()
    conn.close()
    return render_template('index.html', ingredients=ingredients)


@app.route('/preparation', methods=['GET', 'POST'])
def preparation():
    """The 'Gatekeeper' route: Validates stock before allowing the user to start cooking."""
    if request.method == 'POST':
        # Capture user customization choices
        needs_onion = request.form.get('onion') == 'yes'
        needs_pepper = request.form.get('pepper') == 'yes'
        needs_bread = request.form.get('bread') == 'yes'
        
        conn = get_db_connection()
        # Create a dictionary for easy stock lookup
        items = conn.execute('SELECT item, stock_count FROM ingredient_list').fetchall()
        stock = {row['item']: row['stock_count'] for row in items}
        conn.close()

        # VALIDATION LOGIC: Business rules for a valid Menemen
        # Core ingredients check (Hard Requirement)
        if stock.get('Tomato', 0) < 3 or stock.get('Egg', 0) < 2:
            return "Out of core ingredients! Please order any other day.", 400

        # Optional ingredients check (Soft Requirement based on choice)
        if needs_onion and stock.get('Onion', 0) < 1:
            return "Out of onions! Please go back and choose no onions or restock.", 400
        
        if needs_pepper and stock.get('Pepper', 0) < 2:
            return "Out of peppers!", 400
            
        if needs_bread and stock.get('Bread', 0) < 1:
            return "Out of bread!", 400

        # SESSION STORAGE: Save validated choices to follow user through the cooking steps
        session['needs_onion'] = needs_onion
        session['needs_pepper'] = needs_pepper
        session['needs_bread'] = needs_bread
        session['selected_spice'] = request.form.get('spice')
        session['step'] = 1
        return redirect(url_for('cooking'))
        
    return render_template('preparation.html')


# --- Step-by-Step Cooking Logic & Transaction Processing ---
@app.route('/cooking', methods=['GET', 'POST'])
def cooking():
    """Manages the multi-step cooking process and finalizes the transaction."""
    # Safety Check: If user tries to access /cooking without prep, send them back
    if 'step' not in session:
        return redirect(url_for('preparation'))

    step = session.get('step')

    if request.method == 'POST':
        # Increment progress
        session['step'] = step + 1

        # Check if the user has completed the final cooking step (Step 5)
        if session['step'] > 5:
            conn = get_db_connection()
            sale_price = 20.00  # Base price for standard Menemen

            # 1. INVENTORY REDUCTION & DYNAMIC PRICING:
            # Check for Bread (Increases price and reduces specific stock)
            if session.get('needs_bread'):
                sale_price += 5.00
                conn.execute("UPDATE ingredient_list SET stock_count = stock_count - 1 WHERE item = 'Bread'")

            # Core Ingredient Deduction (3 Tomatoes, 2 Eggs)
            conn.execute("UPDATE ingredient_list SET stock_count = stock_count - 3 WHERE item = 'Tomato'")
            conn.execute("UPDATE ingredient_list SET stock_count = stock_count - 2 WHERE item = 'Egg'")

            # Optional Ingredient Deduction (Pepper and Onion)
            if session.get('needs_pepper'):
                conn.execute("UPDATE ingredient_list SET stock_count = stock_count - 2 WHERE item = 'Pepper'")

            if session.get('needs_onion'):
                conn.execute("UPDATE ingredient_list SET stock_count = stock_count - 1 WHERE item = 'Onion'")

            # 2. REVENUE UPDATE: Update total revenue and calculate new profit
            conn.execute('''
                UPDATE finances
                SET total_revenue = total_revenue + ?,
                    profit = (total_revenue + ?) - total_costs
                WHERE id = 1
            ''', (sale_price, sale_price))

            # 3. SALES LOGGING: Create a detailed entry for the manager to see
            log_msg = f"Sold Menemen {'+ Bread' if session.get('needs_bread') else ''} ({session.get('selected_spice')})"
            conn.execute("INSERT INTO activity_logs (activity_text, amount, type) VALUES (?, ?, ?)",
                         (log_msg, sale_price, "sale"))

            conn.commit()
            conn.close()
            return redirect(url_for('serve'))

        # If cooking is still in progress, refresh the page for the next step
        return redirect(url_for('cooking'))

    # --- GET REQUEST LOGIC: Step Descriptions ---
    # Dynamic text based on user choices from the preparation phase
    steps_logic = {
        1: "Preheating the stove. Adding a knob of butter and a drizzle of olive oil...",
        2: "Cooking the finely diced onions until translucent..." if session.get('needs_onion') else "Skipping onions per your choice. Moving to the next base...",
        3: "Adding the peppers. Stir-frying until tender..." if session.get('needs_pepper') else "No peppers for this order. Letting the base flavors meld...",
        4: "Folding in the juicy tomatoes and signature spices. Simmering...",
        5: "Pouring in the whisked eggs for a creamy finish..."
    }

    current_text = steps_logic.get(session['step'], "Cooking complete!")
    return render_template('cooking.html', step_text=current_text)


@app.route('/serve')
def serve():
    """Simple completion page after transaction is finalized."""
    return render_template('serve.html')


# --- Feedback System: Collecting User Insights ---
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    """Allows users to submit feedback which is then grouped in the Manager Dashboard."""
    spice = session.get('selected_spice')

    # Sentiment Logic: Pre-fill specific text based on user choices
    bonus_text = ""
    if spice == 'chili':
        bonus_text = "The chili flakes were amazing! 5 stars for the heat!"
    elif spice == 'none':
        bonus_text = "A bit plain, but okay."

    if request.method == 'POST':
        user = request.form.get('user_name')
        # Map various feedback questions to their values
        feedback_data = {
            'q1': request.form.get('q1'),
            'q2': request.form.get('q2'),
            'q3': request.form.get('q3'),
            'q5': request.form.get('q5'),
            'q7': request.form.get('q7')
        }

        conn = get_db_connection()
        cursor = conn.cursor()
        # Insert each feedback point as a separate row for granular reporting
        for q_id, ans in feedback_data.items():
            cursor.execute(
                "INSERT INTO feedback (user, q_id, ans) VALUES (?, ?, ?)",
                (user, q_id, str(ans))
            )
        conn.commit()
        conn.close()

        return redirect(url_for('index'))
        
    return render_template('feedback.html', bonus_text=bonus_text)

# --- Bulk Inventory Management: Reset & Reorder ---
@app.route('/restock', methods=['POST'])
@login_required # Suggested: Only the manager should be able to trigger a $75 expense!
def restock():
    """
    Simulates a bulk delivery service. 
    Resets all inventory to full capacity for a flat delivery fee.
    """
    # Define the fixed cost for a full pantry refill
    bulk_delivery_cost = 75.00

    conn = get_db_connection()

    # 1. INVENTORY RESET: Set all stock counts to a baseline of 20 units
    conn.execute('UPDATE ingredient_list SET stock_count = 20')

    # 2. FINANCIAL IMPACT: 
    # Log the expense by increasing total_costs and decreasing the net profit
    conn.execute('''
        UPDATE finances
        SET total_costs = total_costs + ?,
            profit = total_revenue - (total_costs + ?)
        WHERE id = 1
    ''', (bulk_delivery_cost, bulk_delivery_cost))

    # 3. AUDIT TRAIL: (Suggested addition for your project)
    conn.execute('''
        INSERT INTO activity_logs (activity_text, amount, type)
        VALUES (?, ?, ?)
    ''', ("Bulk Delivery Received", -bulk_delivery_cost, "expense"))

    conn.commit()
    conn.close()

    # Return the manager to the dashboard to see the refreshed stock and updated finances
    return redirect(url_for('manager_dashboard'))


# --- Application Entry Point ---
if __name__ == '__main__':
    # debug=True allows the server to auto-reload when you save changes
    # and provides an interactive debugger in the browser if an error occurs.
    app.run(debug=True)