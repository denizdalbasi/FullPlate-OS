# importing
import sqlite3
import time


# Global variables
needs_onion = False



def init_db():
    conn = sqlite3.connect('kitchen.db')
    cursor = conn.cursor()

    # 1. Ingredient List Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredient_list (
            item TEXT PRIMARY KEY,
            stock_count INTEGER,
            critical_count INTEGER,
            units TEXT
        )
    ''')

    # 2. Recipe Amounts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recipe_amounts (
            item TEXT PRIMARY KEY,
            required_amount INTEGER,
            units TEXT
        )
    ''')

    # 3. Kitchen Tools Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mutfak_araclari (
            urun TEXT PRIMARY KEY,
            ekstrasi TEXT,
            durum_ana TEXT,
            durum_ekst TEXT
        )
    ''')

    # Table for Service Accompaniments
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS sides (
                urun TEXT PRIMARY KEY,
                eldeki_sayi INTEGER,
                birimler TEXT
            )
        ''')

    tools = [
        ('spatula', 'kasik', 'mevcut', 'mevcut'),
        ('tava', 'sahan', 'mevcut', 'mevcut'),
        ('kesme tahtasi', 'none', 'mevcut', 'none'),
        ('kase', 'derin tabak', 'none', 'none')
    ]

    cursor.executemany('INSERT OR IGNORE INTO mutfak_araclari VALUES (?,?,?,?)', tools)

    sides = [
        ('Bread', 5, 'slices'),
        ('Tea', 10, 'cups'),
        ('Cheese', 4, 'slices')
    ]
    cursor.executemany('INSERT OR IGNORE INTO sides VALUES (?,?,?)', sides)

    ingredients = [
        ('Tomato', 3, 1, 'piece'),
        ('Pepper', 5, 2, 'piece'),
        ('Egg', 10, 2, 'piece'),  # Increased egg seed for testing
        ('Oil', 10, 1, 'spoon'),
        ('Spices', 10, 1, 'teaspoon'),
        ('Onion', 5, 1, 'piece')
    ]
    cursor.executemany('INSERT OR IGNORE INTO ingredient_list VALUES (?,?,?,?)', ingredients)

    recipe = [
        ('Tomato', 3, 'piece'),
        ('Pepper', 5, 'piece'),
        ('Egg', 2, 'piece'),
        ('Oil', 2, 'spoon'),
        ('Spices', 1, 'teaspoon'),
        ('Onion', 1, 'piece')
    ]
    cursor.executemany('INSERT OR IGNORE INTO recipe_amounts VALUES (?,?,?)', recipe)

    conn.commit()
    conn.close()
    print("Database initialized (and persisted) successfully.")

# side functions
def slow_print(text, delay=0.8):
    print(text)
    time.sleep(delay)

def waste_management(items):
    # Check if the input is a list or just a single string
    if isinstance(items, list):
        for item in items:
            print(f"   [Waste Management] {item} waste has been separated.")
    else:
        print(f"   [Waste Management] {items} waste has been separated.")



def temizle(urun_listesi):
    print("\n--- Cleaning Process Started (Temizle) ---")

    # Are there items left in the list?)
    while urun_listesi:
        current_item = urun_listesi.pop(0)
        print(f"\nProcessing: {current_item['name']}")

        # Ingredient or Kitchen Tool?
        if current_item['type'] == 'mutfak gereci':
            print(f"   [Tool] Washing {current_item['name']} with a soapy sponge.")
            print(f"   [Tool] Rinsing {current_item['name']} with hot water.")

            # Is it dry?
            while True:
                is_dry = input(f"   Is {current_item['name']} dry? (yes/no): ").lower().strip()
                if is_dry == 'yes':
                    break
                else:
                    print("   Waiting for it to dry...")
                    time.sleep(1)  # Rinsing/Waiting simulation

        elif current_item['type'] == 'malzeme':
            print(f"   [Ingredient] Rinsing {current_item['name']} under cold water.")

            # Is it dry?
            while True:
                print(f"   [Ingredient] Drying {current_item['name']}...")
                is_dry = input(f"   Is {current_item['name']} dry? (yes/no): ").lower().strip()
                if is_dry == 'yes':
                    break
                else:
                    print("   Continuing to dry/drain...")

    print("\n--- Cleaning Complete. No items left in list. (End) ---")


