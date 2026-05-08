/**
 * MSI Mystic Light Control Panel - Frontend
 */

const API_BASE = '';
let modes = [];
let presets = [];
let currentGroupIndex = 0;
let isUpdating = false;

// Speed mapping
const SPEED_LABELS = ['慢', '中', '快'];
const SPEED_VALUES = ['low', 'medium', 'high'];

// Modes that use built-in rainbow/preset colors (user color has no effect)
const RAINBOW_MODES = [
    'Rainbow wave', 'Color ring', 'Rainbow flashing', 'Fire'
];

// Modes that require a second color to show effect properly
const DUAL_COLOR_MODES = [
    'Double flashing', 'Lightning', 'Meteor', 'Blink', 'Color shift',
    'Color wave', 'Double meteor', 'Color ring double flashing',
    'Color pulse', 'Marquee', 'Stack', 'Flashing', 'Planetary', 'Energy', 'Visor'
];

// DOM Elements
const masterSwitch = document.getElementById('masterSwitch');
const statusDot = document.getElementById('statusDot');
const toast = document.getElementById('toast');
const presetTabs = document.getElementById('presetTabs');
const presetGrid = document.getElementById('presetGrid');
const scheduleToggle = document.getElementById('scheduleToggle');

// Zone elements
const zones = ['JRGB1', 'JRAINBOW1', 'JRAINBOW2', 'ONBOARD'];
const zoneElements = {};

zones.forEach(zone => {
    const card = document.querySelector(`.zone-card[data-zone="${zone}"]`);
    if (card) {
        zoneElements[zone] = {
            card,
            colorPicker: card.querySelector('.color-picker'),
            colorHex: card.querySelector('.color-hex'),
            modeSelect: card.querySelector('.mode-select'),
            brightnessSlider: card.querySelector('.brightness-slider'),
            brightnessValue: card.querySelector('.brightness-slider + .slider-value'),
            speedSlider: card.querySelector('.speed-slider'),
            speedValue: card.querySelector('.speed-slider + .slider-value'),
            syncToggle: card.querySelector('.zone-sync'),
            preview: card.querySelector('.zone-preview'),
        };
    }
});

// ============================================
// Initialization
// ============================================

async function init() {
    await loadModes();
    await loadPresets();
    await loadStatus();
    setupEventListeners();
    renderPresetTabs();
    renderPresetGrid(0);
    // Initialize color2 visibility for all zones
    zones.forEach(zone => updateColor2Visibility(zone));
}

async function loadModes() {
    try {
        const res = await fetch(`${API_BASE}/api/modes`);
        const data = await res.json();
        // New format: [{key: 'Static', name: '静态'}, ...]
        modes = data.modes || [];
        populateModeSelects();
    } catch (e) {
        console.error('Failed to load modes:', e);
        showToast('无法连接到服务');
        statusDot.classList.add('offline');
    }
}

async function loadPresets() {
    try {
        const res = await fetch(`${API_BASE}/api/presets`);
        const data = await res.json();
        presets = data.groups || [];
    } catch (e) {
        console.error('Failed to load presets:', e);
    }
}

async function loadStatus() {
    try {
        const res = await fetch(`${API_BASE}/api/status`);
        const data = await res.json();
        if (data.connected) {
            statusDot.classList.remove('offline');
        } else {
            statusDot.classList.add('offline');
        }
        if (!data.master_on) {
            masterSwitch.checked = false;
        }
    } catch (e) {
        statusDot.classList.add('offline');
    }
}

function populateModeSelects() {
    zones.forEach(zone => {
        const select = zoneElements[zone].modeSelect;
        select.innerHTML = '';
        modes.forEach(mode => {
            const option = document.createElement('option');
            option.value = mode.key;
            option.textContent = mode.name;
            select.appendChild(option);
        });
    });
}

// ============================================
// Event Listeners
// ============================================

