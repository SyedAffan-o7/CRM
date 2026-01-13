/**
 * Enquiries Management Module
 * Handles all lead list interactions including stage/status updates and modals
 */
class EnquiriesManager {
    constructor(config) {
        console.log('EnquiriesManager constructor called');

        // Configuration
        this.config = config;

        // State
        this.pendingStageSelect = null;
        this.pendingStageValue = null;
        this.currentLeadId = null;
        this.currentStatusSelect = null;
        this.invoiceCreateWarningLeadId = null;

        // Initialize when DOM is loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.initialize());
        } else {
            // DOM is already loaded
            this.initialize();
        }
        console.log('EnquiriesManager constructor completed');
    }

    /**
     * Initialize the manager
     */
    initialize() {
        console.log('EnquiriesManager initializing...');
        this.initializeModals();
        this.initializeEventListeners();
        this.checkExistingLockedLeads();

        // Set CSRF token for AJAX requests
        this.setupCSRFToken();
        console.log('EnquiriesManager initialized with config:', this.config);
    }

    /**
     * Set up CSRF token for AJAX requests
     */
    setupCSRFToken() {
        // Use the token from config or try to get from cookie
        window.csrftoken = this.config.csrfToken || this.getCookie('csrftoken');
    }

    /**
     * Check for existing locked leads on page load and apply visual indicators
     */
    checkExistingLockedLeads() {
        console.log('🔍 Checking for existing locked leads...');

        // Find all stage select elements that are already in "invoice_sent" stage
        const invoiceSentSelects = document.querySelectorAll('.stage-select[data-current-stage="invoice_sent"]');

        console.log(`Found ${invoiceSentSelects.length} leads already in "invoice_sent" stage`);

        invoiceSentSelects.forEach(selectElement => {
            console.log(`Applying lock styling to lead ${selectElement.dataset.leadId}`);

            // Apply the same locking behavior as when a lead gets locked after update
            selectElement.disabled = true;
            selectElement.classList.add('bg-light', 'text-muted');
            selectElement.title = 'This enquiry is locked and cannot be modified after fulfillment';

            // Also disable the status select for this lead
            const statusSelect = document.querySelector(`.status-select[data-lead-id="${selectElement.dataset.leadId}"]`);
            if (statusSelect) {
                statusSelect.disabled = true;
                statusSelect.classList.add('bg-light', 'text-muted');
                statusSelect.title = 'This enquiry is locked and cannot be modified after fulfillment';
            }

            // Add visual indicator to the card
            const card = selectElement.closest('.modern-enquiry-card');
            if (card) {
                card.classList.add('opacity-75');
                card.style.borderLeftColor = '#28a745';

                // Add a small badge or indicator
                const badge = document.createElement('span');
                badge.className = 'badge bg-success position-absolute';
                badge.style.cssText = 'top: 5px; right: 5px; font-size: 0.6rem;';
                badge.textContent = '✓';
                badge.title = 'Fulfilled & Locked';
                card.style.position = 'relative';
                card.appendChild(badge);
            }
        });

        console.log('✅ Existing locked leads styling applied');
    }

    /**
     * Update Kanban UI after a stage change without reloading the page
     */
    updateKanbanAfterStageChange(selectElement, stage) {
        try {
            // Detect if we're on the kanban page
            const kanbanBoard = document.querySelector('.kanban-board');
            if (!kanbanBoard || !selectElement) return;

            const card = selectElement.closest('.kanban-card');
            const oldColumn = selectElement.closest('.kanban-column');
            const newColumn = document.querySelector(`.kanban-column.stage-${stage}`);

            if (!card || !oldColumn || !newColumn) return;
            if (oldColumn === newColumn) return; // No move needed

            // Add a brief 'moving' style then move the card: insert just after the header in the new column
            card.classList.add('moving');
            const header = newColumn.querySelector('.kanban-header');
            if (header && header.parentNode === newColumn) {
                newColumn.insertBefore(card, header.nextSibling);
            } else {
                newColumn.appendChild(card);
            }
            // Trigger animate-in and remove 'moving'
            card.classList.remove('moving');
            card.classList.add('animate-in');
            setTimeout(() => card.classList.remove('animate-in'), 350);

            // Update column counts
            const parseCount = (el) => {
                if (!el) return 0;
                const n = parseInt(el.textContent.trim(), 10);
                return isNaN(n) ? 0 : n;
            };

            const oldCountEl = oldColumn.querySelector('.stage-count');
            const newCountEl = newColumn.querySelector('.stage-count');
            const oldCount = parseCount(oldCountEl);
            const newCount = parseCount(newCountEl);
            if (oldCountEl) {
                oldCountEl.textContent = Math.max(0, oldCount - 1);
                oldCountEl.classList.add('bump');
                setTimeout(() => oldCountEl.classList.remove('bump'), 350);
            }
            if (newCountEl) {
                newCountEl.textContent = newCount + 1;
                newCountEl.classList.add('bump');
                setTimeout(() => newCountEl.classList.remove('bump'), 350);
            }

            // Remove placeholder in new column if present
            const placeholderEl = newColumn.querySelector('.text-center.text-muted.py-4');
            if (placeholderEl) placeholderEl.remove();

            // Optionally add placeholder to old column if it became empty
            const hasAnyCards = oldColumn.querySelector('.kanban-card');
            if (!hasAnyCards) {
                // Create a minimal placeholder similar to the template's empty state
                const emptyDiv = document.createElement('div');
                emptyDiv.className = 'text-center text-muted py-4';
                emptyDiv.innerHTML = '<i class="bi bi-inbox" style="font-size: 2rem;"></i><p class="mt-2">No enquiries in this stage</p>';
                oldColumn.appendChild(emptyDiv);
            }
        } catch (e) {
            console.error('Error updating Kanban after stage change:', e);
        }
    }

    handleInvoiceCreateRedirect() {
        const leadId = this.invoiceCreateWarningLeadId;
        if (this.invoiceCreateWarningModal) {
            this.invoiceCreateWarningModal.hide();
        }

        let targetUrl = (this.config.urls && this.config.urls.invoiceAdd) ? this.config.urls.invoiceAdd : '/invoices/add/';
        if (leadId) {
            const sep = targetUrl.indexOf('?') === -1 ? '?' : '&';
            targetUrl = `${targetUrl}${sep}lead=${encodeURIComponent(leadId)}`;
        }
        window.location.href = targetUrl;
    }

    /**
     * Initialize all modals
     */
    initializeModals() {
        console.log('Initializing modals...');

        // Check if Bootstrap is available
        if (typeof bootstrap === 'undefined') {
            console.error('❌ Bootstrap is not loaded! Modal initialization failed.');
            return;
        }

        if (!bootstrap.Modal) {
            console.error('❌ Bootstrap Modal class not available!');
            return;
        }

        // Invoice/Proforma Modal
        const invoiceModalEl = document.getElementById('invoiceModal');
        if (invoiceModalEl) {
            try {
                this.invoiceModal = new bootstrap.Modal(invoiceModalEl);
                console.log('✅ Invoice modal initialized successfully');
            } catch (error) {
                console.error('❌ Failed to initialize invoice modal:', error);
                this.invoiceModal = null;
            }
        } else {
            console.warn('⚠️ Invoice modal element not found');
        }

        this.invoiceTitleEl = document.getElementById('invoiceModalTitle');
        this.invoiceLabelEl = document.getElementById('invoiceInputLabel');
        this.invoiceInputEl = document.getElementById('invoiceInput');
        this.invoiceHelpEl = document.getElementById('invoiceHelp');

        // Reason Modal
        const reasonModalEl = document.getElementById('reasonModal');
        if (reasonModalEl) {
            try {
                this.reasonModal = new bootstrap.Modal(reasonModalEl);
                console.log('✅ Reason modal initialized successfully');
            } catch (error) {
                console.error('❌ Failed to initialize reason modal:', error);
                this.reasonModal = null;
            }
        } else {
            console.warn('⚠️ Reason modal element not found');
        }

        this.reasonSelect = document.getElementById('reasonSelect');

        const invoiceCreateWarningEl = document.getElementById('invoiceCreateWarningModal');
        if (invoiceCreateWarningEl) {
            try {
                this.invoiceCreateWarningModal = new bootstrap.Modal(invoiceCreateWarningEl);
            } catch (error) {
                console.error('❌ Failed to initialize invoice create warning modal:', error);
                this.invoiceCreateWarningModal = null;
            }
        }

        console.log('Modal initialization completed');
    }

    /**
     * Initialize event listeners using event delegation
     */
    initializeEventListeners() {
        try {
            console.log('Initializing event listeners...');

            // Listen for all change events on the document
            document.addEventListener('change', (e) => {
                if (e.target.matches('.status-select')) {
                    this.handleStatusChange(e.target);
                } else if (e.target.matches('.reason-select')) {
                    this.handleReasonChange(e.target);
                } else if (e.target.matches('.stage-select')) {
                    this.handleStageChange(e.target);
                }
            });

            // Direct bindings for modals
            const saveInvoiceBtn = document.getElementById('invoiceSave');
            if (saveInvoiceBtn) {
                saveInvoiceBtn.addEventListener('click', () => this.handleInvoiceSave());
            }

            const saveReasonBtn = document.getElementById('saveReason');
            if (saveReasonBtn) {
                saveReasonBtn.addEventListener('click', () => this.handleReasonSave());
            }

            const goToInvoiceBtn = document.getElementById('invoiceCreateWarningGoBtn');
            if (goToInvoiceBtn) {
                goToInvoiceBtn.addEventListener('click', () => this.handleInvoiceCreateRedirect());
            }

            const invoiceModal = document.getElementById('invoiceModal');
            if (invoiceModal) {
                invoiceModal.addEventListener('hidden.bs.modal', () => {
                    this.resetInvoiceModal();
                });
            }

            console.log('Event listeners initialized');

        } catch (error) {
            console.error('Error initializing event listeners:', error);
        }
    }

    /**
     * Handle status change event
     */
    async handleStatusChange(selectElement) {
        try {
            if (!selectElement) return;

            const leadId = selectElement.dataset.leadId;
            const newStatus = selectElement.value;
            const previousStatus = selectElement.dataset.currentStatus;

            if (!leadId) return;

            // If status is changing to 'not_fulfilled', show reason modal
            if (newStatus === 'not_fulfilled') {
                this.currentLeadId = leadId;
                this.currentStatusSelect = selectElement;

                if (!this.reasonModal) {
                    const modalEl = document.getElementById('reasonModal');
                    if (modalEl) {
                        this.reasonModal = new bootstrap.Modal(modalEl);
                    }
                }

                this.reasonModal.show();
                selectElement.value = previousStatus;
                return;
            }

            await this.updateStatus(leadId, newStatus, null, selectElement);

        } catch (error) {
            console.error('Error in handleStatusChange:', error);
            if (selectElement) {
                selectElement.value = selectElement.dataset.currentStatus || '';
            }
            this.showError('Failed to update status. Please try again.');
        }
    }

    /**
     * Handle stage change event
     */
    async handleStageChange(selectElement) {
        try {
            if (!selectElement) return;

            const leadId = selectElement.dataset.leadId;
            const newStage = selectElement.value;

            if (!leadId) return;

            if (newStage === 'invoice_sent') {
                selectElement.value = selectElement.dataset.currentStage || '';
                this.showCreateInvoiceWarning(leadId);
                return;
            }

            if (newStage === 'proforma_invoice_sent') {
                this.pendingStageSelect = selectElement;
                this.pendingStageValue = newStage;
                this.showInvoiceModal('Proforma Invoice', 'Enter Proforma Invoice Number', 'Please enter the Proforma Invoice number');
                return;
            }

            if (newStage === 'invoice_made') {
                this.pendingStageSelect = selectElement;
                this.pendingStageValue = newStage;
                this.showInvoiceModal('Invoice', 'Enter Invoice Number', 'Please enter the Invoice number');
                return;
            }

            // For other stages, update directly
            await this.updateEnquiryStage(leadId, newStage, selectElement);

        } catch (error) {
            console.error('Error in handleStageChange:', error);
            if (selectElement) {
                selectElement.value = selectElement.dataset.currentStage || '';
            }
            this.showError('Failed to update stage. Please try again.');
        }
    }

    showCreateInvoiceWarning(leadId) {
        this.invoiceCreateWarningLeadId = leadId;
        if (this.invoiceCreateWarningModal) {
            this.invoiceCreateWarningModal.show();
        } else {
            this.showError('Please create an invoice for this enquiry from the Invoices module before marking it as Invoice Sent.');
        }
    }

    /**
     * Show invoice modal with custom text
     */
    showInvoiceModal(title, label, helpText = '') {
        // Ensure modal elements exist
        if (!this.invoiceModal) {
            this.initializeModals();
        }

        if (this.invoiceTitleEl) this.invoiceTitleEl.textContent = title;
        if (this.invoiceLabelEl) this.invoiceLabelEl.textContent = label;
        if (this.invoiceHelpEl) this.invoiceHelpEl.textContent = helpText;
        if (this.invoiceInputEl) {
            this.invoiceInputEl.value = '';
            this.invoiceInputEl.classList.remove('is-invalid');
        }

        if (this.invoiceModal) {
            this.invoiceModal.show();
        } else {
            console.error('Modal not available!');
        }
    }

    /**
     * Handle invoice modal save
     */
    async handleInvoiceSave() {
        const num = this.invoiceInputEl.value.trim();

        if (!num) {
            this.invoiceInputEl.classList.add('is-invalid');
            return;
        }

        this.invoiceInputEl.classList.remove('is-invalid');

        if (!this.pendingStageSelect || !this.pendingStageValue) {
            console.error('No pending stage data available');
            this.invoiceModal.hide();
            return;
        }

        try {
            await this.updateEnquiryStage(
                this.pendingStageSelect.dataset.leadId,
                this.pendingStageValue,
                this.pendingStageSelect,
                num
            );
            this.invoiceModal.hide();
        } catch (error) {
            console.error('Error in handleInvoiceSave:', error);
            this.invoiceModal.hide();
        } finally {
            this.pendingStageSelect = null;
            this.pendingStageValue = null;
        }
    }

    /**
     * Handle reason modal save
     */
    async handleReasonSave() {
        const reasonId = this.reasonSelect.value;
        if (!reasonId) {
            alert('Please select a reason');
            return;
        }

        await this.updateStatus(this.currentLeadId, 'not_fulfilled', reasonId, this.currentStatusSelect);
        this.reasonModal.hide();
    }

    /**
     * Reset invoice modal
     */
    resetInvoiceModal() {
        if (this.pendingStageSelect) {
            this.pendingStageSelect.value = this.pendingStageSelect.dataset.currentStage;
        }

        this.pendingStageSelect = null;
        this.pendingStageValue = null;

        if (this.invoiceInputEl) {
            this.invoiceInputEl.value = '';
            this.invoiceInputEl.classList.remove('is-invalid');
        }
    }

    /**
     * Update status via AJAX
     */
    async updateStatus(leadId, status, reasonId, selectElement) {
        if (!selectElement) return;

        const previousStatus = selectElement.dataset.currentStatus;
        this.setLoadingState(selectElement, true, previousStatus);

        try {
            const formData = new FormData();
            formData.append('status', status);
            formData.append('csrfmiddlewaretoken', window.csrftoken);

            if (reasonId) {
                formData.append('reason_id', reasonId);
            }

            const response = await fetch(this.config.urls.updateStatus.replace('999', leadId), {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': window.csrftoken,
                },
                body: formData,
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success) {
                selectElement.dataset.currentStatus = status;
                selectElement.value = status;
                selectElement.classList.add('bg-success', 'text-white');
                setTimeout(() => {
                    selectElement.classList.remove('bg-success', 'text-white');
                }, 1000);

                this.showSuccess('Status updated successfully');
                setTimeout(() => window.location.reload(), 1500);
            } else {
                throw new Error(data.error || 'Failed to update status');
            }
        } catch (error) {
            console.error('Error updating status:', error);
            selectElement.value = previousStatus;
            this.showError('Failed to update status: ' + error.message);
        } finally {
            this.setLoadingState(selectElement, false);
        }
    }

    /**
     * Update enquiry stage via AJAX
     */
    async updateEnquiryStage(leadId, stage, selectElement, numberValue = null) {
        if (!selectElement) return;

        const previousStage = selectElement.dataset.currentStage;
        this.setLoadingState(selectElement, true, previousStage);

        try {
            const formData = new FormData();
            formData.append('enquiry_stage', stage);
            formData.append('csrfmiddlewaretoken', window.csrftoken);

            if (stage === 'proforma_invoice_sent' && numberValue) {
                formData.append('proforma_invoice_number', numberValue);
            } else if ((stage === 'invoice_made' || stage === 'invoice_sent') && numberValue) {
                formData.append('invoice_number', numberValue);
            }

            const response = await fetch(this.config.urls.updateStage.replace('999', leadId), {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': window.csrftoken,
                },
                body: formData,
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (data.success) {
                selectElement.dataset.currentStage = stage;
                selectElement.value = stage;

                // Update PI and Invoice numbers in the table row (if present)
                const row = selectElement.closest('tr');
                if (row) {
                    const piCell = row.querySelector('.pi-number-cell');
                    if (piCell && 'proforma_invoice_number' in data) {
                        piCell.textContent = data.proforma_invoice_number || '-';
                    }

                    const invoiceCell = row.querySelector('.invoice-number-cell');
                    if (invoiceCell && 'invoice_number' in data) {
                        invoiceCell.textContent = data.invoice_number || '-';
                    }
                }

                // Handle locked leads
                if (data.is_locked) {
                    selectElement.disabled = true;
                    selectElement.classList.add('bg-light', 'text-muted');
                    selectElement.title = 'This enquiry is locked and cannot be modified after fulfillment';

                    // Also disable the status select for this lead
                    const statusSelect = document.querySelector(`.status-select[data-lead-id="${leadId}"]`);
                    if (statusSelect) {
                        statusSelect.disabled = true;
                        statusSelect.classList.add('bg-light', 'text-muted');
                        statusSelect.title = 'This enquiry is locked and cannot be modified after fulfillment';
                    }

                    const card = selectElement.closest('.modern-enquiry-card');
                    if (card) {
                        card.classList.add('opacity-75');
                        card.style.borderLeftColor = '#28a745';
                    }
                }

                this.showSuccess(data.message || 'Stage updated successfully');
            } else {
                throw new Error(data.error || 'Failed to update stage');
            }
        } catch (error) {
            console.error('Error updating stage:', error);
            selectElement.value = previousStage;
            this.showError('Failed to update stage: ' + error.message);
        } finally {
            this.setLoadingState(selectElement, false);
        }
    }

    /**
     * Set loading state for an element
     */
    setLoadingState(element, isLoading, originalValue = null) {
        if (!element) return;

        if (isLoading) {
            element.disabled = true;
            const originalHTML = element.innerHTML;
            element.dataset.originalHtml = originalHTML;
            element.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        } else {
            element.disabled = false;
            if (originalValue !== null && element.tagName === 'SELECT') {
                element.value = originalValue;
            }
            if (element.dataset.originalHtml) {
                element.innerHTML = element.dataset.originalHtml;
                delete element.dataset.originalHtml;
            }
        }
    }

    /**
     * Show success message
     */
    showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-success alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `<strong>Success!</strong> ${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 3000);
    }

    /**
     * Show error message
     */
    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `<strong>Error!</strong> ${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
        document.body.appendChild(notification);

        setTimeout(() => notification.remove(), 5000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('EnquiriesManager script loaded and DOM is ready');
    if (window.leadListConfig) {
        console.log('leadListConfig found:', window.leadListConfig);
        window.enquiriesManager = new EnquiriesManager(window.leadListConfig);
        console.log('EnquiriesManager instance created');
    } else {
        console.error('leadListConfig is not defined. Please check your template.');
    }
});

// Debug: Log when the script is loaded
console.log('enquiries.js script loaded');

// Add a global function for manual testing
window.testModal = function() {
    console.log('Testing modal manually...');
    if (window.enquiriesManager) {
        console.log('EnquiriesManager found');
        window.enquiriesManager.showInvoiceModal(
            'Test Modal',
            'Test Label',
            'This is a test'
        );
    } else {
        console.error('EnquiriesManager not found');
    }
};

window.testStageChange = function(leadId, newStage) {
    console.log('🧪 Testing stage change manually...');
    console.log('Parameters:', { leadId, newStage });

    if (!window.enquiriesManager) {
        console.error('❌ EnquiriesManager not found');
        return;
    }

    // Find the stage select dropdown for the specified lead
    const stageSelect = document.querySelector(`.stage-select[data-lead-id="${leadId}"]`);
    if (!stageSelect) {
        console.error(`❌ No stage select found for lead ID: ${leadId}`);
        console.log('Available lead IDs:', Array.from(document.querySelectorAll('.stage-select')).map(el => el.dataset.leadId));
        return;
    }

    console.log('✅ Found stage select element:', stageSelect);
    console.log('Current stage:', stageSelect.value);
    console.log('Current dataset:', stageSelect.dataset);

    // Set the new stage value
    stageSelect.value = newStage;
    console.log('Set new stage value to:', newStage);

    // Trigger the change event
    console.log('Triggering change event...');
    stageSelect.dispatchEvent(new Event('change', { bubbles: true }));

    console.log('✅ Test completed. Check console for update logs.');
};

// Helper function to test with first available lead
window.testFirstStageChange = function(newStage = 'invoice_sent') {
    const firstStageSelect = document.querySelector('.stage-select');
    if (firstStageSelect) {
        const leadId = firstStageSelect.dataset.leadId;
        console.log(`Testing with first lead (ID: ${leadId})`);
        window.testStageChange(leadId, newStage);
    } else {
        console.error('No stage selects found on page');
    }
};

console.log('🧪 Available test functions:');
console.log('- testStageChange(leadId, newStage) - Test specific lead stage change');
console.log('- testFirstStageChange(newStage) - Test first lead stage change');
console.log('- testImmediateUpdate(leadId, newStage) - Test DOM update without AJAX');
console.log('- testAllSelects() - List all stage selects');
console.log('- debugPendingData() - Check current pending stage data');
console.log('- clearPendingData() - Clear pending stage data manually');
console.log('- forceReload() - Force reload page to clear cache');
console.log('Example: testFirstStageChange("invoice_sent") or testStageChange(1, "invoice_sent")');

// Force reload function to clear browser cache
window.forceReload = function() {
    console.log('🔄 Forcing page reload to clear cache...');
    window.location.reload(true);
};

// Test immediate DOM update (no AJAX)
window.testImmediateUpdate = function(leadId, newStage) {
    console.log('🧪 Testing immediate DOM update...');
    console.log('Parameters:', { leadId, newStage });

    const selectElement = document.querySelector(`.stage-select[data-lead-id="${leadId}"]`);
    if (!selectElement) {
        console.error(`❌ No stage select found for lead ID: ${leadId}`);
        return;
    }

    console.log('Found element:', selectElement);
    console.log('Current value:', selectElement.value);

    // Direct DOM update
    const oldValue = selectElement.value;
    selectElement.value = newStage;
    selectElement.dataset.currentStage = newStage;

    console.log(`✅ DOM updated: ${oldValue} → ${selectElement.value}`);

    // Add visual feedback
    selectElement.classList.add('bg-success', 'text-white');
    setTimeout(() => {
        selectElement.classList.remove('bg-success', 'text-white');
    }, 1000);

    console.log('✅ Test completed - check if dropdown shows new value');
};

// Test all stage selects
window.testAllSelects = function() {
    console.log('🧪 Testing all stage selects...');
    const selects = document.querySelectorAll('.stage-select');
    console.log(`Found ${selects.length} stage selects:`);

    selects.forEach((select, index) => {
        console.log(`${index + 1}. Lead ID: ${select.dataset.leadId}, Current: ${select.value}`);
    });
};

// Debug pending data
window.debugPendingData = function() {
    console.log('🔍 Current pending stage data:');
    console.log('pendingStageSelect:', window.enquiriesManager?.pendingStageSelect);
    console.log('pendingStageValue:', window.enquiriesManager?.pendingStageValue);

    if (window.enquiriesManager?.pendingStageSelect) {
        console.log('Element details:', {
            tagName: window.enquiriesManager.pendingStageSelect.tagName,
            value: window.enquiriesManager.pendingStageSelect.value,
            dataset: window.enquiriesManager.pendingStageSelect.dataset,
            inDOM: document.contains(window.enquiriesManager.pendingStageSelect)
        });
    }
};

// Clear pending data manually
window.clearPendingData = function() {
    console.log('🧹 Clearing pending stage data manually');
    if (window.enquiriesManager) {
        window.enquiriesManager.pendingStageSelect = null;
        window.enquiriesManager.pendingStageValue = null;
        console.log('✅ Pending data cleared');
    }
};