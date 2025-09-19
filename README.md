
STM32 Smart Energy Grid Node - Starter Package
=============================================

What's inside this ZIP
- server/node_simulator/  -> A fully runnable Python simulator that mimics an STM32 energy node:
    - exposes Modbus/TCP registers (port 5020),
    - provides a Flask dashboard (http://localhost:5000),
    - demonstrates AES-256 OTA upload & simulated apply,
    - logs telemetry and stores encrypted firmware.
- firmware_template/     -> STM32 firmware templates, code snippets and guidance to port to STM32 (STM32CubeIDE / HAL).
- scripts/               -> Helper scripts (encrypt firmware, sign guidance).
- example_firmware.bin   -> small placeholder firmware binary you can use to test OTA.
- LICENSE, README.md

Quick start (recommended)
1. Install Python 3.8+ and pip on your machine (Windows 10: use the official installer).
2. Open a terminal and create a virtual env (optional):
   python -m venv venv
   source venv/bin/activate   # or `venv\Scripts\activate` on Windows
3. Install dependencies:
   pip install -r server/node_simulator/requirements.txt
4. Run the simulator (it runs Modbus server + Flask dashboard):
   python server/node_simulator/sim_node.py
5. Open http://localhost:5000 in your browser to view the dashboard and OTA endpoints.
6. To test OTA upload: use the dashboard Upload button or run scripts/encrypt_firmware.py to create an encrypted package and then POST to /ota/upload.

Notes & Next steps
- The Python simulator is ready-to-run and tested in a desktop environment; it is meant to validate system architecture, Modbus mapping, OTA flow, AES encryption and dashboard functionality quickly.
- The firmware_template folder contains annotated C sources that explain how to port the logic to an STM32 microcontroller (ADC sampling, RMS and power calculation, Modbus mapping with LwIP or an industrial Modbus stack, and a secure OTA approach using AES + signed images).
- Real STM32 deployment will require adapting the template to your target MCU, CubeMX-generated initialization files, using a real ADC driver and a networking stack (LwIP/FreeRTOS) or a cellular modem library if using NB-IoT/4G.
- I aimed for practical, expert-level starter code — but please review crypto key management and secure boot measures before deploying to production.

If you want, I can:
- add a preconfigured STM32CubeMX .ioc file for a specific MCU (e.g. STM32F746 or STM32F407),
- create a PlatformIO / STM32CubeIDE project that you can open and build directly,
- or extend the simulator to push telemetry to InfluxDB + Grafana.