def check_multiple_ingredients(conn, item_list):
    slow_print("\n--- Automatic Restocking System Active ---")
    cursor = conn.cursor()

    for item_name in item_list:
        # join with recipe_amounts to see exactly what the recipe requires
        cursor.execute('''
            SELECT il.stock_count, il.critical_count, ra.required_amount 
            FROM ingredient_list il
            JOIN recipe_amounts ra ON il.item = ra.item
            WHERE il.item = ?
        ''', (item_name,))

        result = cursor.fetchone()
        if not result:
            continue

        stock, critical, recipe_need = result

        # If stock is below critical OR below what the recipe needs
        if stock < critical or stock < recipe_need:
            new_stock = recipe_need + (critical * 2)

            cursor.execute('''
                UPDATE ingredient_list 
                SET stock_count = ? 
                WHERE item = ?
            ''', (new_stock, item_name))

            slow_print(f"   [Auto-Buy] {item_name} was low ({stock}). Restocked to {new_stock}.")
        else:
            print(f"   [+] {item_name} stock is sufficient ({stock}).")

    conn.commit()
    slow_print("\n--- Inventory Check Complete ---")

def buy_tool(tool_name):

    print(f"   [PURCHASE] {tool_name} is being ordered.")


def check_multiple_tools(conn,tool_list):
    print(f"--- Kitchen Tools Check Started for {len(tool_list)} items ---")


    cursor = conn.cursor()

    for tool_name in tool_list:
        cursor.execute('''
            SELECT urun, ekstrasi, durum_ana, durum_ekst 
            FROM mutfak_araclari 
            WHERE urun = ?
        ''', (tool_name,))
        result = cursor.fetchone()

        if not result:
            print(f"   [!] {tool_name} not found in tools database. Skipping.")
            continue

        item, extra, status_main, status_extra = result

        # Is the main tool available?
        if status_main == 'mevcut':
            print(f"   [+] {item} is available.")
        else:
            # Is the alternative available?
            if status_extra == 'mevcut':
                # Yes -> End
                print(f"   [+] {item} missing, but alternative ({extra}) is available.")
            else:
                print(f"   [-] Neither {item} nor {extra} are available!")

                #Buy the tool
                buy_tool(item)

                # UPDATE DB
                cursor.execute('''
                    UPDATE mutfak_araclari 
                    SET durum_ana = 'mevcut' 
                    WHERE urun = ?
                ''', (item,))
                print(f"   [DB Update] {item} status set to 'mevcut'.")

    conn.commit()
    print("--- Kitchen Tools Check Complete (End) ---")


def update_final_stock(conn, item_list):
    global needs_onion
    cursor = conn.cursor()
    for item in item_list:
        if item == "Onion" and not needs_onion:
            continue
        cursor.execute('''
            UPDATE ingredient_list
            SET stock_count = stock_count - (
                SELECT required_amount 
                FROM recipe_amounts 
                WHERE recipe_amounts.item = ingredient_list.item
            )
            WHERE item = ? 
              AND EXISTS (SELECT 1 FROM recipe_amounts WHERE item = ?)
        ''', (item, item))
    conn.commit()
    print("   [DB Update] Actual recipe amounts deducted from stock.")


def is_inventory_sufficient(conn, item_list):
    cursor = conn.cursor()
    insufficient_items = []

    for item_name in item_list:
        cursor.execute('''
            SELECT il.item, il.stock_count, ra.required_amount 
            FROM ingredient_list il
            JOIN recipe_amounts ra ON il.item = ra.item
            WHERE il.item = ?
        ''', (item_name,))

        result = cursor.fetchone()
        if result:
            name, stock, required = result
            if stock < required:
                insufficient_items.append(f"{name} (Need {required}, Have {stock})")
        else:
            insufficient_items.append(f"{item_name} (Missing from Database)")

    return insufficient_items


def check_sides_stock(conn):
    slow_print("--- Side Items Inventory Check in Progress ---")
    cursor = conn.cursor()

    # Check all side items (Bread, Tea, Cheese, etc.)
    cursor.execute("SELECT urun, eldeki_sayi FROM sides")
    sides = cursor.fetchall()

    for side_name, count in sides:
        # Define a critical threshold (e.g., if stock is less than 3)
        if count < 3:
            # Automatic restock: add 10 units to the current stock
            new_count = count + 10
            cursor.execute('''
                UPDATE sides 
                SET eldeki_sayi = ? 
                WHERE urun = ?
            ''', (new_count, side_name))

            print(f"   [Auto-Restock] {side_name} was low. Stock replenished. New count: {new_count}")
        else:
            print(f"   [+] {side_name} stock is sufficient ({count}).")

    conn.commit()
    slow_print("\n--- Sides Inventory Check Complete ---")

