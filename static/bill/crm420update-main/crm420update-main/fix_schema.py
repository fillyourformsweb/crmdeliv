import sqlite3
import os

# Default path based on finding it in 'instance' folder
db_path = os.path.join('instance', 'crm_delivery.db')

if not os.path.exists(db_path):
    # Try root if instance doesn't have it (though list_dir said it does)
    db_path = 'crm_delivery.db'

with open('schema_log.txt', 'w') as log:
    log.write(f"Connecting to database at: {db_path}\n")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(orders)")
    columns_info = cursor.fetchall()
    existing_columns = [col[1] for col in columns_info]

    log.write(f"Existing columns: {existing_columns}\n")

    # List of columns to check and add if missing
    columns_to_check = [
        ('weight_category', 'VARCHAR(50)'),
        ('weight_in_kg', 'FLOAT'),
        ('dimensions', 'VARCHAR(50)'),
        ('base_amount', 'FLOAT DEFAULT 0'),
        ('weight_charges', 'FLOAT DEFAULT 0'),
        ('additional_charges', 'FLOAT DEFAULT 0'),
        ('discount', 'FLOAT DEFAULT 0'),
        ('tax_amount', 'FLOAT DEFAULT 0'),
        ('total_amount', 'FLOAT DEFAULT 0'),
        ('calculated_amount', 'FLOAT DEFAULT 0'),
        ('received_amount', 'FLOAT DEFAULT 0'),
        ('amount_difference', 'FLOAT DEFAULT 0'),
        ('difference_reason', 'VARCHAR(200)'),
        ('excel_verified', 'BOOLEAN DEFAULT 0'),
        ('excel_weight', 'FLOAT'),
        ('excel_amount', 'FLOAT'),
        ('customer_form_link', 'VARCHAR(100)'),
        ('customer_form_completed', 'BOOLEAN DEFAULT 0'),
        ('special_instructions', 'TEXT'),
        ('internal_notes', 'TEXT'),
        ('receipt_mode', 'VARCHAR(30)'),
        ('order_type', 'VARCHAR(20)'),
        # Adding newly discovered missing columns
        ('order_number', 'VARCHAR(50)'),
        ('order_date', 'VARCHAR(20)'),
        ('consignment_number', 'VARCHAR(50)')
    ]

    for col_name, col_type in columns_to_check:
        if col_name not in existing_columns:
            log.write(f"Adding missing column: {col_name}\n")
            try:
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}")
                log.write(f"Successfully added {col_name}\n")
            except Exception as e:
                log.write(f"Error adding {col_name}: {e}\n")

    conn.commit()
    conn.close()
    log.write("Schema update check complete.\n")
