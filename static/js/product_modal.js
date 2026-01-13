// Global function definitions for onclick handlers
window.showProductModal = function(leadId) {
    const modalEl = document.getElementById('productModal');
    const body = document.getElementById('productModalBody');
    if (modalEl.parentElement !== document.body) {
        document.body.appendChild(modalEl);
    }
    const modal = new bootstrap.Modal(modalEl);
    body.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading product details...</p></div>';
    modal.show();
    fetch('/enquiries/' + leadId + '/products/')
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            let htmlContent = '';
            if (data.lead_products && data.lead_products.length > 0) {
                htmlContent += '<div class="row">';
                for (let i = 0; i < data.lead_products.length; i++) {
                    const product = data.lead_products[i];
                    const imageHtml = product.image ? '<img src="' + product.image + '" class="card-img-top" style="height:160px;object-fit:cover;" alt="Product image">' : '<div class="card-img-top bg-light d-flex align-items-center justify-content-center" style="height:160px;"><span class="text-muted">No image</span></div>';
                    const categoryText = product.category || 'No category';
                    const subcategoryBadge = product.subcategory ? ' <span class="badge bg-light text-dark ms-1">' + product.subcategory + '</span>' : '';
                    const descriptionText = product.description || 'No description';
                    const qtyText = (product.quantity !== null && product.quantity !== undefined) ? product.quantity : '-';
                    const priceText = (product.price !== null && product.price !== undefined) ? product.price : '-';
                    htmlContent += '<div class="col-md-6 mb-4">';
                    htmlContent += '<div class="card h-100">';
                    htmlContent += imageHtml;
                    htmlContent += '<div class="card-body">';
                    htmlContent += '<h6 class="card-title">' + categoryText + subcategoryBadge + '</h6>';
                    htmlContent += '<p class="card-text text-muted mb-2">' + descriptionText + '</p>';
                    htmlContent += '<div class="d-flex gap-3">';
                    htmlContent += '<span class="badge bg-primary">Qty: ' + qtyText + '</span>';
                    htmlContent += '<span class="badge bg-success">Rate: ' + priceText + '</span>';
                    htmlContent += '</div>';
                    htmlContent += '</div>';
                    htmlContent += '</div>';
                    htmlContent += '</div>';
                }
                htmlContent += '</div>';
            }
            if (htmlContent === '') {
                htmlContent = '<p class="text-muted">No products found.</p>';
            }
            body.innerHTML = htmlContent;
        })
        .catch(function(error) {
            body.innerHTML = '<div class="alert alert-danger"><i class="bi bi-exclamation-triangle"></i> ' + error.message + '</div>';
        });
};

// Function to handle onclick from data attributes (for enquiry history table)
window.showProductModalFromData = function(buttonElement) {
    const leadId = buttonElement.getAttribute('data-lead-id');
    if (leadId) {
        window.showProductModal(leadId);
    } else {
        console.error('No lead ID found in button data attributes');
    }
};