def preperation(conn):
    global needs_onion

    needs_onion = input("Do you want to include onions? (yes/no): ").lower().strip()

    slow_print("\n--- Starting Preparation Process ---")
    ingredients_to_check = ["Tomato", "Pepper", "Egg", "Onion"]

    # STEP 1: Kitchen Tools Check
    check_multiple_tools(conn, ["spatula", "tava", "kesme tahtasi", "kase"])

    # STEP 2: AUTOMATIC RESTOCK
    slow_print("Checking pantry and automatically restocking if necessary...")
    check_multiple_ingredients(conn, ingredients_to_check)

    # STEP 3: Sufficiency Check
    # Now that we've tried to buy more, do we have enough for the recipe?
    missing = is_inventory_sufficient(conn, ingredients_to_check)

    if missing:
        # If it's still missing, it means the restock logic didn't buy enough
        # or the item isn't in the database correctly.
        print("\n[!] CRITICAL ERROR: Even after restocking, we are missing supplies!")
        for m in missing:
            print(f"   - {m}")
        return False

    # STEP 4: Physical Prep (Only happens if the above passed)
    slow_print("[Pepper] Dicing peppers...")
    waste_management(["seeds", "white membranes"])

    has_skin = input("Is the tomato peelable/has skin? (yes/no): ").lower().strip()
    if has_skin == "yes":
        print("[Tomato] Cutting head and dicing into 1x1.5cm cubes.")
        waste_management("stems/trash")
    else:
        print("[Tomato] Scoring with an X and peeling gently.")
        waste_management("peels")

    if needs_onion:
        print("[Onion] Peeling, slicing half-moons, and dicing cubes.")
        waste_management("onion skins")

    print("[Egg] Cracking eggs one by one into a small bowl.")
    while True:
        shell_in = input("Did a piece of shell fall into the bowl? (yes/no): ").lower().strip()
        if shell_in == "yes":
            print("   Action: Removing the shell with a fork...")
        else:
            break
    waste_management("egg shells")

    print("--- Preparation Complete (End) ---")
    return True

def cooking(conn):
    global needs_onion
    slow_print("\n--- Starting Cooking Process (Pisirme Sureci) ---")

    print("Gathering materials: Spatula, Tomato, Pepper, Onion, Salt, Butter/Oil...")
    print("Gathering tools: Pan, Stove, Spatula, Fork...")
    print("Setting pan on the stove over medium heat.")

    # 1. Oil Selection
    oil_choice = input("Choose oil type - Olive Oil or Butter? (olive/butter): ").lower().strip()
    if oil_choice == "olive":
        print("Adding olive oil and a small piece of butter to the pan.")
    else:
        print("Adding 2-3 tablespoons of butter to the pan.")

    # 2. Heat Check
    while True:
        ready = input("Is the oil hot enough? (yes/no): ").lower().strip()
        if ready == "yes":
            break
        else:
            print("Waiting 20 seconds for the oil to heat...")
            time.sleep(1)  # Simulation

    # 3. Onion Cooking
    if needs_onion:
        print("Adding onions to the pan. Wait for 2 minutes.")
        while True:
            pink = input("Are the onions pink? (yes/no): ").lower().strip()
            if pink == "yes":
                break
            else:
                print("Cooking for 1 more minute...")

    # 4. Pepper Cooking
    print("Adding peppers to the pan.")
    while True:
        print("Stirring peppers and waiting 30 seconds...")
        soft = input("Are the peppers softened and edges slightly browned? (yes/no): ").lower().strip()
        if soft == "yes":
            break

    # 5. Tomato Cooking
    print("Adding diced tomatoes to the pan. Adding salt and spices.")
    print("Cooking for 5 minutes...")
    while True:
        homogenized = input("Has it reached a sauce-like, homogenized consistency? (yes/no): ").lower().strip()
        if homogenized == "yes":
            break
        else:
            print("Cooking for 1 more minute...")

    # 6. Egg Cooking
    print("Pouring the cracked eggs from the bowl into the pan.")
    print("Mixing with the tomato base and cooking for 2 minutes over low heat.")

    while True:
        perfect = input("Has it reached the desired consistency? (yes/no): ").lower().strip()
        if perfect == "yes":
            print("Turning off the stove.")
            update_final_stock(conn, ["Tomato", "Pepper", "Egg", "Onion"])
            break
        else:
            print("Taking it off the heat immediately so it doesn't overcook.")
            update_final_stock(conn, ["Tomato", "Pepper", "Egg", "Onion"])
            break

    print("Turning off the stove.")

    slow_print("\n--- Cooking Process Complete (End) ---")


