# SPDX-FileCopyrightText: Copyright (c) 2022 Erik Hess
#
# SPDX-License-Identifier: MIT

"""
`HX711_GPIO`
====================================================

CircuitPython GPIO driver subclass for the HX711 load cell amplifer and ADC


* Author(s): Erik Hess

Implementation Notes
--------------------

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

import time
from digitalio import DigitalInOut
from . import HX711


class HX711_GPIO(HX711):
    """HX711 driver subclass for GPIO"""

    def __init__(
        self,
        pin_data: DigitalInOut,
        pin_clk: DigitalInOut,
        *,
        gain: int = 1,
        offset: int = 0,
        scalar: int = 1,
        tare: bool = False,
    ):

        self._pin_data = pin_data
        self._pin_data.switch_to_input()

        self._pin_clk = pin_clk
        self._pin_clk.switch_to_output()

        self.gain = gain

        self.read_raw()

        super().__init__(gain, offset, scalar, tare)

    def _gain_pulse(self, gain: int) -> None:
        for _ in range(gain):
            self._pin_clk.value = True
            self._pin_clk.value = False

    def read_raw(self) -> int:
        while self._pin_data.value:
            time.sleep(0.01)

        raw_reading = 0
        for _ in range(HX711.HX_DATA_BITS):
            self._pin_clk.value = True
            self._pin_clk.value = False
            raw_reading = raw_reading << 1 | self._pin_data.value

        self._gain_pulse(self.gain)

        # Handle two's compliment negative numbers
        if raw_reading > HX711.HX_MAX_VALUE:
            raw_reading -= HX711.COMPLMENT_MASK

        return raw_reading
