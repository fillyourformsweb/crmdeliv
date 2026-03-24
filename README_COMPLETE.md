# 🚚 CRM Delivery System - Complete Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Features](#features)
3. [System Architecture](#system-architecture)
4. [Installation & Setup](#installation--setup)
5. [User Roles & Permissions](#user-roles--permissions)
6. [Core Modules](#core-modules)
7. [API Endpoints](#api-endpoints)
8. [Database Schema](#database-schema)
9. [Workflow Guide](#workflow-guide)

---

## 🎯 Project Overview

**CRM Delivery 420** is an enterprise-grade logistics and delivery management system designed for courier services, parcel delivery operations, and commercial freight management.

### Key Capabilities:
- **Walk-in Order Management**: Quick order creation for immediate shipments
- **Corporate Client Management**: Dedicated systems for bulk orders and partnerships
- **Smart Pricing System**: Weight-based, state-specific, and client-specific pricing tiers
- **Billing Pattern Management**: Multiple billing strategies (10%, 15%, 30% discount patterns)
- **Shipping Mode Support**: 6 different shipping modes (Standard, Prime, Parcel, State Express, Road Express, Air)
- **Analytics & Reporting**: Real-time dashboards, revenue tracking, and performance metrics
- **Offer & Promotion System**: Dynamic discount management
- **Audit Logging**: Complete transaction history and compliance tracking

---

## ✨ Features

### 1. **Order Management**
- **Walk-in Orders**: Fast-track orders from walk-in customers
- **Corporate Orders**: Bulk orders from registered clients with enhanced features
  - **Saved Receiver Selection**: Quick dropdown to select from saved receivers
  - **Handling Tags**: 18 predefined + custom tags for special packaging instructions
  - **Additional Charges**: Track Stationary, Matrix, and Custom charges per order
  - **Pricing Summary**: Real-time display of charges breakdown
- **Order Tracking**: Real-time shipment status updates
- **Receipt Management**: Auto-generated or manual receipt numbering
- **Shipping Mode Selection**: 6 modes with automatic rate selection (Standard, Prime, Parcel, State Express, Road Express, Air)

### 2. **Pricing Engine**
- **Weight-Based Calculation**:
  - ≤3kg: Fixed rates per weight step (100g, 250g, 500g, 1kg)
  - >3kg: Direct per-kg calculation (weight × rate_per_kg)
- **State-Based Pricing**: Different rates for different delivery states
- **Client-Specific Pricing**: Custom rates for corporate clients
- **Tiered Bulk Pricing**: Discounts for orders 3-10kg, 10-25kg, 25-50kg, 50-100kg, 100+kg
- **Automatic Rate Fallback**: System automatically falls back to default rates if client rates unavailable

### 3. **Client Management**
- **Corporate Client Registration**: Company details, billing information
- **Billing Pattern Assignment**: Link clients to specific billing patterns
- **Address Management**: Multiple delivery addresses per client
- **Receiver Management**: Save frequent receivers for quick order creation
- **Credit Tracking**: Monitor outstanding dues and payments

### 4. **Billing & Invoicing**
- **Receipt Types**: Standard (auto-generated) or Manual
- **Bill Patterns**: 10%, 15%, 30% discount options
- **Consolidated Bills**: Monthly or custom period statements
- **Payment Tracking**: Paid/Unpaid status with amount reconciliation
- **Audit Trail**: Complete payment history

### 5. **Analytics & Reporting**
- **Marketing Sales Dashboard**: Revenue trends, client engagement, order breakdown
- **Shipment Tracking**: Real-time order status monitoring
- **Client Due Reports**: Outstanding payments and overdue orders
- **Performance Metrics**: Operational efficiency, conversion rates
- **Export Features**: PDF reports and Excel datasets

### 6. **Offer Management**
- **Auto-Matching Offers**: System automatically selects applicable discounts
- **Amount-Based Offers**: Different discounts for various order ranges
- **Visual Highlighting**: Real-time offer display and selection
- **Discount Application**: Automatic amount calculation after discount

### 7. **Staff Management**
- **Role-Based Access Control**: Admin, Manager, Staff, Delivery users
- **Performance Tracking**: Individual staff performance metrics
- **Receipt Assignment**: Track which staff created orders
- **Branch Management**: Multi-branch operations support

### 8. **Enhanced Client Order Management**

#### 8.1 Saved Receiver Selection
- **Quick Receiver Lookup**: Dropdown selector showing all saved receivers for selected client
- **Auto-Fill Details**: Automatically populates all receiver information when selected:
  - Name, phone number, delivery address
  - City, state, pincode
  - Auto-matches state from database
- **Flexibility**: Option to enter new receiver details instead of using saved receivers

#### 8.2 Handling Tags System
- **18 Predefined Tags** for shipping instructions:
  - Care & Fragility: HANDLE WITH CARE, FRAGILE
  - Positioning: THIS SIDE UP, KEEP UPRIGHT
  - Environment: KEEP DRY, TEMPERATURE SENSITIVE
  - Warnings: DO NOT BEND, DO NOT STACK, DO NOT DROP
  - Special: SIGNATURE REQUIRED
  - Content: PERISHABLE, HAZARDOUS MATERIAL, ELECTRONICS, GLASS INSIDE, HEAVY PACKAGE, LIQUID INSIDE
  - Handling: NO HOOKS, PROTECT FROM SUN
- **Custom Tag Input**: Add custom handling instructions (max 50 characters)
- **Database Storage**: All selected tags stored as comma-separated values with order
- **Label Printing**: Tags display on shipping labels for carrier handling

#### 8.3 Additional Charges Management
- **Four Charge Categories**:
  - **Insured Value**: Insurance for package contents (₹)
  - **Stationary Charge**: Packaging material costs (₹)
  - **Matrix Charge**: Matrix/warehouse fees (₹)
  - **Custom Charge**: Any miscellaneous charges (₹)
- **Real-time Calculation**: All charges summed and included in order total
- **Order-Level Tracking**: Each charge recorded separately for accounting

#### 8.4 Dynamic Pricing Summary
- **Real-time Price Breakdown**:
  1. Base + Weight Charge (calculated based on weight and shipping mode)
  2. Insurance Surcharge (if insured amount specified)
  3. Additional Charges (sum of all extra charges)
  4. **Grand Total** (all components combined)
- **Automatic Updates**: Summary recalculates when:
  - Weight changes
  - State/delivery location changes
  - Insured amount changes
  - Any additional charge is modified
- **Visual Display**: Clear, formatted pricing with rupee symbols and decimal precision

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND LAYER                       │
│  (Jinja2 Templates + Bootstrap + Vanilla JavaScript)    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ├─ Walk-in Order Portal                               │
│  ├─ Client Order Management                            │
│  ├─ Admin Dashboard                                    │
│  ├─ Analytics Suite                                    │
│  └─ Billing & Reports                                 │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                    │
│                     (Flask & Routes)                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ├─ @app.route('/walkin-order')                       │
│  ├─ @app.route('/client-order')                       │
│  ├─ @app.route('/api/calculate-rate')                 │
│  ├─ @app.route('/api/get-all-offers')                 │
│  └─ @app.route('/api/reports/*')                      │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                    BUSINESS LOGIC LAYER                 │
│                  (Pricing Calculations)                │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ├─ calculate_from_state_price()                       │
│  ├─ calculate_from_client_price()                      │
│  ├─ apply_offer()                                      │
│  └─ generate_receipt()                                 │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                    DATA ACCESS LAYER                    │
│                   (SQLAlchemy ORM)                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ├─ Order Model                                        │
│  ├─ Client Model                                       │
│  ├─ BillingPattern Model                              │
│  ├─ DefaultStatePrice Model                           │
│  ├─ ClientStatePrice Model                            │
│  └─ Offer Model                                        │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                    DATABASE LAYER                       │
│                   (SQLite/PostgreSQL)                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager
- SQLite3 or PostgreSQL

### Quick Start

```bash
# 1. Clone/Navigate to project
cd crmdeliv

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialize database
python create_demo_database.py

# 5. Run application
python app.py

# Access at http://localhost:5000
```

### Configuration

**config.py**
```python
# Database
SQLALCHEMY_DATABASE_URI = 'sqlite:///crm_delivery.db'

# Security
SECRET_KEY = 'your-secret-key'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True

# File Upload
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
```

---

## 👥 User Roles & Permissions

| Role | Primary Functions | Access Level |
|------|-------------------|--------------|
| **Admin** | User management, system settings, complete access | Full system access |
| **Manager** | Analytics, reporting, marketing, offer management | Analytics + limited admin |
| **Staff** | Order creation, receipt generation, order tracking | Order operations only |
| **Delivery** | Order pickup/delivery, status updates | Delivery operations only |

### Role-Based Routes
```python
@admin_required      # Full system access
@manager_required    # Analytics, reports, offers
@staff_required      # Order operations
@delivery_required   # Delivery operations
```

---

## 📚 Core Modules

### 1. **Order Management Module**
**File**: Part of `app.py` (lines 2227-3120)

Functions:
- `walkin_order()` - Create walk-in orders
- `client_order()` - Create corporate orders
- `order_details()` - View order information
- `update_order_status()` - Track shipment status

### 2. **Pricing Calculation Module**
**File**: `app.py` (lines 352-407)

```python
def calculate_from_state_price(selected_price, weight):
    """
    Calculate shipping cost based on weight and state pricing
    
    ≤3kg: Uses predefined rates (100g, 250g, 500g, 1kg)
    >3kg: weight × price_extra_per_kg
    """
```

### 3. **Client Management Module**
**File**: `app.py` (lines 3124-3220)

Functions:
- `list_clients()` - View all clients
- `add_client()` - Register new client
- `edit_client()` - Update client information
- `client_details()` - Client profile view

### 4. **Billing Pattern Module**
**File**: `app.py` (lines 4068-4127)

Functions:
- `list_billing_patterns()` - View all patterns
- `add_billing_pattern()` - Create new pattern
- `edit_billing_pattern()` - Modify pattern
- `delete_billing_pattern()` - Remove pattern

### 5. **Analytics Module**
**File**: `app.py` (lines 1770-1850)

Dashboards:
- `operations_marketing_sales()` - Revenue & sales analytics
- `operations_shipment_tracking()` - Real-time tracking
- `operations_client_due_report()` - Payment tracking

### 6. **Pricing Matrix Module**
**File**: `app.py` (lines 4906-5180)

Functions:
- `default_prices()` - View state pricing matrix
- `add_default_price()` - Add new state rate
- `normal_client_prices()` - View client pricing
- `set_client_prices()` - Set custom rates

---

## 🔌 API Endpoints

### Order Management
```
POST   /walkin-order                 Create walk-in order
POST   /client-order                 Create client order
GET    /order/<id>/details           Get order details
POST   /order/<id>/update-status     Update order status
```

### Pricing Calculation
```
GET    /api/calculate-rate           Calculate shipping rate
GET    /api/get-all-offers          List available offers
POST   /api/apply-offer/<id>         Apply discount
```

### Client Management
```
GET    /clients                      List all clients
POST   /client/add                   Register new client
POST   /client/edit/<id>             Update client
GET    /client/<id>/details          View client profile
```

### Billing Patterns
```
GET    /billing-patterns             List all patterns
POST   /billing-patterns/add         Create new pattern
POST   /billing-patterns/edit/<id>   Update pattern
POST   /billing-patterns/delete/<id> Delete pattern
```

### Analytics & Reports
```
GET    /operations/marketing-sales   Sales dashboard
GET    /operations/shipment-tracking Shipment tracking
GET    /operations/client-due-report Due amounts report
GET    /api/reports/overview         Report overview data
GET    /api/reports/generate-pdf     Export PDF report
GET    /api/reports/export-dataset   Export Excel data
```

### Pricing Matrix
```
GET    /default-prices               View state pricing
POST   /add-default-price            Add state rate
GET    /normal-client-prices/<id>    View client rates
POST   /set-client-price/<id>        Set custom rate
```

---

## 💾 Database Schema

### Core Tables

#### **order** (_shipment records_)
```
id (PK)
receipt_number         VARCHAR - Tracking number
sender_name            VARCHAR - Shipper name
sender_phone           VARCHAR - Shipper contact
receiver_name          VARCHAR - Recipient name
receiver_address       TEXT    - Delivery address
receiver_state         VARCHAR - Delivery state
receiver_city          VARCHAR - Delivery city
order_type             VARCHAR - 'walkin' or 'client'
weight                 FLOAT   - Package weight
total_amount           DECIMAL - Final charge
payment_status         VARCHAR - 'Paid' or 'Due'
shipping_mode          VARCHAR - Delivery type
status                 VARCHAR - Order status
created_at             DATETIME
created_by_id          FK (User)
```

#### **client** (_corporate accounts_)
```
id (PK)
name                   VARCHAR - Client name
company_name           VARCHAR - Company registered name
email                  VARCHAR
phone                  VARCHAR
billing_pattern_id     FK (BillingPattern)
outstanding_amount     DECIMAL - Total dues
created_at             DATETIME
```

#### **billing_pattern** (_discount schemes_)
```
id (PK)
name                   VARCHAR - Pattern name
pattern_type           INT     - 10, 15, or 30 (discount %)
base_rate              DECIMAL - Base shipping rate
rate_per_kg            DECIMAL - Per kg charge
additional_charges     DECIMAL - Extra fees
is_active              BOOLEAN - Active status
created_at             DATETIME
```

#### **default_state_price** (_state shipping rates_)
```
id (PK)
state_name             VARCHAR - State/region
price_100g             DECIMAL - 100g rate
price_250g             DECIMAL - 250g rate
price_500g             DECIMAL - 500g rate
price_1kg              DECIMAL - 1kg rate
price_extra_per_kg     DECIMAL - Rate per kg >3kg
created_at             DATETIME
```

#### **client_state_price** (_client-specific rates_)
```
id (PK)
client_id              FK (Client)
state_name             VARCHAR
price_100g             DECIMAL
price_250g             DECIMAL
price_500g             DECIMAL
price_1kg              DECIMAL
price_extra_per_kg     DECIMAL
created_at             DATETIME
```

#### **offer** (_promotions_)
```
id (PK)
description            TEXT    - Offer details
min_amount             DECIMAL - Min order amount
max_amount             DECIMAL - Max order amount
offer_amount           DECIMAL - Discount amount
is_active              BOOLEAN
created_at             DATETIME
```

---

## 🔄 Workflow Guide

### Workflow 1: Walk-in Order Creation
```
1. User navigates to /walkin-order
2. Fill order details:
   - Receipt type (Standard/Manual)
   - Sender info
   - Receiver name, address, state
   - Weight, Shipping mode
3. System calculates:
   - FETCH state default pricing
   - CALCULATE: weight × rate_per_kg
   - DISPLAY: total amount
4. Optional: View & apply offers
   - CLICK "View Offers" button
   - SYSTEM matches offer based on amount
   - SELECT offer to apply discount
5. Submit order
   - GENERATE receipt number
   - SAVE to database
   - DISPLAY confirmation with tracking number
```

### Workflow 2: Corporate Client Order
```
1. User navigates to /client-order
2. SELECT existing client or create new
3. Fill shipment details
4. System calculates:
   - CHECK if client has custom pricing
   - IF custom: use ClientStatePrice
   - ELSE: fallback to DefaultStatePrice
   - APPLY billing pattern discount
5. System displays:
   - Item weight
   - Base rate
   - Discount percentage
   - Final amount
6. Submit order
   - LINK to client account
   - UPDATE client outstanding amount
   - GENERATE receipt
```

### Workflow 3: Order Tracking
```
1. User navigates to /operations/shipment-tracking
2. SEARCH by:
   - Receipt number
   - Customer name
   - Status filter
3. DISPLAY order details:
   - Current status
   - Tracking updates
   - Timeline events
4. UPDATE status when needed
   - Click status button
   - SAVE update
   - RECORD timestamp
```

### Workflow 4: Pricing Management
```
1. Admin navigates to /default-prices
2. VIEW state-wise pricing matrix
3. ACTIONS per state:
   - Add new state: Click "+" or right-click
   - Edit rates: Click edit button
   - Delete: Click delete button
4. RIGHT-CLICK context menu:
   - Modal opens for quick entry
   - Fill 5 fields (prices for 100g, 250g, 500g, 1kg, per-kg)
   - SUBMIT to save
5. System validates:
   - Rates must be positive
   - State name required
```

### Workflow 5: Client-Specific Pricing
```
1. Admin navigates to /client-prices/<client_id>
2. VIEW client's custom rates (if any)
3. OPTIONS:
   - Use defaults: No custom rates set
   - Override: Set custom prices
4. SET CUSTOM PRICES:
   - Navigate to /set-client-price/<id>
   - FILL rates for each weight tier
   - APPLY tiered bulk pricing (3-10kg, 10-25kg, etc.)
   - SUBMIT
5. SYSTEM stores in ClientStatePrice table
```

### Workflow 6: Bill Amount Due Report
```
1. Manager navigates to /operations/client-due-report
2. FILTER by:
   - Date range
   - Client tier (All/Corporate)
3. VIEW report showing:
   - Client name
   - Total orders
   - Total due
   - Payment percentage
4. CLICK client to view:
   - Individual order details
   - Payment history
5. EXPORT:
   - Generate PDF summary
   - Export Excel dataset
```

### Workflow 7: Analytics Dashboard
```
1. Manager navigates to /operations/marketing-sales
2. SYSTEM displays:
   - Key metrics (total orders, revenue, conversion rate)
   - Top performing states
   - Top clients by revenue
   - Daily order trends
   - Revenue breakdown by type
3. FILTER by:
   - Timeframe (daily, weekly, monthly, yearly)
   - Date range
   - Order type (walkin/client)
4. DOWNLOAD:
   - Generate Executive PDF
   - Export Dataset (Excel)
```

---

## 🎨 Frontend Structure

### Key Templates

| Template | Purpose | Route |
|----------|---------|-------|
| `walkin_order.html` | Walk-in order form | `/walkin-order` |
| `client_order.html` | Corporate order form | `/client-order` |
| `admin_dashboard.html` | Admin overview | `/admin` |
| `operations_marketing_sales.html` | Sales dashboard | `/operations/marketing-sales` |
| `operations_shipment_tracking.html` | Order tracking | `/operations/shipment-tracking` |
| `detailed_reports.html` | Analytics suite | `/reports` |
| `default_prices.html` | State pricing matrix | `/default-prices` |
| `normal_client_prices.html` | Client pricing matrix | `/normal-client-prices/<id>` |
| `add_billing_pattern.html` | New billing pattern | `/billing-patterns/add` |
| `edit_billing_pattern.html` | Edit pattern | `/billing-patterns/edit/<id>` |

---

## 🔒 Security Features

- **Authentication**: Flask-Login with session management
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Server-side form validation
- **CSRF Protection**: Token-based CSRF prevention
- **Password Security**: Hashed passwords (Werkzeug)
- **Audit Logging**: Complete transaction history
- **SQL Injection Prevention**: SQLAlchemy ORM parameterized queries

---

## 📊 Performance Optimization

- **Database Indexing**: Indexed frequently queried columns
- **Query Optimization**: Efficient joins and aggregations
- **Caching**: Client-side caching for static assets
- **Pagination**: Large datasets paginated for faster loading
- **Lazy Loading**: Related data loaded on demand

---

## 🐛 Troubleshooting

### Common Issues

**Issue: Rate calculation not working**
- Check if state exists in `default_state_price` table
- Verify all rate fields are populated
- Check weight input is valid number

**Issue: Offers not displaying**
- Verify offers exist and `is_active = True`
- Check offer amount range matches order total
- Clear browser cache and reload

**Issue: Client pricing not applied**
- Verify `billing_pattern_id` is set for client
- Check `ClientStatePrice` record exists for that state
- Ensure rates are greater than 0

**Issue: Reports not generating**
- Ensure reportlab and pandas are installed: `pip install reportlab pandas`
- Check file permissions in /uploads directory
- Verify order data exists in database

---

## 📝 License & Credits

CRM Delivery 420 © 2024 - All Rights Reserved

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section above
2. Review workflow documentation
3. Check database schema and data integrity
4. Review application logs

---

**Last Updated**: March 2026
**Version**: 4.2.0
