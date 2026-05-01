import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('irrigation-settings-card')
export class IrrigationSettingsCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;
  @state() selectedZone = null;
  @state() zoneConfig = {};

  setConfig(config) {
    this.config = config;
  }

  _getZones() {
    if (!this.hass || !this.config?.entry_id) return [];
    const entryId = this.config.entry_id;
    const zones = [];

    Object.entries(this.hass.states).forEach(([entityId, state]) => {
      if (entityId.includes(`select.${entryId}`) && entityId.includes('_modus')) {
        const zoneId = entityId.split('_modus')[0].split('_').pop();
        zones.push({
          zone_id: zoneId,
          name: state.attributes.friendly_name || zoneId,
        });
      }
    });

    return zones;
  }

  _selectZone(zoneId) {
    this.selectedZone = zoneId;
    this._loadZoneConfig(zoneId);
  }

  _loadZoneConfig(zoneId) {
    if (!this.hass || !this.config?.entry_id) return;
    const entryId = this.config.entry_id;

    // Load all zone parameter entities
    this.zoneConfig = {
      modus: this.hass.states[`select.${entryId}_${zoneId}_modus`]?.state || 'aus',
      dauer: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_dauer`]?.state) || 0,
      schwellwert: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_schwellwert`]?.state) || 50,
      zielwert: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_zielwert`]?.state) || 80,
      manuelle_dauer: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_manuelle_dauer`]?.state) || 30,
      cs_zyklen: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_cs_zyklen`]?.state) || 1,
      cs_pause: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_cs_pause`]?.state) || 30,
      ansaat_intervall: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_ansaat_intervall`]?.state) || 1,
      ansaat_dauer: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_ansaat_dauer`]?.state) || 5,
      ansaat_laufzeit_tage: parseFloat(this.hass.states[`number.${entryId}_${zoneId}_ansaat_laufzeit_tage`]?.state) || 21,
      start_time: this.hass.states[`time.${entryId}_${zoneId}_start`]?.state || '19:00',
      ansaat_von: this.hass.states[`time.${entryId}_${zoneId}_ansaat_von`]?.state || '06:00',
      ansaat_bis: this.hass.states[`time.${entryId}_${zoneId}_ansaat_bis`]?.state || '10:00',
    };
  }

  _updateNumber(key, value) {
    if (!this.hass || !this.config?.entry_id || !this.selectedZone) return;
    const entryId = this.config.entry_id;
    const entityId = `number.${entryId}_${this.selectedZone}_${key}`;
    this.hass.callService('number', 'set_value', {
      entity_id: entityId,
      value: value,
    });
    this.zoneConfig[key] = value;
  }

  _updateSelect(key, value) {
    if (!this.hass || !this.config?.entry_id || !this.selectedZone) return;
    const entryId = this.config.entry_id;
    const entityId = `select.${entryId}_${this.selectedZone}_${key}`;
    this.hass.callService('select', 'select_option', {
      entity_id: entityId,
      option: value,
    });
    this.zoneConfig[key] = value;
  }

  _updateTime(key, value) {
    if (!this.hass || !this.config?.entry_id || !this.selectedZone) return;
    const entryId = this.config.entry_id;
    const entityId = `time.${entryId}_${this.selectedZone}_${key}`;
    this.hass.callService('input_datetime', 'set_datetime', {
      entity_id: entityId,
      time: value,
    });
    this.zoneConfig[key] = value;
  }

  _renderSlider(label, key, min, max, step = 1, unit = '') {
    return html`
      <div class="parameter-row">
        <div class="parameter-label">
          <span>${label}</span>
          <span class="parameter-value">${this.zoneConfig[key]}${unit ? ' ' + unit : ''}</span>
        </div>
        <input
          type="range"
          min="${min}"
          max="${max}"
          step="${step}"
          .value="${this.zoneConfig[key]}"
          @input=${(e) => this._updateNumber(key, parseFloat(e.target.value))}
          class="slider"
        />
      </div>
    `;
  }

  render() {
    const zones = this._getZones();
    const selectedZone = zones.find((z) => z.zone_id === this.selectedZone) || zones[0];

    return html`
      <ha-card header="Einstellungen">
        <div class="card-content">
          <!-- Zone selector -->
          <div class="zone-selector">
            ${zones.map(
              (zone) => html`
                <button
                  class="zone-button ${zone.zone_id === this.selectedZone ? 'active' : ''}"
                  @click=${() => this._selectZone(zone.zone_id)}
                >
                  ${zone.name}
                </button>
              `
            )}
          </div>

          ${selectedZone
            ? html`
                <!-- Mode selector -->
                <div class="settings-section">
                  <h3>Betriebsmodus</h3>
                  <div class="mode-grid">
                    ${['aus', 'semi', 'voll', 'ansaat'].map(
                      (mode) => html`
                        <button
                          class="mode-button ${this.zoneConfig.modus === mode ? 'active' : ''}"
                          @click=${() => this._updateSelect('modus', mode)}
                        >
                          ${this._getModeEmoji(mode)} ${this._getModeLabel(mode)}
                        </button>
                      `
                    )}
                  </div>
                </div>

                <!-- General parameters -->
                <div class="settings-section">
                  <h3>Allgemein</h3>
                  ${this._renderSlider(
                    'Standard-Laufzeit',
                    'dauer',
                    5,
                    120,
                    5,
                    'min'
                  )}
                  ${this._renderSlider(
                    'Bewässerungs-Grenzwert',
                    'schwellwert',
                    10,
                    90,
                    5,
                    '%'
                  )}
                  ${this._renderSlider(
                    'Zielwert nach Ber.',
                    'zielwert',
                    30,
                    100,
                    5,
                    '%'
                  )}
                </div>

                <!-- Time settings -->
                <div class="settings-section">
                  <h3>Zeitpunkte</h3>
                  <div class="parameter-row">
                    <label>Semi-Auto Start:</label>
                    <input
                      type="time"
                      .value="${this.zoneConfig.start_time}"
                      @change=${(e) => this._updateTime('start', e.target.value)}
                      class="time-input"
                    />
                  </div>
                </div>

                <!-- Cycle & Soak settings -->
                <div class="settings-section">
                  <h3>Cycle & Soak (C&S)</h3>
                  ${this._renderSlider(
                    'Anzahl Zyklen',
                    'cs_zyklen',
                    1,
                    5,
                    1,
                    '×'
                  )}
                  ${this._renderSlider(
                    'Pause zwischen Zyklen',
                    'cs_pause',
                    10,
                    120,
                    5,
                    'min'
                  )}
                </div>

                <!-- Manual irrigation -->
                <div class="settings-section">
                  <h3>Manuelle Bewässerung</h3>
                  ${this._renderSlider(
                    'Standard-Dauer',
                    'manuelle_dauer',
                    5,
                    120,
                    5,
                    'min'
                  )}
                </div>

                <!-- Ansaat (seed watering) settings -->
                ${this.zoneConfig.modus === 'ansaat'
                  ? html`
                      <div class="settings-section">
                        <h3>Ansaat (Keimung)</h3>
                        <div class="parameter-row">
                          <label>Zeitfenster von:</label>
                          <input
                            type="time"
                            .value="${this.zoneConfig.ansaat_von}"
                            @change=${(e) => this._updateTime('ansaat_von', e.target.value)}
                            class="time-input"
                          />
                        </div>
                        <div class="parameter-row">
                          <label>Zeitfenster bis:</label>
                          <input
                            type="time"
                            .value="${this.zoneConfig.ansaat_bis}"
                            @change=${(e) => this._updateTime('ansaat_bis', e.target.value)}
                            class="time-input"
                          />
                        </div>
                        ${this._renderSlider(
                          'Bewässerungs-Intervall',
                          'ansaat_intervall',
                          1,
                          12,
                          1,
                          'h'
                        )}
                        ${this._renderSlider(
                          'Laufzeit pro Intervall',
                          'ansaat_dauer',
                          1,
                          15,
                          1,
                          'min'
                        )}
                        ${this._renderSlider(
                          'Dauer des Ansaat-Programms',
                          'ansaat_laufzeit_tage',
                          7,
                          90,
                          1,
                          'd'
                        )}
                      </div>
                    `
                  : html``}

                <!-- Info section -->
                <div class="settings-section info">
                  <h3>ℹ️ Hinweise</h3>
                  <ul>
                    <li><strong>Aus:</strong> Zone ist deaktiviert</li>
                    <li><strong>Semi-Automatik:</strong> Bewässerung zu festgelegtem Zeitpunkt</li>
                    <li><strong>Voll-Automatik:</strong> Bewässerung wenn NFK unter Grenzwert</li>
                    <li><strong>Ansaat:</strong> Intensive Bewässerung für Keimung (Zeit-limitiert)</li>
                    <li><strong>C&S:</strong> Bewässerung in Zyklen mit Pausen (für Durchdringung)</li>
                  </ul>
                </div>
              `
            : html`<div class="no-zones">Keine Zonen konfiguriert</div>`}
        </div>
      </ha-card>
    `;
  }

  _getModeEmoji(mode) {
    const map = { aus: '⏸️', semi: '📅', voll: '💧', ansaat: '🌱' };
    return map[mode] || '?';
  }

  _getModeLabel(mode) {
    const map = {
      aus: 'Aus',
      semi: 'Semi',
      voll: 'Voll',
      ansaat: 'Ansaat',
    };
    return map[mode] || mode;
  }

  static get styles() {
    return css`
      .card-content {
        padding: 16px;
      }

      .zone-selector {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        flex-wrap: wrap;
      }

      .zone-button {
        padding: 6px 12px;
        border: 2px solid var(--divider-color);
        border-radius: 4px;
        background: transparent;
        cursor: pointer;
        font-size: 12px;
        transition: all 0.2s ease;
      }

      .zone-button:hover {
        border-color: var(--primary-color);
      }

      .zone-button.active {
        background: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
      }

      .settings-section {
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid var(--divider-color);
      }

      .settings-section h3 {
        margin: 0 0 12px 0;
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .settings-section.info {
        background: var(--card-background-color);
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 12px;
        border-bottom: none;
      }

      .settings-section.info ul {
        margin: 0;
        padding-left: 20px;
        font-size: 12px;
      }

      .settings-section.info li {
        margin: 4px 0;
        color: var(--secondary-text-color);
      }

      .mode-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 8px;
      }

      .mode-button {
        padding: 12px;
        border: 2px solid var(--divider-color);
        border-radius: 4px;
        background: transparent;
        cursor: pointer;
        font-size: 12px;
        text-align: center;
        transition: all 0.2s ease;
      }

      .mode-button:hover {
        border-color: var(--primary-color);
      }

      .mode-button.active {
        background: var(--primary-color);
        color: white;
        border-color: var(--primary-color);
      }

      .parameter-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        gap: 12px;
      }

      .parameter-label {
        display: flex;
        justify-content: space-between;
        flex: 1;
        font-size: 12px;
        color: var(--primary-text-color);
      }

      .parameter-value {
        font-weight: bold;
        color: var(--primary-color);
      }

      .slider {
        flex: 1;
        max-width: 150px;
      }

      .time-input {
        padding: 4px 8px;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        font-size: 12px;
      }

      .no-zones {
        padding: 32px 16px;
        text-align: center;
        color: var(--secondary-text-color);
      }

      @media (max-width: 600px) {
        .mode-grid {
          grid-template-columns: repeat(2, 1fr);
        }

        .parameter-row {
          flex-direction: column;
          align-items: flex-start;
        }

        .slider {
          width: 100%;
          max-width: none;
        }
      }
    `;
  }
}
