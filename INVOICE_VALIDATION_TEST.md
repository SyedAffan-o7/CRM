# Invoice Number Validation - Test Documentation

## Overview
This document explains the invoice number validation implemented in the CRM system to ensure proper workflow compliance.

## Validation Rules

### Rule 1: PI First Requirement
- **Requirement**: Invoice numbers can only be entered AFTER a Proforma Invoice (PI) number has been created
- **Affected Stages**: 
  - `invoice_made` (Invoice Made)
  - `invoice_sent` (Invoice Sent) 
  - `won` (Won)
- **Error Message**: "Enter PI first. Invoice Number can only be entered after Proforma Invoice (PI) is created."

### Rule 2: Stage-Specific Requirements
- **Proforma Invoice Sent**: Requires `proforma_invoice_number`
- **Invoice Made/Sent/Won**: Requires both `proforma_invoice_number` AND `invoice_number`

## Implementation Details

### Backend Validation (leads_app/views.py)
- Located in `lead_update_stage()` function (lines 838-845)
- Checks if `lead.proforma_invoice_number` exists before allowing invoice number entry
- Returns JSON error response if validation fails

### Model Validation (leads_app/models.py)
- Located in `Lead.clean()` method (lines 104-113)
- Provides additional validation at the model level
- Ensures data integrity across all entry points

### Frontend Handling (static/js/enquiries.js)
- Error messages are displayed using `showError()` method
- Creates temporary alert notifications with auto-dismiss
- Reverts dropdown selection on validation failure

## Test Scenarios

### Scenario 1: Valid Flow ✅
1. Set stage to "Proforma Invoice Sent" → Enter PI number → Success
2. Set stage to "Invoice Made" → Enter Invoice number → Success (PI exists)

### Scenario 2: Invalid Flow ❌
1. Set stage to "Invoice Made" directly → Error: "Enter PI first..."
2. Set stage to "Won" without PI → Error: "Enter PI first..."

### Scenario 3: Edge Cases
1. Empty PI number when setting "Proforma Invoice Sent" → Error
2. Empty Invoice number when setting "Invoice Made" (with PI) → Error

## Testing Instructions

### Manual Testing via Browser
1. Navigate to `/enquiries/` (http://127.0.0.1:8000/enquiries/)
2. Find an enquiry without PI number
3. Try to change stage to "Invoice Made" → Should show error
4. First set to "Proforma Invoice Sent" and enter PI number
5. Then change to "Invoice Made" and enter Invoice number → Should succeed

### Console Testing (Developer Tools)
```javascript
// Test with first available lead
testFirstStageChange("invoice_made"); // Should fail if no PI

// Test specific lead
testStageChange(1, "won"); // Replace 1 with actual lead ID
```

## Error Message Display
- Errors appear as red alert notifications in top-right corner
- Auto-dismiss after 5 seconds
- Dropdown reverts to previous value on error
- Console logging for debugging

## Files Modified
1. `leads_app/views.py` - Backend validation logic
2. `leads_app/models.py` - Model-level validation
3. `static/js/enquiries.js` - Frontend error handling (already existed)

## Validation Flow
```
User selects Invoice stage
    ↓
JavaScript detects change
    ↓
AJAX request to backend
    ↓
Backend checks PI exists
    ↓
If PI missing: Return error
    ↓
Frontend shows error & reverts
    ↓
If PI exists: Continue with modal
```

This ensures proper business workflow compliance where Proforma Invoices must be created before regular invoices.
