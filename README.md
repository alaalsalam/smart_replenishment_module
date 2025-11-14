# Smart Replenishment Module for Pharmacy Supply Chain

Intelligent inventory management system for ERPNext that automatically analyzes consumption patterns and generates purchase orders when stock reaches critical levels.

---

## What This Module Does

The Smart Replenishment Module extends ERPNext with intelligent, data-driven inventory management specifically designed for pharmacy supply chains. It analyzes historical consumption patterns to calculate optimal reorder points and automatically generates purchasing recommendations.

**Key Capability:** Instead of manually tracking when to reorder, the system tells you exactly when and what to order based on actual usage patterns.

---

## Features

### 📊 Intelligent Reorder Points
- Analyzes last 90 days of consumption from stock ledger
- Calculates average daily usage
- Accounts for supplier lead times
- Adds safety stock buffer (configurable in days)
- **Result:** Optimal reorder point = (Daily Usage × Lead Time) + Safety Stock

### 🏢 Warehouse-Specific Settings
- Different reorder levels for same item across warehouses
- Each warehouse can have preferred supplier
- Separate safety stock settings per location
- Lead time variations by warehouse
- **Independent calculations per warehouse** - each location analyzed separately

### 🔄 Automated Recommendations
- Daily scheduler scans inventory at 12:00 AM
- Generates recommendations when stock < reorder point
- Prevents duplicate recommendations
- Priority-based (High/Medium/Low) based on urgency

### 📦 Purchase Order Integration
- Converts approved recommendations → Purchase Orders automatically
- Tracks which recommendations created which POs
- Maintains full audit trail
- Seamless ERPNext integration

