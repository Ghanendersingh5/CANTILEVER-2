import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry  # Provides a nice, interactive date picker
import sqlite3
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # To embed Matplotlib plots in Tkinter
import os

# --- Database Management ---
class ExpenseTrackerDB:
    """
    Manages all database operations for the Expense Tracker.
    Utilizes SQLite for persistent, file-based data storage.
    """
    def __init__(self, db_name="expense_tracker.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        if self.conn: # Only proceed if connection was successful
            self._create_tables()

    def _connect(self):
        """Establishes connection to the SQLite database. Handles connection errors."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            # print(f"Connected to database: {self.db_name}") # Optional: for initial debugging
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect to database: {e}")
            self.conn = None # Explicitly set to None if connection failed

    def _create_tables(self):
        """Creates the 'expenses' and 'categories' tables if they don't already exist."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category_id INTEGER,
                    date TEXT NOT NULL,
                    description TEXT,
                    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
                )
            """)
            self.conn.commit()
            # print("Tables checked/created.") # Optional: for initial debugging
            self._insert_default_categories() # Ensure essential categories are present
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to create tables: {e}")

    def _insert_default_categories(self):
        """Inserts a set of predefined categories into the database if they don't exist."""
        default_categories = ["Food", "Transport", "Utilities", "Rent", "Shopping", "Entertainment", "Salary", "Other"]
        for category in default_categories:
            try:
                self.cursor.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (category,))
            except sqlite3.Error as e:
                print(f"Error inserting default category '{category}': {e}") # Debugging categories
        self.conn.commit()


    def _get_category_id(self, category_name):
        """Helper to retrieve a category ID by its name."""
        self.cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_expense(self, amount, category_name, date, description=""):
        """Adds a new expense record to the database."""
        if not self.conn: return False # Guard against disconnected DB

        try:
            category_id = self._get_category_id(category_name)
            if category_id is None:
                messagebox.showerror("Error", f"Category '{category_name}' not found. Please select a valid category.")
                return False

            self.cursor.execute(
                "INSERT INTO expenses (amount, category_id, date, description) VALUES (?, ?, ?, ?)",
                (amount, category_id, date, description)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to add expense: {e}")
            return False

    def get_expenses(self, start_date=None, end_date=None, category_name=None):
        """Retrieves expenses from the database, with optional date and category filters."""
        if not self.conn: return []

        query = """
            SELECT e.id, e.amount, c.name, e.date, e.description
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("e.date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("e.date <= ?")
            params.append(end_date)
        if category_name:
            conditions.append("c.name = ?")
            params.append(category_name)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY e.date DESC" # Always order by date for consistency

        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to retrieve expenses: {e}")
            return []
    
    def get_expense_by_id(self, expense_id):
        """Retrieves a single expense record by its unique ID."""
        if not self.conn: return None
        try:
            self.cursor.execute("""
                SELECT e.id, e.amount, c.name, e.date, e.description
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.id = ?
            """, (expense_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to retrieve expense by ID: {e}")
            return None

    def update_expense(self, expense_id, amount, category_name, date, description=""):
        """Updates an existing expense record in the database."""
        if not self.conn: return False

        try:
            category_id = self._get_category_id(category_name)
            if category_id is None:
                messagebox.showerror("Error", f"Category '{category_name}' not found. Please select a valid category.")
                return False

            self.cursor.execute(
                "UPDATE expenses SET amount = ?, category_id = ?, date = ?, description = ? WHERE id = ?",
                (amount, category_id, date, description, expense_id)
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update expense: {e}")
            return False

    def delete_expense(self, expense_id):
        """Deletes a specific expense record from the database by its ID."""
        if not self.conn: return False
        try:
            self.cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete expense: {e}")
            return []

    def get_categories(self):
        """Retrieves a list of all available category names."""
        if not self.conn: return []
        try:
            self.cursor.execute("SELECT name FROM categories ORDER BY name ASC")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to retrieve categories: {e}")
            return []

    def get_spending_by_category(self, start_date=None, end_date=None):
        """Calculates the total spending for each category within an optional date range."""
        if not self.conn: return {}

        query = """
            SELECT c.name, SUM(e.amount)
            FROM expenses e
            JOIN categories c ON e.category_id = c.id
        """
        conditions = []
        params = []

        if start_date:
            conditions.append("e.date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("e.date <= ?")
            params.append(end_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " GROUP BY c.name ORDER BY c.name ASC" # Group and order for consistent reports

        try:
            self.cursor.execute(query, params)
            return {row[0]: row[1] for row in self.cursor.fetchall()}
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to get spending by category: {e}")
            return {}

    def close(self):
        """Closes the database connection. Important for resource management."""
        if self.conn:
            self.conn.close()
            # print("Database connection closed.") # Optional: for initial debugging


# --- Tkinter GUI Application ---
class ExpenseTrackerApp:
    """
    The main Tkinter application for the Expense Tracker.
    Handles all GUI elements, user interaction, and integrates with the database.
    """
    def __init__(self, master):
        self.master = master
        master.title("Expense Tracker")
        master.geometry("1000x700")  # Initial window size, can be resized
        master.resizable(True, True) # Allow window resizing

        self.db = ExpenseTrackerDB()

        # Apply basic global UI styling for a consistent look
        master.option_add('*Font', 'Inter 10')
        master.option_add('*Button.pady', 5)
        master.option_add('*Button.padx', 10)
        master.option_add('*Entry.relief', 'flat')
        master.option_add('*Entry.bg', '#e0e0e0') # Light grey background for entries
        master.option_add('*Button.fg', 'white') # White text on colored buttons
        
        # --- Configure Treeview selection style ---
        # The 'clam' theme often provides better control over styling than 'default'
        style = ttk.Style()
        style.theme_use('clam') 
        
        # Define a custom style for the Treeview rows
        style.configure("Custom.Treeview",
                        background="#f0f0f0", # Default row background
                        foreground="black", # Default text color
                        rowheight=25, # Optional: adjust row height for better visual separation
                        fieldbackground="#f0f0f0") # Ensure field background matches row background

        # Define how the selected state maps to colors for "Custom.Treeview"
        style.map('Custom.Treeview',
                  background=[('selected', '#0078D7')], # Strong blue for selection
                  foreground=[('selected', 'white')]) # White text on selection


        # Store references to main frames for show/hide functionality
        self.input_frame = None
        self.button_frame = None
        self.list_frame = None
        self.chart_frame = None # This will be created/destroyed dynamically

        self.create_widgets()
        self.update_expense_list() # Populate the expense table on startup
        self.load_categories_to_dropdown() # Populate the category selection dropdown

    def create_widgets(self):
        """Constructs and arranges all Tkinter widgets (input fields, buttons, table)."""
        # --- Input Frame for new/editing expenses ---
        self.input_frame = tk.LabelFrame(self.master, text="New Expense / Edit Expense", padx=15, pady=15, bd=2, relief="groove")
        self.input_frame.pack(fill=tk.X, padx=10, pady=10)

        # Amount Input
        tk.Label(self.input_frame, text="Amount:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.amount_entry = tk.Entry(self.input_frame, width=20)
        self.amount_entry.grid(row=0, column=1, pady=5, padx=5)

        # Category Dropdown
        tk.Label(self.input_frame, text="Category:").grid(row=0, column=2, sticky="w", pady=5, padx=5)
        self.category_var = tk.StringVar(self.master)
        self.category_dropdown = ttk.Combobox(self.input_frame, textvariable=self.category_var, width=17, state="readonly")
        self.category_dropdown.grid(row=0, column=3, pady=5, padx=5)

        # Date Picker
        tk.Label(self.input_frame, text="Date (YYYY-MM-DD):").grid(row=0, column=4, sticky="w", pady=5, padx=5)
        self.date_entry = DateEntry(self.input_frame, width=15, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.date_entry.grid(row=0, column=5, pady=5, padx=5)

        # Description Input
        tk.Label(self.input_frame, text="Description:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.description_entry = tk.Entry(self.input_frame, width=60)
        self.description_entry.grid(row=1, column=1, columnspan=5, sticky="ew", pady=5, padx=5)

        # --- Action Buttons Frame ---
        self.button_frame = tk.Frame(self.master, padx=10, pady=5)
        self.button_frame.pack(fill=tk.X, pady=5)

        # Using consistent button width and distinct colors for better UX
        button_width = 15
        tk.Button(self.button_frame, text="Add Expense", command=self.add_expense_gui, width=button_width, bg='#2196F3').pack(side=tk.LEFT, padx=5)  # Blue
        tk.Button(self.button_frame, text="Update Selected", command=self.update_expense_gui, width=button_width, bg='#FFC107').pack(side=tk.LEFT, padx=5) # Amber
        tk.Button(self.button_frame, text="Delete Selected", command=self.delete_expense_gui, width=button_width, bg='#F44336').pack(side=tk.LEFT, padx=5) # Red
        tk.Button(self.button_frame, text="Clear Fields", command=self.clear_entries, width=button_width, bg='#9E9E9E').pack(side=tk.LEFT, padx=5) # Grey
        tk.Button(self.button_frame, text="Generate Report", command=self.generate_report_gui, width=button_width, bg='#4CAF50').pack(side=tk.LEFT, padx=5) # Green


        # --- Expense List Display (using Treeview for tabular data) ---
        self.list_frame = tk.LabelFrame(self.master, text="Expenses List", padx=15, pady=10, bd=2, relief="groove")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("ID", "Amount", "Category", "Date", "Description")
        self.expense_tree = ttk.Treeview(self.list_frame, columns=columns, show="headings", style="Custom.Treeview") # Apply custom style here
        self.expense_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure column headings and widths
        for col in columns:
            self.expense_tree.heading(col, text=col, anchor=tk.W)
        
        self.expense_tree.column("ID", width=50, stretch=tk.NO)
        self.expense_tree.column("Amount", width=80, stretch=tk.NO)
        self.expense_tree.column("Category", width=100, stretch=tk.NO)
        self.expense_tree.column("Date", width=100, stretch=tk.NO)
        self.expense_tree.column("Description", width=250, stretch=tk.YES) # Description expands to fill space

        # Add a scrollbar to the Treeview
        scrollbar = ttk.Scrollbar(self.list_frame, orient="vertical", command=self.expense_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.expense_tree.config(yscrollcommand=scrollbar.set)

        # Bind row selection in Treeview to load data into input fields
        self.expense_tree.bind("<<TreeviewSelect>>", self.load_selected_expense_to_entries)

        # --- Status Message Label at the bottom ---
        self.status_label = tk.Label(self.master, text="", fg="blue", padx=10, pady=5, wraplength=900)
        self.status_label.pack(fill=tk.X, pady=5)

    def _show_status_message(self, message, is_error=False):
        """Displays a status message to the user in the GUI, changing color for errors."""
        self.status_label.config(text=message, fg="red" if is_error else "blue")

    def load_categories_to_dropdown(self):
        """Fetches categories from the DB and populates the category dropdown menu."""
        categories = self.db.get_categories()
        self.category_dropdown['values'] = categories
        if categories:
            self.category_var.set(categories[0]) # Set the first category as default selection

    def _validate_input(self, amount_str, category_name, date_str):
        """Performs basic validation on the expense input fields."""
        if not amount_str.strip():
            return False, "Amount cannot be empty."
        try:
            amount = float(amount_str)
            if amount <= 0:
                return False, "Amount must be a positive number."
        except ValueError:
            return False, "Amount must be a valid number (e.g., 100 or 50.75)."

        if not category_name.strip():
            return False, "Category cannot be empty. Please select one."

        if not date_str.strip():
            return False, "Date cannot be empty."
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d') # Validate YYYY-MM-DD format
        except ValueError:
            return False, "Date format must be YYYY-MM-DD."
        
        return True, "" # Validation successful

    def add_expense_gui(self):
        """Handles adding a new expense, triggered by the 'Add Expense' button."""
        amount_str = self.amount_entry.get().strip()
        category_name = self.category_var.get().strip()
        date_str = self.date_entry.get().strip()
        description = self.description_entry.get().strip()

        is_valid, message = self._validate_input(amount_str, category_name, date_str)
        if not is_valid:
            messagebox.showerror("Input Error", message)
            self._show_status_message(message, is_error=True)
            return

        amount = float(amount_str)

        if self.db.add_expense(amount, category_name, date_str, description):
            self.update_expense_list() # Refresh the displayed list
            self.clear_entries()      # Clear input fields for next entry
            self._show_status_message("Expense added successfully!")
        else:
            self._show_status_message("Failed to add expense.", is_error=True)

    def update_expense_gui(self):
        """Handles updating a selected expense, triggered by the 'Update Selected' button."""
        selected_item = self.expense_tree.focus() # Get ID of the selected row
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select an expense from the list to update.")
            self._show_status_message("No expense selected for update.", is_error=True)
            return

        # Extract expense ID from the selected row's values (first column)
        expense_id = self.expense_tree.item(selected_item)['values'][0]

        amount_str = self.amount_entry.get().strip()
        category_name = self.category_var.get().strip()
        date_str = self.date_entry.get().strip()
        description = self.description_entry.get().strip()

        is_valid, message = self._validate_input(amount_str, category_name, date_str)
        if not is_valid:
            messagebox.showerror("Input Error", message)
            self._show_status_message(message, is_error=True)
            return

        amount = float(amount_str)

        if messagebox.askyesno("Confirm Update", "Are you sure you want to update this expense?"):
            if self.db.update_expense(expense_id, amount, category_name, date_str, description):
                self.update_expense_list()
                self.clear_entries()
                self._show_status_message(f"Expense ID {expense_id} updated successfully!")
            else:
                self._show_status_message(f"Failed to update expense ID {expense_id}.", is_error=True)

    def delete_expense_gui(self):
        """Handles deleting a selected expense, triggered by the 'Delete Selected' button."""
        selected_item = self.expense_tree.focus()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select an expense from the list to delete.")
            self._show_status_message("No expense selected for deletion.", is_error=True)
            return

        # Extract expense ID from the selected row
        expense_id = self.expense_tree.item(selected_item)['values'][0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete expense ID {expense_id}?"):
            if self.db.delete_expense(expense_id):
                self.update_expense_list()
                self.clear_entries() # Clear fields after deletion
                self._show_status_message(f"Expense ID {expense_id} deleted successfully!")
            else:
                self._show_status_message(f"Failed to delete expense ID {expense_id}.", is_error=True)

    def clear_entries(self):
        """Clears all input fields and resets selections."""
        self.amount_entry.delete(0, tk.END)
        self.description_entry.delete(0, tk.END)
        self.date_entry.set_date(datetime.date.today()) # Reset date to current day
        self.load_categories_to_dropdown()             # Reset dropdown to default category
        

    def update_expense_list(self):
        """Fetches all expenses from the database and repopulates the Treeview display."""
        # Clear all existing items in the Treeview
        for item in self.expense_tree.get_children():
            self.expense_tree.delete(item)

        expenses = self.db.get_expenses()
        if expenses:
            for expense in expenses:
                self.expense_tree.insert("", tk.END, values=expense)
            self._show_status_message(f"Loaded {len(expenses)} expenses.")
        else:
            self._show_status_message("No expenses recorded yet.")

    def load_selected_expense_to_entries(self, event):
        """Loads details of the selected expense from the Treeview into the input fields."""
        selected_item = self.expense_tree.focus()
        if selected_item:
            values = self.expense_tree.item(selected_item)['values']
            # values are (ID, Amount, Category, Date, Description)
            self.clear_entries() # Clear current fields first
            self.amount_entry.insert(0, str(values[1]))  # Amount
            self.category_var.set(values[2])           # Category
            self.date_entry.set_date(values[3])         # Date
            self.description_entry.insert(0, values[4]) # Description
            self._show_status_message(f"Expense ID {values[0]} loaded for editing.")

    def show_expense_list_view(self):
        """Shows the expense input/buttons/list and hides the report view."""
        # Restore packing of input, button, and list frames
        self.input_frame.pack(fill=tk.X, padx=10, pady=10)
        self.button_frame.pack(fill=tk.X, pady=5)
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Destroy the chart frame to remove it completely
        if self.chart_frame:
            self.chart_frame.destroy()
            self.chart_frame = None # Clear reference
        #self._show_status_message("Back to expense list.")

    def generate_report_gui(self):
        """Generates and displays a spending report by category using Matplotlib."""
        spending_data = self.db.get_spending_by_category()

        if not spending_data:
            messagebox.showinfo("No Data", "No expense data available to generate a report.")
            self._show_status_message("No data for report.", is_error=True)
            return

        categories = list(spending_data.keys())
        amounts = list(spending_data.values())

        # Hide the expense list and input/action buttons to make space for the report
        self.input_frame.pack_forget()
        self.button_frame.pack_forget()
        self.list_frame.pack_forget()

        # Clean up any previously displayed chart and its frame
        if self.chart_frame:
            self.chart_frame.destroy()
            self.chart_frame = None

        # Create a new frame specifically for the chart
        self.chart_frame = tk.LabelFrame(self.master, text="Spending Report by Category", padx=15, pady=10, bd=2, relief="groove")
        self.chart_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create the Matplotlib figure and axes
        fig, ax = plt.subplots(figsize=(10, 6)) # A good default size for Tkinter embedding
        ax.bar(categories, amounts, color='skyblue')
        ax.set_xlabel("Category")
        ax.set_ylabel("Total Amount")
        ax.set_title("Expense Breakdown by Category")
        ax.tick_params(axis='x', rotation=45) # Rotate category labels for readability
        plt.tight_layout() # Automatically adjust plot parameters for a tight layout

        # Add a button to hide the report and show the expense list again -- PACKED FIRST
        tk.Button(self.chart_frame, text="Back to Expenses", command=self.show_expense_list_view, bg='#607D8B', fg='white').pack(side=tk.BOTTOM, pady=10)

        # Embed the Matplotlib figure into the Tkinter window -- PACKED AFTER THE BUTTON
        self.chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        
        # Force Tkinter to process geometry updates immediately for proper rendering
        self.master.update_idletasks()
        self.master.update() 
        
        # Close the Matplotlib figure to free up memory (important when embedding)
        plt.close(fig)

        #self._show_status_message("Spending report generated. Click 'Back to Expenses' to return to list.")

    def on_closing(self):
        """Handles actions to perform when the application window is closed (e.g., closing DB connection)."""
        if messagebox.askokcancel("Quit", "Do you want to quit the application?"):
            self.db.close() # Ensure database connection is closed gracefully
            self.master.destroy() # Close the Tkinter window

# --- Application Entry Point ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    # Bind the window close button (X) to our custom on_closing method
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop() # Start the Tkinter event loop, which keeps the window open
