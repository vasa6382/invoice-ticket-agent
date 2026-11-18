# Power Automate Implementation Guide & Workflow Expressions

This guide provides exact connector names, action configurations, and Workflow Definition Language (WDL) expressions for building the Automated Invoice & Ticket Processing Agent in Microsoft Power Automate.

---

## 1. Flow Overview & Connectors

| Step | Connector | Action Name | Purpose |
| :--- | :--- | :--- | :--- |
| **Trigger** | Office 365 Outlook | `When a new email arrives (V3)` | Listens for new incoming emails with invoice attachments |
| **Var 1** | Built-in | `Initialize variable - varThreshold` | Stores approval threshold (e.g. 1000.0 or 50000.0) |
| **Var 2** | Built-in | `Initialize variable - varProcessedStatus`| Tracks approval status across branches |
| **Scope** | Built-in | `Scope - Try` | Encapsulates all document processing logic |
| **Loop** | Built-in | `Apply to each - Attachment` | Iterates through email attachments |
| **Condition 1**| Built-in | `Condition - Is Document` | Filters out signature images & small files |
| **Action** | Office 365 Outlook | `Get Attachment (V2)` | Retrieves file content bytes |
| **Extraction** | AI Builder | `Extract information from invoices` | Prebuilt Document Processing Model |
| **HTTP Fallback**| HTTP | `HTTP - Extract Invoice` *(Optional)* | Calls local/cloud Python FastAPI engine if AI Builder credits are absent |
| **Condition 2**| Built-in | `Condition - Needs Approval` | Tests if `TotalAmount > varThreshold` or `Confidence < 0.65` |
| **Approval** | Approvals | `Start and wait for an approval (V2)` | Sends card to Finance Manager via Teams/Outlook |
| **Database** | Microsoft Dataverse | `Add a new row` | Persists record into `cr_invoices_processeds` table |
| **Database Alt**| Excel Online (Business)| `Add a row into a table` | Writes to `Invoices_Tracker.xlsx` |
| **Notification**| Office 365 Outlook | `Send an email (V2)` | Sends approval / rejection email |
| **Scope Catch** | Built-in | `Scope - Catch` | Configured with `Run After: has failed, has timed out` |

---

## 2. Trigger Configuration & Filters

### Trigger: `When a new email arrives (V3)`
* **Folder**: `Inbox`
* **Include Attachments**: `Yes`
* **Only with Attachments**: `Yes`

### Trigger Conditions (Under Settings > Trigger Conditions):
```text
@and(
  greater(length(triggerOutputs()?['body/attachments']), 0),
  or(
    contains(toLower(triggerOutputs()?['body/subject']), 'invoice'),
    contains(toLower(triggerOutputs()?['body/subject']), 'bill'),
    contains(toLower(triggerOutputs()?['body/subject']), 'service request')
  )
)
```

---

## 3. Signature & Format Validation Expression

Inside `Apply to each - Attachment`, add a Condition action:

```text
@and(
  or(
    endsWith(toLower(items('Apply_to_each_-_Attachment')?['name']), '.pdf'),
    endsWith(toLower(items('Apply_to_each_-_Attachment')?['name']), '.png'),
    endsWith(toLower(items('Apply_to_each_-_Attachment')?['name']), '.jpeg'),
    endsWith(toLower(items('Apply_to_each_-_Attachment')?['name']), '.jpg')
  ),
  greater(items('Apply_to_each_-_Attachment')?['size'], 10240)
)
```

---

## 4. WDL Data Cleaning Expressions

Use these expressions in Compose actions or directly in field inputs:

### Vendor Name
```text
coalesce(
  outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/VendorName/value'],
  outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/VendorAddressRecipient/value'],
  'Unknown Vendor'
)
```

### Invoice / Ticket ID
```text
coalesce(
  outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceId/value'],
  concat('GEN-', formatDateTime(utcNow(), 'yyyyMMddHHmmss'))
)
```

### Invoice Date (ISO 8601 formatting)
```text
if(
  empty(outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceDate/value']),
  formatDateTime(utcNow(), 'yyyy-MM-dd'),
  formatDateTime(outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceDate/value'], 'yyyy-MM-dd')
)
```

### Total Amount (Cleans currency symbols, commas, and handles nulls)
```text
if(
  empty(outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceTotal/value']),
  0.0,
  float(
    replace(
      replace(
        replace(
          replace(
            string(outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceTotal/value']),
            '$', ''
          ),
          '₹', ''
        ),
        '€', ''
      ),
      ',', ''
    )
  )
)
```

### Currency
```text
coalesce(
  outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/Currency/value'],
  'USD'
)
```

### AI Confidence Score
```text
float(coalesce(outputs('Extract_information_from_invoices')?['body/responsev2/predictionOutput/labels/InvoiceTotal/confidence'], 0.0))
```

---

## 5. Threshold & Confidence Gate Condition

Add a condition before database logging:

```text
@or(
  greater(outputs('Clean_Total_Amount'), variables('varThreshold')),
  less(outputs('Extract_Confidence'), 0.65)
)
```

* **If True:**
  * Action: `Start and wait for an approval (V2)`
  * Outcome check: `body('Start_and_wait_for_an_approval_(V2)')?['outcome'] equals 'Approve'`
    * If Approved: Set `varProcessedStatus` = `'Approved'`, log to Dataverse / Excel.
    * If Rejected: Set `varProcessedStatus` = `'Rejected'`, send rejection email to `@triggerOutputs()?['body/from']`.
* **If False:**
  * Set `varProcessedStatus` = `'Auto-Approved'`.
  * Directly log to Dataverse / Excel.

---

## 6. Calling the Python Fallback Microservice from Power Automate

If you run without AI Builder premium credits:
1. Replace `Extract information from invoices` with an **HTTP** connector:
   * **Method**: `POST`
   * **URI**: `https://your-service-host.com/api/v1/extract-invoice` (or Azure App Service / Tunnel)
   * **Headers**:
     * `Content-Type`: `multipart/form-data`
   * **Body**: Attach `contentBytes` from `Get Attachment (V2)`.
2. Add a **Parse JSON** action with the schema provided in `app/models.py`.
