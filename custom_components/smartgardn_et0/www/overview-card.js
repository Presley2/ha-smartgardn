import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('irrigation-overview-card')
export class IrrigationOverviewCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;
  @state() zones = [];
  @state() globalState = {};

  setConfig(config) {
    this.config = config;
  }

  connectedCallback() {
    super.connectedCallback();
    this._subscribe();
  }

  disconnectedCallback() {
    this._unsubscribe();
    super.disconnectedCallback();
  }

  _subscribe() {
    if (!this.hass) return;
    const entryId = this.config.entry_id;
    if (!entryId) {
      console.warn('irrigation-overview-card: entry_id not configured');
      return;
    }
  }

  _unsubscribe() {
    // Cleanup listeners
  }

  _getZoneData() {
    if (!this.hass || !this.config?.entry_id) return [];
    const entryId = this.config.entry_id;
    const zones = [];

    // Collect all zone entities from hass.states
    Object.entries(this.hass.states).forEach(([entityId, state]) => {
      if (entityId.includes(`select.${entryId}`) && entityId.includes('_modus')) {
        const zoneId = entityId.split('_modus')[0].split('_').pop();
        zones.push({
          zone_id: zoneId,
          name: state.attributes.friendly_name || zoneId,
          modus: state.state,
          nfk: this._getEntityState(`sensor.${entryId}_${zoneId}_nfk`),
          nfk_prozent: this._getEntityState(`sensor.${entryId}_${zoneId}_nfk_prozent`),
          etc_hoje: this._getEntityState(`sensor.${entryId}_${zoneId}_etc_hoje`),
          regen_hoje: this._getEntityState(`sensor.${entryId}_${zoneId}_regen_hoje`),
          beregnung_hoje: this._getEntityState(`sensor.${entryId}_${zoneId}_beregnung_hoje`),
          timer: this._getEntityState(`sensor.${entryId}_${zoneId}_timer`),
          naechster_start: this._getEntityState(`sensor.${entryId}_${zoneId}_naechster_start`),
          frost_warnung: this._getEntityState(`binary_sensor.${entryId}_frost_warnung`),
          dry_run: this._getEntityState(`switch.${entryId}_dry_run`),
        });
      }
    });

    // Global state
    this.globalState = {
      et0_fao: this._getEntityState(`sensor.${entryId}_et0_fao`),
      gts: this._getEntityState(`sensor.${entryId}_gts`),
      et_methode: this._getEntityState(`select.${entryId}_et_methode`),
      frost_warnung: this._getEntityState(`binary_sensor.${entryId}_frost_warnung`),
      trafo_problem: this._getEntityState(`binary_sensor.${entryId}_trafo_problem`),
      et_fallback_active: this._getEntityState(`binary_sensor.${entryId}_et_fallback_active`),
      sensoren_ok: this._getEntityState(`binary_sensor.${entryId}_sensoren_ok`),
    };

    return zones;
  }

  _getEntityState(entityId) {
    const entity = this.hass?.states[entityId];
    return entity ? entity.state : 'unavailable';
  }

  _getEntityAttr(entityId, attr) {
    const entity = this.hass?.states[entityId];
    return entity?.attributes?.[attr];
  }

  _formatTime(timestamp) {
    if (!timestamp || timestamp === 'unavailable') return '—';
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '—';
    }
  }

  _formatValue(value, unit = '') {
    if (!value || value === 'unavailable') return '—';
    return `${parseFloat(value).toFixed(1)}${unit ? ' ' + unit : ''}`;
  }

  _getNFKColor(prozent) {
    const val = parseFloat(prozent);
    if (isNaN(val)) return '#888888';
    if (val < 30) return '#d32f2f'; // red
    if (val < 60) return '#f57c00'; // orange
    return '#388e3c'; // green
  }

  _getFrostIcon() {
    const frost = this.globalState.frost_warnung;
    return frost === 'on' ? '❄️' : '☀️';
  }

  render() {
    const zones = this._getZoneData();

    return html`
      <ha-card header="Bewässerung ET₀">
        <div class="card-content">
          <!-- Global status bar -->
          <div class="status-bar">
            <div class="status-item">
              <span class="label">Frost:</span>
              <span class="value">${this._getFrostIcon()}</span>
            </div>
            <div class="status-item">
              <span class="label">ET₀ (${this.globalState.et_methode}):</span>
              <span class="value">${this._formatValue(this.globalState.et0_fao, 'mm')}</span>
            </div>
            <div class="status-item">
              <span class="label">GTS:</span>
              <span class="value">${this._formatValue(this.globalState.gts, '°C·d')}</span>
            </div>
            <div class="status-item">
              <span class="label">Modus:</span>
              <span class="value">${this.globalState.dry_run === 'on' ? '🔒 Trocken' : '💧 Live'}</span>
            </div>
          </div>

          <!-- Zones grid -->
          <div class="zones-grid">
            ${zones.map(
              (zone) => html`
                <div class="zone-card">
                  <div class="zone-header">
                    <span class="zone-name">${zone.name}</span>
                    <span class="zone-status" data-modus="${zone.modus}">
                      ${this._formatModus(zone.modus)}
                    </span>
                  </div>
                  <div class="zone-body">
                    <div class="nfk-bar">
                      <div
                        class="nfk-fill"
                        style="width: ${zone.nfk_prozent}%; background-color: ${this._getNFKColor(
                          zone.nfk_prozent
                        )}"
                      ></div>
                    </div>
                    <div class="nfk-label">${this._formatValue(zone.nfk_prozent, '%')}</div>
                    <table class="zone-data">
                      <tr>
                        <td>NFK:</td>
                        <td>${this._formatValue(zone.nfk, 'mm')}</td>
                      </tr>
                      <tr>
                        <td>ETc:</td>
                        <td>${this._formatValue(zone.etc_hoje, 'mm')}</td>
                      </tr>
                      <tr>
                        <td>Regen:</td>
                        <td>${this._formatValue(zone.regen_hoje, 'mm')}</td>
                      </tr>
                      <tr>
                        <td>Ber.:</td>
                        <td>${this._formatValue(zone.beregnung_hoje, 'mm')}</td>
                      </tr>
                      <tr>
                        <td>Timer:</td>
                        <td>${this._formatValue(zone.timer, 'min')}</td>
                      </tr>
                    </table>
                    <div class="next-start">
                      Nächst: ${this._formatTime(zone.naechster_start)}
                    </div>
                  </div>
                </div>
              `
            )}
          </div>

          <!-- Warnings -->
          ${this._renderWarnings()}
        </div>
      </ha-card>
    `;
  }

  _formatModus(modus) {
    const map = {
      aus: '⏸️ Aus',
      semi: '📅 Semi',
      voll: '💧 Voll',
      ansaat: '🌱 Ansaat',
    };
    return map[modus] || modus;
  }

  _renderWarnings() {
    const warnings = [];
    if (this.globalState.frost_warnung === 'on') {
      warnings.push(html`<div class="warning frost">⚠️ Froststarre aktiviert</div>`);
    }
    if (this.globalState.trafo_problem === 'on') {
      warnings.push(html`<div class="warning trafo">⚠️ Trafoventil Problem</div>`);
    }
    if (this.globalState.et_fallback_active === 'on') {
      warnings.push(html`<div class="warning fallback">⚠️ ET-Fallback aktiv</div>`);
    }
    if (this.globalState.sensoren_ok === 'off') {
      warnings.push(html`<div class="warning sensor">⚠️ Sensor-Fehler</div>`);
    }
    return warnings.length > 0
      ? html`<div class="warnings-section">${warnings}</div>`
      : html``;
  }

  static get styles() {
    return css`
      :host {
        --nfk-height: 20px;
        --gap: 12px;
      }

      ha-card {
        box-shadow: none;
      }

      .card-content {
        padding: 16px;
      }

      .status-bar {
        display: flex;
        gap: var(--gap);
        margin-bottom: 20px;
        padding: 12px;
        background: var(--card-background-color);
        border-radius: 8px;
        flex-wrap: wrap;
      }

      .status-item {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .status-item .label {
        font-weight: 500;
        color: var(--secondary-text-color);
      }

      .status-item .value {
        font-weight: bold;
        color: var(--primary-text-color);
      }

      .zones-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: var(--gap);
        margin-bottom: 16px;
      }

      .zone-card {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 12px;
        background: var(--card-background-color);
      }

      .zone-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--divider-color);
      }

      .zone-name {
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .zone-status {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
      }

      .zone-status[data-modus='aus'] {
        background: #ccc;
        color: #000;
      }

      .zone-status[data-modus='semi'] {
        background: #81c784;
        color: #fff;
      }

      .zone-status[data-modus='voll'] {
        background: #42a5f5;
        color: #fff;
      }

      .zone-status[data-modus='ansaat'] {
        background: #ffb74d;
        color: #000;
      }

      .nfk-bar {
        width: 100%;
        height: var(--nfk-height);
        background: #f0f0f0;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 4px;
      }

      .nfk-fill {
        height: 100%;
        transition: width 0.3s ease;
      }

      .nfk-label {
        text-align: center;
        font-weight: bold;
        margin-bottom: 8px;
        color: var(--primary-text-color);
      }

      .zone-data {
        width: 100%;
        font-size: 12px;
        border-collapse: collapse;
        margin-bottom: 8px;
      }

      .zone-data td {
        padding: 4px 0;
      }

      .zone-data td:first-child {
        color: var(--secondary-text-color);
        width: 50%;
      }

      .zone-data td:last-child {
        text-align: right;
        color: var(--primary-text-color);
        font-weight: 500;
      }

      .next-start {
        font-size: 12px;
        color: var(--secondary-text-color);
        padding-top: 8px;
        border-top: 1px solid var(--divider-color);
      }

      .warnings-section {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .warning {
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
      }

      .warning.frost {
        background: #ffebee;
        color: #c62828;
      }

      .warning.trafo {
        background: #fff3e0;
        color: #e65100;
      }

      .warning.fallback {
        background: #f3e5f5;
        color: #6a1b9a;
      }

      .warning.sensor {
        background: #fce4ec;
        color: #ad1457;
      }

      @media (max-width: 768px) {
        .zones-grid {
          grid-template-columns: 1fr;
        }
      }
    `;
  }
}
