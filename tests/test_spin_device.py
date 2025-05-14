import logging
import threading

import pytest
import time
import spin_stepper as sp
from spin_stepper import SpinDirection, SpinStatus, SpinDevice

logger = logging.getLogger(__name__)

"""
This test requires:
* Two L6470 devices chained together.
* A stepper motor with end switch connected to tha last device (0) in the chain.
"""


def setup_motor(_motor: sp.SpinDevice):
    """
    This is a hook for running tests with motors that can't run with default config.
    """
    _motor.set_acceleration(dec=200, acc=200)
    _motor.set_speed_limits(min_speed=2.0, max_speed=500.0)
    _motor.set_micro_step(16)
    _motor.set_ocd_th(3.0)
    _motor.set_stall_th(1.5)
    _motor.set_kval(kval_hold=0.05, kval_acc=0.1, kval_run=0.1, kval_dec=0.1)


@pytest.fixture
def motor_0() -> sp.SpinDevice:
    st_chain = sp.SpinChain(
        total_devices=2,
        spi_select=(0, 0),
    )
    _motor = st_chain.create(0)  # Last motor in the cain
    _motor.reset_device()
    time.sleep(0.1)
    _motor.hard_hiz()
    yield _motor
    _motor.hard_hiz()


@pytest.fixture
def motor_1() -> sp.SpinDevice:
    st_chain = sp.SpinChain(
        total_devices=2,
        spi_select=(0, 0),
    )
    _motor = st_chain.create(1)  # First motor in the chain.
    _motor.reset_device()
    time.sleep(0.1)
    _motor.hard_hiz()
    yield _motor
    _motor.hard_hiz()


def test_register_enum():
    assert sp.SpinRegister.ACC.value == 0x05
    assert sp.SpinRegister.ACC.size == 2

    assert sp.SpinRegister.STALL_TH.value == 0x14
    assert sp.SpinRegister.STALL_TH.size == 1


def test_get_register(motor_1: SpinDevice):
    assert 0 < motor_1.get_register(sp.SpinRegister.ADC_OUT) < 128
    print(f"\nADC out:{motor_1.get_register(sp.SpinRegister.ADC_OUT)}\n")

    assert 0 < motor_1.get_register(sp.SpinRegister.STEP_MODE) < 9
    print(f"StepMode:{motor_1.get_register(sp.SpinRegister.STEP_MODE)}\n")


def test_set_register(motor_1: SpinDevice):
    old_step_mode = motor_1.get_register(sp.SpinRegister.STEP_MODE)
    motor_1.set_register(sp.SpinRegister.STEP_MODE, 3)
    assert motor_1.get_register(sp.SpinRegister.STEP_MODE) == 3
    motor_1.set_register(sp.SpinRegister.STEP_MODE, old_step_mode)
    assert motor_1.get_register(sp.SpinRegister.STEP_MODE) == old_step_mode


def test_get_status(motor_1: SpinDevice):
    motor_1.get_status()  # clear old warnings
    status = motor_1.get_status()
    logger.info(f"Status:{status.name}")
    assert status is SpinStatus.HiZ


def test_is_busy(motor_1: SpinDevice):
    motor_1.get_status()  # clear old warnings
    assert motor_1.is_busy() is False


def test_abs_pos(motor_1: SpinDevice):
    # this should be 0 after reset
    assert motor_1.abs_pos == 0
    motor_1.move(1000)
    assert motor_1.is_busy() is True

    while motor_1.is_busy():
        time.sleep(0.1)

    assert motor_1.abs_pos == 1000


def test_abs_pos_negative(motor_1: SpinDevice):
    assert motor_1.abs_pos == 0

    motor_1.direction = sp.SpinDirection.Reverse
    motor_1.move(1000)
    assert motor_1.is_busy() is True

    while motor_1.is_busy():
        time.sleep(0.1)

    assert motor_1.abs_pos == -1000


def test_get_speed_limits(motor_1: SpinDevice):
    min_speed, max_speed = motor_1.get_speed_limits()
    assert min_speed == pytest.approx(0.0, abs=0.1)
    assert max_speed == pytest.approx(991.8, abs=15.25)


def test_set_speed_limits(motor_1: SpinDevice):
    min_limit = 1.0
    max_limit = 200.0
    motor_1.set_speed_limits(min_speed=min_limit, max_speed=max_limit)
    min_speed, max_speed = motor_1.get_speed_limits()
    assert min_speed == pytest.approx(min_limit, abs=0.1)
    assert max_speed == pytest.approx(max_limit, abs=15.25)