def get_valid_input(prompt, validation_type):
    while True:
        answer = input(prompt).strip().lower()

        if validation_type == "1-10":
            if answer.isdigit() and 1 <= int(answer) <= 10:
                return answer
            print("   [!] Invalid input. Please enter a number between 1 and 10.")

        elif validation_type == "level":
            if answer in ["low", "normal", "high"]:
                return answer
            print("   [!] Invalid input. Please type 'low', 'normal', or 'high'.")

        elif validation_type == "yes_no":
            if answer in ["yes", "no"]:
                return answer
            print("   [!] Invalid input. Please type 'yes' or 'no'.")

        elif validation_type == "text":
            if answer:
                return answer
            print("   [!] Input cannot be empty.")


def feedback_process(conn, user_name):
    slow_print(f"\n--- Feedback System for {user_name} ---")

    # Mapping questions to their specific validation types
    questions = [
        ("1. Taste Score (1-10): ", "1-10"),
        ("2. Salt Level (Low/Normal/High): ", "level"),
        ("3. Cooking Consistency (Soggy/Dry): ", "text"),
        ("4. Visual Appeal Score (1-10): ", "1-10"),
        ("5. Freshness of Ingredients (Yes/No): ", "yes_no"),
        ("6. Recommendation Likelihood (Yes/No): ", "yes_no"),
        ("7. New Requests (Extra cheese, etc.): ", "text")
    ]

    cursor = conn.cursor()
    # Ensure table exists
    cursor.execute("CREATE TABLE IF NOT EXISTS feedback (user TEXT, q_id TEXT, ans TEXT)")

    for i, (q_text, v_type) in enumerate(questions, 1):
        valid_ans = get_valid_input(q_text, v_type)

        cursor.execute(
            "INSERT INTO feedback (user, q_id, ans) VALUES (?, ?, ?)",
            (user_name, f"q{i}", valid_ans)
        )
    conn.commit()
    slow_print("Feedback successfully saved to the database. Thank you!")

def serve(conn):
    print("\n--- Starting Service (Servis) ---")
    check_sides_stock(conn)

    # 1. Menemen Preparation and Plate
    print("Plating the Menemen...")

    # 2. Accompaniments
    cursor = conn.cursor()

    add_sides = input("Would you like side items (Bread, Tea, Cheese)? (yes/no): ").lower().strip()
    if add_sides == "yes":
        cursor.execute("SELECT urun, eldeki_sayi, birimler FROM sides")
        sides = cursor.fetchall()
        for side, count, unit in sides:
            if count > 0:
                print(f"   [Adding Side] {side} ({count} {unit} available)")
                cursor.execute("UPDATE sides SET eldeki_sayi = eldeki_sayi - 1 WHERE urun = ?", (side,))

    conn.commit()

    # 3. User Feedback Trigger
    user_name = input("Enter your name for the feedback session: ")
    feedback_process(conn, user_name)

    # 4. Final Cleaning
    print("\n--- Final Kitchen Cleanup ---")
    items_to_clean = [
        {'name': 'plate', 'type': 'mutfak gereci'},
        {'name': 'fork', 'type': 'mutfak gereci'},
        {'name': 'knife', 'type': 'mutfak gereci'},
        {'name': 'glass', 'type': 'mutfak gereci'},
        {'name': 'Tava (Pan)', 'type': 'mutfak gereci'},
        {'name': 'Spatula', 'type': 'mutfak gereci'}
    ]

    temizle(items_to_clean)

    print("--- Service Process Complete (End) ---")
if __name__ == "__main__":
    init_db()
    main_conn = sqlite3.connect('kitchen.db')

    try:
        while True:
            hungry = input("\nAre you hungry? (Yes/No) [Press 'q' to quit]: ").strip().lower()
            if hungry == "q": break

            if hungry == "yes":
                # Only cook if preparation was successful
                if preperation(main_conn):
                    cooking(main_conn)
                    serve(main_conn)
                    print("\nSimulation cycle complete!")

                else:
                    print("\nCycle aborted due to missing supplies.")
            elif hungry == "no":
                print("Please come when you are hungry")

    finally:
        main_conn.close()
