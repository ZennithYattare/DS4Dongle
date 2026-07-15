#!/usr/bin/env python3
"""
Reboot the DS4Dongle into BOOTSEL (USB bootloader) from the host, so it can be
reflashed without pressing the physical BOOTSEL button.

Sends HID feature report 0xF6 with funcid 0x04, which the firmware answers by
dropping into BOOTSEL (src/cmd.cpp: `buffer[0] == 0x04 -> reset_usb_boot()`).
The dongle then re-enumerates as the RP2350 mass-storage drive. The HID device
disappears mid-request, so a send error here is EXPECTED and means success.

PLATFORM NOTE (Windows): report id 0xF6 is not declared in the DS4 HID report
descriptor (it is kept byte-identical to a real DS4 v2). Windows' HID stack
drops SET_FEATURE for any undeclared report id, so the request never reaches
the firmware and the dongle does NOT reboot -- send_feature_report just returns
-1. Use the physical BOOTSEL button on Windows, or run this from Linux, where
hidraw passes the raw request through regardless of the descriptor.

Requires: pip install hidapi
Run:      python reboot_bootsel.py
"""
import platform
import sys

# open_device() finds and opens the DS4 gamepad HID interface (and prints a
# helpful message if the dongle isn't present). Shared with config_tool so the
# device-selection logic stays in one place.
from config_tool import open_device, REPORT_SET, SET_DATA_LEN

FUNCID_REBOOT_BOOTSEL = 0x04


def main():
    dev = open_device()
    # [report id][funcid][padding...] -> 1 + SET_DATA_LEN bytes total
    payload = bytes([REPORT_SET, FUNCID_REBOOT_BOOTSEL]).ljust(SET_DATA_LEN + 1, b"\x00")
    try:
        result = dev.send_feature_report(payload)
    except (OSError, ValueError) as e:
        # Device reboots and drops off the bus mid-request -- this is success.
        print(f"Send raised (device already rebooting -- expected): {e}")
        return
    finally:
        try:
            dev.close()
        except Exception:
            pass

    # hidapi returns the byte count on success, or -1 if the host stack rejected
    # the report without sending it (the Windows undeclared-report-id case).
    if result is not None and result < 0:
        msg = "Failed to send the reboot command (report 0xF6, funcid 0x04)."
        if platform.system() == "Windows":
            msg += ("\n\nExpected on Windows: report id 0xF6 is not declared in the DS4 HID\n"
                    "report descriptor, so Windows drops the SET_FEATURE and the dongle does\n"
                    "not reboot. Hold the physical BOOTSEL button while plugging the dongle in\n"
                    "instead, or run this from Linux (hidraw passes the request through).")
        sys.exit(msg)
    print("Sent reboot-to-BOOTSEL. The dongle should now appear as the RP2350 drive.")


if __name__ == "__main__":
    main()