def test_get_acceleration(motor_1: SpinDevice):
    dec, acc = motor_1.get_acceleration()
    assert dec == pytest.approx(2008.0, abs=15.0)
    assert acc == pytest.approx(2008.0, abs=15.0)


def test_set_acceleration(motor_1: SpinDevice):
    motor_1.set_acceleration(500.0, 600.0)
    dec, acc = motor_1.get_acceleration()
    assert dec == pytest.approx(500, abs=15.0)
    assert acc == pytest.approx(600.0, abs=15.0)

    motor_1.set_acceleration(500.0, 600.0)


def test_get_fs_spd(motor_1: SpinDevice):
    assert motor_1.get_fs_spd() == pytest.approx(602.7, abs=15.25)


def test_set_fs_spd(motor_1: SpinDevice):
    motor_1.set_fs_spd(500.0)
    assert motor_1.get_fs_spd() == pytest.approx(500.0, abs=15.25)


def test_get_kval(motor_1: SpinDevice):
    kval_hold, kval_run, kval_acc, kval_dec = motor_1.get_kval()
    assert kval_hold == pytest.approx(0.16, abs=0.004)
    assert kval_run == pytest.approx(0.16, abs=0.004)
    assert kval_acc == pytest.approx(0.16, abs=0.004)
    assert kval_dec == pytest.approx(0.16, abs=0.004)


def test_set_kval(motor_1: SpinDevice):
    motor_1.set_kval(kval_hold=0.1, kval_run=0.2, kval_acc=0.3, kval_dec=0.4)
    kval_hold, kval_run, kval_acc, kval_dec = motor_1.get_kval()
    assert kval_hold == pytest.approx(0.1, abs=0.004)
    assert kval_run == pytest.approx(0.2, abs=0.004)
    assert kval_acc == pytest.approx(0.3, abs=0.004)
    assert kval_dec == pytest.approx(0.4, abs=0.004)


def test_get_bemf(motor_1: SpinDevice):
    int_speed, st_slp, fn_slp_acc, fn_slp_dec = motor_1.get_bemf()
    assert int_speed == pytest.approx(61.5, abs=0.06)
    assert st_slp == pytest.approx(0.038, abs=0.003)
    assert fn_slp_acc == pytest.approx(0.063, abs=0.003)
    assert fn_slp_dec == pytest.approx(0.063, abs=0.003)


def test_set_bemf(motor_1: SpinDevice):
    motor_1.set_bemf(int_speed=60.0, st_slp=0.1, fn_slp_acc=0.2, fn_slp_dec=0.3)
    int_speed, st_slp, fn_slp_acc, fn_slp_dec = motor_1.get_bemf()
    assert int_speed == pytest.approx(60, abs=0.06)
    assert st_slp == pytest.approx(0.1, abs=0.003)
    assert fn_slp_acc == pytest.approx(0.2, abs=0.003)
    assert fn_slp_dec == pytest.approx(0.3, abs=0.003)


def test_get_k_therm(motor_1: SpinDevice):
    assert motor_1.get_k_therm() == pytest.approx(1.0, abs=0.03)


def test_set_k_therm(motor_1: SpinDevice):
    motor_1.set_k_therm(1.2)
    assert motor_1.get_k_therm() == pytest.approx(1.2, abs=0.03)


def test_get_adc(motor_1: SpinDevice):
    value = motor_1.adc_out
    logger.info(f"ADC: {value}")
    assert 8 / 32 < value < 30 / 32


def test_get_ocd_th(motor_1: SpinDevice):
    assert motor_1.get_ocd_th() == pytest.approx(3.38, abs=0.375)


def test_set_ocd_th(motor_1: SpinDevice):
    motor_1.set_ocd_th(2.0)
    assert motor_1.get_ocd_th() == pytest.approx(2.0, abs=0.375)


def test_get_stall_th(motor_1: SpinDevice):
    assert motor_1.get_stall_th() == pytest.approx(2.03, abs=0.032)


def test_set_stall_th(motor_1: SpinDevice):
    motor_1.set_stall_th(1.0)
    assert motor_1.get_stall_th() == pytest.approx(1.0, abs=0.032)


def test_get_micro_step(motor_1: SpinDevice):
    assert motor_1.get_micro_step() == 128


def test_set_step_mode(motor_1: SpinDevice):
    motor_1.set_micro_step(8)
    assert motor_1.get_micro_step() == 8


def test_set_illegal_tep_mode(motor_1: SpinDevice):
    with pytest.raises(ValueError):
        motor_1.set_micro_step(3)


