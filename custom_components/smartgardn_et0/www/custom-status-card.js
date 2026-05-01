import { LitElement, html, css } from 'lit';
import { customElement, property } from 'lit/decorators.js';

@customElement('irrigation-custom-status-card')
export class CustomStatusCard extends LitElement {
  @property({ attribute: false }) hass;
  @property({ type: Object }) config;

  setConfig(config) {
    if (!config.entry_id) {
      throw new Error('entry_id is required in card config');
    }
    this.config = config;
  }

  render() {
    const entryId = this.config.entry_id;
    const nfkSensor = `sensor.${entryId}_zone0_nfk_prozent`;
    const state = this.hass.states[nfkSensor];
    const nfk = state ? parseFloat(state.state) : 0;

    return html`
      <ha-card header="Custom Feuchte Status">
        <div class="card-content">
          <div class="status-container">
            <span class="label">NFK (Bodenfeuchte):</span>
            <span class="value">${nfk.toFixed(1)}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${nfk}%"></div>
          </div>
        </div>
      </ha-card>
    `;
  }

  static styles = css`
    .card-content {
      padding: 16px;
    }
    .status-container {
      display: flex;
      justify-content: space-between;
      margin-bottom: 12px;
      font-size: 14px;
    }
    .label {
      font-weight: 500;
    }
    .value {
      color: var(--primary-color);
      font-weight: 600;
    }
    .progress-bar {
      width: 100%;
      height: 24px;
      background: var(--paper-card-background-color);
      border-radius: 4px;
      overflow: hidden;
      border: 1px solid var(--divider-color);
    }
    .progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #4CAF50, #FFC107);
      transition: width 0.3s ease;
    }
  `;
}