### 🎯 Intelligent Supplier Selection
- **4 Selection Strategies:** Preferred Supplier, Shortest Lead Time, Lowest Cost, Balanced
- Automatically evaluates all available suppliers
- Considers lead times and prices for optimal selection
- Configurable per organization needs
- See [Supplier Selection Strategies](#supplier-selection-strategies) for details

### 🔔 Notification System
- **Configurable Recipients:** Notify specific users or entire roles
- **Priority-Based Filtering:** Choose when to send notifications:
  - **All:** Notify for all recommendations (High, Medium, Low priority)
  - **High Only:** Only critical stock situations
  - **High & Medium:** Exclude low-priority recommendations
- **Real-Time Alerts:** Notifications sent immediately when recommendations are created
- **Notification Log Tracking:** All notifications logged in ERPNext's Notification Log
- **Automatic Delivery:** System notifications appear in user's notification center
- **Test Verification:** Automated test cycle verifies notification delivery

### 🔐 REST API
- Full API access for external systems
- Get recommendations with filters
- Approve/reject programmatically
- Create POs via API
- Perfect for mobile apps or third-party systems

### 💊 Pharmacy-Specific Features
- **Prescription Flag:** Mark medications requiring prescriptions
- **Compliance Ready:** Audit trail for all replenishment decisions
- **Multi-Warehouse:** Manage central + local pharmacies
- **Supplier Flexibility:** Multiple suppliers per item

### 🔄 Automatic Stock Movement Integration
- **Real-time Reorder Updates:** Stock Entry, Delivery Note, and Sales Invoice submissions automatically trigger reorder point recalculation
- **Recommendation Auto-Generation:** When stock falls below reorder level after a movement, recommendations are automatically created
- **Background Processing:** All calculations run asynchronously without blocking your workflow
- **Warehouse-Specific:** Only non-group warehouses are available for reorder configuration

### 💰 Intelligent Pricing
- **Multi-Source Rate Retrieval:** Automatically fetches rates from Purchase Order history, valuation rate, or standard rate
- **Currency Handling:** Supports multi-currency operations with automatic exchange rate handling
- **Estimated Costs:** Real-time cost estimation based on current rates and recommended quantities
- **Valuation Rate Fallback:** Uses item's valuation rate (most accurate for costing) when purchase history is unavailable

### 🔧 Flexible Consumption Calculation
- **Configurable Method:** Choose between "Active Days Only" (more accurate for sporadic sales) or "Full Period" (more conservative)
- **Active Days Only:** Divides consumption by days with actual transactions - better for items with irregular sales
- **Full Period:** Divides by entire analysis period - accounts for idle days, more conservative approach
- **Dynamic Adjustment:** System adapts to your business patterns

---

## Installation

### System Requirements
- **ERPNext:** Version 15 (latest stable)
- **Python:** 3.10+
- **Database:** MariaDB 10.6+

### Step 1: Install the App

```bash
cd ~/your-bench-directory

# Get the app from repository
bench get-app smart_replenishment_module https://github.com/yourusername/smart-replenishment-module

# Install to your site
bench install-app smart_replenishment_module --site your-site-name
```

### Step 2: Run Migrations

```bash
bench migrate --site your-site-name
```

This will:
- Create custom fields on Item and Item Reorder
- Set up Replenishment Recommendation DocType
- Configure Replenishment Settings
- Install workflows and notifications

### Step 3: Disable Standard Auto-Reorder (IMPORTANT)

By default, ERPNext creates Material Requests automatically. Since we create Purchase Orders directly, we need to disable this:

1. Login to ERPNext
2. Search for **Stock Settings**
3. **Uncheck** "Raise Material Request When Stock Reaches Re-order Level"
4. Save

**Why?** Our module creates POs directly. The standard ERPNext feature would conflict with our workflow.

### Step 4: Restart and Clear Cache

```bash
bench restart
bench clear-cache
```

---

## Initial Setup

### 1. Configure Replenishment Settings

Navigate to **Replenishment Settings** and set:

| Setting | Default | Description |
|---------|---------|-------------|
| **Consumption Period (Days)** | 90 | Days of history to analyze |
| **Consumption Calculation Method** | Active Days Only | How to calculate average daily consumption: "Active Days Only" (more accurate for sporadic sales) or "Full Period" (more conservative) |
| **Enable Safety Stock (Days) Auto-Population** | Disabled | When enabled, auto-populates Safety Stock (Days) from default when adding new Item Reorder rows |
| **Default Safety Stock (Days)** | 2 | Default buffer days (only visible if auto-population enabled) |
| **Enable Supplier Lead Time (Days) Auto-Population** | Disabled | When enabled, auto-populates Supplier Lead Time (Days) from default when adding new Item Reorder rows |
| **Default Supplier Lead Time (Days)** | 7 | Default lead time in days (only visible if auto-population enabled) |
| **Auto-Generate Recommendations** | Enabled | Daily automatic generation |
| **Supplier Selection Strategy** | Preferred Supplier | How to select supplier when multiple available (see [Supplier Selection Strategies](#supplier-selection-strategies) below) |
| **Notify On Priority** | All/High Only/High & Medium | When to send notifications (see [Notification Configuration](#notification-configuration) below) |

**Note:** 
- The Safety Stock (Days) and Supplier Lead Time (Days) fields are **always visible** in the Item Reorder table
- The checkboxes control **auto-population** behavior:
  - **Enabled (checked)**: Fields auto-populate from default values when adding new rows
  - **Disabled (unchecked)**: Fields are visible but user enters values manually

### 2. Set Up Item Reorder Levels

For each inventory item:

1. Navigate to **Item** (Search bar)
2. Scroll to **Reorder Level** table
3. Add rows for each warehouse:

```
Warehouse: Main Store
  ├─ Warehouse Reorder Level: (Mandatory - Auto-calculated based on consumption)
  ├─ Warehouse Reorder Qty: 500 (order this much when low)
  ├─ Safety Stock Days: 2 (keep 2 days of buffer) [Auto-filled if enabled, or enter manually]
  ├─ Supplier Lead Time Days: 7 (takes 7 days to arrive) [Auto-filled if enabled, or enter manually]
  └─ Preferred Supplier: ABC Pharma
```

**Note:** 
- Safety Stock Days and Supplier Lead Time Days fields are **always visible** in Item Reorder table
- If auto-population is enabled in Settings, default values are automatically filled when adding new rows
- If auto-population is disabled, you enter values manually
- Calculated fields (Minimum Stock Level, Maximum Stock Level, Reorder Point, Average Daily Consumption) are read-only and updated automatically

### 3. Enable Scheduler

The module runs scheduled tasks automatically. Ensure bench scheduler is running:

```bash
# Check if scheduler is running
bench worker list

# If not running, start it
bench worker start
```

---

## How It Works: Complete Flow

### Day-to-Day Operation

```
1. Stock Changes
   └─ Item used in pharmacy
      └─ Stock decreases (via Sales/Stock Issue)

2. Daily Analysis (12:00 AM)
   └─ Scheduler analyzes stock levels
   └─ Checks against reorder points
   └─ Generates recommendations for items below threshold

3. Review & Approve
   └─ Pharmacist reviews recommendation
   └─ Uses workflow actions (Approve/Reject buttons) to change status
   └─ Status field is read-only and managed by workflow system (Pending → Approved/Rejected)
   └─ When approved and submitted, system creates Purchase Order automatically
   └─ Status automatically transitions to "Ordered" when PO is created (via workflow transition)

4. Purchase Order
   └─ PO sent to supplier
   └─ Tracked in ERPNext
   └─ On arrival, receive goods
   └─ Stock replenished
   └─ If PO is cancelled, recommendation resets to "Pending" for re-processing

5. Cycle Repeats
   └─ System continues monitoring
   └─ New recommendations generated as needed
```

### Reorder Point Calculation

The system uses this formula:

```
Reorder Point = (Average Daily Consumption × Lead Time Days) + Safety Stock

Example:
- Average Daily: 50 units/day
- Lead Time: 7 days
- Safety Stock: 2 days

Reorder Point = (50 × 7) + (50 × 2) = 450 units
```

When current stock < 450 units:
- System creates a recommendation
- Recommends ordering 500 units (your warehouse_reorder_qty)
- Marks as "High Priority" if very low
- Notifies configured users

### Priority Assignment

- **High:** Stock < 50% of reorder point (critical)
- **Medium:** Stock between 50-80% of reorder point (soon)
- **Low:** Stock 80-100% of reorder point (planned)

---

## Multiple Warehouses: How It Works

When an item exists in **multiple warehouses**, the system handles each warehouse **independently**. Here's exactly what happens:

### Example Scenario

**Item:** "Paracetamol 500mg" (Item Code: `PAR-500`)

**Warehouses:**
- Main Pharmacy (Warehouse: `Main - P`)
- Branch Pharmacy A (Warehouse: `Branch A - P`)
- Branch Pharmacy B (Warehouse: `Branch B - P`)

### Step 1: Configuration (Item Reorder Table)

In the Item form, you add **3 separate rows** in the "Reorder Level" table:

```
Row 1:
  - Warehouse: Main - P
  - Reorder Qty: 500
  - Safety Stock Days: 5
  - Lead Time Days: 7
  - Preferred Supplier: Supplier A

Row 2:
  - Warehouse: Branch A - P
  - Reorder Qty: 300
  - Safety Stock Days: 3
  - Lead Time Days: 5
  - Preferred Supplier: Supplier B

Row 3:
  - Warehouse: Branch B - P
  - Reorder Qty: 200
  - Safety Stock Days: 2
  - Lead Time Days: 10
  - Preferred Supplier: Supplier A
```

### Step 2: Reorder Point Calculation

When you run **"Update Reorder Points"**, the system processes **each warehouse separately**:

**For Main - P:**
- Analyzes consumption history from Main Pharmacy only
- Calculates: `(Daily Usage × 7 days) + (Daily Usage × 5 days)`
- Example: If Main Pharmacy uses 50 units/day → Reorder Point = 600 units

**For Branch A - P:**
- Analyzes consumption history from Branch A only
- Calculates: `(Daily Usage × 5 days) + (Daily Usage × 3 days)`
- Example: If Branch A uses 30 units/day → Reorder Point = 240 units

**For Branch B - P:**
- Analyzes consumption history from Branch B only
- Calculates: `(Daily Usage × 10 days) + (Daily Usage × 2 days)`
- Example: If Branch B uses 20 units/day → Reorder Point = 240 units

**Result:** Each warehouse gets its **own reorder point** based on **its own consumption pattern**.

### Step 3: Recommendation Generation

When the daily scheduler runs, it checks **each warehouse independently**:

**Scenario:**
- Main - P: Current Stock = 400 units (Reorder Point = 600) → **Below threshold** ✓
- Branch A - P: Current Stock = 300 units (Reorder Point = 240) → **Above threshold** ✗
- Branch B - P: Current Stock = 100 units (Reorder Point = 240) → **Below threshold** ✓

**What Happens:**
1. **Main - P:** Creates recommendation `REP-REC-2025-00001`
   - Item: PAR-500
   - Warehouse: Main - P
   - Recommended Qty: 500 units
   - Supplier: Supplier A
   - Priority: Medium (400/600 = 67% of reorder point)

2. **Branch A - P:** No recommendation (stock is above reorder point)

3. **Branch B - P:** Creates recommendation `REP-REC-2025-00002`
   - Item: PAR-500
   - Warehouse: Branch B - P
   - Recommended Qty: 200 units
   - Supplier: Supplier A
   - Priority: High (100/240 = 42% of reorder point)

**Result:** **2 separate recommendations** for the same item, but different warehouses.

### Step 4: Purchase Order Creation

When you approve each recommendation:

1. **REP-REC-2025-00001** (Main - P) → Creates **PO-2025-00001**
   - Supplier: Supplier A
   - Qty: 500 units
   - Warehouse: Main - P

2. **REP-REC-2025-00002** (Branch B - P) → Creates **PO-2025-00002**
   - Supplier: Supplier A
   - Qty: 200 units
   - Warehouse: Branch B - P

**Result:** **2 separate Purchase Orders**, each for a different warehouse.

### Key Points

✅ **Independent Analysis:** Each warehouse's consumption is analyzed separately  
✅ **Separate Recommendations:** One recommendation per warehouse when needed  
✅ **Different Suppliers:** Each warehouse can have its own preferred supplier  
✅ **Warehouse-Specific Settings:** Safety stock, lead time, and reorder quantities are per warehouse  
✅ **No Conflicts:** Recommendations don't interfere with each other  
✅ **Accurate Calculations:** Reorder points reflect actual usage patterns per location  

### What If Multiple Warehouses Need the Same Item?

**Example:** Both Main - P and Branch B - P need Paracetamol

**System Behavior:**
- Creates **2 separate recommendations** (one per warehouse)
- Each recommendation has its own:
  - Recommended quantity (based on warehouse settings)
  - Preferred supplier (can be different)
  - Priority level (based on stock level in that warehouse)
  - Purchase Order (when approved)

**You can:**
- Approve both recommendations → Creates 2 separate POs
- Approve one, reject the other → Only one PO created
- Modify quantities before approving → Adjust per warehouse needs

### Benefits

1. **Location-Specific Optimization:** Each warehouse gets reorder points based on its actual usage
2. **Flexible Supplier Management:** Different warehouses can use different suppliers
3. **Independent Operations:** One warehouse's stock issues don't affect others
4. **Accurate Forecasting:** Consumption patterns are analyzed per location, not globally

---

## Supplier Selection Strategies

When an item is available from **multiple suppliers** with **different lead times and prices**, the system can intelligently select the best supplier based on your configured strategy. This is a key feature that helps optimize both delivery speed and cost.

**Configure the selection strategy in:** **Replenishment Settings** → **Supplier Selection Strategy**

### Available Strategies

#### 1. **Preferred Supplier** (Default)
- Uses the preferred supplier set in Item Reorder or recommendation
- Falls back to default supplier from Item Supplier table
- **Best for:** When you have established supplier relationships

#### 2. **Shortest Lead Time**
- Evaluates all available suppliers
- Selects the supplier with the **shortest delivery time**
- **Best for:** Urgent replenishment needs, critical items

#### 3. **Lowest Cost**
- Evaluates all available suppliers
- Selects the supplier with the **lowest price**
- **Best for:** Cost optimization, non-urgent items

#### 4. **Balanced (Lead Time + Cost)**
- Evaluates all available suppliers
- Normalizes lead time and cost (0-1 scale)
- Selects supplier with best **balanced score** (50% lead time, 50% cost)
- **Best for:** General use, balancing speed and cost

### How Lead Times Are Determined

**The lead time selection logic differs based on your strategy:**

#### For "Preferred Supplier" Strategy:
Lead time is determined in this priority order:

1. **Item Reorder → Supplier Lead Time Days** ⭐ **PRIMARY SOURCE**
   - **Manually entered** per warehouse/supplier combination
   - Location: Item → Reorder Level table → Supplier Lead Time (Days) field
   - **This is where you configure lead times** for each supplier per warehouse
   - **Most relevant** for preferred supplier strategy

2. **Item Price** (supplier-specific, price list-based)
   - Lead time per supplier per price list (if configured)
   - Location: Item Price → Lead Time in days field
   - Used as fallback if not set in Item Reorder

3. **Recommendation's Lead Time** (from reorder point calculation)
   - Lead time used when calculating the reorder point
   - Based on Item Reorder settings at recommendation creation time

4. **Item Level** (fallback)
   - General lead time for the item
   - Location: Item → Lead Time in days

#### For "Shortest Lead Time" / "Lowest Cost" / "Balanced" Strategies:
Lead time comes from the **evaluation process** (same priority for all suppliers):

1. **Item Reorder → Supplier Lead Time Days** ⭐ **PRIMARY SOURCE**
   - **Manually entered** per warehouse/supplier combination
   - Location: Item → Reorder Level table → Supplier Lead Time (Days) field
   - **This is where you configure lead times** for each supplier
   - Used during supplier evaluation

2. **Item Price** (supplier-specific, price list-based)
   - Lead time per supplier per price list (if configured)
   - Location: Item Price → Lead Time in days field
   - Used as fallback if not set in Item Reorder

3. **Item Level** (fallback)
   - General lead time for the item
   - Location: Item → Lead Time in days
   - Used if no supplier-specific data found

**Key Points:**
- **Primary Source:** Item Reorder → `supplier_lead_time_days` (manually entered)
- **Item Price:** Only used as fallback if lead time not set in Item Reorder
- **Same Logic:** Both strategies use the same priority, but Preferred Supplier uses it for one supplier, while intelligent strategies evaluate all suppliers

### Example Scenario

**Item:** "Paracetamol 500mg"

**Available Suppliers:**
- Supplier A: Lead Time = 5 days, Price = $10/unit
- Supplier B: Lead Time = 7 days, Price = $8/unit
- Supplier C: Lead Time = 10 days, Price = $7/unit

**Strategy: Shortest Lead Time**
- **Selected:** Supplier A (5 days)
- **Reason:** Fastest delivery

**Strategy: Lowest Cost**
- **Selected:** Supplier C ($7/unit)
- **Reason:** Cheapest option

**Strategy: Balanced**
- **Selected:** Supplier B (balanced score)
- **Reason:** Good balance between speed (7 days) and cost ($8)

### Setting Up Supplier Lead Times

**⭐ Option 1: Item Reorder (PRIMARY METHOD - Recommended)**
1. Go to **Item** → **Reorder Level** table
2. For each warehouse row:
   - Set **Preferred Supplier** (if using Preferred Supplier strategy)
   - Set **Supplier Lead Time (Days)** - **This is where you enter lead times**
3. **For multiple suppliers:** Create separate Item Reorder rows for each supplier-warehouse combination
   - Row 1: Warehouse A, Supplier X, Lead Time = 5 days
   - Row 2: Warehouse A, Supplier Y, Lead Time = 7 days
   - Row 3: Warehouse B, Supplier X, Lead Time = 10 days

**Note:** Item Reorder → `supplier_lead_time_days` is the **primary source** for lead times. This is manually entered per warehouse/supplier.

**Option 2: Item Price (Fallback)**
1. Go to **Item Price**
2. Create price for each supplier
3. Set **Lead Time in days** per supplier (if not set in Item Reorder)
4. Link to appropriate **Price List**
5. **Note:** Only used if lead time not set in Item Reorder

**Option 3: Item Level (General Fallback)**
1. Go to **Item**
2. Set **Lead Time in days** (applies to all suppliers if not set elsewhere)

### Important Notes

✅ **Supplier-specific lead times** are used when creating Purchase Orders  
✅ **Strategy applies globally** to all recommendations (configure in Replenishment Settings)  
✅ **Preferred supplier** always takes priority if set in Item Reorder  
✅ **Fallback logic** ensures a supplier is always selected if available  

---

## Automatic Recalculation: Step-by-Step Guide

When you change `supplier_lead_time_days` or `safety_stock_days` in Item Reorder settings, the system automatically recalculates everything. Here's exactly what happens at each step:

### Step 1: User Changes Values

**Action:** User edits Item → Changes `supplier_lead_time_days` or `safety_stock_days` in Reorder Level table

**Location:** Item form → Reorder Level child table

**Example:**
```
Before:
  - Supplier Lead Time Days: 7
  - Safety Stock Days: 2
  - Reorder Point: 450 units

User changes to:
  - Supplier Lead Time Days: 10
  - Safety Stock Days: 3
```

**File Involved:** `doc_events/item.py` (line 9)

---

### Step 2: User Saves Item

**Action:** User clicks "Save" button

**What Happens:**
- ERPNext validates the Item document
- Triggers `on_update` hook registered in `hooks.py`
- Hook function `on_update()` is called

**File Involved:** `hooks.py` (line 141-145)
```python
doc_events = {
    "Item": {
        "on_update": "smart_replenishment_module.doc_events.item.on_update"
    }
}
```

---

### Step 3: Hook Detects Changes

**Action:** `on_update()` function checks if Reorder Level table changed

**Code Location:** `doc_events/item.py` (line 16)

**Logic:**
```python
# Check if reorder_levels table has changed
if not doc.has_value_changed("reorder_levels"):
    return  # No changes, exit early
```

**What It Checks:**
- Compares old values (from database) vs new values (from form)
- Specifically looks for changes in:
  - `supplier_lead_time_days`
  - `safety_stock_days`

**File Involved:** `doc_events/item.py` (lines 28-66)

---

### Step 4: Identify Changed Rows

**Action:** System compares each Item Reorder row

**Code Location:** `doc_events/item.py` (lines 28-66)

**Process:**
```python
for new_row in doc.reorder_levels:
    # Find corresponding old row
    old_row = find_matching_row(old_doc.reorder_levels, new_row.name)
    
    # Check if supplier_lead_time_days changed
    if old_row.supplier_lead_time_days != new_row.supplier_lead_time_days:
        add_to_recalculate_list(item_code, warehouse, "lead_time_changed")
    
    # Check if safety_stock_days changed
    if old_row.safety_stock_days != new_row.safety_stock_days:
        add_to_recalculate_list(item_code, warehouse, "safety_stock_changed")
```

**Result:** List of items that need recalculation

---

### Step 5: Show User Message

**Action:** System displays notification to user

**Code Location:** `doc_events/item.py` (lines 79-94)

**Message Shown:**
```
"Reorder point will be recalculated for ITEM-001 in Warehouse Main Store 
due to lead time change"
```

**Why:** User feedback that recalculation is happening

---

### Step 6: Queue Background Job

**Action:** System queues recalculation job (non-blocking)

**Code Location:** `doc_events/item.py` (lines 71-76)

**Why Background?**
- Doesn't block the save operation
- User can continue working
- Heavy calculations don't slow down UI

**Code:**
```python
frappe.enqueue(
    "smart_replenishment_module.doc_events.item.recalculate_reorder_points",
    items=recalculate_items,
    queue="short",
    now=False  # Run in background
)
```

**File Involved:** `doc_events/item.py` (lines 71-76)

---

### Step 7: Background Job Starts

**Action:** Background worker picks up the job

**Code Location:** `doc_events/item.py` (lines 97-126)

**What Happens:**
- Worker calls `recalculate_reorder_points(items)`
- Loops through each item that needs recalculation
- Calls `update_reorder_points()` for each item-warehouse

---

### Step 8: Recalculate Reorder Point

**Action:** System calculates new reorder point

**Code Location:** `api/stock_analyzer.py` → `update_reorder_points()` (lines 91-187)

**Formula Applied:**
```
Reorder Point = Average Daily Consumption × (Lead Time Days + Safety Stock Days)

Example:
- Average Daily Consumption: 50 units/day
- New Lead Time: 10 days
- New Safety Stock: 3 days
- New Reorder Point = 50 × (10 + 3) = 650 units
```

**What Gets Updated:**
1. `warehouse_reorder_level` = 650 units
2. `minimum_stock_level` = 650 units (same as reorder point)
3. `maximum_stock_level` = 1150 units (650 + 500 reorder qty)
4. `average_daily_consumption` = 50 units/day (if not already set)
5. `last_calculation_date` = Today

**File Involved:** `api/stock_analyzer.py` (lines 154-176)

---

### Step 9: Update Item Reorder Record

**Action:** Save updated values to database

**Code Location:** `api/stock_analyzer.py` (lines 172-180)

**What Gets Saved:**
```python
reorder_doc.warehouse_reorder_level = 650.00
reorder_doc.minimum_stock_level = 650.00
reorder_doc.maximum_stock_level = 1150.00
reorder_doc.average_daily_consumption = 50.00
reorder_doc.last_calculation_date = today()
reorder_doc.save()
```

**Result:** Item Reorder table now has new calculated values

---

### Step 10: Check Existing Recommendations

**Action:** System checks if there are pending/approved recommendations

**Code Location:** `doc_events/item.py` (lines 129-218)

**What It Checks:**
```python
existing_recommendations = frappe.get_all(
    "Replenishment Recommendation",
    filters={
        "item_code": item_code,
        "warehouse": warehouse,
        "status": ["in", ["Pending", "Approved"]]  # Only these statuses
    }
)
```

**Why:** Only update recommendations that haven't been ordered yet

---

### Step 11: Update Recommendation Fields

**Action:** Update each existing recommendation with new values

**Code Location:** `doc_events/item.py` (lines 164-214)

**Fields Updated:**
1. `reorder_point` → 650 (new calculated value)
2. `minimum_stock_level` → 650 (updated)
3. `maximum_stock_level` → 1150 (updated)
4. `current_stock_qty` → Current stock balance (refreshed)

**Code:**
```python
rec_doc.reorder_point = item_reorder.warehouse_reorder_level
rec_doc.minimum_stock_level = item_reorder.minimum_stock_level
rec_doc.maximum_stock_level = item_reorder.maximum_stock_level
rec_doc.current_stock_qty = current_stock
```

---

### Step 12: Recalculate Recommended Quantity (If Needed)

**Action:** If stock is still below reorder point, recalculate recommended qty

**Code Location:** `doc_events/item.py` (lines 175-210)

**Condition:** Only if `current_stock < warehouse_reorder_level`

**Calculation Logic:**
```python
if item_reorder_doc.warehouse_reorder_qty > 0:
    recommended_qty = warehouse_reorder_qty  # Use fixed qty
else:
    # Calculate based on consumption
    recommended_qty = avg_daily_consumption × (lead_time + safety_stock)
    # Example: 50 × (10 + 3) = 650 units
```

**Also Updates:**
- `recommended_order_qty` → New calculated value
- `estimated_cost` → `recommended_qty × item_rate`
- `lead_time_days` → 10 (new value)
- `safety_stock_days` → 3 (new value)

---

### Step 13: Save Updated Recommendations

**Action:** Save all changes to recommendations

**Code Location:** `doc_events/item.py` (lines 213-214)

**Code:**
```python
rec_doc.save(ignore_permissions=True)
frappe.db.commit()
```

**Result:** Recommendations now reflect new reorder point values

---

### Step 14: Log Completion

**Action:** System logs successful recalculation

**Code Location:** `doc_events/item.py` (lines 112-115, 216-218)

**Log Entry:**
```
"Recalculated reorder point for ITEM-001 in Main Store: 1 updated"
"Updated recommendation REP-REC-2025-00001 after reorder point recalculation"
```

**Where to View:** (filter by "Recalculated reorder point")

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: User Changes Lead Time or Safety Stock            │
│ Location: Item Form → Reorder Level Table                 │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: User Saves Item                                     │
│ Triggers: doc_events["Item"]["on_update"]                  │
│ File: hooks.py (line 141)                                   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Hook Detects Changes                                │
│ Function: on_update()                                        │
│ File: doc_events/item.py (line 9)                           │
│ Checks: has_value_changed("reorder_levels")                │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Compare Old vs New Values                           │
│ File: doc_events/item.py (lines 28-66)                      │
│ Checks: supplier_lead_time_days, safety_stock_days         │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Show User Message                                   │
│ Message: "Reorder point will be recalculated..."            │
│ File: doc_events/item.py (lines 79-94)                      │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Queue Background Job                                │
│ Function: frappe.enqueue()                                  │
│ File: doc_events/item.py (lines 71-76)                      │
│ Queue: "short", now=False                                   │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 7: Background Worker Starts                            │
│ Function: recalculate_reorder_points()                      │
│ File: doc_events/item.py (lines 97-126)                      │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 8: Calculate New Reorder Point                         │
│ Function: update_reorder_points()                           │
│ File: api/stock_analyzer.py (lines 91-187)                  │
│ Formula: Avg Daily × (Lead Time + Safety Stock)            │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 9: Update Item Reorder Record                          │
│ Fields: warehouse_reorder_level, minimum_stock_level, etc.  │
│ File: api/stock_analyzer.py (lines 172-180)                 │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 10: Check Existing Recommendations                     │
│ Filter: status in ["Pending", "Approved"]                   │
│ File: doc_events/item.py (lines 154-162)                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 11: Update Recommendation Fields                       │
│ Fields: reorder_point, minimum_stock_level, etc.            │
│ File: doc_events/item.py (lines 169-172)                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 12: Recalculate Recommended Qty (if needed)            │
│ Condition: current_stock < reorder_point                     │
│ File: doc_events/item.py (lines 175-210)                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 13: Save Updated Recommendations                       │
│ Action: rec_doc.save() + commit()                           │
│ File: doc_events/item.py (lines 213-214)                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 14: Log Completion                                     │
│ Location: Error Log (Tools → Error Log)                     │
│ File: doc_events/item.py (lines 112-115, 216-218)          │
└─────────────────────────────────────────────────────────────┘
```

---

## What Gets Recalculated

| Field | Before Change | After Change | Formula |
|-------|--------------|--------------|---------|
| **Reorder Point** | 450 units | 650 units | `Avg Daily × (Lead Time + Safety Stock)` |
| **Minimum Stock Level** | 450 units | 650 units | Same as Reorder Point |
| **Maximum Stock Level** | 950 units | 1150 units | `Reorder Point + Reorder Qty` |
| **Recommendation Reorder Point** | 450 units | 650 units | Updated from Item Reorder |
| **Recommendation Min Level** | 450 units | 650 units | Updated from Item Reorder |
| **Recommendation Max Level** | 950 units | 1150 units | Updated from Item Reorder |
| **Recommended Qty** | 500 units | 650 units* | Recalculated if stock still low |
| **Estimated Cost** | $2,500 | $3,250* | `Qty × Rate` |

*Only if stock is still below reorder point

---

## Testing the Feature

### Manual Test Steps

1. **Open an Item** that has Reorder Level configured
2. **Note current values:**
   - Supplier Lead Time Days: 7
   - Safety Stock Days: 2
   - Warehouse Reorder Level: 450
3. **Change values:**
   - Supplier Lead Time Days: 10
   - Safety Stock Days: 3
4. **Save Item**
5. **Check message:** "Reorder point will be recalculated..."
6. **Wait 5-10 seconds** (background job processes)
7. **Refresh Item**
8. **Verify:**
   - Warehouse Reorder Level: 650 (updated)
   - Minimum Stock Level: 650 (updated)
   - Maximum Stock Level: 1150 (updated)
9. **Check Recommendations:**
   - Open Replenishment Recommendation list
   - Filter by the item
   - Verify reorder_point, minimum_stock_level, maximum_stock_level are updated

---

## Workflow & Status

### Workflow States
The Replenishment Recommendation workflow has **3 states** that can be transitioned via workflow actions:
- **Pending** - Newly created, awaiting review (default state)
- **Approved** - Approved by user via workflow action, ready for PO creation
- **Rejected** - Rejected by user via workflow action

### Status Field Values
The status field can have **4 values**:
- **Pending** - Managed by workflow (default)
- **Approved** - Managed by workflow (via Approve action)
- **Rejected** - Managed by workflow (via Reject action)
- **Ordered** - Managed by workflow (via Mark Ordered transition)
  - Automatically transitions from "Approved" to "Ordered" when Purchase Order is created
  - Updated via SQL in `purchase_order_creator.py` when PO is successfully created
  - Occurs automatically when an Approved recommendation is submitted and PO creation succeeds

**Note:** The workflow includes four states: Pending (draft), Approved (submitted), Rejected (submitted), and Ordered (submitted). All final states (Approved, Rejected, Ordered) are locked and cannot be edited.

---

## Data Model

### Custom Fields Added

**On Item:**
- `requires_prescription` (Check) - Mark medications needing prescriptions

**On Item Reorder (warehouse-specific settings):**
- `minimum_stock_level` (Float) - Reorder point (auto-calculated)
- `maximum_stock_level` (Float) - Max stock to maintain
- `safety_stock_days` (Int) - Days of buffer stock
- `supplier_lead_time_days` (Int) - Days for supplier delivery
- `preferred_supplier` (Link) - Primary supplier
- `average_daily_consumption` (Float) - Auto-calculated usage
- `last_calculation_date` (Date) - When metrics updated

### DocTypes Created

| DocType | Purpose |
|---------|---------|
| **Replenishment Recommendation** | Generated recommendations for purchasing |
| **Replenishment Settings** | Global configuration |
| **Replenishment Notification User** | Users to notify |
| **Replenishment Notification Role** | Roles to notify |
| **Replenishment Activity Log** | System activity logging (replaces frappe.logger) |

---

## API Documentation

### Get Recommendations

```http
GET /api/resource/Replenishment%20Recommendation?filters=[["status","=","Pending"]]
```

**Parameters:**
- `filters` - Filter by status, item, warehouse, priority
- `fields` - Specific fields to return
- `limit_page_length` - Number of results

**Response:**
```json
{
  "data": [
    {
      "name": "REP-REC-2025-00001",
      "item_code": "AMOXICILLIN-500",
      "warehouse": "Main Store",
      "current_stock_qty": 250,
      "reorder_point": 612,
      "recommended_order_qty": 529,
      "priority": "High",
      "status": "Pending"
    }
  ]
}
```

### Approve Recommendation

```http
POST /api/method/smart_replenishment_module.api.recommendation_api.approve_recommendation
Content-Type: application/json

{
  "recommendation_name": "REP-REC-2025-00001"
}
```

**Response:**
```json
{
  "status": "success",
  "new_status": "Approved",
  "message": "Recommendation approved successfully"
}
```

### Create Purchase Order

```http
POST /api/method/smart_replenishment_module.api.recommendation_api.create_purchase_order
Content-Type: application/json

{
  "recommendation_name": "REP-REC-2025-00001"
}
```

**Response:**
```json
{
  "status": "success",
  "purchase_order": "PUR-ORD-2025-00001",
  "supplier": "ABC Pharma",
  "total_amount": 2645
}
```

### Generate Recommendations (Manual Trigger)

```http
POST /api/method/smart_replenishment_module.api.recommendation_generator.generate_recommendations
Content-Type: application/json

{
  "warehouse": "Main Store",
  "force": true
}
```

**Parameters:**
- `warehouse` (optional) - Specific warehouse only
- `force` (optional) - Force generation even if recent

---

## Testing

### Quick Test (Automated)

**Before running the test, ensure the module is installed:**

```bash
bench --site your-site migrate
```

This ensures custom fields and property setters are installed.

**Then run the complete test cycle:**

```bash
bench --site your-site execute smart_replenishment_module.test_cycle.test_complete_cycle
```

**Note:** The test automatically runs the install script if custom fields are missing, but it's recommended to run `bench migrate` first.

This tests:
✓ Custom fields installation (auto-installs if missing)
✓ Reorder point calculation
✓ Recommendation generation
✓ Purchase order creation
✓ API endpoints
✓ All 8 assessment requirements

### Clear Demo Data

After testing, clean up all demo/test data:

```bash
bench --site your-site execute smart_replenishment_module.test_cycle.clear_all_demo_data
```

**⚠️ Important:** Use the full module path

**❌ Wrong:** 
- `bench execute test_cycle.clear_all_demo_data` (won't work)
- `bench execute test_cycle.test_complete_cycle` (won't work)

**✅ Correct:**
- `bench --site your-site execute smart_replenishment_module.test_cycle.test_complete_cycle`
- `bench --site your-site execute smart_replenishment_module.test_cycle.clear_all_demo_data`

This removes:
- All Replenishment Recommendations
- Test Purchase Orders
- Test Stock Entries (ledger cleared first to avoid negative stock errors)
- Test Items (TEST-*)
- Test Suppliers
- Test Warehouses

**Cleanup Process:**
1. Deletes Recommendations (cancels if submitted)
2. Deletes Purchase Orders (cancels if submitted)
3. **Clears Stock Ledger Entries FIRST** (prevents negative stock errors)
4. Deletes Stock Entries (after ledger cleared)
5. Deletes Items
6. Deletes Suppliers
7. Deletes Warehouses

**Note:** If some Stock Entries cannot be deleted (due to complex dependencies), they will be reported but won't block the cleanup process.

### Manual Testing

See **TESTING_GUIDE.md** for step-by-step manual testing instructions.

---

## Notification Configuration

The notification system alerts users when new replenishment recommendations are created. Configure who receives notifications and when.

### Step 1: Configure Notification Recipients

1. Navigate to **Replenishment Settings** (Search bar)
2. Scroll to **"Notification Settings"** section
3. **Add Notification Users:**
   - Click **"Add Row"** in the "Notification Users" table
   - Select a user from the dropdown
   - Repeat to add multiple users
4. **Add Notification Roles (Optional):**
   - Click **"Add Row"** in the "Notification Roles" table
   - Select a role (e.g., "Purchase Manager", "Stock Manager")
   - All users with this role will receive notifications
   - Example: Adding "Purchase Manager" role notifies all purchase managers

### Step 2: Set Priority Filter

Choose when notifications are sent:

- **All:** Notify for all recommendations (High, Medium, Low priority)
  - Best for: Small teams who want to see everything
  - Use case: You want to be aware of all replenishment needs

- **High Only:** Only notify for critical stock situations
  - Best for: Reducing notification noise
  - Use case: Only alert when stock is critically low (<50% of reorder point)

- **High & Medium:** Exclude low-priority recommendations
  - Best for: Balanced approach
  - Use case: Alert for urgent and moderate needs, but skip routine reorders

### Step 3: Verify Notifications

After configuration:

1. **Generate a test recommendation** (see [Testing Guide](#testing-guide))
2. **Check Notification Log:**
   - Navigate to **Notification Log** (Search bar)
   - Filter by **Document Type:** "Replenishment Recommendation"
   - Verify notifications were created for configured users
3. **Check User Notifications:**
   - Log in as a configured user
   - Check the notification bell icon (top right)
   - Should see: "New Replenishment Recommendation: REP-REC-XXXXX"

### Notification Details

Each notification includes:
- **Subject:** "New Replenishment Recommendation: [Recommendation Name]"
- **Type:** Alert
- **Document Link:** Click to open the recommendation
- **Priority:** High/Medium/Low (in notification content)
- **Timestamp:** When the recommendation was created

### Testing Notifications

The automated test cycle (`test_complete_cycle`) automatically:
- Configures notification settings
- Adds current user to notification recipients
- Generates recommendations
- Verifies notifications were sent
- Displays notification details in test output

Run the test to verify your notification setup:

```bash
bench --site your-site.local execute smart_replenishment_module.test_cycle.test_complete_cycle
```

---

## Configuration Examples

### Example 1: Antibiotic (Fast Moving)

```
Item: Amoxicillin 500mg
├─ Warehouse Reorder Qty: 5000 (high volume)
├─ Safety Stock Days: 3 (need buffer)
├─ Supplier Lead Time: 7 days
├─ Preferred Supplier: Pharma Supplies Inc
└─ Requires Prescription: ✓
```

### Example 2: Specialty Drug (Slow Moving)

```
Item: Specialty Cardiac Drug
├─ Warehouse Reorder Qty: 100 (low volume)
├─ Safety Stock Days: 5 (important, don't run out)
├─ Supplier Lead Time: 14 days (international)
├─ Preferred Supplier: Global Pharma
└─ Requires Prescription: ✓
```

### Example 3: Multiple Warehouses

Same item, different settings per location:

```
ITEM: Ibuprofen 200mg

Central Pharmacy:
├─ Reorder Qty: 10000
├─ Lead Time: 7 days
└─ Supplier: Local Distributor

Branch Pharmacy:
├─ Reorder Qty: 2000
├─ Lead Time: 3 days (nearby supplier)
└─ Supplier: Regional Distributor
```

---

## Troubleshooting

### Issue: Custom fields not appearing

**Solution:**
```bash
bench migrate --site your-site
bench restart
```

### Issue: Recommendations not generating

**Check:**
1. Is Item Reorder configured? (Add warehouse reorder levels)
2. Is scheduler running? (`bench worker list`)
3. Is stock actually below reorder point?

**Manual trigger:**
```bash
bench --site your-site execute smart_replenishment_module.api.recommendation_generator.generate_recommendations
```

### Issue: Purchase Orders not created automatically

**Check:**
1. Is recommendation status "Approved"?
2. Does the item have a supplier configured?
3. Check logs: `bench log -f`

---

## File Structure

```
smart_replenishment_module/                    # App root
├── smart_replenishment_module/               # Python package
│   ├── api/
│   │   ├── stock_analyzer.py                 # Reorder point calculation
│   │   ├── recommendation_generator.py       # Create recommendations
│   │   ├── purchase_order_creator.py        # Create POs from recommendations
│   │   ├── recommendation_api.py            # REST API endpoints
│   │   └── scheduled_tasks.py               # Daily scheduler tasks
│   ├── doc_events/
│   │   └── item.py                          # Auto-recalculation hooks
│   ├── smart_replenishment/
│   │   ├── doctype/
│   │   │   ├── replenishment_recommendation/
│   │   │   ├── replenishment_settings/
│   │   │   └── notification_tables/
│   │   ├── config/
│   │   │   └── smart_replenishment.py       # Module navigation
│   │   └── fixtures/                        # Workflows, workspace
│   ├── utils/
│   │   └── install.py                       # Custom fields setup
│   ├── hooks.py                             # App configuration
│   ├── modules.txt                          # Module definition
│   └── test_cycle.py                        # ⭐ Main test script (here)
├── README.md                                # This file
├── TESTING_GUIDE.md                         # Testing instructions
├── API Documentation.md                     # API documentation
└── [Other documentation files]
```

**Key Files:**
- **Test Script**: `smart_replenishment_module/smart_replenishment_module/test_cycle.py`
- **Auto-Recalc Hook**: `smart_replenishment_module/smart_replenishment_module/doc_events/item.py`

---

## Performance Considerations

### Large Inventories (1000+ items)

1. **Increase consumption analysis period** - Reduces daily processing
2. **Filter recommendations by priority** - Process High priority first
3. **Use warehouse-specific generation** - Process one warehouse at a time

```bash
# Process only critical items
bench --site your-site execute smart_replenishment_module.api.recommendation_generator.generate_recommendations warehouse=MainStore
```

### Stock Ledger Analysis

The module analyzes stock ledger entries for consumption patterns. For optimal performance:
- Archive old stock ledgers (after 2 years)
- Limit consumption analysis to 90-180 days
- Use scheduled tasks during off-peak hours

---

## Activity Logging

The module uses a custom **Replenishment Activity Log** DocType to track all system activities, replacing standard Frappe logging. This provides:

- **Centralized Logging**: All module activities logged in one place
- **Structured Data**: Logs include item codes, warehouses, references, and tracebacks
- **Filterable**: Filter by log type (Info, Warning, Error, Success), severity, item, warehouse
- **Traceable**: Link logs to related documents (Recommendations, Items, etc.)
- **User Tracking**: Each log entry records the user who triggered the action

### Log Types

- **Info**: General informational messages (e.g., scheduled task completion)
- **Warning**: Warning messages (e.g., skipped items)
- **Error**: Error messages with tracebacks
- **Success**: Successful operations (e.g., recommendations generated)

### Severity Levels

- **Low**: Informational messages
- **Medium**: Warnings
- **High**: Errors
- **Critical**: Critical errors requiring immediate attention

### Viewing Logs

Navigate to **Replenishment Activity Log** to view all module activities. You can:
- Filter by log type, severity, item, warehouse, or date
- View tracebacks for errors
- See which user triggered each action
- Link to related documents

### Logging Functions

The module provides utility functions in `utils/logger.py`:
- `log_info()` - Log informational messages
- `log_warning()` - Log warnings
- `log_error()` - Log errors with traceback
- `log_success()` - Log successful operations
- `log_critical_error()` - Log critical errors

---

## Security & Permissions

The module respects ERPNext's permission system:

- **Purchase User** - Can view recommendations and activity logs
- **Purchase Manager** - Can approve/reject recommendations, view all logs
- **Stock Manager** - Can manage item reorder levels
- **System Administrator** - Full access including log management

To restrict access:
1. Go to **Role** (search bar)
2. Configure which users can access each DocType
3. Set read/write/submit permissions

---

## Support & Contribution

### Documentation
- **README.md** - Overview and setup (this file)
- **TESTING_GUIDE.md** - Testing instructions
- **API Documentation.md** - API reference
- **CYCLE_DOCUMENTATION.md** - Workflow details
- **WORKFLOW_GUIDE.md** - Workflow configuration and approval processes
- **AUTO_PO_CREATION.md** - Automatic Purchase Order creation

### Getting Help
1. Check the Testing Guide for common issues
2. Review ERPNext logs: `bench log -f`
3. Check module logs for errors

### Contributing
We welcome contributions! Areas for enhancement:
- Additional pricing rules
- Advanced forecasting models
- Multi-currency support
- Seasonal demand patterns

---

## License

MIT License - See LICENSE file for details

---

## Authors

Zeiad Madboly - Pharmacy Supply Chain Optimization

---

## Version History

**v1.1** (November 14, 2025)
- ✅ **Configurable Consumption Calculation:** Choose between "Active Days Only" or "Full Period" methods
- ✅ **Mandatory Reorder Level:** `warehouse_reorder_level` is now required and auto-calculated
- ✅ **Intelligent Rate Fallback:** Prioritizes valuation_rate over standard_rate for accurate costing
- ✅ **PO Cancellation Handling:** Cancelled Purchase Orders automatically reset recommendations to "Pending"
- ✅ **Real-time Stock Movement Integration:** Stock Entry, Delivery Note, and Sales Invoice trigger automatic reorder updates
- ✅ **Warehouse Filtering:** Only non-group warehouses available for reorder configuration
- ✅ **Currency Support:** Automatic currency handling based on supplier defaults
- ✅ **Dynamic Recommendation Regeneration:** Reorder level changes trigger automatic recommendation updates

**v1.0** (November 2025)
- Initial release
- Reorder point calculation
- Recommendation generation
- Purchase order integration
- REST API
- Notification system
- Pharmacy-specific features

---

**Last Updated:** November 14, 2025
**Status:** Production Ready
