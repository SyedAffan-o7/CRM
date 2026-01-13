/* Outbound interactions and logging */
(function() {
  // --- Helper Functions ---
  function getCookie(name) {
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          return decodeURIComponent(cookie.substring(name.length + 1));
        }
      }
    }
    return null;
  }

  const csrftoken = getCookie('csrftoken');

  // --- Main Logic ---
  document.addEventListener('DOMContentLoaded', function() {
    const logActivityForm = document.getElementById('logActivityForm');

    // 1. Delegated click handler for all communication buttons
    document.body.addEventListener('click', function(e) {
      const commButton = e.target.closest('[data-action="comm"]');
      if (commButton) {
        e.preventDefault();
        const { method, contactId, contactName, phone, whatsapp, email } = commButton.dataset;
        openModalWith(contactId, method, contactName, phone, whatsapp, email);
      }
    });

    // 2. Form submission handler (attached once)
    if (logActivityForm) {
      logActivityForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;

        const contactId = form.querySelector('input[name="contact"]').value;
        const urlTemplate = form.dataset.logUrl;
        const postUrl = urlTemplate.replace('0', contactId);

        try {
          const response = await fetch(postUrl, {
            method: 'POST',
            headers: {
              'X-Requested-With': 'XMLHttpRequest',
              'X-CSRFToken': csrftoken,
            },
            body: new FormData(form),
            credentials: 'same-origin',
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.error || `HTTP ${response.status}`);
          }

          // On success, hide modal and reload the page
          const modalEl = document.getElementById('logActivityModal');
          const modal = bootstrap.Modal.getInstance(modalEl);
          if (modal) {
            modal.hide();
          }
          window.location.reload();

        } catch (err) {
          console.error('Save error:', err);
          alert('Failed to save activity: ' + err.message);
        } finally {
          submitBtn.disabled = false;
        }
      });
    }

    // 3. Hover card functionality
    attachHoverCards(document.body);
  });

  // --- Modal & UI Functions ---

  function openModalWith(contactId, method, contactName, phone, whatsapp, email) {
    const modalEl = document.getElementById('logActivityModal');
    if (!modalEl) return;

    // Populate form and title
    modalEl.querySelector('input[name="contact"]').value = contactId;
    modalEl.querySelector('select[name="method"]').value = method || 'PHONE';
    modalEl.querySelector('#logActivityTitle').textContent = `Log Activity — ${contactName || ''}`;

    // Update the 'Open' button link
    updateOpenCommButton(method, contactName, phone, whatsapp, email);

    // Show the modal
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
  }

  function updateOpenCommButton(method, contactName, phone, whatsapp, email) {
    const quickBtn = document.getElementById('openCommBtn');
    if (!quickBtn) return;

    let href = '#';
    let label = 'Open';
    let icon = 'bi-arrow-up-right-square';

    if (method === 'WHATSAPP') {
      const number = (whatsapp || phone || '').replace(/\D/g, '');
      href = `https://wa.me/${number}`;
      label = 'Open WhatsApp';
      icon = 'bi-whatsapp';
    } else if (method === 'EMAIL') {
      const recipient = (email || '').trim();
      href = `mailto:${recipient}`;
      label = 'Open Email';
      icon = 'bi-envelope';
    } else if (method === 'PHONE') {
      const number = (phone || '').replace(/\D/g, '');
      href = `tel:${number}`;
      label = 'Start Call';
      icon = 'bi-whatsapp';
    }

    quickBtn.href = href;
    quickBtn.innerHTML = `<i class="${icon} me-1"></i> ${label}`;
  }

  function attachHoverCards(scope) {
    scope.querySelectorAll('.hover-card-container').forEach(container => {
      const trigger = container.querySelector('.hover-trigger');
      const card = container.querySelector('.hover-card');
      if (!trigger || !card) return;

      let hideTimeout;
      const show = () => {
        clearTimeout(hideTimeout);
        card.classList.add('show');
      };
      const hide = () => {
        hideTimeout = setTimeout(() => card.classList.remove('show'), 120);
      };

      container.addEventListener('mouseenter', show);
      container.addEventListener('mouseleave', hide);
      trigger.addEventListener('focus', show);
      card.addEventListener('blur', hide); // Hide if focus moves out of card
    });
  }
})();
