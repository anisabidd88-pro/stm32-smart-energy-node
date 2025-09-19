
STM32 Firmware Template - Guidance
=================================

This folder contains code snippets and guidance to port the simulator behavior to a real STM32 MCU.

Key areas covered:
- ADC sampling & RMS calculation (floating-point or fixed-point)
- Modbus/TCP holding register mapping (using LwIP or an industrial stack)
- AES-based OTA flow: download encrypted image, verify signature, decrypt, write to Flash, verify, reboot
- Secure Boot & image signing: sign with RSA/ECC and verify in bootloader
- Suggestions for sensors: ADE7753 / INA219 / MCP39F511
- Hardware considerations: voltage dividers, burden resistor for CT, isolation (opto or isolated ADC), TVS, common-mode protection

Files included:
- main.c (template with ADC & telemetry)
- aes_ota.c/.h (conceptual helpers; replace with mbedTLS or tiny-AES-c for real use)
- notes.txt with checklist for production readiness

Important:
- The provided C files are templates. You'll need to import them into an STM32CubeIDE project, configure clocks/peripherals and include CubeMX-generated HAL code.
- Always test cryptography and bootloader code in a safe environment before field deployment.
