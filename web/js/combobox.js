/**
 * BMS Accessible Combobox Component (Popover + Search + Keyboard Nav)
 * Zero browser-native <select> / <option> tags
 */

export class BmsCombobox {
  constructor(containerId, options, onSelectCallback) {
    this.container = document.getElementById(containerId);
    this.options = options;
    this.onSelect = onSelectCallback;
    this.isOpen = false;
    this.selectedIndex = 0;
    this.init();
  }

  init() {
    if (!this.container) return;
    this.triggerBtn = this.container.querySelector('.combobox-trigger');
    this.menu = this.container.querySelector('.combobox-menu');
    this.searchInput = this.container.querySelector('.combobox-search-input');
    this.listContainer = this.container.querySelector('.combobox-options-list');
    this.selectedLabel = this.container.querySelector('#combobox-selected-label');

    this.renderOptions(this.options);

    this.triggerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    if (this.searchInput) {
      this.searchInput.addEventListener('input', (e) => this.filterOptions(e.target.value));
      this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));
    }

    document.addEventListener('click', (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    });
  }

  toggle() {
    this.isOpen ? this.close() : this.open();
  }

  open() {
    this.isOpen = true;
    this.container.classList.add('combobox-open');
    if (this.searchInput) {
      this.searchInput.value = '';
      this.filterOptions('');
      setTimeout(() => this.searchInput.focus(), 50);
    }
  }

  close() {
    this.isOpen = false;
    this.container.classList.remove('combobox-open');
  }

  renderOptions(opts) {
    if (!this.listContainer) return;
    this.listContainer.innerHTML = '';
    opts.forEach((opt, idx) => {
      const item = document.createElement('div');
      item.className = 'combobox-item' + (idx === this.selectedIndex ? ' is-selected' : '');
      item.textContent = opt.label;
      item.dataset.key = opt.key;
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectItem(idx, opt);
      });
      this.listContainer.appendChild(item);
    });
  }

  selectItem(idx, opt) {
    this.selectedIndex = idx;
    if (this.selectedLabel) {
      this.selectedLabel.textContent = 'Metric: ' + opt.label;
    }
    const items = this.listContainer.querySelectorAll('.combobox-item');
    items.forEach((it, i) => {
      it.classList.toggle('is-selected', i === idx);
    });
    this.close();
    if (this.onSelect) this.onSelect(opt.key, opt.label);
  }

  filterOptions(query) {
    const q = (query || '').toLowerCase().trim();
    const items = this.listContainer.querySelectorAll('.combobox-item');
    items.forEach(it => {
      const text = it.textContent.toLowerCase();
      it.style.display = text.includes(q) ? 'flex' : 'none';
    });
  }

  handleKeydown(e) {
    const visibleItems = Array.from(this.listContainer.querySelectorAll('.combobox-item')).filter(
      it => it.style.display !== 'none'
    );
    if (!visibleItems.length) return;

    if (e.key === 'Escape') {
      this.close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      // cycle down
      let next = visibleItems.findIndex(it => it.classList.contains('is-selected')) + 1;
      if (next >= visibleItems.length) next = 0;
      visibleItems.forEach((it, i) => it.classList.toggle('is-selected', i === next));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      // cycle up
      let prev = visibleItems.findIndex(it => it.classList.contains('is-selected')) - 1;
      if (prev < 0) prev = visibleItems.length - 1;
      visibleItems.forEach((it, i) => it.classList.toggle('is-selected', i === prev));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const selected = visibleItems.find(it => it.classList.contains('is-selected')) || visibleItems[0];
      if (selected) {
        const key = selected.dataset.key;
        const opt = this.options.find(o => o.key === key);
        if (opt) this.selectItem(this.options.indexOf(opt), opt);
      }
    }
  }
}
