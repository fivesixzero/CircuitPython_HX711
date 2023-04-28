# SPDX-FileCopyrightText: Copyright (c) 2022 Erik Hess
#
# SPDX-License-Identifier: MIT

"""
`HX711`
====================================================

Driver superclass for the HX711 load cell amplifier/DAC.

* Author(s): Erik Hess

Implementation Notes
--------------------

**Driver Subclasses**

* `HX711_GPIO`, works with all CircuitPython boards but may be subject to timing issues
* `HX711_PIO`, uses RP2-series (ie, RP2040) PIO to provide consistent pulse timing

**Hardware:**

* SparkFun `HX711 Load Cell Amplifier Breakout (SEN-13879)
  <https://www.sparkfun.com/products/13879>`_

* DFRobot `Gravity Digital Weight Sensor (SEN0160)
  <https://www.dfrobot.com/product-1031.html>`_

* DFRobot `Gravity I2C Weight Sensor Kit (KIT0176)
  <https://www.dfrobot.com/product-2289.html>`_

* M5Stack `Mini Weight Unit HX711 Load Cell Amplifier (U030)
  <https://shop.m5stack.com/products/weight-sensor-unit>`_

* Seeed Studio `Grove ADC For Load Cell (101020712)
  <https://www.seeedstudio.com/Grove-ADC-for-Load-Cell-HX711-p-4361.html>`_

* Nightshade `Trēo 24-bit Load Cedll ADC - HX711 (NSE-1132-1)
  <https://nightshade.net/product/treo-24-bit-load-cell-adc-hx711>`_

* Elecrow `Weight Sensor Amplifier - HX711 (SHX7110)
  <https://www.elecrow.com/weight-sensor-amplifier-hx711-p-715.html>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""

from micropython import const

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/fivesixzero/CircuitPython_HX711"


class HX711:
    """
    Provide basic driver services for the HX711 load cell amplifier/ADC

    This subclass includes a GPIO bit-bang implemenation of the HX711 two-wire serial protocol using
    two GPIO pins, one for data and one for clock.

    :param gain int: Gain/channel setting for ADC readings. Defaults to :const:`1`
    :param offset int: Zero-offset to apply to readings. Defaults to :const:`0`
    :param float scalar: Scalar to use for conversion of ADC counts to units. Defaults to :const:`1`
    :param bool tare: If true, perform ``tare()`` on instantiation. Defaults to :const:`False`


    **Quickstart: Importing and using the HX711**

        Here is an example of using the :class:`HX711` class.

        First you will need to import the specific library subclass you'd like to use to access
        the sensor

        .. code-block:: python

            import board
            from hx711.hx711_gpio import HX711_GPIO

        Once this is done you can define your ``DigitalInOut`` objects for the pins attached to the
        HX711 sensor and define the sensor object.

        .. code-block:: python

            from digitalio import DigitalInOut

            gpio_data = DigitalInOut(board.D5)
            gpio_clk = DigitalInOut(board.D6)
            hx711 = HX711_GPIO(gpio_data, gpio_clk)

        For defining the PIO subclass, you only need to use the ``board`` ``Pin`` rather than
        ``DigitalInOut`` objects.

        .. code-block:: python

            pin_data = board.D5
            pin_clk = board.D6
            hx711 = HX711_PIO(pin_data, pin_clk)

        After instantiation, you'll have access to raw ADC counts.

        .. code-block:: python

            hx711.read_raw()

        These readings are a bit more useful with an offset applied, known as a "tare" operation.
        With this complete, future ``read()`` operations will return the difference between the
        offset and the reading.

        .. code-block:: python

            hx711.tare()
            print(hx711.read())

        This ``tare()`` operation can be performed on instantation via kwarg as well.

        .. code-block:: python

            hx711 = HX711_GPIO(gpio_data, gpio_clk, tare=True)

        To return a weight in more useful units, you can determine and set a scalar value. The
        appropriate scalar for your particular load cell and unit of choice can be determined by
        adding a known weight and running ``determine_scalar(weight)``.

        .. code-block:: python

            hx711.determine_scalar(weight)
            print(hx711.scalar)

        This scalar value can be applied in the future by directly setting it, like this.

        .. code-block:: python

            hx711.scalar = new_scalar

        A scalar value can be assigned at instantiation as well.

        .. code-block:: python

            hx711 = HX711_GPIO(gpio_data, gpio_clk, scalar=new_scalar, tare=True)

        Now you can read in weight values from the scale in the same units used to determine the
        scalar value.

        .. code-block:: python

            hx711.read()
    """

    HX_DATA_BITS = const(24)
    HX_MAX_VALUE = const(0x7FFFFF)
    COMPLMENT_MASK = const(0x1000000)

    def __init__(
        self, gain: int = 1, offset: int = 0, scalar: float = 1, tare: bool = False
    ):

        self.gain = gain
        self.offset = offset
        self.scalar = scalar

        if tare:
            self.tare()

    @property
    def gain(self) -> int:
        """Int value, ``1``, ``2``, or ``3``, representing the gain and channel to use for future
        ADC counts.

        .. csv-table::
           :header: "Channel", "Gain"

           "A", "128"
           "B", "32"
           "A", "64"

        .. hint:: See the HX711 datasheet for more details."""
        return self._gain

    @gain.setter
    def gain(self, gain: int) -> None:
        if gain > 1 or gain < 3:
            self._gain = gain
        else:
            raise ValueError()

    def tare(self, pre_read: bool = True) -> None:
        """Helper to zero out future measurements by setting an offset

        :param bool pre_read: If true, read in ADC values prior to tare to clear prior state or
            FIFOs. Defaults to :const:`True`"""
        if pre_read:
            self.read_average(5)

        self.offset = self.read_average()

    def determine_scalar(self, added_weight: float) -> float:
        """Helper for determining scalar based on an object of known weight. This scalar is used
        for future ``read()`` operations to return a weight value scaled to any desired unit rather
        than raw ADC counts.

        :param float added_weight: Known weight of added object, in any desired units of measure.

        .. caution:: An offset is required for a scalar to be effectively determined.

        """
        if not self.offset:
            raise ValueError("Offset required for scalar determination")

        self.read_raw()  # Clear any FIFOs with a pre-read
        reading = self.read_raw()
        diff = abs(reading - self.offset)
        self.scalar = diff / added_weight
        return self.scalar

    def read(self, average_count: int = 1) -> float:
        """Retrieves a raw ADC count (or an average of counts) and applies scalar before returning
        unit weight value

        :param int average_count: Number of reads to perform for average. Defaults to :const:`1`."""
        if average_count > 1:
            read_raw = (self.read_average(average_count) - self.offset) / self.scalar
        else:
            read_raw = (self.read_raw() - self.offset) / self.scalar

        return read_raw

    def read_average(self, count: int = 10) -> int:
        """Performs multiple raw ADC count reads and averages them"""
        readings = []

        for _ in range(count):
            readings.append(self.read_raw())

        return sum(readings) // len(readings)

    def read_raw(self) -> int:
        """Retrieves and returns a raw ADC count"""
        raise NotImplementedError()