function setupEventListeners() {
    // Master switch
    masterSwitch.addEventListener('change', async () => {
        const state = masterSwitch.checked ? 'on' : 'off';
        try {
            await fetch(`${API_BASE}/api/master`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state }),
            });
            showToast(masterSwitch.checked ? '灯光已开启' : '灯光已关闭');
        } catch (e) {
            showToast('操作失败');
        }
    });

    // Zone controls
    zones.forEach(zone => {
        const els = zoneElements[zone];

        // Color picker
        els.colorPicker.addEventListener('input', (e) => {
            const hex = e.target.value.replace('#', '').toUpperCase();
            els.colorHex.textContent = `#${hex}`;
            updatePreview(zone, hex);
        });

        els.colorPicker.addEventListener('change', () => {
            applyZoneChange(zone);
        });

        // Mode select
        els.modeSelect.addEventListener('change', () => {
            updateColor2Visibility(zone);
            applyZoneChange(zone);
        });

        // Brightness slider
        els.brightnessSlider.addEventListener('input', (e) => {
            els.brightnessValue.textContent = `${e.target.value}%`;
        });

        els.brightnessSlider.addEventListener('change', () => {
            applyZoneChange(zone);
        });

        // Speed slider
        els.speedSlider.addEventListener('input', (e) => {
            const idx = parseInt(e.target.value);
            els.speedValue.textContent = SPEED_LABELS[idx];
        });

        els.speedSlider.addEventListener('change', () => {
            applyZoneChange(zone);
        });

        // Sync toggle
        els.syncToggle.addEventListener('change', () => {
            const isSync = els.syncToggle.checked;
            els.card.classList.toggle('independent', !isSync);
        });

        // Color2 picker
        if (els.color2Picker) {
            els.color2Picker.addEventListener('input', (e) => {
                const hex = e.target.value.replace('#', '').toUpperCase();
                els.color2Hex.textContent = `#${hex}`;
            });
            els.color2Picker.addEventListener('change', () => {
                applyZoneChange(zone);
            });
        }
    });

    // Schedule toggle
    scheduleToggle.addEventListener('change', async () => {
        try {
            await fetch(`${API_BASE}/api/schedule`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: scheduleToggle.checked }),
            });
            showToast(scheduleToggle.checked ? '自动灯光已启用' : '自动灯光已关闭');
        } catch (e) {
            showToast('设置失败');
        }
    });
}

// ============================================
// API Actions
// ============================================