@pytest.mark.timeout(10)
def test_move(motor_1: SpinDevice):
    setup_motor(motor_1)
    motor_1.move(10000, direction=sp.SpinDirection.Forward)
    assert motor_1.is_busy() is True
    while motor_1.is_busy():
        time.sleep(0.1)

    assert motor_1.abs_pos == 10000

    motor_1.move(8000, direction=sp.SpinDirection.Reverse)
    assert motor_1.is_busy() is True
    while motor_1.is_busy():
        time.sleep(0.1)

    assert motor_1.abs_pos == 2000


@pytest.mark.timeout(10)
def test_go_to(motor_1: SpinDevice):
    motor_1.go_to(10000)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos == 10000

    # negative position
    motor_1.reset_position()
    motor_1.go_to(-1000)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos < 0


@pytest.mark.timeout(10)
def test_go_home(motor_1: SpinDevice):
    motor_1.go_to(10000)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos == 10000

    motor_1.go_home()
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos == 0


@pytest.mark.timeout(10)
def test_go_mark(motor_1: SpinDevice):
    motor_1.mark = 5000
    assert motor_1.mark == 5000
    motor_1.go_mark()
    while motor_1.is_busy():
        time.sleep(0.1)

    assert motor_1.abs_pos == 5000


def test_speed(motor_1: SpinDevice):
    setup_motor(motor_1)
    time.sleep(1.0)
    assert motor_1.speed < 5.0
    motor_1.run(speed=200)
    time.sleep(1.0)
    speed = motor_1.speed
    assert speed > 190
    motor_1.soft_hiz()


@pytest.mark.timeout(10)
def test_reset_position(motor_1: SpinDevice):
    assert motor_1.abs_pos == 0
    motor_1.move(1000)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos == 1000
    motor_1.reset_position()
    assert motor_1.abs_pos == 0


def test_hard_stop(motor_1: SpinDevice):
    motor_1.run(100)
    time.sleep(1.0)
    motor_1.hard_stop()
    assert motor_1.is_busy() is False
    assert sp.SpinStatus.HiZ not in motor_1.get_status()


def test_hard_hiz(motor_1: SpinDevice):
    motor_1.run(100)
    time.sleep(1.0)
    motor_1.hard_hiz()
    assert motor_1.is_busy() is False
    assert sp.SpinStatus.HiZ in motor_1.get_status()


@pytest.mark.timeout(10)
def test_soft_stop(motor_1: SpinDevice):
    setup_motor(motor_1)
    motor_1.run(2000)
    time.sleep(2.0)
    motor_1.soft_stop()
    assert motor_1.is_busy() is True
    assert sp.SpinStatus.HiZ not in motor_1.get_status()
    while motor_1.is_busy():
        time.sleep(0.1)
    assert sp.SpinStatus.HiZ not in motor_1.get_status()


@pytest.mark.timeout(10)
def test_soft_hiz(motor_1: SpinDevice):
    motor_1.run(200)
    time.sleep(1.0)
    motor_1.soft_hiz()
    assert motor_1.is_busy() is True
    while motor_1.is_busy():
        time.sleep(0.1)
    assert sp.SpinStatus.HiZ in motor_1.get_status()


@pytest.mark.timeout(30)
def test_go_until(motor_1: SpinDevice):
    setup_motor(motor_1)
    motor_1.move(2000)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert sp.SpinStatus.SwitchFlag not in motor_1.get_status()

    motor_1.go_until(direction=sp.SpinDirection.Reverse, speed=200)

    while motor_1.is_busy():
        time.sleep(0.1)
    assert sp.SpinStatus.SwitchFlag in motor_1.get_status()
    assert 0 <= motor_1.abs_pos <= 5


@pytest.mark.timeout(60)
def test_go_until_and_release(motor_1: SpinDevice):
    """
    Test homing using a switch.
    First move towards switch for course home position.
    Then move away from switch until released to get accurate home position.
    :param motor:
    :return:
    """
    setup_motor(motor_1)
    motor_1.direction = sp.SpinDirection.Forward
    motor_1.move(20000)
    while motor_1.is_busy():
        time.sleep(0.1)
    motor_1.go_until(direction=sp.SpinDirection.Reverse, speed=200)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert 0 <= motor_1.abs_pos <= 5
    time.sleep(0.1)
    assert sp.SpinStatus.SwitchFlag in motor_1.get_status()

    motor_1.release_switch(direction=sp.SpinDirection.Forward)
    while motor_1.is_busy():
        time.sleep(0.1)
    assert motor_1.abs_pos < 100

    motor_1.move(10000)
    while motor_1.is_busy():
        time.sleep(0.1)
    time.sleep(0.1)
    assert sp.SpinStatus.SwitchFlag not in motor_1.get_status()

    motor_1.go_home()
    while motor_1.is_busy() and time.monotonic():
        time.sleep(0.1)
    assert 0 <= motor_1.abs_pos <= 5


