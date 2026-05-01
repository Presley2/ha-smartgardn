import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';

@customElement('irrigation-ansaat-card')
export class IrrigationAnsaatCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;
  @state() ansaatZones = [];

  setConfig(config) {
    this.config = config;
  }

  connectedCallback() {
    super.connectedCallback();
    this._updateAnsaatZones();
  }

  _updateAnsaatZones() {
    if (!this.hass || !this.config?.entry_id) return;
    const entryId = this.config.entry_id;

    // Find all zones in Ansaat mode
    this.ansaatZones = [];
    Object.entries(this.hass.states).forEach(([entityId, state]) => {
      if (entityId.includes(`select.${entryId}`) && entityId.includes('_modus')) {
        if (state.state === 'ansaat') {
          const zoneId = entityId.split('_modus')[0].split('_').pop();
          this.ansaatZones.push({
            zone_id: zoneId,
            name: state.attributes.friendly_name || zoneId,
            status: this._getAnsaatStatus(zoneId, entryId),
          });
        }
      }
    });
  }

  _getAnsaatStatus(zoneId, entryId) {
    const startDate = this.hass?.states[
      `sensor.${entryId}_${zoneId}_ansaat_start_datum`
    ];
    const interval = parseFloat(
      this.hass?.states[`number.${entryId}_${zoneId}_ansaat_intervall`]?.state
    ) || 1;
    const duration = parseFloat(
      this.hass?.states[`number.${entryId}_${zoneId}_ansaat_laufzeit_tage`]?.state
    ) || 21;
    const dauer = parseFloat(
      this.hass?.states[`number.${entryId}_${zoneId}_ansaat_dauer`]?.state
    ) || 5;
    const vonTime = this.hass?.states[`time.${entryId}_${zoneId}_ansaat_von`]?.state;
    const bisTime = this.hass?.states[
      `time.${entryId}_${zoneId}_ansaat_bis`
    ]?.state;

    if (!startDate || startDate.state === 'unavailable') {
      return {
        active: false,
        daysRemaining: 0,
        daysTotal: duration,
        interval,
        dauer,
        vonTime,
        bisTime,
        progress: 0,
      };
    }

    const start = new Date(startDate.state);
    const end = new Date(start);
    end.setDate(end.getDate() + duration);
    const now = new Date();
    const elapsed = (now - start) / (1000 * 60 * 60 * 24);
    const remaining = Math.max(0, duration - elapsed);
    const progress = (elapsed / duration) * 100;

    return {
      active: elapsed >= 0 && remaining > 0,
      daysRemaining: Math.ceil(remaining),
      daysTotal: duration,
      interval,
      dauer,
      vonTime,
      bisTime,
      progress: Math.min(100, progress),
      startDate: start.toLocaleDateString('de-DE'),
    };
  }

  _startAnsaat(zoneId) {
    if (!this.hass || !this.config?.entry_id) return;
    const entryId = this.config.entry_id;
    this.hass.callService('smartgardn_et0', 'start_zone', {
      zone: `select.${entryId}_${zoneId}_modus`,
      dauer_min: 5, // Default short burst for ansaat
    });
  }

  _stopAnsaat(zoneId) {
    if (!this.hass || !this.config?.entry_id) return;
    const entryId = this.config.entry_id;
    this.hass.callService('smartgardn_et0', 'stop_zone', {
      zone: `select.${entryId}_${zoneId}_modus`,
    });
  }

  render() {
    this._updateAnsaatZones();

    return html`
      <ha-card header="🌱 Ansaat (Keimung)">
        <div class="card-content">
          ${this.ansaatZones.length > 0
            ? html`
                <div class="ansaat-grid">
                  ${this.ansaatZones.map((zone) => this._renderAnsaatZone(zone))}
                </div>
              `
            : html`
                <div class="no-ansaat">
                  <p>Keine Zonen im Ansaat-Modus</p>
                  <p class="hint">
                    Setzen Sie eine Zone auf "Ansaat" um intensive Keimungs-Bewässerung zu aktivieren.
                  </p>
                </div>
              `}
        </div>
      </ha-card>
    `;
  }

  _renderAnsaatZone(zone) {
    const status = zone.status;

    return html`
      <div class="ansaat-card">
        <div class="ansaat-header">
          <h3>${zone.name}</h3>
          <span class="status-badge ${status.active ? 'active' : 'inactive'}">
            ${status.active ? '⏱️ Läuft' : '⏸️ Inaktiv'}
          </span>
        </div>

        <div class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${status.progress}%"></div>
          </div>
          <div class="progress-label">
            <span>${Math.round(status.progress)}% — ${status.daysRemaining} / ${status.daysTotal} Tage</span>
          </div>
        </div>

        <div class="config-grid">
          <div class="config-item">
            <span class="config-label">Intervall:</span>
            <span class="config-value">${status.interval} h</span>
          </div>
          <div class="config-item">
            <span class="config-label">Laufzeit:</span>
            <span class="config-value">${status.dauer} min</span>
          </div>
          <div class="config-item">
            <span class="config-label">Zeitfenster:</span>
            <span class="config-value">${status.vonTime} - ${status.bisTime}</span>
          </div>
          <div class="config-item">
            <span class="config-label">Start:</span>
            <span class="config-value">${status.startDate || '—'}</span>
          </div>
        </div>

        <div class="timeline-visualization">
          <div class="timeline-container">
            ${this._renderTimeline(status)}
          </div>
        </div>

        <div class="action-buttons">
          <button
            class="btn btn-primary"
            @click=${() => this._startAnsaat(zone.zone_id)}
            ?disabled=${status.active}
          >
            Start
          </button>
          <button
            class="btn btn-secondary"
            @click=${() => this._stopAnsaat(zone.zone_id)}
            ?disabled=${!status.active}
          >
            Stop
          </button>
        </div>

        <div class="info-box">
          <strong>Ansaat-Modus:</strong> Bewässert intensiv in Intervallen während des Keim-Zeitfensters.
          Ideal für Rasen-Neuaussaat, Blumensamen und empfindliche Keimpflanzen.
        </div>
      </div>
    `;
  }

  _renderTimeline(status) {
    const segments = Math.min(21, status.daysTotal);
    const daysPerSegment = status.daysTotal / segments;

    return html`
      <div class="timeline">
        ${Array.from({ length: segments }).map(
          (_, idx) => {
            const dayStart = idx * daysPerSegment;
            const dayEnd = (idx + 1) * daysPerSegment;
            const isComplete = dayEnd <= status.daysTotal - status.daysRemaining;
            const isCurrent = dayStart <= status.daysTotal - status.daysRemaining && dayEnd > status.daysTotal - status.daysRemaining;

            return html`
              <div
                class="timeline-segment ${isComplete ? 'complete' : ''} ${isCurrent ? 'current' : ''}"
                title="Tag ${Math.round(dayStart + 1)}-${Math.round(dayEnd)}"
              ></div>
            `;
          }
        )}
      </div>
    `;
  }

  static get styles() {
    return css`
      :host {
        --color-active: #4caf50;
        --color-inactive: #9e9e9e;
        --color-current: #2196f3;
      }

      .card-content {
        padding: 16px;
      }

      .ansaat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        gap: 16px;
      }

      .ansaat-card {
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 16px;
        background: var(--card-background-color);
      }

      .ansaat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--divider-color);
      }

      .ansaat-header h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .status-badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }

      .status-badge.active {
        background: var(--color-active);
        color: white;
      }

      .status-badge.inactive {
        background: var(--color-inactive);
        color: white;
      }

      .progress-section {
        margin-bottom: 16px;
      }

      .progress-bar {
        width: 100%;
        height: 24px;
        background: #f0f0f0;
        border-radius: 4px;
        overflow: hidden;
        margin-bottom: 4px;
      }

      .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--color-active) 0%, var(--color-current) 100%);
        transition: width 0.3s ease;
      }

      .progress-label {
        text-align: center;
        font-size: 12px;
        font-weight: 600;
        color: var(--primary-text-color);
      }

      .config-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-bottom: 16px;
        padding: 12px;
        background: rgba(0, 0, 0, 0.02);
        border-radius: 4px;
      }

      .config-item {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }

      .config-label {
        font-size: 11px;
        color: var(--secondary-text-color);
        text-transform: uppercase;
        font-weight: 600;
      }

      .config-value {
        font-size: 13px;
        font-weight: bold;
        color: var(--primary-text-color);
      }

      .timeline-visualization {
        margin-bottom: 16px;
      }

      .timeline-container {
        padding: 12px;
        background: rgba(0, 0, 0, 0.02);
        border-radius: 4px;
      }

      .timeline {
        display: flex;
        gap: 2px;
        height: 32px;
      }

      .timeline-segment {
        flex: 1;
        background: #e0e0e0;
        border-radius: 2px;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .timeline-segment:hover {
        transform: scaleY(1.2);
      }

      .timeline-segment.complete {
        background: var(--color-active);
      }

      .timeline-segment.current {
        background: var(--color-current);
        box-shadow: 0 0 4px rgba(33, 150, 243, 0.5);
      }

      .action-buttons {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;
      }

      .btn {
        flex: 1;
        padding: 8px 12px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
      }

      .btn-primary {
        background: var(--color-active);
        color: white;
      }

      .btn-primary:hover:not(:disabled) {
        opacity: 0.9;
      }

      .btn-primary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .btn-secondary {
        background: var(--divider-color);
        color: var(--primary-text-color);
      }

      .btn-secondary:hover:not(:disabled) {
        background: var(--primary-color);
        color: white;
      }

      .btn-secondary:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .info-box {
        padding: 10px;
        background: #e3f2fd;
        border-left: 4px solid var(--color-current);
        border-radius: 2px;
        font-size: 11px;
        line-height: 1.4;
        color: #01579b;
      }

      .no-ansaat {
        padding: 32px 16px;
        text-align: center;
        color: var(--secondary-text-color);
      }

      .no-ansaat p {
        margin: 8px 0;
      }

      .no-ansaat .hint {
        font-size: 12px;
        font-style: italic;
      }

      @media (max-width: 600px) {
        .ansaat-grid {
          grid-template-columns: 1fr;
        }

        .config-grid {
          grid-template-columns: 1fr;
        }

        .action-buttons {
          flex-direction: column;
        }
      }
    `;
  }
}