async function applyGlobal(mode, color, brightness, speed, color2 = null) {
    if (isUpdating) return;
    isUpdating = true;

    const payload = { mode, color, brightness, speed };
    if (color2) payload.color2 = color2;

    try {
        await fetch(`${API_BASE}/api/set`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
    } catch (e) {
        showToast('设置失败');
    } finally {
        isUpdating = false;
    }
}

function updateColor2Visibility(zone) {
    const els = zoneElements[zone];
    const mode = els.modeSelect.value;
    const needsColor2 = DUAL_COLOR_MODES.includes(mode);
    const isRainbow = RAINBOW_MODES.includes(mode);
    
    if (els.color2Row) {
        els.color2Row.classList.toggle('hidden', !needsColor2);
    }
    
    // Show/hide rainbow hint
    let hint = els.card.querySelector('.rainbow-hint');
    if (isRainbow) {
        if (!hint) {
            hint = document.createElement('div');
            hint.className = 'rainbow-hint';
            hint.textContent = '此模式使用内置颜色序列，所选颜色不影响效果';
            els.card.querySelector('.zone-body').insertBefore(hint, els.modeSelect);
        }
        hint.style.display = 'block';
    } else if (hint) {
        hint.style.display = 'none';
    }
}

async function applyZoneChange(zone) {
    const els = zoneElements[zone];
    const isSync = els.syncToggle.checked;

    const color = els.colorPicker.value.replace('#', '').toUpperCase();
    const mode = els.modeSelect.value; // English key
    const brightness = parseInt(els.brightnessSlider.value);
    const speed = SPEED_VALUES[parseInt(els.speedSlider.value)];
    const needsColor2 = DUAL_COLOR_MODES.includes(mode);
    const color2 = needsColor2 ? els.color2Picker.value.replace('#', '').toUpperCase() : null;

    updatePreview(zone, color);

    const payload = { zone, mode, color, brightness, speed };
    if (color2) payload.color2 = color2;

    if (isSync) {
        // Apply to all synced zones
        const globalPayload = { mode, color, brightness, speed };
        if (color2) globalPayload.color2 = color2;
        await applyGlobal(mode, color, brightness, speed, color2);
        // Update UI for all synced zones
        zones.forEach(z => {
            if (zoneElements[z].syncToggle.checked) {
                updateZoneUI(z, mode, color, brightness, speed, color2);
            }
        });
    } else {
        // Apply only to this zone
        try {
            await fetch(`${API_BASE}/api/set_zone`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
        } catch (e) {
            showToast('设置失败');
        }
    }
}

function updateZoneUI(zone, mode, color, brightness, speed, color2 = null) {
    const els = zoneElements[zone];
    els.colorPicker.value = `#${color}`;
    els.colorHex.textContent = `#${color}`;
    els.modeSelect.value = mode; // English key
    els.brightnessSlider.value = brightness;
    els.brightnessValue.textContent = `${brightness}%`;
    const speedIdx = SPEED_VALUES.indexOf(speed);
    if (speedIdx >= 0) {
        els.speedSlider.value = speedIdx;
        els.speedValue.textContent = SPEED_LABELS[speedIdx];
    }
    if (color2 && els.color2Picker) {
        els.color2Picker.value = `#${color2}`;
        els.color2Hex.textContent = `#${color2}`;
    }
    updateColor2Visibility(zone);
    updatePreview(zone, color);
}

function updatePreview(zone, hex) {
    const els = zoneElements[zone];
    els.preview.style.background = `#${hex}`;
    els.preview.style.boxShadow = `0 0 12px #${hex}66`;
}

// ============================================
// Presets
// ============================================

function renderPresetTabs() {
    presetTabs.innerHTML = '';
    presets.forEach((group, index) => {
        const btn = document.createElement('button');
        btn.className = `preset-tab ${index === 0 ? 'active' : ''}`;
        btn.textContent = group.name;
        btn.addEventListener('click', () => {
            currentGroupIndex = index;
            document.querySelectorAll('.preset-tab').forEach(t => t.classList.remove('active'));
            btn.classList.add('active');
            renderPresetGrid(index);
        });
        presetTabs.appendChild(btn);
    });
}

function renderPresetGrid(groupIndex) {
    presetGrid.innerHTML = '';
    const group = presets[groupIndex];
    if (!group) return;

    group.colors.forEach(color => {
        const swatch = document.createElement('div');
        swatch.className = 'preset-swatch';
        swatch.style.background = `#${color.hex}`;

        const tooltip = document.createElement('span');
        tooltip.className = 'tooltip';
        tooltip.textContent = color.name;
        swatch.appendChild(tooltip);

        swatch.addEventListener('click', () => {
            applyPreset(color.hex);
        });

        presetGrid.appendChild(swatch);
    });
}

async function applyPreset(hex) {
    // When clicking a preset, apply Static mode with the preset color
    const mode = 'Static';
    const brightness = 100;
    const speed = 'medium';

    await applyGlobal(mode, hex, brightness, speed);

    // Update all synced zones UI
    zones.forEach(zone => {
        updateZoneUI(zone, mode, hex, brightness, speed);
    });

    showToast(`已应用: #${hex}`);
}

// ============================================
// Toast
// ============================================

let toastTimeout;
function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
        toast.classList.remove('show');
    }, 2000);
}

// ============================================
// Start
// ============================================

document.addEventListener('DOMContentLoaded', init);