def test_multi_thread(motor_1: SpinDevice):
    def loop(_motor, name):
        while run:
            speed = _motor.speed
            pos = _motor.abs_pos
            status = _motor.status
            logger.info(f"{name} {speed=} ({pos=} {status=})")
            time.sleep(0.001)

    run = True
    setup_motor(motor_1)
    thread1 = threading.Thread(target=loop, args=(motor_1, "thread_1"), daemon=True)
    thread1.start()
    thread2 = threading.Thread(target=loop, args=(motor_1, "thread_2"), daemon=True)
    thread2.start()
    motor_1.run(200, SpinDirection.Forward)
    last_pos = motor_1.abs_pos
    for i in range(100):
        time.sleep(0.05)
        speed = motor_1.speed
        pos = motor_1.abs_pos
        assert pos > last_pos
        last_pos = pos
        logger.info(f"for {speed=} ({pos=})")
    motor_1.soft_hiz()
    run = False
    thread1.join(1.0)
    thread2.join(1.0)


def test_step_modes_speed(motor_1: SpinDevice):
    """
    Speed settings does not depend on micro step mode.
    :param motor:
    :return:
    """
    setup_motor(motor_1)
    speed = 200
    step_modes = [2, 16, 128]

    for step_mode in step_modes:
        motor_1.set_micro_step(step_mode)
        logger.info(f"{motor_1.get_micro_step()} micro steps")
        assert motor_1.get_micro_step() == step_mode
        motor_1.run(speed, SpinDirection.Forward)
        time.sleep(4)
        assert motor_1.speed == pytest.approx(speed, abs=20)
        motor_1.soft_hiz()
        motor_1.run(speed, SpinDirection.Reverse)
        time.sleep(4)
        motor_1.soft_hiz()
        while motor_1.is_busy():
            time.sleep(0.5)


def test_step_modes_move(motor_1: SpinDevice):
    """
    Position and distance settings do depend on micro step mode.
    :param motor:
    :return:
    """
    setup_motor(motor_1)
    motor_1.set_speed_limits(max_speed=500)
    distance = 300
    step_modes = [2, 16, 128]

    for step_mode in step_modes:
        motor_1.set_micro_step(step_mode)
        logger.info(f"{motor_1.get_micro_step()} micro steps")
        assert motor_1.get_micro_step() == step_mode
        motor_1.move(distance * step_mode, SpinDirection.Forward)
        while motor_1.is_busy():
            time.sleep(0.1)
        motor_1.move(distance * step_mode, SpinDirection.Reverse)
        while motor_1.is_busy():
            time.sleep(0.1)
        motor_1.soft_hiz()
        while motor_1.is_busy():
            time.sleep(0.1)


def test_step_clock(motor_0: SpinDevice, motor_1: SpinDevice):
    """
    Test the synchronous drive of two motors using StepClock pin.
    Note that the Busy/Sync out is step frequency / 2
    This only works at low speeds.
    :param motor_0:
    :param motor_1:
    :return:
    """
    time.sleep(2.0)
    micro_step = 64
    move = 200  # one turn
    max_speed = 100  # slow speed
    setup_motor(motor_0)
    setup_motor(motor_1)

    motor_0.set_micro_step(micro_step)
    motor_0.set_sync_out(micro_step, True)
    motor_0.set_speed_limits(1, max_speed)
    motor_0.set_acceleration(dec=100, acc=100)
    motor_1.set_micro_step(micro_step // 2)
    motor_1.set_acceleration(dec=100, acc=100)
    assert motor_0.get_micro_step() == micro_step
    assert motor_1.get_micro_step() == micro_step / 2
    sync_out, flag = motor_0.get_sync_out()
    assert sync_out == micro_step
    assert flag is True

    motor_1.step_clock(direction=sp.SpinDirection.Forward)
    motor_0.move(move * micro_step, SpinDirection.Forward)
    while motor_0.is_busy():
        time.sleep(0.1)
        assert motor_0.abs_pos == pytest.approx(motor_1.abs_pos * 2, abs=16)
    assert motor_0.abs_pos == move * micro_step
    assert motor_1.abs_pos == move * micro_step / 2

    time.sleep(2.0)
    motor_1.step_clock(direction=sp.SpinDirection.Reverse)
    motor_0.move(move * micro_step, SpinDirection.Reverse)
    while motor_0.is_busy():
        time.sleep(0.1)
