# Third-Party Licenses and Acknowledgments

This project uses the following third-party libraries and resources. We respect their licenses and include proper attribution.

---

## Vendored Libraries

### PyETo — FAO-56 ET₀ Calculations
- **Source:** https://github.com/woodcrafty/PyETo
- **License:** BSD 3-Clause License
- **Author:** Mark Richards
- **Vendored Version:** d5f1809 (2018-07-31)
- **Usage:** Subset of pure mathematical functions for reference evapotranspiration (ET₀) calculation following FAO-56 Penman-Monteith method
- **Modifications:** None — only mathematical functions extracted, no algorithms modified

**BSD 3-Clause License Text:**
```
Copyright (c) 2018, Mark Richards
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

---

## External Services (No Vendoring Required)

### Deutsches Wetterdienst (DWD) MOSMIX-S Forecast via brightsky.dev
- **Service:** brightsky.dev REST API (free wrapper around DWD MOSMIX-S)
- **Provider:** brightsky.dev (https://brightsky.dev/)
- **Source Data:** Deutscher Wetterdienst (DWD) — German national weather service
- **Data License:** [CC0 1.0 Universal (Public Domain Dedication)](https://creativecommons.org/publicdomain/zero/1.0/)
- **Usage:** Optional 3-day ET₀ and precipitation forecast for intelligent rain-skip irrigation scheduling
- **API Key:** Not required
- **Rate Limiting:** Free service with fair-use limits (no explicit cap per docs)
- **API Terms:** Subject to brightsky.dev's [Terms of Service](https://brightsky.dev/)
- **Attribution:** Data from DWD MOSMIX model, aggregated by brightsky.dev

### Home Assistant Core
- **License:** Apache License 2.0
- **Project:** https://github.com/home-assistant/core
- **Usage:** Integration runs as a Home Assistant custom component
- **Required Version:** Home Assistant 2024.10+

---

## Development Dependencies

These are used for testing, linting, and type checking, but are **not** bundled in the production integration:

- **pytest** — Testing framework (MIT License)
- **pytest-homeassistant-custom-component** — HA test harness (Apache 2.0)
- **pytest-asyncio** — Async test support (Apache 2.0)
- **pytest-cov** — Coverage reporting (MIT License)
- **freezegun** — Time mocking for tests (Apache 2.0)
- **ruff** — Fast Python linter (MIT License)
- **mypy** — Static type checker (MIT License)

---

## Scientific References

This integration implements the following scientific standards and methods:

### FAO-56 Penman-Monteith Equation
- **Reference:** [Crop Evapotranspiration - Guidelines for Computing Crop Water Requirements](http://www.fao.org/3/X0490E/X0490E00.htm) (FAO Irrigation and Drainage Paper 56)
- **License:** FAO documents are freely available for educational use
- **Citation:** Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). FAO Irrigation and Drainage Paper 56. ISBN 92-5-104219-5

### Grünlandtemperatursumme (GTS) — Growing Degree Sum
- **Standard:** German agricultural standard for crop development calculation
- **Reference:** DWD Agrarmeteorologie documentation

---

## License Compatibility

**SmartGardn ET₀** is released under the **MIT License**.

All included third-party components are compatible with the MIT License:
- ✅ BSD 3-Clause (PyETo) — Compatible with MIT
- ✅ Apache 2.0 (Home Assistant) — Compatible with MIT (permissive)
- ✅ DWD Open Data — Public domain (compatible)

---

## Attribution Summary

| Component | License | Status | Attribution Required? |
|-----------|---------|--------|----------------------|
| PyETo (vendored) | BSD 3-Clause | Included | ✅ Yes (see above) |
| DWD Forecast API | Open Data | External | ✅ Yes (no code changes needed) |
| Home Assistant | Apache 2.0 | External | ✅ Yes (standard for HA integrations) |
| Development tools | MIT, Apache 2.0 | Dev-only | ❌ No (not bundled) |

---

## How to Report License Issues

If you discover a potential license issue or have questions about third-party usage, please:

1. Open a GitHub issue: [Issues](https://github.com/Presley2/ha-smartgardn/issues)
2. Tag as `type:license` for visibility
3. Provide specific details about the concern

---

## Data Attribution

### Weather Data Chain
```
DWD (Deutscher Wetterdienst)
    ↓ MOSMIX-S forecast model
    ↓ 
brightsky.dev (free public API)
    ↓ CC0 Public Domain data
    ↓
SmartGardn ET₀ (this integration)
    → ET₀ calculation (FAO-56)
    → Irrigation decision logic
```

All data in this chain is in the **public domain** with no attribution requirement, but we recognize and credit:
1. DWD for the meteorological model and data
2. brightsky.dev for the free API wrapper service
3. FAO for the ET₀ calculation methodology

---
## Additional Notes

- This project contains **no proprietary or commercial code**
- All vendored code is pure mathematical functions with no modifications
- The integration is designed to be transparent about dependencies
- Questions about licensing are welcome and encouraged
- **No tracking, analytics, or telemetry** to external services beyond optional brightsky.dev weather API

---

*Last Updated: May 2026*
