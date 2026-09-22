(() => {
  const focusableSelector = [
    'a[href]:not([tabindex="-1"])',
    'button:not([disabled]):not([tabindex="-1"])',
    'input:not([disabled]):not([tabindex="-1"])',
    'select:not([disabled]):not([tabindex="-1"])',
    'textarea:not([disabled]):not([tabindex="-1"])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  const menuToggle = document.querySelector('[data-menu-toggle]');
  const menu = document.querySelector('[data-menu]');

  const closeMenu = () => {
    if (!menuToggle || !menu) return;
    menu.classList.remove('is-open');
    menuToggle.setAttribute('aria-expanded', 'false');
  };

  if (menuToggle && menu) {
    menuToggle.addEventListener('click', () => {
      const isOpen = menuToggle.getAttribute('aria-expanded') === 'true';
      menuToggle.setAttribute('aria-expanded', String(!isOpen));
      menu.classList.toggle('is-open', !isOpen);
    });

    menu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeMenu);
    });
  }

  document.querySelectorAll('[data-tabs]').forEach((tabsRoot) => {
    const tabs = [...tabsRoot.querySelectorAll('[role="tab"]')];
    const panels = [...tabsRoot.querySelectorAll('[role="tabpanel"]')];

    const activateTab = (nextTab, moveFocus = true) => {
      tabs.forEach((tab) => {
        const isActive = tab === nextTab;
        tab.setAttribute('aria-selected', String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
      });

      panels.forEach((panel) => {
        panel.hidden = panel.id !== nextTab.getAttribute('aria-controls');
      });

      if (moveFocus) nextTab.focus();
    };

    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => activateTab(tab, false));
      tab.addEventListener('keydown', (event) => {
        let nextIndex = index;
        if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') nextIndex = 0;
        if (event.key === 'End') nextIndex = tabs.length - 1;
        if (nextIndex !== index) {
          event.preventDefault();
          activateTab(tabs[nextIndex]);
        }
      });
    });
  });

  let activeModal = null;
  let modalOpener = null;

  const getFocusable = (root) => [...root.querySelectorAll(focusableSelector)]
    .filter((element) => !element.hasAttribute('hidden') && element.offsetParent !== null);

  const closeModal = () => {
    if (!activeModal) return;
    activeModal.hidden = true;
    document.body.classList.remove('modal-open');
    const opener = modalOpener;
    activeModal = null;
    modalOpener = null;
    if (opener) opener.focus();
  };

  const openModal = (modal, opener) => {
    if (!modal) return;
    activeModal = modal;
    modalOpener = opener;
    modal.hidden = false;
    document.body.classList.add('modal-open');
    requestAnimationFrame(() => {
      const focusable = getFocusable(modal);
      if (focusable.length) focusable[0].focus();
    });
  };

  document.querySelectorAll('[data-open-modal]').forEach((button) => {
    button.addEventListener('click', () => {
      openModal(document.getElementById(button.dataset.openModal), button);
    });
  });

  document.querySelectorAll('[data-close-modal]').forEach((button) => {
    button.addEventListener('click', closeModal);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      if (activeModal) {
        closeModal();
      } else if (menu?.classList.contains('is-open')) {
        closeMenu();
        menuToggle?.focus();
      }
    }

    if (event.key === 'Tab' && activeModal) {
      const focusable = getFocusable(activeModal);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  const setFieldError = (field, message) => {
    const container = field.closest('.form-field');
    const error = container?.querySelector('.field-error');
    if (!error) return;
    error.textContent = message;
    field.setAttribute('aria-invalid', String(Boolean(message)));
    if (message) {
      if (!error.id) error.id = `${field.id}-error`;
      field.setAttribute('aria-describedby', error.id);
    } else {
      field.removeAttribute('aria-describedby');
    }
  };

  document.querySelectorAll('[data-demo-form]').forEach((form) => {
    const requiredFields = [...form.querySelectorAll('[required]')];

    requiredFields.forEach((field) => {
      field.addEventListener('input', () => {
        if (field.checkValidity()) setFieldError(field, '');
      });
      field.addEventListener('change', () => {
        if (field.checkValidity()) setFieldError(field, '');
      });
    });

    form.addEventListener('submit', (event) => {
      event.preventDefault();
      let firstInvalid = null;

      requiredFields.forEach((field) => {
        const message = field.checkValidity() ? '' : field.validationMessage;
        setFieldError(field, message);
        if (message && !firstInvalid) firstInvalid = field;
      });

      if (firstInvalid) {
        firstInvalid.focus();
        return;
      }

      const success = form.querySelector('[data-form-success]');
      if (success) {
        success.hidden = false;
        success.focus();
      }
      form.reset();
      requiredFields.forEach((field) => setFieldError(field, ''));
    });
  });

  document.querySelectorAll('[data-carousel]').forEach((carousel) => {
    const track = carousel.querySelector('[data-carousel-track]');
    const slides = [...carousel.querySelectorAll('[data-slide]')];
    const previous = carousel.querySelector('[data-carousel-prev]');
    const next = carousel.querySelector('[data-carousel-next]');
    const status = carousel.querySelector('[data-carousel-status]');
    let current = 0;

    const render = () => {
      if (!track || !slides.length) return;
      track.style.transform = `translateX(-${current * 100}%)`;
      slides.forEach((slide, index) => {
        slide.setAttribute('aria-hidden', String(index !== current));
      });
      if (previous) previous.disabled = current === 0;
      if (next) next.disabled = current === slides.length - 1;
      if (status) status.textContent = `${current + 1} / ${slides.length}`;
    };

    previous?.addEventListener('click', () => {
      if (current > 0) current -= 1;
      render();
    });

    next?.addEventListener('click', () => {
      if (current < slides.length - 1) current += 1;
      render();
    });

    render();
  });
})();
