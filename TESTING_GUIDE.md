# Smart Replenishment Module - Testing Guide

Complete step-by-step guide to test the Smart Replenishment Module and understand how it works.

---

## Quick Start: Run the Complete Test Cycle

The easiest way to test the module is to run the automated test cycle. This simulates the entire workflow in minutes.

### Run the Test

```bash
cd ~/smart-replenishment-module
bench --site srm.local execute smart_replenishment_module.test_cycle.test_complete_cycle
```

### What the Test Does

The test automatically:

1. **Verifies Installation** - Checks that all custom fields and property setters are installed
2. **Creates Test Data** - Sets up a test Item, Warehouse, Supplier, and Company
3. **Configures Reorder Settings** - Creates an Item Reorder entry with random test parameters
4. **Simulates 30 Days of Consumption** - Creates stock ledger entries to establish consumption patterns
5. **Calculates Reorder Points** - Analyzes consumption and calculates optimal reorder points
6. **Triggers Recommendations** - Generates replenishment recommendations when stock drops below reorder point
7. **Creates Purchase Order** - Converts approved recommendations into a Purchase Order
8. **Verifies Notifications** - Configures notification settings and verifies notifications are sent
9. **Verifies Integration** - Tests API endpoints and workflow states
10. **Checks Activity Logs** - Verifies that all activities are logged in Replenishment Activity Log

**Expected Output:** The test will display detailed progress for each step, showing calculated values, recommendations generated, and final summary of all assessment requirements met.

---

## Manual Testing: Step-by-Step

If you prefer to test manually or understand the process step-by-step:

### Step 1: Verify Installation

1. **Check Custom Fields**
   - Navigate to **Item** (Search bar)
   - Open any item
   - Scroll down - you should see: **"Requires Prescription"** field
   - This field is pharmacy-specific for compliance tracking

2. **Check Item Reorder Extensions**
   - From the Item, scroll to the **"Reorder Level"** table
   - Each row should have these NEW fields:
     - **Minimum Stock Level** - Calculated reorder point
     - **Maximum Stock Level** - Max capacity (Reorder Point + Reorder Qty)
     - **Safety Stock (Days)** - Days of buffer stock
     - **Supplier Lead Time (Days)** - Days to receive from supplier
     - **Preferred Supplier** - Pick a specific supplier for this warehouse
     - **Average Daily Consumption** - Auto-calculated from usage history
     - **Last Calculation Date** - When metrics were last updated

### Step 2: Create Test Data


1. **Create a Warehouse**
   - Navigate to **Warehouse** (Search bar)
   - Create a warehouse linked to your company
   - Example: "Main Store - PS"

2. **Create a Test Item**
   - Navigate to **Item** (Search bar)
   - Create a new item:
     - **Item Code**: TEST-MED-001 (or any name)
     - **Item Name**: Test Medicine 500mg
     - **Item Group**: Products
     - **Stock UOM**: Unit
     - **Is Stock Item**: ✓ (checked)
     - **Maintain Stock**: ✓ (checked)
     - **Lead Time Days**: 7
     - **Standard Rate**: 5.00

3. **Create a Supplier**
   - Navigate to **Supplier** (Search bar)
   - Create a supplier (e.g., "Test Supplier")

### Step 3: Configure Item Reorder

1. **Open the Item** you created
2. **Scroll to "Reorder Level"** table
3. **Add a Row** with:
   - **Warehouse**: Select your test warehouse
   - **Warehouse Reorder Qty**: 500 (order quantity)
   - **Safety Stock Days**: 2 (days of buffer)
   - **Supplier Lead Time Days**: 7 (days to receive)
   - **Preferred Supplier**: Select your test supplier

### Step 4: Create Consumption History

Create stock ledger entries to simulate consumption:

1. **Go to Stock Entry** (Search bar)
2. **Create new Stock Entry**:
   - **Stock Entry Type**: Material Issue
   - **Posting Date**: Today minus 30 days (e.g., Oct 8, 2025)
   - **Item**: Your test item
   - **Source Warehouse**: Your test warehouse
   - **Quantity**: 50

3. **Repeat this 30 times** (or use the automated test)
   - Each entry 1 day apart
   - Vary quantities (40-60 units)
   - This establishes consumption history for analysis

