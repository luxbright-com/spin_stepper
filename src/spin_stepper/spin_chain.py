from typing import Callable, List
from .spin_device import SpinDevice


class SpinChain:
    """Class for constructing a chain of SPIN devices"""

    def __init__(
        self,
        total_devices: int,
        spi_select: tuple[int, int] | None = None,
        spi_transfer: Callable[[List[int]], List[int]] | None = None,
    ) -> None:
        """
        If different from hardware SPI CS pin
        :total_devices: Total number of devices in the chain.
        :spi_select: A SPI bus, device pair, e.g. (0, 0)
        :spi_transfer: A SPI transfer function that behaves like
            spidev.xfer2.
            It should write a list of bytes as ints with MSB first,
            while correctly latching using the chip select pins
            Then return an equal-length list of bytes as ints from MISO
        """
        if total_devices < 1:
            raise RuntimeError("total_devices must be greater than 0")

        if spi_select is None and spi_transfer is None:
            raise RuntimeError("spi_select or spi_transfer must be set")

        self._total_devices: int = total_devices

        # {{{ SPI setup
        if spi_transfer is not None:
            self._spi_transfer = spi_transfer

        elif spi_select is not None:
            import spidev

            self._spi = spidev.SpiDev()

            bus, device = spi_select
            self._spi.open(bus, device)

            self._spi.mode = 3
            # Device expects MSB to be sent first
            self._spi.lsbfirst = False
            self._spi.max_speed_hz = 1000000
            # CS pin is active low
            self._spi.cshigh = False

            self._spi_transfer = self._spi.xfer2
        # }}}

    def create(self, position: int) -> SpinDevice:
        """
                    +----------+
               MOSI |   MCU    | MISO
        +-----------+          +---------------+
        |           +----------+               |
        |                                      |
        |                                      |
        |             SPIN ICs                 |
        |   +-----+     +-----+     +-----+    |
        |SDI|     |     |     |     |     |SDO |
        +---+  2  +-----+  1  +-----+  0  +----+
            |     |     |     |     |     |
            |     |     |     |     |     |
            +-----+     +-----+     +-----+
         Create a new SPIN device at the specified chain location
         :position: Device position in chain
         :return: A newly-instantiated SpinDevice

        """
        if position < 0:
            raise RuntimeError("position must be greater than or equal to 0")

        if position >= self._total_devices:
            raise RuntimeError("position must be less than or equal to total devices")

        return SpinDevice(
            position,
            self._total_devices,
            self._spi_transfer,
        )
