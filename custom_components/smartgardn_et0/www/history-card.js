import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('irrigation-history-card')
export class IrrigationHistoryCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;
  @state() zoneHistory = {};
  @state() selectedZone = null;

  setConfig(config) {
    this.config = config;
  }

  connectedCallback() {
    super.connectedCallback();
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

  _getZoneHistory(zoneId) {
    // This would normally fetch from diagnostics or coordinator storage
    // For now, return empty mock structure
    return {
      labels: [],
      nfk: [],
      etc: [],
      regen: [],
      beregnung: [],
    };
  }

  _selectZone(zoneId) {
    this.selectedZone = zoneId;
    this.zoneHistory = this._getZoneHistory(zoneId);
  }

  _renderChart() {
    const history = this.zoneHistory;
    if (!history.labels || history.labels.length === 0) {
      return html`<div class="no-data">Keine Verlaufsdaten verfügbar</div>`;
    }

    // Simple SVG chart for water balance over time
    const width = 600;
    const height = 300;
    const padding = 40;
    const graphWidth = width - 2 * padding;
    const graphHeight = height - 2 * padding;

    // Find max value for scaling
    const allValues = [
      ...history.nfk,
      ...history.etc,
      ...history.regen,
      ...history.beregnung,
    ];
    const maxValue = Math.max(...allValues.map(Number), 100);
    const scale = graphHeight / maxValue;

    return html`
      <svg viewBox="0 0 ${width} ${height}" class="chart-svg">
        <!-- Grid lines -->
        <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" class="grid-line" />
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="grid-line" />
        <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" class="grid-line" />
        <line x1="${width - padding}" y1="${padding}" x2="${width - padding}" y2="${height - padding}" class="grid-line" />

        <!-- NFK line (green) -->
        <polyline
          points="${this._generatePolylinePoints(history.nfk, padding, height - padding, graphWidth, scale)}"
          class="line nfk-line"
        />

        <!-- ETc line (red dashed) -->
        <polyline
          points="${this._generatePolylinePoints(history.etc, padding, height - padding, graphWidth, scale)}"
          class="line etc-line"
        />

        <!-- Rain bars (blue) -->
        ${history.regen.map(
          (val, idx) => html`
            <rect
              x="${padding + (idx / history.regen.length) * graphWidth + 2}"
              y="${height - padding - Number(val) * scale}"
              width="2"
              height="${Number(val) * scale}"
              class="bar rain-bar"
            />
          `
        )}

        <!-- Irrigation bars (cyan) -->
        ${history.beregnung.map(
          (val, idx) => html`
            <rect
              x="${padding + (idx / history.beregnung.length) * graphWidth + 5}"
              y="${height - padding - Number(val) * scale}"
              width="2"
              height="${Number(val) * scale}"
              class="bar irrigation-bar"
            />
          `
        )}

        <!-- Y-axis labels -->
        <text x="${padding - 30}" y="${height - padding + 5}" class="axis-label">0</text>
        <text x="${padding - 35}" y="${padding + 5}" class="axis-label">${Math.round(maxValue)}</text>

        <!-- Legend -->
        <g transform="translate(${width - 150}, ${padding + 10})">
          <line x1="0" y1="0" x2="15" y2="0" class="nfk-line" stroke-width="2" />
          <text x="20" y="5" font-size="12">NFK</text>

          <line x1="0" y1="20" x2="15" y2="20" class="etc-line" stroke-width="2" />
          <text x="20" y="25" font-size="12">ETc</text>

          <rect x="0" y="40" width="8" height="8" class="rain-bar" />
          <text x="20" y="47" font-size="12">Regen</text>

          <rect x="0" y="60" width="8" height="8" class="irrigation-bar" />
          <text x="20" y="67" font-size="12">Ber.</text>
        </g>
      </svg>
    `;
  }

  _generatePolylinePoints(values, paddingX, baselineY, graphWidth, scale) {
    if (!values || values.length === 0) return '';
    const pointSpacing = graphWidth / (values.length - 1 || 1);
    return values
      .map(
        (val, idx) =>
          `${paddingX + idx * pointSpacing},${baselineY - Number(val) * scale}`
      )
      .join(' ');
  }

  render() {
    const zones = this._getZones();
    const selectedZone = zones.find((z) => z.zone_id === this.selectedZone) || zones[0];

    return html`
      <ha-card header="Verlauf">
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

          <!-- Chart -->
          <div class="chart-container">
            ${selectedZone ? this._renderChart() : html`<div class="no-data">Keine Zonen konfiguriert</div>`}
          </div>

          <!-- Summary stats -->
          <div class="stats-section">
            <div class="stat-item">
              <span class="stat-label">Durchschn. NFK:</span>
              <span class="stat-value">—</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Summe Regen (7d):</span>
              <span class="stat-value">—</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Summe Bewässerung (7d):</span>
              <span class="stat-value">—</span>
            </div>
          </div>
        </div>
      </ha-card>
    `;
  }

  static get styles() {
    return css`
      :host {
        --chart-color-nfk: #2e7d32;
        --chart-color-etc: #d32f2f;
        --chart-color-rain: #1976d2;
        --chart-color-irrigation: #0097a7;
      }

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

      .chart-container {
        margin: 16px 0;
        overflow-x: auto;
      }

      .chart-svg {
        width: 100%;
        height: auto;
        max-width: 600px;
      }

      .grid-line {
        stroke: var(--divider-color);
        stroke-width: 1;
      }

      .line {
        fill: none;
        stroke-width: 2;
      }

      .nfk-line {
        stroke: var(--chart-color-nfk);
      }

      .etc-line {
        stroke: var(--chart-color-etc);
        stroke-dasharray: 4,4;
      }

      .bar {
        opacity: 0.7;
      }

      .rain-bar {
        fill: var(--chart-color-rain);
      }

      .irrigation-bar {
        fill: var(--chart-color-irrigation);
      }

      .axis-label {
        font-size: 11px;
        fill: var(--secondary-text-color);
      }

      .stats-section {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-top: 16px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color);
      }

      .stat-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .stat-label {
        font-size: 12px;
        color: var(--secondary-text-color);
      }

      .stat-value {
        font-weight: bold;
        color: var(--primary-text-color);
      }

      .no-data {
        padding: 32px 16px;
        text-align: center;
        color: var(--secondary-text-color);
      }

      @media (max-width: 600px) {
        .chart-svg {
          max-width: 100%;
        }
      }
    `;
  }
}