**Or use the automated test** - Much faster!

### Step 5: Calculate Reorder Points

The system analyzes the last 90 days of consumption.

1. **Navigate to Replenishment Settings** (Search bar)
2. **Click on the item** you configured
3. The system will:
   - Analyze all stock entries
   - Calculate average daily consumption
   - Calculate reorder point: (Avg Daily × Lead Time) + Safety Stock
   - Update Item Reorder fields

**Example calculation:**
- Average Daily Consumption: 50 units/day
- Lead Time: 7 days
- Safety Stock: 2 days
- **Reorder Point = (50 × 7) + (50 × 2) = 450 units**

### Step 6: Generate Recommendations

When stock falls below reorder point, the system creates a recommendation.

**Manually Trigger:**
1. Navigate to **Replenishment Recommendation** (Search bar)
2. Click **New** (or use API)
3. Fill in details manually

**Or let the scheduler do it:**
- all hook is for calling the event in all modes, the system automatically scans inventory
- Creates recommendations for items below reorder points
- Sends notifications to configured users (see [Step 7: Verify Notifications](#step-7-verify-notifications) below)

### Step 7: Approve and Submit Recommendation

**Important:** Purchase Orders are now created automatically when you submit an approved recommendation.

1. **Open the Recommendation**
2. **Review the details**:
   - Current stock level: Should be below reorder point
   - Reorder point: Calculated threshold
   - Recommended order quantity: How much to order
   - Estimated cost: Total purchase cost

3. **Change Status to "Approved"**
4. **Click "Save"**

5. **Click "Submit"** (Critical Step!)
   - Submits the recommendation (docstatus=1)
   - **Automatically creates Purchase Order** via on_submit hook
   - Updates recommendation status to "Ordered"
   - Links PO to recommendation
   - Shows success message with PO number

6. **Verify Automatic PO Creation**:
   - Success message: "Purchase Order PUR-ORD-2025-XXXXX created successfully"
   - Recommendation shows linked PO in "Purchase Order" field
   - Comment added: "Purchase Order XYZ created automatically"

### Step 7: Verify Notifications

The system automatically sends notifications when recommendations are created. Verify they're working:

1. **Configure Notification Settings (if not already done):**
   - Navigate to **Replenishment Settings** (Search bar)
   - Scroll to **"Notification Settings"** section
   - Add your user to **"Notification Users"** table
   - Set **"Notify On Priority"** to "All" (to receive all notifications)
   - Click **"Save"**

2. **Check Notification Log:**
   - Navigate to **Notification Log** (Search bar)
   - Filter by:
     - **Document Type:** "Replenishment Recommendation"
     - **Creation:** Today
   - You should see entries for each recommendation created
   - Each entry shows:
     - **For User:** Who received the notification
     - **Subject:** "New Replenishment Recommendation: [Name]"
     - **Type:** Alert
     - **Document Name:** Link to the recommendation

3. **Check User Notifications:**
   - Look at the notification bell icon (top right of ERPNext)
   - Should see notifications for new recommendations
   - Click to view details and open the recommendation

4. **Verify Notification Content:**
   - Open a notification
   - Should show: "A new [Priority] priority replenishment recommendation has been created."
   - Click the document link to open the recommendation

5. **Test Priority Filtering (Optional):**
   - Change **"Notify On Priority"** to "High Only"
   - Generate a Low-priority recommendation
   - Verify no notification is sent
   - Generate a High-priority recommendation (stock < 50% of reorder point)
   - Verify notification is sent

**Note:** The automated test cycle (`test_complete_cycle`) automatically configures and verifies notifications, so you can use it to test the notification system end-to-end.

### Step 8: Review the Auto-Created Purchase Order

1. **Find the Purchase Order**:
   - Click the PO link in the recommendation, OR
   - Navigate to **Purchase Order** (Search bar)
   - Find the PO that was just created

2. **Verify PO Details**:
   - **Supplier**: Should match preferred supplier from Item Reorder
   - **Item**: Your test item
   - **Quantity**: As recommended (e.g., 500 units)
   - **Rate**: Item's last purchase rate
   - **Total**: Quantity × Rate
   - **Status**: Draft (ready to submit)

3. **Submit the Purchase Order**:
   - Review all details are correct
   - Click "Submit"
   - PO is now submitted (docstatus=1)
   - Ready to send to supplier
   - Workflow state changes (if workflow configured)

---

## Understanding the Output

When you run the test cycle, you'll see:

### Calculated Values Section
```
- Average Daily Consumption: 50.27 units/day
- Reorder Point: 612.00 units
- Minimum Stock Level: 612.00 units
- Maximum Stock Level: 1141.00 units
```

**What this means:**
- The system analyzed 30 days of stock movements
- Average daily usage is 50 units
- When stock reaches 612 units, it's time to reorder
- Max stock should be 1141 units (reorder point + order quantity)

### Recommendation Details Section
```
- Current Stock: 245 units (below reorder point)
- Recommended Qty: 529 units (based on order quantity)
- Estimated Cost: 2645 units (Qty × Unit Cost)
- Priority: High (because stock is very low)
```

**Actions:**
- Approve the recommendation (status → Approved)
- System creates a Purchase Order automatically
- PO is ready for supplier submission

---

## Testing the API

The module includes REST API endpoints for external integrations.

### Get Recommendations
```bash
curl -X GET "http://yoursite/api/resource/Replenishment%20Recommendation?filters=[[\"status\",\"=\",\"Pending\"]]" \
  -H "Authorization: token your-api-key"
```

### Approve a Recommendation
```bash
curl -X POST "http://yoursite/api/method/smart_replenishment_module.api.recommendation_api.approve_recommendation" \
  -H "Content-Type: application/json" \
  -H "Authorization: token your-api-key" \
  -d '{"recommendation_name": "REP-REC-2025-00001"}'
```

### Create Purchase Order from Recommendation
```bash
curl -X POST "http://yoursite/api/method/smart_replenishment_module.api.recommendation_api.create_purchase_order" \
  -H "Content-Type: application/json" \
  -H "Authorization: token your-api-key" \
  -d '{"recommendation_name": "REP-REC-2025-00001"}'
```

---

## Troubleshooting

### Issue: "Warehouse does not belong to Company"

**Solution:**
- Make sure the warehouse you're using is linked to the same company
- Check Warehouse configuration: it should have a company assigned

### Issue: "Negative Stock Error"

**Solution:**
- The test automatically handles this by adding initial stock
- Manually: Create a Material Receipt first, THEN create Material Issues
- Ensure posting dates are in chronological order (oldest first)

### Issue: "Recommendation not generated even though stock is low"

**Solution:**
1. Check if the Item Reorder is configured
2. Ensure warehouse is in Item Reorder
3. Run the recommendation generator manually:
   ```bash
   bench --site srm.local execute smart_replenishment_module.api.recommendation_generator.generate_recommendations
   ```

### Issue: "UOM must be integer"

**Solution:**
- Ensure all stock entry quantities are whole numbers
- The test automatically rounds quantities to prevent this

---

## What Gets Tested

✓ Custom Fields Installation
✓ Data Model (Items, Warehouses, Suppliers, Recommendations)
✓ Reorder Point Calculation Engine
✓ Consumption Analysis (Stock Ledger)
✓ Recommendation Generation Logic
✓ Priority Assignment (High/Medium/Low)
✓ Purchase Order Creation
✓ Status Workflows
✓ API Endpoints
✓ Notification System
   - Configures notification recipients
   - Verifies notifications are sent when recommendations are created
   - Tests priority-based filtering
   - Validates Notification Log entries

---

## Next Steps

After successful testing:

1. **Configure Real Settings**
   - Update Replenishment Settings with your actual preferences
   - Set consumption analysis period (default: 90 days)
   - Configure notification recipients (users and roles)
   - Set priority filtering (All, High Only, High & Medium)

2. **Set Up Actual Items**
   - Configure Item Reorder for your pharmacy inventory
   - Set warehouse-specific reorder points
   - Define preferred suppliers

3. **Enable Scheduler**
   - Daily automatic recommendation generation
   - Scheduled notifications
   - Stock analysis runs automatically

4. **Monitor and Optimize**
   - Review generated recommendations weekly
   - Adjust safety stock based on actual lead times
   - Fine-tune reorder quantities based on usage

---

## Support

For issues or questions:
- Check the README.md for detailed module information
- Review API_DOCS.md for API specifications
- Check the log files for errors: `bench log -f`
