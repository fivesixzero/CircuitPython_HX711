# SPDX-FileCopyrightText: Copyright (c) 2022 Erik Hess
#
# SPDX-License-Identifier: MIT

"""
`HX711_PIO`
====================================================

CircuitPython PIO driver subclass for the HX711 load cell amplifer and ADC


* Author(s): Erik Hess

Implementation Notes
--------------------

**Hardware:**

* Requires RP2-series or compatible PIO capability

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's PIOASM library: https://github.com/adafruit/Adafruit_CircuitPython_PIOASM
"""

import array
from micropython import const
from digitalio import DigitalInOut
import rp2pio
import adafruit_pioasm
from . import HX711

HX711_READ_CODE = """
set x, {0}      ; number of cycles for post-readout gain setting
mov osr, x      ; put the gain into osr for safe keeping
set x, 7        ; number of pad bits, 0-start
set y, {1}      ; number of data bits, 0-start

padloop:        ; build front-pad bits for 32-bit Pythonic int alignment
    in pins, 1
    jmp x-- padloop

wait 0 pin 0    ; wait for the hx711 DAC's cycle-complete signal

mov x, osr      ; set up our gain loop counter, also delays first clock edge by a full cycle

bitloop:        ; read in those bits!
    set pins, 1 [3]
    set pins, 0 [1]
    in pins, 1
    jmp y-- bitloop

gainloop:       ; add 1, 2, or 3 pulses to set gain for next ADC count
    set pins, 1 [3]
    set pins, 0
    jmp x-- gainloop
"""

HX_INIT_DELAY = const(10)
PAD_MASK = const(0x00FFFFFF)


class HX711_PIO(HX711):
    """HX711 driver subclass for RP2-series PIO"""

    def __init__(
        self,
        pin_data: DigitalInOut,
        pin_clk: DigitalInOut,
        *,
        gain: int = 1,
        offset: int = 0,
        scalar: int = 1,
        tare: bool = False,
        pio_freq: int = 4000000
    ):

        self._buffer = array.array("I", [0])

        self._pin_data = pin_data
        self._pin_clk = pin_clk
        self._pio_freq = pio_freq

        self.sm_init(gain)

        super().__init__(gain, offset, scalar, tare)

    def sm_init(self, gain: int) -> None:
        """Initialize a PIO ``StateMachine`` for this driver"""
        self._pioasm_read = adafruit_pioasm.assemble(
            HX711_READ_CODE.format(gain - 1, HX711.HX_DATA_BITS - 1)
        )

        self._sm = rp2pio.StateMachine(
            self._pioasm_read,
            frequency=self._pio_freq,
            first_in_pin=self._pin_data,
            in_pin_count=1,
            first_set_pin=self._pin_clk,
            set_pin_count=1,
            in_shift_right=False,
            push_threshold=32,
            auto_push=True,
        )

    def sm_deinit(self) -> None:
        """De-initialize the PIO ``StateMachine`` for this driver"""
        self._sm.deinit()

    def read_raw(self) -> int:
        """Read in raw ADC reading using PIO state machine"""

        self._sm.clear_rxfifo()
        self._sm.readinto(self._buffer)

        # Mask out our pad bits
        raw_reading = self._buffer[0] & PAD_MASK

        # Handle two's compliment negative numbers
        if raw_reading > HX711.HX_MAX_VALUE:
            raw_reading -= HX711.COMPLMENT_MASK

        return raw_reading
