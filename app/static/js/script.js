(function () {
  // ── Theme & mode ──────────────────────────────────────────────
  const html = document.documentElement;

  const savedTheme = localStorage.getItem('theme') || 'blueprint';
  const savedMode = localStorage.getItem('mode') || 'dark';
  html.setAttribute('data-theme', savedTheme);
  html.setAttribute('data-mode', savedMode);

  // Sync theme toggle buttons
  document.querySelectorAll('.theme-btn').forEach(btn => {
    const isActive = btn.dataset.theme === savedTheme;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-checked', String(isActive));
  });

  // Mode toggle button label
  const modeBtn = document.getElementById('mode-toggle');
  const updateModeBtnLabel = (mode) => {
    modeBtn.textContent = mode === 'dark' ? '☀️' : '🌙';
    modeBtn.setAttribute('aria-label', mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
  };
  updateModeBtnLabel(savedMode);

  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.theme;
      html.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
      document.querySelectorAll('.theme-btn').forEach(b => {
        const active = b.dataset.theme === theme;
        b.classList.toggle('active', active);
        b.setAttribute('aria-checked', String(active));
      });
    });
  });

  modeBtn.addEventListener('click', () => {
    const current = html.getAttribute('data-mode');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-mode', next);
    localStorage.setItem('mode', next);
    updateModeBtnLabel(next);
  });

  // ── Weight unit toggle ────────────────────────────────────────
  let currentUnit = localStorage.getItem('unit') || 'lbs';
  const weightInput = document.getElementById('weight');
  const weightUnitDisplay = document.getElementById('weight-unit-display');

  // Sync unit display and button states from persisted value
  weightUnitDisplay.textContent = currentUnit;
  document.querySelectorAll('.unit-btn').forEach(b => {
    const active = b.dataset.unit === currentUnit;
    b.classList.toggle('active', active);
    b.setAttribute('aria-checked', String(active));
  });

  document.querySelectorAll('.unit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const newUnit = btn.dataset.unit;
      if (newUnit === currentUnit) return;

      const val = parseFloat(weightInput.value) || 0;
      weightInput.value = newUnit === 'kg'
        ? Math.round(val / 2.20462)
        : Math.round(val * 2.20462);
      currentUnit = newUnit;
      localStorage.setItem('unit', newUnit);
      weightUnitDisplay.textContent = newUnit;

      document.querySelectorAll('.unit-btn').forEach(b => {
        const active = b.dataset.unit === newUnit;
        b.classList.toggle('active', active);
        b.setAttribute('aria-checked', String(active));
      });
      updateWeightTrack();
    });
  });

  // ── Gauge track updates ───────────────────────────────────────
  const updateWeightTrack = () => {
    const val = parseFloat(weightInput.value) || 0;
    const max = currentUnit === 'lbs' ? 400 : 180;
    document.getElementById('weight-track').style.width =
      Math.min(100, (val / max) * 100) + '%';
  };

  const ageInput = document.getElementById('age');
  const updateAgeTrack = () => {
    const val = parseFloat(ageInput.value) || 0;
    document.getElementById('age-track').style.width =
      Math.min(100, ((val - 18) / 80) * 100) + '%';
  };

  const drinksInput = document.getElementById('current-drinks');
  const updateDrinksTrack = () => {
    const val = parseFloat(drinksInput.value) || 0;
    document.getElementById('drinks-track').style.width =
      Math.min(100, (val / 20) * 100) + '%';
  };

  weightInput.addEventListener('input', updateWeightTrack);
  ageInput.addEventListener('input', updateAgeTrack);
  drinksInput.addEventListener('input', updateDrinksTrack);

  // Initialize tracks
  updateWeightTrack();
  updateAgeTrack();
  updateDrinksTrack();

  // ── BAC form submission ───────────────────────────────────────
  document.getElementById('bac-form').addEventListener('submit', function (e) {
    e.preventDefault();

    let weight = parseFloat(weightInput.value);
    if (currentUnit === 'lbs') weight = weight / 2.20462;

    const gender = document.querySelector('input[name="gender"]:checked').value;
    const currentDrinks = parseInt(drinksInput.value, 10);

    fetch('/api/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ weight, gender, current_drinks: currentDrinks }),
    })
      .then(r => r.json())
      .then(data => {
        const result = document.getElementById('result');
        const primary = document.getElementById('drinks-to-target');
        const secondary = document.getElementById('time-to-sober');

        if (data.error) {
          primary.textContent = 'Error: ' + data.error;
          secondary.textContent = '';
        } else {
          primary.innerHTML = data.drinks_to_reach_target > 0
            ? `Slam about <strong>${data.drinks_to_reach_target}</strong> more to get legendary.`
            : `Bro, you're already there. Send it.`;
          secondary.innerHTML = data.time_to_sober > 0
            ? `You're seeing double for about <strong>${data.time_to_sober}</strong> more hours.`
            : `You're sober. Time to change that.`;
        }
        result.hidden = false;
        result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      })
      .catch(() => {
        const result = document.getElementById('result');
        document.getElementById('drinks-to-target').textContent = 'Something broke. Try again.';
        result.hidden = false;
      });
  });
})();
