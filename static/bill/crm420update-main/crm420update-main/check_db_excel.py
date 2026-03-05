from app import app, db
from models import ExcelUpload, ExcelData

with app.app_context():
    uploads = ExcelUpload.query.all()
    datas = ExcelData.query.all()
    print(f'Total Uploads: {len(uploads)}')
    print(f'Total ExcelData: {len(datas)}')
    for u in uploads:
        count = ExcelData.query.filter_by(upload_id=u.id).count()
        print(f"Upload ID {u.id} ({u.filename}): {count} records found in ExcelData")
