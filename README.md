# Hunter's Gaze | XL-SOC Dashboard

A single-file Threat Hunting & IOC Aggregation platform built with Flask and Alpine.js.

## Features
- **Real-time Threat Feeds**: Aggregates data from SANS, URLhaus, ThreatFox, CISA KEV, and 30+ other sources.
- **Cross-Correlation**: Automatically highlights IOCs that appear in multiple threat feeds.
- **Interactive Dashboard**: 3D Globe visualization and Radar charts using Plotly.
- **Simulation Mode**: Generates realistic mock data if offline or rate-limited.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mindfliphacks/Hunter-s-Gaze-XL-SOC.git
   cd Hunter-s-Gaze-XL-SOC
   python3 hunters-gaze-ioc.py
