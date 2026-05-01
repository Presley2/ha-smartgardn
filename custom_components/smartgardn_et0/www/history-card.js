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
    if (!this.hass || !this.config?.entry_id) {
      return {
        labels: [],
        nfk: [],
        etc: [],
        regen: [],
        beregnung: [],
      };
    }
    const entryId = this.config.entry_id;
    const sensorId = `sensor.${entryId}_${zoneId}_nfk`;
    const sensor = this.hass.states[sensorId];
    const verlauf = sensor?.attributes?.verlauf || [];

    return {
      labels: verlauf.map((e) => e.datum),
      nfk: verlauf.map((e) => parseFloat(e.nfk_ende || 0)),
      etc: verlauf.map((e) => parseFloat(e.etc || 0)),
      regen: verlauf.map((e) => parseFloat(e.regen || 0)),
      beregnung: verlauf.map((e) => parseFloat(e.beregnung || 0)),
    };
  }

  _getForecastData() {
    if (!this.hass || !this.config?.entry_id) return null;
    const entryId = this.config.entry_id;
    const et0_morgen = this.hass.states[`sensor.${entryId}_et0_prognose_morgen`];
    const et0_uebermorgen = this.hass.states[`sensor.${entryId}_et0_prognose_uebermorgen`];
    const et0_tag3 = this.hass.states[`sensor.${entryId}_et0_prognose_tag3`];
    const regen_morgen = this.hass.states[`sensor.${entryId}_regen_prognose_morgen`];
    const regen_uebermorgen = this.hass.states[`sensor.${entryId}_regen_prognose_uebermorgen`];
    const regen_tag3 = this.hass.states[`sensor.${entryId}_regen_prognose_tag3`];

    if (!et0_morgen || !regen_morgen) return null;

    return {
      et0: [
        parseFloat(et0_morgen?.state || 0),
        parseFloat(et0_uebermorgen?.state || 0),
        parseFloat(et0_tag3?.state || 0),
      ],
      regen: [
        parseFloat(regen_morgen?.state || 0),
        parseFloat(regen_uebermorgen?.state || 0),
        parseFloat(regen_tag3?.state || 0),
      ],
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
    const width = 700;
    const height = 300;
    const padding = 40;
    const graphWidth = width - 2 * padding;
    const graphHeight = height - 2 * padding;

    // Find max value for scaling
    const forecast = this._getForecastData();
    const allValues = [
      ...history.nfk,
      ...history.etc,
      ...history.regen,
      ...history.beregnung,
      ...(forecast?.et0 || []),
      ...(forecast?.regen || []),
    ];
    const maxValue = Math.max(...allValues.map(Number), 100);
    const scale = graphHeight / maxValue;

    // Position of "today" separator (end of history)
    const historyWidth = (history.labels.length / (history.labels.length + 3)) * graphWidth;
    const todayX = padding + historyWidth;

    return html`
      <svg viewBox="0 0 ${width} ${height}" class="chart-svg">
        <!-- Grid lines -->
        <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" class="grid-line" />
        <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" class="grid-line" />
        <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" class="grid-line" />
        <line x1="${width - padding}" y1="${padding}" x2="${width - padding}" y2="${height - padding}" class="grid-line" />

        <!-- Today separator (dashed vertical line) -->
        <line x1="${todayX}" y1="${padding}" x2="${todayX}" y2="${height - padding}" class="today-separator" stroke-dasharray="2,2" />

        <!-- NFK line (green) -->
        <polyline
          points="${this._generatePolylinePoints(history.nfk, padding, height - padding, historyWidth, scale)}"
          class="line nfk-line"
        />

        <!-- ETc line (red dashed) -->
        <polyline
          points="${this._generatePolylinePoints(history.etc, padding, height - padding, historyWidth, scale)}"
          class="line etc-line"
        />

        <!-- Rain bars (blue) -->
        ${history.regen.map(
          (val, idx) => html`
            <rect
              x="${padding + (idx / history.regen.length) * historyWidth + 2}"
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
              x="${padding + (idx / history.beregnung.length) * historyWidth + 5}"
              y="${height - padding - Number(val) * scale}"
              width="2"
              height="${Number(val) * scale}"
              class="bar irrigation-bar"
            />
          `
        )}

        <!-- Forecast section (dashed lines) -->
        ${forecast
          ? html`
              <!-- ET₀ forecast line (green dashed) -->
              <polyline
                points="${this._generateForecastPolylinePoints(forecast.et0, todayX, height - padding, graphWidth - historyWidth, scale)}"
                class="line nfk-line forecast-line"
              />
              <!-- Rain forecast bars (blue) -->
              ${forecast.regen.map(
                (val, idx) => html`
                  <rect
                    x="${todayX + (idx / forecast.regen.length) * (graphWidth - historyWidth) + 2}"
                    y="${height - padding - Number(val) * scale}"
                    width="2"
                    height="${Number(val) * scale}"
                    class="bar rain-bar forecast-bar"
                  />
                `
              )}
            `
          : ''}

        <!-- Y-axis labels -->
        <text x="${padding - 30}" y="${height - padding + 5}" class="axis-label">0</text>
        <text x="${padding - 35}" y="${padding + 5}" class="axis-label">${Math.round(maxValue)}</text>

        <!-- Legend -->
        <g transform="translate(${width - 180}, ${padding + 10})">
          <line x1="0" y1="0" x2="15" y2="0" class="nfk-line" stroke-width="2" />
          <text x="20" y="5" font-size="11">NFK</text>

          <line x1="0" y1="18" x2="15" y2="18" class="etc-line" stroke-width="2" />
          <text x="20" y="23" font-size="11">ETc</text>

          <rect x="0" y="34" width="6" height="6" class="rain-bar" />
          <text x="20" y="41" font-size="11">Regen</text>

          <rect x="0" y="52" width="6" height="6" class="irrigation-bar" />
          <text x="20" y="59" font-size="11">Ber.</text>

          <line x1="0" y1="70" x2="15" y2="70" class="nfk-line forecast-line" stroke-width="2" stroke-dasharray="3,3" />
          <text x="20" y="75" font-size="11">Prognose</text>
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

  _generateForecastPolylinePoints(values, startX, baselineY, graphWidth, scale) {
    if (!values || values.length === 0) return '';
    const pointSpacing = graphWidth / (values.length - 1 || 1);
    return values
      .map(
        (val, idx) =>
          `${startX + idx * pointSpacing},${baselineY - Number(val) * scale}`
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

      .forecast-line {
        stroke-dasharray: 3,3;
        opacity: 0.7;
      }

      .forecast-bar {
        opacity: 0.5;
      }

      .today-separator {
        stroke: var(--divider-color);
        opacity: 0.5;
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
