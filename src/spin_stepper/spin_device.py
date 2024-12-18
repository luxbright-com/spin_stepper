import enum
import logging
from threading import Lock
from typing import Callable

SET_MARK_FLAG = 0x04

logger = logging.getLogger(__name__)


def decode_twos_complement(value: int, bits: int) -> int:
    """
    Decode two complement binary numbers to int.
    :param value: Binary value
    :param bits: Bit width
    :return:
    """
    if (value & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        return value - (1 << bits)  # compute negative value
    return value  # return positive value as is


def encode_twos_complement(value: int, bits: int) -> int:
    """
    Encode int to signed binary of defined bit width.
    :param value: Int value to encode
    :param bits: Bit width
    :return:
    """
    if value >= 0:
        return value
    mask = (1 << bits) - 1
    tmp = (abs(value) ^ mask) + 1
    return tmp & mask

def resize_to_length(array: list[int], length: int) -> list[int]:
    """Resizes the array, 0-extending the first positions,
    or truncating the first positions

    :array: Array to resize (if at all)
    :length: Desired length of array
    :returns: Resized array or original array

    """
    if length < 0:
        raise ValueError("length must be non-negative")
    difference = abs(len(array) - length)

    if len(array) > length:
        return array[difference:]

    return ([0] * difference) + array


def to_byte_array(value: int) -> list[int]:
    """Splits an integer into a list of bytes
    :value: Value to convert. Must be non-negative
    :returns: List of bytes, with MSB at entry 0

    """
    if value < 0:
        raise ValueError("value must be non-negative")

    byte_count = 1 if value == 0 else (value.bit_length() + 7) // 8
    return list(value.to_bytes(byte_count, byteorder="big"))


def to_byte_array_with_length(value: int, length: int) -> list[int]:
    """
    Splits an integer into a list of bytes
    First bytes will be truncated or padded with 0 as
    required by length

    :value: Value to convert. Must be non-negative
    :length: Desired length in bytes
    :returns: List of bytes, with MSB at entry 0

    """
    return resize_to_length(to_byte_array(value), length)


def to_int(byte_array: list[int]) -> int:
    """
    Convert a byte array to an integer

    :byte_array: Byte array with MSB first
    :returns: Single integer equivalent to the given byte array

    """
    result = 0
    for byte in byte_array:
        result = result * 256 + byte

    return result


class SpinDirection(enum.IntEnum):
    Reverse = 0
    Forward = 1


class SpinRegister(enum.IntEnum):
    """
    RegisterAddresses
    """

    ACC = 0x05
    ADC_OUT = 0x12
    ALARM_EN = 0x17
    DEC = 0x06
    CONFIG = 0x18
    K_THERM = 0x11
    KVAL_ACC = 0x0B
    KVAL_DEC = 0x0C
    KVAL_HOLD = 0x09
    KVAL_RUN = 0x0A
    MARK = 0x03
    ABS_POS = 0x01
    EL_POS = 0x02
    FN_SLP_ACC = 0x0F
    FN_SLP_DEC = 0x10
    ST_SLP = 0x0E
    SPEED = 0x04
    FS_SPEED = 0x15
    INT_SPEED = 0x0D
    MAX_SPEED = 0x07
    MIN_SPEED = 0x08
    STATUS = 0x19
    STEP_MODE = 0x16
    OCD_TH = 0x13
    STALL_TH = 0x14

    @property
    def size(self) -> int:
        """
        Returns the register size in bytes.
        :return: Register size.
        """
        register_size: dict[int, int] = {
            SpinRegister.ACC.value: 2,
            SpinRegister.ADC_OUT.value: 1,
            SpinRegister.ALARM_EN.value: 1,
            SpinRegister.DEC.value: 2,
            SpinRegister.CONFIG.value: 2,
            SpinRegister.K_THERM.value: 1,
            SpinRegister.KVAL_ACC.value: 1,
            SpinRegister.KVAL_DEC.value: 1,
            SpinRegister.KVAL_HOLD.value: 1,
            SpinRegister.KVAL_RUN.value: 1,
            SpinRegister.MARK.value: 3,
            SpinRegister.ABS_POS.value: 3,
            SpinRegister.EL_POS.value: 2,
            SpinRegister.FN_SLP_ACC.value: 1,
            SpinRegister.FN_SLP_DEC.value: 1,
            SpinRegister.ST_SLP.value: 1,
            SpinRegister.SPEED.value: 3,
            SpinRegister.FS_SPEED.value: 2,
            SpinRegister.INT_SPEED.value: 2,
            SpinRegister.MAX_SPEED.value: 2,
            SpinRegister.MIN_SPEED.value: 2,
            SpinRegister.STATUS.value: 2,
            SpinRegister.STEP_MODE.value: 1,
            SpinRegister.OCD_TH.value: 1,
            SpinRegister.STALL_TH.value: 1,
        }

        return register_size[self.value]


class SpinCommand(enum.IntEnum):
    GoHome = 0x70
    GoMark = 0x78
    GoTo = 0x60
    GoToDir = 0x68  # ORed with DIR
    GoUntil = 0x82  # ORed with ACT, DIR
    HiZHard = 0xA8
    HiZSoft = 0xA0
    Nop = 0x00
    Move = 0x40  # ORed with DIR. Unusable while running
    ParamGet = 0x20  # ORed with target register value
    ParamSet = 0x00  # ORed with target register value
    ReleaseSw = 0x92  # ORed with ACT, DIR
    ResetDevice = 0xC0
    ResetPos = 0xD8  # Clears ABS_POS
    Run = 0x50  # ORed with DIR
    StatusGet = 0xD0
    StepClock = 0x58  # ORed with DIR
    HardStop = 0xB8
    SoftStop = 0xB0

    @property
    def size(self) -> int:
        """
        Returns the register size in bytes.
        :return: Register size.
        """
        command_size: dict[int, int] = {
            SpinCommand.GoHome.value: 0,
            SpinCommand.GoMark.value: 0,
            SpinCommand.GoTo.value: 3,
            SpinCommand.GoToDir.value: 3,
            SpinCommand.GoUntil.value: 3,
            SpinCommand.HiZHard.value: 0,
            SpinCommand.HiZSoft.value: 0,
            SpinCommand.Nop.value: 0,
            SpinCommand.Move.value: 3,
            SpinCommand.ReleaseSw.value: 0,
            SpinCommand.ResetDevice.value: 0,
            SpinCommand.ResetPos.value: 0,
            SpinCommand.Run.value: 3,
            SpinCommand.StatusGet.value: 2,
            SpinCommand.StepClock.value: 0,
            SpinCommand.HardStop.value: 0,
            SpinCommand.SoftStop.value: 0,
        }
        return command_size[self.value]

    def __or__(self, register: SpinRegister) -> int:
        return self.value | register.value


class SpinStatus(enum.IntFlag):
    """
    ST_SPIN Device Status
    Some flags are active low from the device,
    those are inverted by the spin_status_factory to get flags that are easier to use.
    Inverted flags are marked with * below
    """

    HiZ = 0x0001
    Busy = 0x0002  # * active low
    SwitchFlag = 0x0004  # low on closed switch, high on open
    SwitchEvent = 0x0008  # high on falling edge
    Forward = 0x0010
    Acceleration = 0x0020
    Deceleration = 0x0040
    ConstantSpeed = 0x0060  # note the bit overlap with Acceleration and Deceleration
    CmdNotPerformed = 0x0080
    CmdWrong = 0x0100
    UnderVoltage = 0x0200  # * active low
    ThermalWarning = 0x0400  # * active low
    ThermalShutdown = 0x0800  # * active low
    OverCurrent = 0x1000  # * active low
    StepLossA = 0x2000  # * low on stall detect
    StepLossB = 0x4000  # * low on stall detect
    StepClockMode = 0x8000


def spin_status_factory(raw_value: int) -> SpinStatus:
    """
    Invert active low flags and return a SpinStatus instance
    :param raw_value: raw status register value
    :return: SpinStatus instance
    """
    invert_mask = 0x7E02
    return SpinStatus(raw_value ^ invert_mask)


class SpinDevice:
    """Class providing access to a single SPIN device"""

    max_steps_per_second: float = 15625.0
    max_steps: int = 2**22 - 1
    _TICK_SECONDS: float = 250e-9
    _MAX_SPEED_K = 2**-18
    _MIN_SPEED_K = 2**-24
    _ACC_K = 2**-40

    def __init__(
        self,
        position: int,
        total_devices: int,
        spi_transfer: Callable[[list[int]], list[int]],
        lock: Lock,
    ):
        """
        :position: Position in the chain, where 0 is the last device in the chain.
        :total_devices: Total number of devices in the chain.
        :spi: SPI object used for serial communication.
        :lock: A shared Lock object used for thread safety.
        """
        self._position: int = position
        self._total_devices: int = total_devices
        self._spi_transfer: callable = spi_transfer
        self.lock = lock

        self._direction = SpinDirection.Forward.value

    @property
    def direction(self) -> SpinDirection:
        """
        Get motor direction.
        :return: Motor direction
        """
        return SpinDirection(self._direction)

    @direction.setter
    def direction(self, direction: SpinDirection) -> None:
        """
        Set motor direction.
        :param direction: Direction to set motor to.
        """
        self._direction = direction.value

    @property
    def abs_pos(self) -> int:
        """
        Read the absolute position register.
        The resolution is in agreement with the selected step size.
        :return: Absolute position register.
        """
        return decode_twos_complement(self.get_register(SpinRegister.ABS_POS), 22)

    @property
    def mark(self) -> int:
        """
        Read the mark register.
        The resolution is in agreement with the selected step size.
        :return: The mark register.
        """
        return decode_twos_complement(self.get_register(SpinRegister.MARK), 22)

    @mark.setter
    def mark(self, pos: int) -> None:
        """
        Read the mark register.
        The resolution is in agreement with the selected step size.
        :return: The mark register.
        """
        value = decode_twos_complement(pos, 22)
        self.set_register(SpinRegister.MARK, value)

    @property
    def speed(self) -> float:
        """
        Returns current motor speed in pulses per second.
        :return: Current motor speed in pulses per second.
        """
        _speed = self.get_register(SpinRegister.SPEED)
        _k = 2**-28
        return _speed * _k / self._TICK_SECONDS

    def get_speed_limits(self) -> (float, float):
        """
        Get the speed min and max limits of the device.
        :return: The min_speed, max_speed limits
        """
        min_speed = (
            self.get_register(SpinRegister.MIN_SPEED)
            * self._MIN_SPEED_K
            / self._TICK_SECONDS
        )
        max_speed = (
            self.get_register(SpinRegister.MAX_SPEED)
            * self._MAX_SPEED_K
            / self._TICK_SECONDS
        )
        return min_speed, max_speed

    def set_speed_limits(
        self, min_speed: float | None = None, max_speed: float | None = None
    ) -> None:
        """
        Set the min_speed and max_speed limits of the device.
        :param min_speed: Min_speed in pulses/s
        :param max_speed: Max_speed in pulses/s
        """
        if min_speed:
            self.set_register(
                SpinRegister.MIN_SPEED,
                int(min_speed * self._TICK_SECONDS / self._MIN_SPEED_K),
            )

        if max_speed:
            self.set_register(
                SpinRegister.MAX_SPEED,
                int(max_speed * self._TICK_SECONDS / self._MAX_SPEED_K),
            )

    def get_acceleration(self) -> (float, float):
        """
        Get the deceleration and acceleration of the device in steps/s2.
        :return: Acceleration and deceleration
        """
        dec = self.get_register(SpinRegister.DEC) * self._ACC_K / self._TICK_SECONDS**2
        acc = self.get_register(SpinRegister.ACC) * self._ACC_K / self._TICK_SECONDS**2
        return dec, acc

    def set_acceleration(
        self, dec: float | None = None, acc: float | None = None
    ) -> None:
        """
        Set the deceleration and acceleration of the device in steps/s2.
        :param dec: Deceleration in steps/s2
        :param acc: Acceleration in steps/s2
        """
        if dec:
            self.set_register(
                SpinRegister.DEC, int(dec * self._TICK_SECONDS**2 / self._ACC_K)
            )
        if acc:
            self.set_register(
                SpinRegister.ACC, int(acc * self._TICK_SECONDS**2 / self._ACC_K)
            )

    def get_fs_spd(self) -> float:
        """
        Read the FS_SPD register.
        The FS_SPD register contains the threshold speed.
        When the actual speed exceeds this value, the step mode is automatically switched to full-step two-phase on.
        Its value is expressed in step/tick.
        :return: FS_SPD
        """
        return (
            (self.get_register(SpinRegister.FS_SPEED) + 0.5)
            * self._MAX_SPEED_K
            / self._TICK_SECONDS
        )

    def set_fs_spd(self, value: float) -> None:
        """
        Set the FS_SPD register.
        The FS_SPD register contains the threshold speed.
        When the actual speed exceeds this value, the step mode is automatically switched to full-step two-phase on.
        Its value is expressed in step/tick.
        :return: None
        """
        v = (value - 0.5) * self._TICK_SECONDS / self._MAX_SPEED_K
        self.set_register(SpinRegister.FS_SPEED, int(v))

    def get_kval(self) -> (float, float, float, float):
        """
        Read the KVAL registers.
        The KVAL_HOLD register contains the KVAL value assigned to the PWM modulators
        when the motor is stopped (compensation excluded).
        The KVAL_RUN register contains the KVAL value assigned to the PWM modulators
        when the motor is running at constant speed (compensation excluded).
        The KVAL_ACC register contains the starting KVAL value that can be assigned to the PWM
        modulators during acceleration (compensation excluded).
        The KVAL_DEC register contains the starting KVAL value that can be assigned to the PWM
        modulators during deceleration (compensation excluded).

        The available range is from 0 to 0.996 x VS with a resolution of 0.004 x VS (Voltage Source)
        :return: KVAL_HOLD, KVAL_RUN, KVAL_ACC, KVAL_DEC
        """
        _k = 256.0
        kval_hold = self.get_register(SpinRegister.KVAL_HOLD) / _k
        kval_run = self.get_register(SpinRegister.KVAL_RUN) / _k
        kval_acc = self.get_register(SpinRegister.KVAL_ACC) / _k
        kval_dec = self.get_register(SpinRegister.KVAL_DEC) / _k
        return kval_hold, kval_run, kval_acc, kval_dec

    def set_kval(
        self,
        kval_hold: float | None = None,
        kval_run: float | None = None,
        kval_acc: float | None = None,
        kval_dec: float | None = None,
    ) -> None:
        """
        Set the KVAL registers.
        The KVAL_HOLD register contains the KVAL value assigned to the PWM modulators
        when the motor is stopped (compensation excluded).
        The KVAL_RUN register contains the KVAL value assigned to the PWM modulators
        when the motor is running at constant speed (compensation excluded).
        The KVAL_ACC register contains the starting KVAL value that can be assigned to the PWM
        modulators during acceleration (compensation excluded).
        The KVAL_DEC register contains the starting KVAL value that can be assigned to the PWM
        modulators during deceleration (compensation excluded).

        The available range is from 0 to 0.996 x VS with a resolution of 0.004 x VS (Voltage Source)
        """
        _k = 256.0
        if kval_hold:
            self.set_register(SpinRegister.KVAL_HOLD, int(kval_hold * _k))
        if kval_run:
            self.set_register(SpinRegister.KVAL_RUN, int(kval_run * _k))
        if kval_acc:
            self.set_register(SpinRegister.KVAL_ACC, int(kval_acc * _k))
        if kval_dec:
            self.set_register(SpinRegister.KVAL_DEC, int(kval_dec * _k))

    def get_bemf(self) -> (float, float, float, float):
        """
        Read BEMF registers.
        Using the speed information, a compensation curve is added to the amplitude of the voltage
        waveform applied to the motor winding in order to compensate the BEMF variations during
        acceleration and deceleration.

        The INT_SPEED register contains the speed value at which the BEMF compensation curve changes slope.
        The ST_SLP register contains the BEMF compensation curve slope used when the speed is lower than the INT_SPEED.
        The FN_SLP_ACC register contains the BEMF compensation curve slope used when the speed is greater than
        the INT_SPEED during acceleration.
        The FN_SLP_DEC register contains the BEMF compensation curve slope used when
        the speed is greater than the INT_SPEED during deceleration.
        :return: INT_SPEED, ST_SLP, FN_SLP_ACC, FN_SLP_DEC
        """
        _speed_k = 2**-26
        _slope_k = 0.0015
        int_speed = (
            self.get_register(SpinRegister.INT_SPEED) * _speed_k / self._TICK_SECONDS
        )
        st_slp = self.get_register(SpinRegister.ST_SLP) * _slope_k
        fn_slp_acc = self.get_register(SpinRegister.FN_SLP_ACC) * _slope_k
        fn_slp_dec = self.get_register(SpinRegister.FN_SLP_DEC) * _slope_k
        return int_speed, st_slp, fn_slp_acc, fn_slp_dec

    def set_bemf(
        self,
        int_speed: float | None = None,
        st_slp: float | None = None,
        fn_slp_acc: float | None = None,
        fn_slp_dec: float | None = None,
    ):
        """
        Set BEMF registers.
        Using the speed information, a compensation curve is added to the amplitude of the voltage
        waveform applied to the motor winding in order to compensate the BEMF variations during
        acceleration and deceleration.

        :param int_speed: The speed value at which the BEMF compensation curve changes slope.
        :param st_slp: The BEMF compensation curve slope used when the speed is lower than the INT_SPEED.
        :param fn_slp_acc: The BEMF compensation curve slope used when the speed is greater than
        the INT_SPEED during acceleration.
        :param fn_slp_dec: The BEMF compensation curve slope used when the speed is greater than
        the INT_SPEED during deceleration.

        :return: None
        """
        _speed_k = 2**-26
        _slope_k = 0.0015

        if int_speed:
            self.set_register(
                SpinRegister.INT_SPEED, int(int_speed / _speed_k * self._TICK_SECONDS)
            )
        if st_slp:
            self.set_register(SpinRegister.ST_SLP, int(st_slp / _slope_k))
        if fn_slp_acc:
            self.set_register(SpinRegister.FN_SLP_ACC, int(fn_slp_acc / _slope_k))
        if fn_slp_dec:
            self.set_register(SpinRegister.FN_SLP_DEC, int(fn_slp_dec / _slope_k))

    def get_k_therm(self) -> float:
        """
        The K_THERM register contains the value used by the winding resistance thermal drift compensation system.
        :return: K_THERM
        """
        _k = 0.03125
        return self.get_register(SpinRegister.K_THERM) * _k + 1.0

    def set_k_therm(self, k_therm: float) -> None:
        """
        The K_THERM register contains the value used by the winding resistance thermal drift compensation system.
        :return: None
        """
        _k = 0.03125
        value = int((k_therm - 1.0) / _k)
        self.set_register(SpinRegister.K_THERM, value)

    @property
    def adc_out(self) -> float:
        """
        Read the ADC out register.
        The ADC_OUT register contains the result of the analog-to-digital conversion of the ADCIN
        pin voltage; the result is available even if the supply voltage compensation is disabled.
        :return: ADC_OUT as a value between 0.0 and 1.0 in 5-bit resolution.
        """
        return self.get_register(SpinRegister.ADC_OUT) / 32.0

    def get_ocd_th(self) -> float:
        """
        Read the OCD_TH register.
        The OCD_TH register contains the over current threshold value.
        The available range is from 375 mA to 6 A, in steps of 375 mA.
        :return: OCD_TH in A
        """
        _k = 0.375
        return self.get_register(SpinRegister.OCD_TH) * _k + _k

    def set_ocd_th(self, ocd_th: float) -> None:
        """
        Set the OCD_TH register.
        The OCD_TH register contains the over current threshold value.
        The available range is from 375 mA to 6 A, in steps of 375 mA.
        :param ocd_th: OCD_TH in A
        :return: None
        """
        _k = 0.375
        self.set_register(SpinRegister.OCD_TH, int((ocd_th - _k) / _k))

    def get_stall_th(self) -> float:
        """
        Read the STALL_TH register.
        The STALL_TH register contains the stall detection threshold value.
        The available range is from 31.25 mA to 4 A with a resolution of 31.25 mA.
        :return: STALL_TH in A
        """
        _k = 0.03125
        return self.get_register(SpinRegister.STALL_TH) * _k + _k

    def set_stall_th(self, stall_th: float) -> None:
        """
        Set the STALL_TH register.
        The STALL_TH register contains the stall detection threshold value.
        The available range is from 31.25 mA to 4 A with a resolution of 31.25 mA.
        :param stall_th: STALL_TH in A
        :return: None
        """
        _k = 0.03125
        self.set_register(SpinRegister.STALL_TH, int((stall_th - _k) / _k))

    def get_micro_step(self) -> int:
        """
        Read the low part of the STEP_MODE register.

        """
        return 2 ** (self.get_register(SpinRegister.STEP_MODE) & 0x07)

    def set_micro_step(self, micro_step: int) -> None:
        """
        Set the low part of the STEP_MODE register.
        :param micro_step: Step value as 1 / value
        """
        try:
            step_value = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6, 128: 7}
            self.set_register(SpinRegister.STEP_MODE, step_value[micro_step])
        except KeyError:
            raise ValueError(
                "Invalid micro_step value. Must be 1, 2, 4, 8, 16, 32, 64 or 128"
            )

    def reset_position(self) -> None:
        """
        The ResetPos command resets the ABS_POS register to zero.
        The zero position is also defined as HOME position
        """
        with self.lock:
            self._writeCommand(SpinCommand.ResetPos)

    def reset_device(self) -> None:
        """
        Reset device.
        :return: None
        """
        with self.lock:
            self._writeCommand(SpinCommand.ResetDevice)

    def set_register(self, register: SpinRegister, value: int) -> None:
        """
        Set the specified register to the given value
        :register: The register location
        :value: Value register should be set to
        """
        with self.lock:
            self._writeCommand(SpinCommand.ParamSet, option=register, payload=value)

    def get_register(self, register: SpinRegister) -> int:
        """
        Fetches a register's contents and returns the current value

        :register: Register location to be accessed
        :returns: Value of specified register

        """
        with self.lock:
            self._writeCommand(SpinCommand.ParamGet, option=register)
            return self._writeMultiple([0x00] * register.size)

    def go_until(
        self,
        set_mark: bool = False,
        direction: SpinDirection | None = None,
        speed: float = 100.0
    ) -> None:
        """
        Go until switch turn on event.
        This is used to set the home or mark positions
        :param set_mark: Set to True to set mark instead of resetting the position register.
        :param direction: Direction to move.
        :param speed: Speed of the movement.
        """
        if speed < 0.0 or speed > self.max_steps_per_second:
            raise ValueError("Speed must be between 0.0 and max_steps_per_second")

        if isinstance(direction, SpinDirection):
            self.direction = direction

        act = SET_MARK_FLAG if set_mark else 0
        option = act | self._direction
        _k = 2 ** -28
        payload = int(speed / _k * self._TICK_SECONDS)
        with self.lock:
            self._writeCommand(SpinCommand.GoUntil, option=option, payload=payload)

    def release_switch(
        self, set_mark: bool = False, direction: SpinDirection | None = None
    ) -> None:
        """
        Move until the switch is released.
        This is used in combination with the go_until to get very accurate home or mark positions
        """
        if isinstance(direction, SpinDirection):
            self.direction = direction
        act = SET_MARK_FLAG if set_mark else 0
        option = act | self._direction
        with self.lock:
            self._writeCommand(SpinCommand.ReleaseSw, option=option)

    def move(self, steps: int, direction: SpinDirection | None = None) -> None:
        """
        Move motor n steps
        :steps: Number of (micro)steps to take
        """
        if steps < 0:
            raise ValueError("Steps cannot be negative")
        if steps > self.max_steps:
            raise ValueError("Steps cannot be greater than MaxSteps")

        if isinstance(direction, SpinDirection):
            self.direction = direction
        with self.lock:
            self._writeCommand(SpinCommand.Move, option=self._direction, payload=steps)

    def go_to(self, position: int) -> None:
        """
        The GoTo command produces a motion to ABS_POS absolute position through the shortest path.
        The ABS_POS value is always in agreement with the selected step mode;
        the parameter value unit is equal to the selected step mode (full, half, quarter, etc.).
        The GoTo command keeps the BUSY flag low until the target position is reached.
        This command can be given only when the previous motion command has been completed (BUSY flag released).
        :param position: Absolute position relative to ABS_POS
        :return: None
        """
        with self.lock:
            self._writeCommand(SpinCommand.GoTo, payload=encode_twos_complement(position, 22))

    def go_home(self) -> None:
        """
        The GoHome command produces a motion to the HOME position (zero position) via the shortest path.
        Note that this command is equivalent to the “GoTo(0…0)” command.
        This command can be given only when the previous motion command has been completed (BUSY flag released).
        :return: None
        """
        with self.lock:
            self._writeCommand(SpinCommand.GoHome)

    def go_mark(self) -> None:
        """
        The GoMark command produces a motion to the MARK position performing the minimum path.
        """
        with self.lock:
            self._writeCommand(SpinCommand.GoMark)

    def run(self, speed: float, direction: SpinDirection | None = None) -> None:
        """
        Run the motor at the given steps per second
        :param speed: Full steps per second up to 15 625.
        :param direction: Direction to move
        :return: None
        """
        if speed < 0.0 or speed > self.max_steps_per_second:
            raise ValueError("Speed must be between 0.0 and max_steps_per_second")

        if isinstance(direction, SpinDirection):
            self.direction = direction

        _k = 2**-28
        payload = int(speed / _k * self._TICK_SECONDS)
        with self.lock:
            self._writeCommand(SpinCommand.Run, option=self._direction, payload=payload)

    def hard_hiz(self) -> None:
        """
        Stop motors abruptly, release holding current.
        :return: None
        """
        with self.lock:
            self._writeCommand(SpinCommand.HiZHard)

    def soft_hiz(self) -> None:
        """
        Stop motors, release holding current.
        """
        with self.lock:
            self._writeCommand(SpinCommand.HiZSoft)

    def hard_stop(self) -> None:
        """Stop motors abruptly, maintain holding current"""
        with self.lock:
            self._writeCommand(SpinCommand.HardStop)

    def soft_stop(self) -> None:
        """
        Stop motors, maintain holding current
        """
        with self.lock:
            self._writeCommand(SpinCommand.SoftStop)

    def get_status(self) -> SpinStatus:
        """Get status register
        Resets alarm flags.
        Does not reset HiZ
        :returns: Status enum.

        """
        with self.lock:
            self._writeCommand(SpinCommand.StatusGet)
            # STEP_LOSS_B, STEP_LOSS A, OCD, TH_SD, TH_WRN, UV_LO, BUSY are active low.
            # Invert them to get usable status flags
            raw_status = self._writeMultiple([0x00] * SpinCommand.StatusGet.size)
            return spin_status_factory(raw_status)

    @property
    def status(self) -> SpinStatus:
        """
        Read status register without clearing warning flags.
        Does not clear status flags.
        :return:
        """
        return spin_status_factory(self.get_register(SpinRegister.STATUS))

    def is_busy(self) -> bool:
        """
        Checks busy status of the device.
        Does not clear status flags.
        :return: True, if the device is busy, else False.
        """
        # We use getRegister instead of getStatus
        # So as not to clear any warning flags
        return SpinStatus.Busy in self.status

    def _write(self, data: int) -> int:
        """Write a single byte to the device.

        :data: A single byte representing a command or value
        :return: Returns response byte
        """
        if data < 0x00 or data > 0xFF:
            raise ValueError("Data must be between 0x00 and 0xFF")

        buffer = [SpinCommand.Nop.value] * self._total_devices
        buffer[self._position] = data

        response = self._spi_transfer(buffer)

        return response[self._position]

    def _writeMultiple(self, data: list[int]) -> int:
        """
        Write each byte in a list to device.
        Used to combine calls to _write.

        :data: List of single byte values to send
        :return: Response bytes as int
        """
        response = [self._write(data_byte) for data_byte in data]
        return to_int(response)

    def _writeCommand(
        self,
        command: SpinCommand,
        option: int | None = None,
        payload: int | None = None,
    ) -> int:
        """Write command to device with payload (if any)

        :command: Command to write
        :option: Option to merge with command byte
        :payload: Payload (if any)
        :payload_size: Payload size in bytes
        :return: Response bytes as int
        """
        if option:
            response = self._write(command.value | option)
        else:
            response = self._write(command.value)

        if payload is None:
            return response

        # send / get payload
        if command == SpinCommand.ParamSet:
            register = SpinRegister(option)
            payload_size = register.size
        else:
            payload_size = command.size

        return self._writeMultiple(to_byte_array_with_length(payload, payload_size))
