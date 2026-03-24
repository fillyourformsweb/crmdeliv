# WORKFLOW Documentation - B2B Courier & Delivery Management System

## Table of Contents

1. [Overview](#overview)
2. [User Roles & Access](#user-roles--access)
3. [Complete Request Flows](#complete-request-flows)
4. [Role-Specific Workflows](#role-specific-workflows)
5. [Core Business Processes](#core-business-processes)
6. [Technical Administrative Tasks](#technical-administrative-tasks)
7. [Troubleshooting Guide](#troubleshooting-guide)

---

## Overview

This document provides detailed step-by-step workflows for all user roles and business processes in the B2B Courier & Delivery Management System. The system handles order management, pricing, client relationships, tracking, billing, and analytics.

### System Architecture
- **Frontend**: HTML/Bootstrap 5 with Jinja2 templating
- **Backend**: Flask with SQLAlchemy ORM
- **Database**: MySQL with 15+ interconnected models
- **Key Features**: Order management, smart pricing, client billing patterns, offer management, comprehensive analytics

---

## User Roles & Access

### 1. **Admin Role**
**Permissions**: Full system access including user management, system configuration, billing patterns, and all reports
**Primary Responsibilities**:
- User and staff management
- System configuration and settings
- Billing pattern management
- Comprehensive analytics and reports
- Offer management

**Landing Dashboard**: Admin Dashboard with system overview

### 2. **Manager Role**
**Permissions**: Client management, order oversight, pricing configuration, report generation
**Primary Responsibilities**:
- Client account management
- Review order status and performance
- Configure client-specific pricing
- Generate marketing and sales reports
- Monitor delivery performance

**Landing Dashboard**: Manager Dashboard with client summaries and orders

### 3. **Operation Manager Role**
**Permissions**: Order management, shipment tracking, delivery coordination
**Primary Responsibilities**:
- Track shipments in real-time
- Update delivery status
- Generate due reports for clients
- Manage order exceptions
- Work with delivery staff

**Landing Dashboard**: Operations Dashboard with tracking and shipment overview

### 4. **Staff Role**
**Permissions**: Order creation and management for walk-in and client orders
**Primary Responsibilities**:
- Create orders for walk-in customers
- Create orders for existing clients
- Apply offers and discounts
- Preview order costs
- Generate order receipts and bills

**Landing Dashboard**: Staff Dashboard with quick order creation links

### 5. **Delivery Role**
**Permissions**: View assigned orders, update delivery status
**Primary Responsibilities**:
- View assigned delivery orders
- Mark orders as picked up
- Mark orders as delivered
- Provide delivery feedback

**Landing Dashboard**: Delivery Dashboard with assigned orders

---

## Complete Request Flows

### Flow 1: Walk-In Order Creation & Billing

**Actors**: Customer, Staff, Operation Manager
**Time**: 5-10 minutes per order
**Outcome**: Complete order with bill, tracking ID, and receipt

#### Step-by-Step Workflow:

1. **Customer visits counter with shipment**
   - Customer provides sender and receiver details
   - Hands over package for weighing
   - Specifies delivery requirement (standard, express, etc.)

2. **Staff logs into system**
   - Click "Walk-In Order" from dashboard
   - Navigate to "Create New Walk-In Order"

3. **Enter Sender Details** (if not already in system)
   - First Name
   - Email
   - Mobile Number
   - Address Details (State, District, Pincode)
   - System validates pincode via API

4. **Enter Receiver Details**
   - First Name
   - Email
   - Mobile Number
   - Address Details (State, District, Pincode)
   - **TIP**: Right-click on State field to add new state if not in dropdown

5. **Enter Shipment Details**
   - Select shipping mode:
     - **Standard Delivery** (7-10 days)
     - **Prime Express** (2-3 days)
     - **Parcel Service** (4-5 days)
     - **State Express** (5-7 days)
     - **Road Express** (3-4 days)
     - **Air** (1-2 days)
   - Weight (in kg)
   - Shipment Type (Document, Parcel, Fragile, etc.)
   - Item Description
   - Declared Value

6. **Review Auto-Calculated Pricing**
   - System displays:
     - Base charge based on weight and shipping mode
     - Weight-based charges (if applicable)
     - Total order amount
   - **Pricing Logic**:
     - Weight ≤ 3kg: Use tiered rates (100g, 250g, 500g, 1kg, 2kg, 3kg)
     - Weight > 3kg: Amount = weight × extra_per_kg rate

7. **Apply Offer (Optional)**
   - Click "Select Offer" button in modal popup
   - System auto-highlights matching offer based on order amount:
     - Green gradient background = offer applies to this order amount
     - "AUTO MATCHED" badge = system detected match
   - Click on matching offer to apply it
   - Discount automatically deducted from total
   - Order total updates immediately

8. **Confirm & Process**
   - Review final amount
   - Check all details are correct
   - Click "Create Order" button
   - System generates unique Order ID

9. **Generate Bill**
   - Click "Generate Bill" button
   - Options:
     - **Print Bill**: Direct thermal printer output
     - **Download PDF**: Save bill to computer
     - **Email Bill**: Send bill to receiver's email
   - Bill includes:
     - Order ID and date
     - Sender and receiver details
     - Shipment details
     - Charges breakdown
     - Final amount
     - Payment status

10. **Complete Transaction**
    - Staff collects payment from customer
    - Marks payment as "Received" in system
    - Provides customer with:
      - Receipt with Order ID
      - Tracking information
      - Estimated delivery date

11. **Operational Handoff**
    - Operation Manager receives shipment in system
    - Updates shipment status to "At Hub"
    - Assigns to delivery staff based on routing
    - Updates status to "In Transit"
    - Updates final status to "Delivered" with proof

---

### Flow 2: Client Order Creation & Management

**Actors**: Client/Account Manager, Staff, Manager, Operation Manager
**Time**: 10-15 minutes for initial setup, 3-5 minutes per order
**Outcome**: Managed client account with linked orders, automated billing

#### Part A: Client Account Setup (One-time)

1. **Manager creates new client account**
   - Navigate to Clients section
   - Click "Add New Client"

2. **Enter Client Details**
   - Business Name
   - Contact Person Name
   - Email Address
   - Mobile Number
   - Business Address:
     - Street Address
     - State (with add-on-the-fly option via right-click)
     - District
     - Pincode
   - Tax ID (GST/PAN)

3. **Select Billing Pattern**
   - Choose from available patterns:
     - **Pattern 10**: Base rate with 10% discount
     - **Pattern 15**: Base rate with 15% discount
     - **Pattern 30**: Base rate with 30% discount
   - Pattern influences pricing calculation for all client orders

4. **Add Receiver Addresses** (Optional but Recommended)
   - Click "Add Receiver Address"
   - Enter frequently used delivery addresses:
     - Business Address
     - Warehouse Address
     - Alternate Location
     - etc.
   - These become quick-select options in order creation

5. **System Verification**
   - Validates pincode locations
   - Checks billing pattern applicability
   - Confirms email and mobile validity
   - Saves client to database with ID

6. **Client Account Activated**
   - Client account ready for orders
   - Can now create orders using client selection

#### Part B: Creating Client Orders

1. **Staff initiates order creation**
   - Navigate to Dashboard
   - Click "Create Client Order"
   - OR in existing client detail: Click "Create Order for [Client Name]"

2. **Select Client** (if not pre-selected)
   - Search/select from client list dropdown
   - System loads client's billing pattern and historical data
   - **Saves to database**: Client's sender information displayed for reference

3. **Select or Add Receiver** (ENHANCED)
   - **Option 1 - Quick Selection**: Use "SAVED RECEIVERS" dropdown
     - Shows all previously saved receivers for this client
     - Displays receiver name and company (if applicable)
     - Click to auto-fill all receiver details:
       - Name, phone number, delivery address
       - City, state, pincode
       - Auto-matches state from database dropdown
     - **Pro Tip**: Fastest option for repeat deliveries
   
   - **Option 2 - Manual Entry**: Enter new receiver details
     - Name
     - Phone number
     - Complete delivery address
     - City, state, pincode
     - New receivers are automatically saved for future use

4. **Enter Shipment & Packaging Details**
   - **Shipping Details**:
     - Select shipping mode (same 6 options as walk-in)
     - Weight (in kg)
     - Quantity (number of boxes/items)
     - Declared insured value (optional)
   
   - **Handling Tags (NEW FEATURE)**:
     - Select applicable handling instructions from 18 predefined tags:
       - **Care Tags**: HANDLE WITH CARE, FRAGILE
       - **Position Tags**: THIS SIDE UP, KEEP UPRIGHT
       - **Environment Tags**: KEEP DRY, TEMPERATURE SENSITIVE
       - **Warning Tags**: DO NOT BEND, DO NOT STACK, DO NOT DROP
       - **Special Tags**: SIGNATURE REQUIRED, PERISHABLE, HAZARDOUS MATERIAL
       - **Content Tags**: ELECTRONICS, GLASS INSIDE, HEAVY PACKAGE, LIQUID INSIDE, NO HOOKS, PROTECT FROM SUN
     - Add custom handling instruction (optional, max 50 characters)
     - **Note**: Tags print on shipping label for carrier handling instructions

5. **Additional Charges Management (NEW FEATURE)**
   - **Four charge categories** (all optional):
     - **Insured Value (₹)**: Insurance premium for package contents
     - **Stationary Charge (₹)**: Packaging materials cost
     - **Matrix Charge (₹)**: Warehouse/processing fee
     - **Custom Charge (₹)**: Any miscellaneous charges
   - Enter amounts for applicable charges
   - Real-time calculation of total charges

6. **Price Summary with Enhanced Breakdown**
   - System displays **four-line pricing summary**:
     1. **Base + Weight Charge**: Auto-calculated based on weight and mode
     2. **Insurance Surcharge**: If insured amount specified
     3. **Additional Charges**: Sum of all entered charges
     4. **GRAND TOTAL**: Final order amount (all components)
   - **Auto-Updates**: Pricing recalculates automatically when:
     - Weight changes
     - State/location changes
     - Insured amount changes
     - Any additional charge is modified
   - **Visual Clarity**: All amounts shown in ₹ with precise decimals

7. **Optional: Apply Special Offer**
   - Same process as walk-in
   - Click "Check Offer" or "View Offers"
   - System highlights matching offer based on total amount
   - Click to apply discount to final amount

8. **Confirm Order**
   - Review all details including:
     - Client and receiver information
     - Selected handling tags
     - All charges breakdown
     - Final total amount
   - Click "CONFIRM CORPORATE ORDER"
   - System generates Order ID and links to client

9. **Generate Documentation**
   - Waybill generation with handling tags
   - Invoice includes all charges breakdown
   - Email to client (auto-sends if configured)
   - PDF for printing/filing

10. **Payment Processing**
    - For pre-paid clients: Mark as paid
    - For post-paid clients: Add to client's due amount
    - All charges tracked separately for accounting

11. **Delivery & Follow-up**
    - Operation Manager picks up shipment
    - Updates tracking status
    - Notifies client of delivery via email
    - Handles any delivery exceptions

---

### Flow 3: Pricing Configuration

**Actors**: Manager/Admin
**Time**: 15-30 minutes for comprehensive setup
**Outcome**: Organized pricing matrix for all states and weight ranges

#### Part A: Default State Pricing (System-wide baseline)

1. **Navigate to Pricing Settings**
   - Admin/Manager → Pricing Configuration
   - Select "Default State Prices"

2. **Add or Edit State Pricing**
   - **Method 1: Direct Entry**
     - Click "Add Default Price"
     - Fill all weight tiers:
       - 100g tier
       - 250g tier
       - 500g tier
       - 1kg tier
       - 2kg tier
       - 3kg tier
       - Extra per kg (for >3kg orders)
     - Enter for each state

   - **Method 2: Quick Add (Right-Click)**
     - Right-click on state column header
     - Context menu opens with form
     - Enter all pricing details
     - Auto-saves to table

3. **Weight Tier Pricing Explanation**
   - **0-100g**: Use "100g tier" rate
   - **101-250g**: Use "250g tier" rate
   - **251-500g**: Use "500g tier" rate
   - **501g-1kg**: Use "1kg tier" rate
   - **1001g-2kg**: Use "2kg tier" rate
   - **2001g-3kg**: Use "3kg tier" rate
   - **>3kg**: Amount = weight × extra_per_kg rate
   
   Example:
   ```
   Maharashtra Pricing:
   - 100g: ₹50
   - 250g: ₹75
   - 500g: ₹100
   - 1kg: ₹130
   - 2kg: ₹200
   - 3kg: ₹250
   - Extra per kg (>3kg): ₹45
   
   Order Calculations:
   - 500g order: ₹100
   - 1.5kg order: ₹200 (between 1kg and 2kg, use 2kg rate)
   - 3kg order: ₹250
   - 4kg order: ₹180 (4 × ₹45)
   - 5kg order: ₹225 (5 × ₹45)
   ```

4. **Review & Publish**
   - Table shows all states with their complete pricing
   - Verify against cost sheets
   - No need to "publish" - changes effective immediately

#### Part B: Client-Specific Pricing (Override for VIP/volume clients)

1. **Navigate to Client Pricing**
   - Admin/Manager → Pricing Configuration
   - Select "Client State Prices"

2. **Add Client-Specific Pricing**
   - Select client from dropdown
   - Click "Add Price for [Client]"
   - Select state
   - Enter custom rates (overrides default):
     - 100g to 3kg tier rates
     - Extra per kg rate

3. **Use Case Examples**
   - **Volume Discount Client**: Reduces per-kg rate by 15%
   - **Strategic Partner**: Custom rates negotiated monthly
   - **High-Volume Route**: Preferred pricing for frequently used state

4. **Verification**
   - When client creates order to this state, system uses client pricing
   - If no client-specific pricing, falls back to default

#### Part C: Normal Client Pricing (Mid-tier pricing option)

1. **Navigate to Normal Client Pricing**
   - Select "Normal Client State Prices"

2. **Configure Alternative Pricing**
   - Similar to default pricing but different rates
   - Used for clients with "Normal" billing pattern
   - Provides tiered pricing option between minimal and premium

3. **Implementation in Orders**
   - Client select determines which pricing to use
   - Creates flexibility in pricing strategies

#### Part D: Billing Patterns (Discount framework)

1. **Navigate to Billing Patterns**
   - Admin → Billing Patterns

2. **View or Edit Patterns**
   - **Pattern Details**:
     - Name: Pattern 10 / Pattern 15 / Pattern 30
     - Discount Percentage: Auto-applied to all client orders
     - Description: Usage guidelines
     - Active Status: Enable/disable pattern

3. **How Patterns Work**
   - Selected during client creation
   - Applied to every order for that client
   - Automatically calculated in order total
   - Example: If Pattern 15 selected, all orders get 15% discount

4. **Creating Custom Pattern** (if needed)
   - Click "Add Billing Pattern"
   - Name it appropriately
   - Set discount percentage
   - Select clients to apply to

---

### Flow 4: Offer & Promotion Management

**Actors**: Admin/Manager
**Time**: 5-10 minutes to set up offer; 1-2 seconds for staff to apply
**Outcome**: Time-limited promotional offers applied to qualifying orders

#### Step-by-Step Setup:

1. **Navigate to Offers Section**
   - Admin/Manager → Offers & Promotions
   - Click "Create New Offer"

2. **Define Offer Details**
   - **Offer Name**: e.g., "Summer Rush Discount 2024"
   - **Description**: Promotional message shown to staff
   - **Discount Type**:
     - Fixed Amount (₹100 off)
     - Percentage (10% off)
   - **Discount Value**: Amount or percentage

3. **Set Offer Conditions**
   - **Minimum Order Amount**: e.g., ₹500 (order must exceed this)
   - **Maximum Order Amount**: e.g., ₹5000 (offer only up to this amount)
   - **Applicable Shipping Modes**: Select which modes qualify
     - Standard Delivery
     - Prime Express
     - etc.

4. **Set Validity Period**
   - **Start Date & Time**: When offer becomes active
   - **End Date & Time**: When offer expires
   - System automatically validates offers within this window

5. **Set Usage Limits**
   - **Maximum Uses**: Total times offer can be used (optional)
   - **Max Per Client**: How many times one client can use (optional)
   - Leave blank for unlimited

6. **Activate Offer**
   - Click "Create Offer"
   - System marks offer as Active
   - Offer available in order creation immediately

#### Order Creation with Auto-Matching (Staff Workflow):

1. **Staff creates walk-in or client order**
   - Enters all shipment details
   - System auto-calculates amount: ₹1,200

2. **System Auto-Detects Matching Offers**
   - Behind the scenes:
     - Checks all active offers
     - Filters by shipping mode
     - Compares order amount (₹1,200) against min/max range
     - Identifies matching offers

3. **Visual Highlight in Offers Modal**
   - Modal opens showing all available offers
   - Matching offer appears with:
     - **Green gradient background gradient**
     - **Bold border**
     - **"AUTO MATCHED" badge in top corner**
     - Discount amount prominently displayed
   - Non-matching offers show in normal styling

4. **Staff Application**
   - Staff clicks on the green (auto-matched) offer
   - OR clicks on any other offer to manually apply
   - System applies discount:
     - Subtracts discount from order total
     - Updates total amount instantly
     - Shows applied offer name in order summary

5. **Order Completion**
   - Order created with applied offer
   - Receipt shows original amount, discount, and final amount
   - Offer tracked in order history

#### Offer Lifecycle:

1. **Active Phase** (Between start and end dates)
   - Available for application to new orders
   - System auto-highlights matching orders
   - Staff can apply manually to any order

2. **Expiration Phase** (After end date)
   - Auto-hidden from new orders
   - Cannot apply to new orders
   - Can view historical use in reports

3. **Management**
   - Manager can view offer performance
   - See total uses, revenue impact, popularity
   - Extend offer validity if needed
   - Archive expired offers

---

## Role-Specific Workflows

### ADMIN WORKFLOW

#### Daily Admin Tasks:

1. **Start of Day**
   - Log in → View Admin Dashboard
   - Check system health indicators:
     - Active users online
     - Orders processed today
     - Revenue summary
     - System alerts (if any)

2. **User Management**
   - Navigate to → Users & Roles
   - Options:
     - **Add New User**: Click button, enter details (name, email, role), system sends password reset link
     - **Edit User**: Update role, status, permissions
     - **Deactivate User**: Remove access without deleting history
     - **View User Activity**: Audit trail of actions

3. **System Configuration**
   - Navigate to → Settings
   - Configure:
     - Email notifications (on/off)
     - SMS integration (API keys)
     - Backup schedule
     - System-wide messaging
     - API rate limits
     - Database retention policy

4. **Billing Pattern Management**
   - Maintain active billing patterns
   - Create new patterns for seasonal promotions
   - Review pattern usage across clients

5. **Analytics & Reports**
   - Navigate to → Reports & Analytics
   - View:
     - Daily revenue trends
     - Top clients by volume
     - Route performance
     - User productivity metrics
   - Generate and export reports for stakeholders

6. **Database Maintenance**
   - Navigate to → Maintenance
   - Tasks:
     - Backup database (daily)
     - Verify data integrity
     - Clean old logs (monthly)
     - Export audit trail (quarterly)

7. **End of Day**
   - Review any system issues logged
   - Ensure backup completed successfully
   - Check for high-value transactions requiring review

---

### MANAGER WORKFLOW

#### Daily Manager Tasks:

1. **Morning Review**
   - Log in → Manager Dashboard
   - View metrics:
     - Clients served today
     - Total orders created
     - Revenue generated
     - Top clients by activity

2. **Client Management** (20-30% of time)
   - Navigate to → Clients
   - Options:
     - **View Client Details**: Full profile, order history, payments, addresses
     - **Create New Client**: Follow Flow 2 Part A
     - **Edit Client**: Update details, billing pattern, contact info
     - **View Client Orders**: All orders linked to this client with status
     - **View Client Payments**: Track paid/due amounts, payment dates

3. **Pricing Configuration** (10-15% of time)
   - Navigate to → Pricing
   - Review and update:
     - Default state pricing (Flow 3 Part A)
     - Client-specific pricing for VIP accounts (Flow 3 Part B)
     - Seasonal adjustments to rates
     - Competitor rate analysis notes

4. **Order Oversight** (30-40% of time)
   - Navigate to → Orders
   - View all orders with filters:
     - By client
     - By date range
     - By status (New, In Transit, Delivered, Failed)
   - Monitor:
     - Any orders delayed >2 days
     - Failed delivery attempts
     - Customer complaints
     - High-value orders (flagged for attention)

5. **Report Generation** (15-20% of time)
   - Navigate to → Reports
   - Generate standard reports:
     - **Client Due Report**: Unpaid invoices by client, aging analysis
     - **Marketing/Sales Analytics**: Top clients, order trends, revenue by route
     - **Client Performance**: Orders completed, average order value, repeat rate
   - Options to:
     - View on-screen
     - Generate PDF for sharing with finance
     - Export to Excel for further analysis
     - Email reports to stakeholders

6. **Offer Management** (5-10% of time)
   - Navigate to → Offers
   - Create and manage promotions (see Flow 4)
   - Review offer usage in analytics
   - Adjust offer strategy based on performance

7. **Issue Resolution**
   - If staff reports delivery issues:
     - Contact Operation Manager for tracking update
     - Communicate with client
     - Track resolution in system notes
   - If pricing discrepancy reported:
     - Review order details
     - Verify pricing calculation
     - Make adjustment if needed

---

### OPERATION MANAGER WORKFLOW

#### Daily Operations Tasks:

1. **Shift Start**
   - Log in → Operations Dashboard
   - View key metrics:
     - Shipments in hub today
     - In-transit orders count
     - Pending deliveries
     - Failed/exception orders
     - Average delivery time

2. **Shipment Intake** (8:00 AM - 12:00 PM)
   - Receive orders from staff
   - Navigate to → Shipments
   - For each shipment:
     - Scan Order ID (barcode)
     - Verify sender/receiver details
     - Check shipment weight/dimensions
     - Confirm declared value matches package
     - Mark status: "Received at Hub" in system

3. **Sorting & Routing** (12:00 PM - 2:00 PM)
   - Sort received shipments by:
     - Destination state
     - Delivery distance
     - Shipping mode (express first)
   - Assign to delivery staff:
     - Consider staff's assigned region
     - Balance workload
     - Priority orders first
   - Update system: Assign order to delivery staff with status "Assigned to Courier"

4. **Dispatch Management** (2:00 PM - 4:00 PM)
   - Coordinate dispatch:
     - Print shipping labels with Order IDs
     - Batch shipments by courier
     - Hand over to delivery staff
     - Get acknowledgment signature
   - Update system: Mark as "In Transit"

5. **Real-time Tracking** (4:00 PM - 6:00 PM)
   - Monitor deliveries in progress:
     - Navigate to → Shipment Tracking
     - View map of in-transit orders (if available)
     - Check for any delivery exceptions
     - Contact delivery staff if issues reported
   - Update system with real-time location/status

6. **Delivery Status Updates** (Throughout day)
   - Receive status updates from delivery staff:
     - "Picked Up": Order collected from hub
     - "In Transit": On delivery route
     - "Delivered": Delivered to receiver
     - "Failed": Unable to deliver, with reason
   - Mark statuses in system with timestamp
   - Notify clients of delivery (auto-email in system)

7. **Exception Handling** (Throughout day)
   - Address delivery issues:
     - **Receiver Not Available**: 
       - Attempt next day
       - Contact client for alternate time
       - Mark status "Pending Redelivery"
     - **Wrong Address**:
       - Contact receiver
       - Correct address if needed
       - Reroute shipment
     - **Damaged Shipment**:
       - Document with photos
       - Notify manager/admin
       - Create claim record
     - **Lost Shipment**:
       - Formal report to admin
       - Client claims process initiated
       - Investigation note in system

8. **End of Day Report**
   - Navigate to → Operations Report
   - Summarize:
     - Total shipments processed: XX
     - Delivered successfully: XX (%)
     - Failed deliveries: XX (reasons)
     - Average delivery time: X days
     - Customer complaints: XX
   - Submit report to manager

9. **Due Reports** (Daily/Weekly)
   - Generate client due reports:
     - Navigate to → Reports → Client Due Report
     - Shows unpaid invoices by client
     - Aging (0-30 days, 30-60 days, 60+ days)
     - Total amount due by client
     - Used for chasing payments with clients

---

### STAFF WORKFLOW

#### Daily Staff Tasks:

1. **Shift Start**
   - Log in → Staff Dashboard
   - Quick links displayed:
     - Create Walk-In Order
     - Create Client Order
     - View Today's Orders
     - Quick Receipt Lookup

2. **Walk-In Orders** (60-70% of work)
   - Customer arrives with shipment
   - Follow Flow 1: Walk-In Order Creation & Billing
   - Typical time: 5-10 minutes per order
   - Tasks:
     - Weighing & inspection
     - Details entry (sender/receiver)
     - Pricing calculation & review
     - Offer application (if applicable)
     - Bill generation
     - Payment collection
     - Receipt provision

3. **Client Orders** (20-30% of work)
   - Client calls/visits with requirements
   - Follow Flow 2: Client Order Creation & Management
   - Typical time: 3-5 minutes per order
   - Tasks:
     - Client & receiver selection
     - Shipment details entry
     - Auto-pricing calculation
     - Discount application
     - Invoice/waybill generation
     - Email confirmation

4. **Order Lookup** (Throughout day)
   - Customer calls: "Can you check my order?"
   - Navigate to → Orders
   - Search by:
     - Order ID
     - Sender mobile number
     - Receiver mobile number
     - Date range
   - Provide customer with:
     - Current status
     - Estimated delivery time
     - Tracking details

5. **Quick Receipts**
   - Customer lost receipt, needs duplicate
   - Navigate to → Orders → Search
   - Find order → Click "Print Receipt"
   - Generate PDF or direct print

6. **Issue Escalation**
   - Customer complaint about pricing:
     - Review order calculation
     - Verify weight classification
     - Check for applicable offers
     - If error found, inform manager for adjustment
   - Customer complaint about delivery:
     - Provide tracking information
     - Escalate to Operation Manager
     - Get ticket number to provide customer

7. **End of Shift**
   - Verify all orders from shift are entered
   - Review any unfinalized orders
   - Handoff notes to next shift (if applicable)
   - Log out

#### Staff Best Practices:

- **Always verify phone numbers**: Ensures customer can be reached if issues arise
- **Confirm receiver location**: Prevents misdelivery due to wrong address
- **Apply auto-matched offers**: Staff should always apply the green auto-matched offer shown by system
- **Get proper weights**: Accuracy in weight determines pricing - use calibrated scales
- **Clarify shipping modes**: Explain delivery timeframes so customer chooses appropriate mode

---

### DELIVERY STAFF WORKFLOW

#### Daily Delivery Tasks:

1. **Shift Start**
   - Log in via mobile app or portal
   - Navigate to → "My Deliveries"
   - View assigned orders for today:
     - List showing all orders assigned to delivery staff
     - Each order shows: Order ID, Receiver Name, Destination, Expected delivery time

2. **Route Planning**
   - Receive batch of 15-30 orders
   - Review geographic clustering:
     - Group orders by delivery area
     - Plan optimal route
     - Usually provided by Operation Manager

3. **Package Pickup**
   - Receive packages from Operation Manager/Hub
   - For each package:
     - Scan Order ID (barcode)
     - Confirm order details:
       - Receiver name
       - Destination address
       - Fragile/special handling notes
     - Physical verification (count, condition)
     - Acknowledge on system: "Picked Up"
     - Status updates to "Picked Up" in system

4. **In-Transit Updates**
   - While en route:
     - Provide GPS location to system (auto-tracked if available)
     - Update system every 2-3 hours: Mark orders as "In Transit"
     - Contact customer if address unclear or need specific delivery time

5. **Delivery Execution**
   - Arrive at delivery location
   - Attempt delivery:
     - Ring bell/knock
     - Verify receiver identity
     - Get signature on waybill
     - Note delivery time
     - Provide receipt/POD (proof of delivery)
   - Update system: Mark order as "Delivered" with timestamp
   - System auto-sends confirmation email to receiver

6. **Delivery Exceptions**
   - **Receiver Not Available**:
     - Note time of attempt
     - Contact receiver if phone available
     - Ask for convenient delivery time
     - Mark status: "Attempted - Will Retry"
     - Schedule reattempt for next day
   
   - **Address Not Found**:
     - Inform Operation Manager immediately
     - Contact customer for clarification
     - Share corrected address in system
     - Reattempt next day if needed
     - Mark status: "Address Clarification Needed"
   
   - **Receiver Refused**:
     - Note reason (damaged, incorrect item, etc.)
     - Mark status: "Refused"
     - Return package to hub
     - Operation Manager contacts client
   
   - **Package Damaged**:
     - Document damage with photos
     - Note details in system
     - Still deliver with damage note
     - Operation Manager initiates claim process

7. **End of Day**
   - Sync all updates to system
   - Log off
   - Provide feedback to Operation Manager on:
     - Delivery challenges
     - Address corrections needed
     - Customer feedback/complaints

#### Delivery Staff KPIs Tracked:

- **On-Time Delivery**: Orders delivered by promised date
- **First-Time Success Rate**: Delivered on first attempt
- **Average Deliveries/Day**: Productivity metric
- **Customer Feedback Rating**: Based on receiver feedback
- **Damage/Loss Rate**: Should be <0.1%

---

## Core Business Processes

### Process 1: Complete Order Lifecycle

**Timeline**: Order creation → Delivery → Billing → Payment
**Actors**: Staff, Operation Manager, Delivery Staff, Manager, Customer

```
┌─────────────────────────────────────────────────────────────────┐
│ WALK-IN ORDER CREATED                                           │
│ - Order ID generated                                            │
│ - Status: "Created"                                             │
│ - Awaiting payment                                              │
│ - Bill generated                                                │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─ PAYMENT PROCESSING
             │  └─ Status: "Payment Received" (on payment)
             │
             ├─ HUB INTAKE
             │  └─ Status: "Received at Hub"
             │     └─ Operation Manager scans package
             │
             ├─ SORTING & ROUTING
             │  └─ Status: "Assigned to Courier"
             │     └─ Assigned to delivery staff
             │
             ├─ IN-TRANSIT
             │  └─ Status: "In Transit"
             │     └─ Dispatch notification sent
             │
             ├─ DELIVERY ATTEMPTS
             │  ├─ First Attempt: Today
             │  │  └─ Status options:
             │  │     ├─ "Delivered" → SUCCESS
             │  │     └─ "Pending Redelivery" → RETRY
             │  │
             │  └─ Subsequent Attempts: Next days
             │     └─ Auto-reattempts on failed delivery
             │
             ├─ FINAL DELIVERY
             │  └─ Status: "Delivered"
             │     └─ Proof of delivery obtained
             │     └─ Confirmation email sent to receiver
             │     └─ Tracking history updated
             │
             └─ BILLING & PAYMENT
                └─ Invoice finalized
                └─ Revenue recognized
                └─ Payment marked complete
```

**Tracking Points**:
- Customer can view order status in tracking system anytime
- Email notifications sent at each major status change
- SMS notifications for time-sensitive updates (delivery tomorrow, out for delivery, delivered)

---

### Process 2: Pricing Calculation (Critical Math)

**Scenario 1: Walk-In Order - Standard Pricing**
```
Order Details:
- Sender State: Maharashtra
- Receiver State: Delhi
- Weight: 450g
- Shipping Mode: Prime Express

Pricing Table for Delhi (from Default Prices):
- 100g: ₹50
- 250g: ₹80
- 500g: ₹120
- 1kg: ₹160
- 2kg: ₹250
- 3kg: ₹320
- Extra per kg: ₹45

Calculation:
1. Weight 450g falls between 250g and 500g
2. Use 500g tier rate: ₹120

Base Amount: ₹120
Shipping mode surcharge: +₹20 (for Prime Express)
Subtotal: ₹140

Apply Offer (if eligible):
- Order amount ₹140 qualifies for "Summer Discount" (min ₹100, max ₹500)
- Discount type: 10% off
- Discount amount: ₹140 × 10% = ₹14

FINAL AMOUNT: ₹140 - ₹14 = ₹126
```

**Scenario 2: Walk-In Order - Extra Weight (>3kg)**
```
Order Details:
- Receiver State: Karnataka
- Weight: 5.2kg
- Shipping Mode: Standard

Pricing Table for Karnataka:
- 1kg: ₹80
- 2kg: ₹140
- 3kg: ₹190
- Extra per kg: ₹35

Calculation:
1. Weight 5.2kg > 3kg, use new extra_per_kg logic
2. Amount = weight × extra_per_kg
3. Amount = 5.2 × ₹35 = ₹182

Base Amount: ₹182
(No mode surcharge for standard)
Total: ₹182

No applicable offers
FINAL AMOUNT: ₹182
```

**Scenario 3: Client Order - With Client Pricing**
```
Order Details:
- Client: "ABC Logistics Ltd"
- Billing Pattern: Pattern 15 (15% discount)
- Receiver State: Tamil Nadu
- Weight: 2.5kg
- Shipping Mode: Road Express

System Check Hierarchy:
1. Check if ABC Logistics has custom pricing for Tamil Nadu
   ✓ Found: Custom pricing exists
   
Client-Specific Pricing for Tamil Nadu:
- 100g: ₹40
- 250g: ₹65
- 500g: ₹95
- 1kg: ₹130
- 2kg: ₹200
- 3kg: ₹270
- Extra per kg: ₹38

Calculation:
1. Weight 2.5kg falls between 2kg and 3kg
2. Use 3kg tier rate: ₹270

Base Amount: ₹270
Road Express surcharge: +₹15
Subtotal: ₹285

Apply Billing Pattern Discount:
- Pattern 15: 15% discount
- Discount = ₹285 × 15% = ₹42.75

FINAL AMOUNT: ₹285 - ₹42.75 = ₹242.25
```

**Scenario 4: Client Order - With Offer**
```
Using Scenario 3 base: ₹285

Check Offers:
- "Monsoon Special": ₹25 flat discount
  - Conditions: Min order ₹250, Max ₹500
  - ₹285 qualifies ✓
  
Apply both Offer and Pattern:
1. Subtotal: ₹285
2. Offer discount: -₹25 → ₹260
3. Pattern discount (15% on original): -₹42.75 → ₹217.25

FINAL AMOUNT: ₹217.25
```

---

### Process 3: Payment & Collections Workflow

**For Walk-In Orders**:
1. Amount finalized at counter
2. Cash collection (payment method: cash only typical)
3. Receipt provided immediately
4. Payment status: "Completed" marked in system immediately
5. No follow-up required

**For Client Orders (Post-Paid)**:
1. Order created in system
2. Payment status: "Pending"
3. Invoice sent to client email automatically
4. Due date: Typically NET 30 (configurable)
5. Manager tracks payments:
   - Navigate to Reports → Client Due Report
   - Shows all unpaid invoices by aging
   - Follows up with overdue clients
6. When payment received:
   - Manager marks payment in system
   - Status updates to "Paid"
   - Confirmation email sent

**Late Payment Handling**:
- 0-30 days: Friendly reminder email
- 30-60 days: Follow-up call/email
- 60+ days: Formal notice, possible service suspension
- Resolved: Payment marked, status updated

---

### Process 4: Returns & Refunds (Exception Process)

**Customer Initiated Return**:
1. Customer contacts staff with return request
2. Reason documented:
   - Damaged item
   - Wrong delivery
   - Receiver refusal
   - Address issue
3. Staff creates return order in system:
   - Original Order ID linked
   - Reason noted
   - Status: "Return Initiated"
4. Customer ships item back (reverse logistics)
5. On return receipt:
   - Operation Manager verifies condition
   - Updates status: "Return Received"
6. Manager reviews and approves refund:
   - Verifies condition matches claim
   - Approves refund amount
   - Updates status: "Refund Approved"
7. Refund processed:
   - For walk-in: Cash refund at counter
   - For client: Credit note or bank transfer
8. Order marked: "Refund Processed"

**Claiming Process Average Time**: 7-14 days

---

## Technical Administrative Tasks

### Task 1: Database Backup & Recovery

**Daily Backup Procedure** (Automated, monitored by Admin):

1. **Automatic Backup Execution**
   - Scheduled: 2:00 AM daily
   - Database dump created with timestamp
   - Location: `/backups/` directory
   - Retention: Keep last 30 days of backups

2. **Verification Check** (Manual, once weekly)
   - Admin navigates to → Maintenance → Backup Status
   - Verifies latest backup:
     - File size (should be >5MB indicating data)
     - Timestamp (should be recent)
     - File integrity (runs checksum)
   - Check backup log for errors
   - Alert if backup failed

3. **Monthly Archive**
   - End of month: Archive backup to cold storage
   - Retention: 1 year compliance requirement
   - Test restore once quarterly to ensure recovery capability

4. **Recovery Procedure** (Emergency only):
   - Contact database administrator
   - Specify recovery point (date/time)
   - System restored from backup
   - Data loss: Up to maximum 24 hours (since daily backups)

---

### Task 2: User Management & Access Control

**Adding New User**:
1. Admin navigates to → Users & Roles
2. Click "Add New User"
3. Enter:
   - Full Name
   - Email Address
   - Assigned Role (from dropdown):
     - Admin
     - Manager
     - Operation Manager
     - Staff
     - Delivery
4. Click "Create"
   - System generates temporary password
   - Sends email with login credentials and link to set new password
   - User receives email, sets password on first login
5. User account activated and ready

**Modifying User Role**:
1. Admin → Users & Roles
2. Find user in list
3. Click "Edit"
4. Change role in dropdown
5. Click "Save"
   - Changes effective immediately
   - User sees new functionality on next login
   - Old permissions removed
   - Audit log records role change

**Deactivating User**:
1. Admin → Users & Roles
2. Find user
3. Click "Deactivate"
   - User can no longer log in
   - All data remains in audit trail
   - Can be reactivated later if needed

**User Activity Audit** (Compliance & Security):
1. Admin → Audit Logs
2. View all user actions:
   - Login/logout times
   - Orders created by user (timestamp)
   - Pricing changes made
   - Data exports
   - Settings modifications
3. Filter by:
   - Date range
   - User name
   - Action type
4. Use for:
   - Compliance verification
   - Identifying unauthorized access
   - Performance evaluation
   - Fraud investigation

---

### Task 3: System Settings & Configuration

**Email Configuration**:
1. Admin → Settings → Email Configuration
2. Configure:
   - SMTP Server (e.g., Gmail, SendGrid, custom server)
   - Authentication credentials
   - From email address
   - Notification templates
3. Use for:
   - Customer order status emails
   - Client invoices
   - Staff notifications
   - Admin alerts

**Mobile App Configuration** (if applicable):
1. Admin → Settings → Mobile App
2. Configure:
   - Push notification settings
   - GPS tracking accuracy
   - Offline mode behavior
   - Sync frequency

**System-Wide Settings**:
1. Admin → Settings → System
2. Adjust:
   - Default currency (₹)
   - Tax rate (if applicable)
   - Default delivery timeframes
   - Minimum order value
   - Return period (days)
   - Payment terms for clients (NET 30, NET 60, etc.)

---

### Task 4: Data Export & Reporting

**Scheduled Report Generation**:

**Daily Summary**:
- Orders created: XX
- Revenue: ₹XXXX
- Deliveries completed: XX%
- Average delivery time: X days

**Weekly Performance**:
- Top 5 clients by revenue
- Busiest routes (states)
- Shipping mode distribution
- Customer complaint summary

**Monthly Analysis**:
- Month-over-month growth
- Client profitability analysis
- Route profitability
- Staff productivity ratings
- Expense breakdown

**Report Export Options**:
1. Navigate to → Reports
2. Select report type
3. Choose:
   - **View Online**: Display in browser
   - **Download PDF**: Professional formatted PDF
   - **Export Excel**: Raw data for further analysis
   - **Email Report**: Auto-send to specified recipients

---

### Task 5: System Performance Monitoring

**Monthly Performance Review**:
1. Admin → System Health
2. Monitor:
   - Database size (growth rate)
   - Server response time
   - Peak usage hours
   - System errors/exceptions
   - User login frequency

**Actions if issues detected**:
- **Slow response time** (>3 seconds)
  - Check database size - may need cleanup of old records
  - Review active user count - may need server scaling
  - Check for storage issues

- **High error rate** (>0.5%)
  - Review error logs
  - Identify failing features
  - Prioritize bug fixes
  - Notify development team

- **Storage capacity** (>80%)
  - Archive old records to cold storage
  - Delete temporary files
  - Plan storage upgrade

---

## Troubleshooting Guide

### Issue: Order Calculation Incorrect

**Symptom**: Customer says bill amount doesn't match system
**Diagnosis Steps**:
1. Retrieve order from system
2. Note order details:
   - Weight
   - Receiver state
   - Shipping mode
   - Applied offer
3. Cross-check pricing:
   - Verify state pricing table in Pricing Configuration
   - Manually calculate using formulas above
   - Check weight classification logic (if >3kg)
4. Verify offers:
   - Check if offer was applicable
   - Verify discount calculation

**Common Causes & Solutions**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Amount lower than expected | System applied auto-matched offer | Check offer details - may be valid |
| Amount higher than expected | Wrong pricing table used | Verify correct state pricing, may need to use client-specific pricing |
| Weight-based calculation off | Weight misclassified | For >3kg, ensure using formula: weight × extra_per_kg |
| Billing pattern not applied | Pattern not selected during client creation | Re-edit client, select correct pattern |

---

### Issue: Order Cannot Be Created

**Symptom**: "Create Order" button grayed out or error appears

**Diagnostic Steps**:
1. Check all required fields filled:
   - Sender details (name, mobile, email)
   - Receiver details (name, mobile, email, address)
   - Weight and shipment type
   - Shipping mode selected

2. Verify address:
   - State must exist in system
   - If new state needed: Right-click state field → Add New State → Save

3. Check weight constraints:
   - Minimum: 0.1 kg
   - Maximum: 100 kg (configurable)
   - Must be numeric

4. Verify pricing availability:
   - Check selected state has pricing configured
   - If no pricing found: Cannot create order until pricing added

**Solutions by Error Message**:

| Error | Fix |
|-------|-----|
| "Sender state cannot be empty" | Select sender state from dropdown |
| "Invalid pincode format" | Enter valid Indian pincode (6 digits) |
| "No pricing available for this state" | Contact manager to configure state pricing |
| "Order amount calculation failed" | System error - contact admin |
| "Offer cannot be applied" | Offer may be expired, try without offer |

---

### Issue: Delivery Status Not Updating

**Symptom**: Order shows "In Transit" but hasn't updated in 12+ hours

**Diagnosis**:
1. Check delivery staff:
   - Is delivery staff logged in?
   - Do they have access to this order?
   - Have they attempted delivery?

2. Check communication:
   - Verify delivery staff has mobile connectivity
   - System updates only on explicit status change by staff
   - GPS tracking (if available) may be enabled but not visible

3. Manager Follow-up:
   - Contact Operation Manager
   - Verify package with driver
   - Check if delivery is planned for next day

**Solutions**:
- **If stuck >24 hours**: Operations Manager contacts delivery staff directly
- **If address issue**: Correct address in system, reattempt delivery
- **If customer moved**: Contact customer for updated address
- **If staff unavailable**: Reassign to different delivery staff

---

### Issue: Client Receives Wrong Pricing

**Symptom**: Invoice shows higher/lower rate than negotiated

**Root Causes**:
1. **Billing Pattern not selected**: Client created without pattern assignment
   - **Fix**: Edit client, select correct pattern
   - **Apply to pending orders**: Manager can manually adjust invoices

2. **Wrong pricing table used**: System using default instead of client-specific
   - **Fix**: Verify client-specific pricing configured for that state
   - **Check**: Pricing Configuration → Client State Prices

3. **Offer applied when shouldn't be**: Order autom-applied unwanted discount
   - **Fix**: Check offer validity criteria
   - **Resolve**: Re-invoice without offer

**Prevention**:
- Verify client setup before creating first order
- Confirm all pricing configured correctly
- Test with sample order calculation
- Get client sign-off on pricing before go-live

---

### Issue: Payment Marked as Paid When Wasn't

**Symptom**: Client disputes paid amount
**Investigation**:
1. Retrieve order/invoice
2. Check payment status in system
3. Review audit log: Who marked as paid? When?
4. Verify against actual payment records

**Recovery**:
- If accidental marking: Revert status to "Pending"
- If multiple orders affected: Bulk correction possible
- Follow up with staff member to prevent repeat
- Ensure only Finance team members mark payments

---

### Issue: Staff Cannot Access Walk-In Order Feature

**Symptom**: "Create Walk-In Order" button not visible

**Causes**:
1. User role doesn't have permission
   - **Fix**: Admin updates user role to Staff or higher
2. Staff user (doesn't have delivery driver role)
   - **Fix**: Verify user has Staff role, not just Delivery role
3. Permission synchronization delay
   - **Fix**: User logs out and back in to refresh permissions

**Resolution**:
- Admin → Users & Roles
- Find user → Click Edit
- Verify role includes Staff or Manager capability
- Click Save
- User logs out/back in

---

### Issue: Printing Bill Fails

**Symptom**: "Generate Bill" → "Print" produces blank page or error

**Causes**:
1. **Printer not connected**: 
   - **Fix**: Check printer connection, test with notepad print first
   
2. **PDF generation failed**:
   - **Symptom**: Error message appears
   - **Fix**: Try "Download PDF" instead of printing
   - If still fails: Check system logs, contact admin

3. **Browser print settings**:
   - **Fix**: Try different browser (Chrome vs Edge)
   - Disable header/footer: Browser → Print → More Settings

**Alternative**:
- Use "Download PDF" to get file
- Print using Adobe Reader or alternative PDF viewer
- Email PDF directly to customer if printing unavailable

---

### Issue: Email Notifications Not Received

**Symptom**: Customer didn't receive order confirmation email

**Check**:
1. **Email address correct**: Verify in order details
2. **Email configuration active**: Admin → Settings → Email
   - SMTP configured?
   - Email enabled?
   - Test email sent successfully?

3. **Email not in spam**: Customer should check spam/junk folder
4. **Manual resend**: Manager can resend invoice/confirmation email

**Long-term Fix**:
- Admin verifies Email Configuration
- Test with admin email first
- Add to whitelist if using corporate email
- Switch email provider if consistent issues (Gmail → SendGrid for reliability)

---

### Issue: Report Generation Takes Too Long

**Symptom**: "Generate PDF" button loading >30 seconds

**Causes**:
1. **Large dataset**: Report covering 1000+ orders
   - **Reduce scope**: Filter by smaller date range
   - **Use Excel export**: Faster than PDF

2. **Server busy**: Other heavy processing happening
   - **Retry later**: Try during off-peak hours (11 PM - 5 AM)

3. **System slowness**: General performance issue
   - **Contact Admin**: May indicate server resources needed

**Workarounds**:
- **Export to Excel instead**: Much faster
- **Break into smaller reports**: Week-by-week instead of full month
- **Schedule off-peak**: Generate reports overnight for morning review

---

### Issue: Database Running Out of Space

**Symptom**: "Disk quota exceeded" error when trying to create orders

**Admin Actions**:
1. Check database size:
   - Admin → Maintenance → Database Info
   - If >90% full: Immediate action needed

2. Clean old data:
   - Archive completed orders >1 year old
   - Delete test/demo records
   - Remove old log entries

3. Plan upgrade:
   - Contact hosting provider for storage expansion
   - Or move to bigger server
   - Perform migration during off hours

4. Implement retention policy:
   - Delete orders after 5 years (compliance check first)
   - Auto-archive monthly for compliance storage

---

## Appendix: Quick Reference

### Quick Links by Role:

**Admin**:
- Dashboard: /admin/dashboard
- User Management: /admin/users
- System Settings: /admin/settings
- Reports: /reports

**Manager**:
- Clients: /clients
- Pricing: /pricing
- Orders: /orders
- Reports: /reports/manager

**Operation Manager**:
- Shipments: /operations/shipments
- Tracking: /operations/tracking
- Deliveries: /operations/deliveries
- Reports: /reports/operations

**Staff**:
- Walk-In Order: /order/walkin
- Client Order: /order/client
- Order Search: /orders/search

**Delivery**:
- My Deliveries: /delivery/myorders
- Update Status: /delivery/update-status

### Keyboard Shortcuts (Optional, if implemented):

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Walk-In Order |
| Ctrl+Shift+N | New Client Order |
| Ctrl+F | Search Orders |
| Ctrl+P | Print Bill |

### Contact & Support:

**For System Issues**: Email support@crmdeliv.com
**For Pricing Questions**: Contact Manager
**For Delivery Issues**: Contact Operation Manager
**For User Access**: Contact Admin
**For Emergency**: Phone: (emergency contact number)

---

## Conclusion

This workflow documentation provides comprehensive guidance for all users of the B2B Courier & Delivery Management System. Each user should familiarize themselves with their role's specific workflows and refer to the troubleshooting guide for common issues.

**Key Takeaways**:
1. Always verify important details (phone, address) at data entry time
2. Leverage system features like auto-matched offers and auto-pricing
3. Escalate issues to appropriate managers when needed
4. Maintain accurate records for compliance and future reference
5. Use reports regularly to monitor performance and identify improvements

For questions or improvements to this documentation, please contact the Admin team.

---

**Document Version**: 1.0
**Last Updated**: March 2026
**Created For**: B2B Courier & Delivery Management System
