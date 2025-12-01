import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re

# --- Part 1: Database Management (The SQL Integration) ---
class DatabaseManager:
    """Handles all SQLite database connections and CRUD operations."""
    def __init__(self, db_name="gcash_logbook.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_name)
            # Enable foreign key support in SQLite
            self.conn.execute("PRAGMA foreign_keys = 1")
            self.cursor = self.conn.cursor()
            print("Successfully connected to the database.")
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to connect: {e}")

    def create_tables(self):
        """Creates the tables matching your SQL Schema deliverables."""
        try:
            # 1. CUSTOMER Table (Stores unique customer data)
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS CUSTOMER (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gcash_number VARCHAR(11) NOT NULL UNIQUE,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL
            )
            """)

            # 2. TRANSACTION Table (Stores the financial details)
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS "TRANSACTION" (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                reference_number VARCHAR(13) NOT NULL UNIQUE, 
                amount REAL NOT NULL CHECK (amount > 0),
                transaction_type TEXT NOT NULL CHECK (transaction_type IN ('Cash-in', 'Cash-out')),
                transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES CUSTOMER(customer_id) ON DELETE CASCADE
            )
            """)
            # Commit changes to make table creation permanent
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error creating tables: {e}")

    def close(self):
        """Closes the database connection safely."""
        if self.conn:
            self.conn.close()

    # --- CRUD Operations ---

    def get_or_create_customer(self, gcash, first, last):
        """
        Handles normalization: Checks if customer exists by gcash_number. 
        Creates a new customer if not found. Returns the customer_id.
        """
        try:
            # Check for existing customer
            self.cursor.execute("SELECT customer_id FROM CUSTOMER WHERE gcash_number = ?", (gcash,))
            result = self.cursor.fetchone()

            if result:
                return result[0]
            else:
                # Insert new customer if not found
                self.cursor.execute(
                    "INSERT INTO CUSTOMER (gcash_number, first_name, last_name) VALUES (?, ?, ?)",
                    (gcash, first, last)
                )
                self.conn.commit()
                return self.cursor.lastrowid # Return the ID of the newly inserted row
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error managing customer: {e}")
            return None

    def add_transaction(self, customer_id, ref_num, amount, trans_type):
        """CREATE Operation: Inserts a new transaction record."""
        try:
            self.cursor.execute(
                "INSERT INTO \"TRANSACTION\" (customer_id, reference_number, amount, transaction_type) VALUES (?, ?, ?, ?)",
                (customer_id, ref_num, amount, trans_type)
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Reference Number '{ref_num}' already exists.")
            return False
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error adding transaction: {e}")
            return False

    def fetch_all_transactions(self):
        """READ Operation: Retrieves all transactions, joining with CUSTOMER data."""
        self.cursor.execute("""
            SELECT
                t.transaction_id,
                c.gcash_number,
                c.first_name,
                c.last_name,
                t.amount,
                t.transaction_type,
                t.reference_number,
                t.transaction_date,
                c.customer_id
            FROM "TRANSACTION" t
            JOIN CUSTOMER c ON t.customer_id = c.customer_id
            ORDER BY t.transaction_id DESC
        """)
        return self.cursor.fetchall()

    def update_transaction(self, trans_id, ref_num, amount, trans_type):
        """UPDATE Operation: Modifies an existing transaction record."""
        try:
            self.cursor.execute("""
                UPDATE "TRANSACTION" 
                SET reference_number = ?, amount = ?, transaction_type = ?
                WHERE transaction_id = ?
            """, (ref_num, amount, trans_type, trans_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Reference Number '{ref_num}' already exists.")
            return False
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error updating: {e}")
            return False

    def delete_transaction(self, trans_id):
        """DELETE Operation: Removes a transaction record by its ID."""
        try:
            self.cursor.execute("DELETE FROM \"TRANSACTION\" WHERE transaction_id = ?", (trans_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error deleting: {e}")
            return False

# --- Part 2: GUI Application (Tkinter) ---

class GCashTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IT211 Final Project: GCash Transaction Log Book")
        self.geometry("1100x750")
        
        self.db = DatabaseManager() # Initialize the database connection
        self.selected_transaction_id = None # Tracks the ID of the record being edited
        
        self.configure_styles()
        self.create_layout()
        self.refresh_data() # Load initial data upon startup

    def configure_styles(self):
        """Sets up the visual themes and fonts for the Tkinter widgets."""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Colors based on App interface
        self.color_primary = '#1a73e8'
        self.color_danger = '#d32f2f'
        self.color_success = '#2e7d32'
        
        # Widget styles
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 18, 'bold'), foreground=self.color_primary)
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=6)
        
        # Transaction List styles
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'), background=self.color_primary, foreground='white')
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=28)

    def create_layout(self):
        """Constructs all the frames, labels, and input fields of the GUI."""
        # Main Container
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill='both', expand=True)

        # Title
        ttk.Label(main_frame, text="GCash Transaction Log Book", style='Header.TLabel').pack(pady=(0, 20))

        # --- Summary Bar ---
        self.summary_frame = ttk.LabelFrame(main_frame, text=" Summary Report ", padding=15)
        self.summary_frame.pack(fill='x', pady=(0, 20))
        
        # Labels for Cash-in, Cash-out, and Net Balance (initialized to 0.00)
        self.lbl_cash_in = ttk.Label(self.summary_frame, text="Cash-in: Php 0.00", font=('Segoe UI', 12, 'bold'), foreground=self.color_danger)
        self.lbl_cash_in.pack(side='left', padx=20)
        
        self.lbl_cash_out = ttk.Label(self.summary_frame, text="Cash-out: Php 0.00", font=('Segoe UI', 12, 'bold'), foreground=self.color_success)
        self.lbl_cash_out.pack(side='left', padx=20)
        
        self.lbl_net = ttk.Label(self.summary_frame, text="Net Balance: Php 0.00", font=('Segoe UI', 12, 'bold'))
        self.lbl_net.pack(side='right', padx=20)

        # --- Input Form ---
        input_frame = ttk.LabelFrame(main_frame, text=" Record Transaction ", padding=15)
        input_frame.pack(fill='x', pady=(0, 10))
        
        # Grid Layout
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)

        # Entry fields and Labels
        # Row 0: GCash Number, Amount
        ttk.Label(input_frame, text="GCash Number:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.ent_gcash = ttk.Entry(input_frame)
        self.ent_gcash.grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        ttk.Label(input_frame, text="Amount (Php):").grid(row=0, column=2, sticky='w', padx=15, pady=5)
        self.ent_amount = ttk.Entry(input_frame)
        self.ent_amount.grid(row=0, column=3, sticky='ew', padx=5, pady=5)

        # Row 1: First Name, Transaction Type
        ttk.Label(input_frame, text="First Name:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.ent_first = ttk.Entry(input_frame)
        self.ent_first.grid(row=1, column=1, sticky='ew', padx=5, pady=5)

        ttk.Label(input_frame, text="Transaction Type:").grid(row=1, column=2, sticky='w', padx=15, pady=5)
        self.var_type = tk.StringVar(value='Cash-in')
        self.cbo_type = ttk.Combobox(input_frame, textvariable=self.var_type, values=['Cash-in', 'Cash-out'], state='readonly')
        self.cbo_type.grid(row=1, column=3, sticky='ew', padx=5, pady=5)

        # Row 2: Last Name, Reference No
        ttk.Label(input_frame, text="Last Name:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.ent_last = ttk.Entry(input_frame)
        self.ent_last.grid(row=2, column=1, sticky='ew', padx=5, pady=5)

        ttk.Label(input_frame, text="Reference No:").grid(row=2, column=2, sticky='w', padx=15, pady=5)
        self.ent_ref = ttk.Entry(input_frame)
        self.ent_ref.grid(row=2, column=3, sticky='ew', padx=5, pady=5)

        # --- Buttons ---
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=10)

        # Add Button (CREATE)
        self.btn_add = ttk.Button(btn_frame, text="Add Transaction", command=self.add_transaction)
        self.btn_add.pack(side='left', padx=5)

        # Update Button (UPDATE)
        self.btn_update = ttk.Button(btn_frame, text="Save Edits", command=self.update_transaction, state='disabled')
        self.btn_update.pack(side='left', padx=5)

        # Clear Form Button
        ttk.Button(btn_frame, text="Clear Form", command=self.reset_form).pack(side='left', padx=5)

        # Delete Button (DELETE)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_transaction).pack(side='right', padx=5)

        # --- Data Table (Treeview) ---
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True)

        cols = ('id', 'gcash', 'name', 'amount', 'type', 'ref', 'date')
        self.tree = ttk.Treeview(tree_frame, columns=cols, show='headings')
        
        # Headers
        self.tree.heading('id', text='ID')
        self.tree.heading('gcash', text='GCash No.')
        self.tree.heading('name', text='Customer Name')
        self.tree.heading('amount', text='Amount')
        self.tree.heading('type', text='Type')
        self.tree.heading('ref', text='Reference No.')
        self.tree.heading('date', text='Date')

        # Columns
        self.tree.column('id', width=40, anchor='center')
        self.tree.column('gcash', width=100)
        self.tree.column('name', width=150)
        self.tree.column('amount', width=100, anchor='e')
        self.tree.column('type', width=80, anchor='center')
        self.tree.column('ref', width=120)
        self.tree.column('date', width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Bind Click Event
        self.tree.bind('<<TreeviewSelect>>', self.load_selected)

    # --- Logic ---

    def validate_inputs(self, is_update=False):
        """Validates all input fields before database operations."""
        gcash = self.ent_gcash.get().strip()
        first = self.ent_first.get().strip()
        last = self.ent_last.get().strip()
        ref = self.ent_ref.get().strip()
        
        if not all([gcash, first, last, ref, self.ent_amount.get()]):
            messagebox.showwarning("Input Error", "All fields are required.")
            return None

        # Regex for PH Mobile Number
        if not re.match(r'^09\d{9}$', gcash):
            messagebox.showwarning("Input Error", "GCash Number must be 11 digits starting with 09.")
            return None

        # Reference length check (max 13)
        if len(ref) > 13:
            messagebox.showwarning("Input Error", "Reference Number cannot exceed 13 characters.")
            return None
        
        # Amount must be a positive float
        try:
            amount = float(self.ent_amount.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Amount must be a positive number.")
            return None

        return (gcash, first, last, ref, amount, self.var_type.get())

    def add_transaction(self):
        """Handles the CREATE operation triggered by the 'Add Transaction' button."""   
        data = self.validate_inputs()
        if not data: return

        gcash, first, last, ref, amount, trans_type = data

        # 1. Handle Customer
        cust_id = self.db.get_or_create_customer(gcash, first, last)
        
        # 2. Add Transaction
        if self.db.add_transaction(cust_id, ref, amount, trans_type):
            messagebox.showinfo("Success", "Transaction added successfully!")
            self.reset_form()
            self.refresh_data()

    def update_transaction(self):
        if not self.selected_transaction_id: return
        
        data = self.validate_inputs(is_update=True)
        if not data: return

         # Only reference_number, amount, and transaction_type are updated
        _, _, _, ref, amount, trans_type = data

        if self.db.update_transaction(self.selected_transaction_id, ref, amount, trans_type):
            messagebox.showinfo("Success", "Transaction updated successfully!")
            self.reset_form()
            self.refresh_data()

    def delete_transaction(self):
        """Handles the DELETE operation triggered by the 'Delete Selected' button."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a transaction to delete.")
            return
        
        item = self.tree.item(selected)
        trans_id = item['values'][0]
        
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this transaction?"):
            if self.db.delete_transaction(trans_id):
                messagebox.showinfo("Success", "Deleted successfully.")
                self.reset_form()
                self.refresh_data()

    def load_selected(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected)['values']
        self.selected_transaction_id = values[0]
        
        # Enable Edit Mode
        self.btn_add['state'] = 'disabled'
        self.btn_update['state'] = 'normal'
        self.ent_gcash['state'] = 'disabled' # Disable name/gcash editing
        self.ent_first['state'] = 'disabled'
        self.ent_last['state'] = 'disabled'
        
        # Populate Fields
        self.ent_gcash.config(state='normal') # Temp enable to write
        
        gcash_val = str(values[1])
        if len(gcash_val) == 10 and not gcash_val.startswith('0'):
             gcash_val = "0" + gcash_val
        
        self.ent_gcash.delete(0, tk.END); self.ent_gcash.insert(0, gcash_val)
        self.ent_gcash.config(state='disabled')

        self.ent_first.config(state='normal')
        self.ent_first.delete(0, tk.END); self.ent_first.insert(0, values[2].split()[0]) # Simple split approximation
        self.ent_first.config(state='disabled')
        
        self.ent_last.config(state='normal')
        self.ent_last.delete(0, tk.END); self.ent_last.insert(0, values[2].split()[-1])
        self.ent_last.config(state='disabled')

        self.ent_amount.delete(0, tk.END); self.ent_amount.insert(0, str(values[3]).replace('Php ', '').replace(',', ''))
        self.var_type.set(values[4])
        self.ent_ref.delete(0, tk.END); self.ent_ref.insert(0, str(values[5]))

    def reset_form(self):
        """Clears all input fields and resets the UI back to CREATE mode."""
        self.selected_transaction_id = None
        self.btn_add['state'] = 'normal'
        self.btn_update['state'] = 'disabled'
        
        # Enable all fields
        self.ent_gcash['state'] = 'normal'
        self.ent_first['state'] = 'normal'
        self.ent_last['state'] = 'normal'
        
        # Clear fields
        self.ent_gcash.delete(0, tk.END)
        self.ent_first.delete(0, tk.END)
        self.ent_last.delete(0, tk.END)
        self.ent_amount.delete(0, tk.END)
        self.ent_ref.delete(0, tk.END)
        self.var_type.set('Cash-in')

    def refresh_data(self):
        # Clear Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        rows = self.db.fetch_all_transactions()
        
        total_in = 0
        total_out = 0
        
        for row in rows:
            # row: id, gcash, first, last, amount, type, ref, date, cust_id
            t_id, gcash, first, last, amount, t_type, ref, date, _ = row
            
            # Update Totals
            if t_type == 'Cash-in':
                total_in += amount
            else:
                total_out += amount
                
            # Format Name
            full_name = f"{first} {last}"
            
            # Format Amount
            fmt_amount = f"Php {amount:,.2f}"
            
            self.tree.insert('', 'end', values=(t_id, gcash, full_name, fmt_amount, t_type, ref, date))
            
        # Update Summary
        net = total_out - total_in
        self.lbl_cash_in.config(text=f"Cash-in: Php {total_in:,.2f}")
        self.lbl_cash_out.config(text=f"Cash-out: Php {total_out:,.2f}")

        # Apply color formatting to Net Balance
        self.lbl_net.config(text=f"Cash on Hand: Php {net:,.2f}", foreground=self.color_success if net >= 0 else self.color_danger)

if __name__ == "__main__":
    app = GCashTrackerApp()
    app.mainloop()