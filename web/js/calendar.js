/**
 * BMS Date-Range Calendar Popover & Time Window Presets
 * Zero browser-native date picker inputs
 */

export class BmsCalendar {
  constructor(containerId, onRangeChangeCallback) {
    this.container = document.getElementById(containerId);
    this.onRangeChange = onRangeChangeCallback;
    this.isOpen = false;
    this.activePreset = "24h";
    this.startDate = null;
    this.endDate = null;
    this.viewDate = new Date();
    this.init();
  }

  init() {
    if (!this.container) return;
    this.triggerBtn = this.container.querySelector('.bms-btn');
    this.panel = this.container.querySelector('.calendar-panel');
    this.rangeLabel = this.container.querySelector('#active-range-label');
    this.monthTitle = this.container.querySelector('#cal-month-title');
    this.calGrid = this.container.querySelector('#cal-grid');

    this.triggerBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggle();
    });

    const presetPills = this.container.querySelectorAll('.preset-pill');
    presetPills.forEach(pill => {
      pill.addEventListener('click', (e) => {
        e.stopPropagation();
        this.selectPreset(pill.dataset.preset, pill);
      });
    });

    const prevBtn = this.container.querySelector('#cal-prev-btn');
    const nextBtn = this.container.querySelector('#cal-next-btn');
    if (prevBtn) prevBtn.addEventListener('click', (e) => { e.stopPropagation(); this.changeMonth(-1); });
    if (nextBtn) nextBtn.addEventListener('click', (e) => { e.stopPropagation(); this.changeMonth(1); });

    document.addEventListener('click', (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    });

    this.renderMonth();
  }

  toggle() {
    this.isOpen ? this.close() : this.open();
  }

  open() {
    this.isOpen = true;
    this.container.classList.add('calendar-open');
    this.renderMonth();
  }

  close() {
    this.isOpen = false;
    this.container.classList.remove('calendar-open');
  }

  selectPreset(presetKey, pillEl) {
    this.activePreset = presetKey;
    const presetPills = this.container.querySelectorAll('.preset-pill');
    presetPills.forEach(p => p.classList.remove('active'));
    if (pillEl) pillEl.classList.add('active');

    const labels = {
      "5m": "Live 5 Minutes",
      "1h": "Past 1 Hour",
      "24h": "Past 24 Hours",
      "7d": "Past 7 Days",
      "30d": "Past 30 Days",
      "ytd": "Year to Date",
      "lifetime": "Lifetime Archive"
    };

    if (this.rangeLabel) {
      this.rangeLabel.textContent = "Range: " + (labels[presetKey] || presetKey);
    }
    this.close();
    if (this.onRangeChange) {
      this.onRangeChange({ preset: presetKey, startEpoch: null, endEpoch: null });
    }
  }

  changeMonth(delta) {
    this.viewDate.setMonth(this.viewDate.getMonth() + delta);
    this.renderMonth();
  }

  renderMonth() {
    if (!this.calGrid || !this.monthTitle) return;
    const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const year = this.viewDate.getFullYear();
    const month = this.viewDate.getMonth();

    this.monthTitle.textContent = `${months[month]} ${year}`;
    this.calGrid.innerHTML = '';

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const prevDays = new Date(year, month, 0).getDate();

    // Fill leading empty days from previous month
    for (let i = firstDayIndex; i > 0; i--) {
      const d = document.createElement('div');
      d.className = 'cal-day other-month';
      d.textContent = prevDays - i + 1;
      this.calGrid.appendChild(d);
    }

    // Days in current month
    for (let day = 1; day <= daysInMonth; day++) {
      const d = document.createElement('div');
      d.className = 'cal-day';
      d.textContent = day;
      const dObj = new Date(year, month, day);

      if (this.startDate && dObj.toDateString() === this.startDate.toDateString()) {
        d.classList.add('start-date');
      }
      if (this.endDate && dObj.toDateString() === this.endDate.toDateString()) {
        d.classList.add('end-date');
      }
      if (this.startDate && this.endDate && dObj > this.startDate && dObj < this.endDate) {
        d.classList.add('in-range');
      }

      d.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleDayClick(dObj);
      });
      this.calGrid.appendChild(d);
    }
  }

  handleDayClick(dObj) {
    if (!this.startDate || (this.startDate && this.endDate)) {
      this.startDate = dObj;
      this.endDate = null;
    } else {
      if (dObj < this.startDate) {
        this.endDate = this.startDate;
        this.startDate = dObj;
      } else {
        this.endDate = dObj;
      }
      this.applyCustomRange();
    }
    this.renderMonth();
  }

  applyCustomRange() {
    if (!this.startDate || !this.endDate) return;
    const startIso = this.startDate.toISOString().split('T')[0];
    const endIso = this.endDate.toISOString().split('T')[0];
    if (this.rangeLabel) {
      this.rangeLabel.textContent = `${startIso} to ${endIso}`;
    }
    this.close();
    if (this.onRangeChange) {
      const startSec = this.startDate.getTime() / 1000;
      const endSec = (this.endDate.getTime() + 86400000) / 1000;
      this.onRangeChange({ preset: null, startEpoch: startSec, endEpoch: endSec });
    }
  }
}
