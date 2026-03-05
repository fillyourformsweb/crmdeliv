from app import app, db
from models import ExcelUpload, ExcelData, Order
import pandas as pd
import os

def get_val(row, aliases):
    for alias in aliases:
        if alias in row:
            val = row[alias]
            if pd.isna(val): return None
            return val
    return None

with app.app_context():
    uploads = ExcelUpload.query.all()
    upload_folder = app.config['UPLOAD_FOLDER']
    
    for upload in uploads:
        filepath = os.path.join(upload_folder, upload.filename)
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        print(f"Reprocessing {upload.filename}...")
        df = pd.read_excel(filepath)
        
        # Clear existing data for this upload to avoid duplicates
        ExcelData.query.filter_by(upload_id=upload.id).delete()
        
        matched_count = 0
        for index, row in df.iterrows():
            receipt_number = get_val(row, ['Awb No', 'receipt_number', 'Receipt Number', 'RECEIPT_NUMBER', 'AWB', 'Consignment No'])
            if receipt_number:
                receipt_number = str(receipt_number).strip()
            
            weight = get_val(row, ['Weight', 'Weight (kg)', 'weight', 'WEIGHT', 'Actual Weight'])
            amount = get_val(row, ['GR Amount', 'Amount', 'amount', 'AMOUNT', 'Total Amount', 'Net Amount'])
            
            savings = get_val(row, ['ValueIf', 'valueif', 'Savings'])
            dest = get_val(row, ['Destination', 'destination', 'City', 'State'])
            
            info_parts = []
            if dest: info_parts.append(f"Dest/State: {dest}")
            if savings: info_parts.append(f"Savings: {savings}")
            info = " | ".join(info_parts) if info_parts else None

            if receipt_number:
                excel_data = ExcelData(
                    receipt_number=receipt_number,
                    weight=float(weight) if weight is not None else None,
                    amount=float(amount) if amount is not None else None,
                    additional_info=info,
                    upload_id=upload.id
                )
                db.session.add(excel_data)
                
                order = Order.query.filter_by(receipt_number=receipt_number).first()
                if order:
                    order.excel_weight = float(weight) if weight is not None else None
                    order.excel_amount = float(amount) if amount is not None else None
                    order.excel_verified = True
                    excel_data.matched = True
                    matched_count += 1
        
        upload.records_processed = len(df)
        upload.records_matched = matched_count
        db.session.commit()
        print(f"Done: {len(df)} records processed, {matched_count} matched.")
