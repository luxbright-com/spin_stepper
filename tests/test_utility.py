import pytest

import spin_stepper.spin_device as sd


def test_resize_to_length():
    assert sd.resize_to_length([], 1) == [0]
    assert sd.resize_to_length([1], 0) == []
    assert sd.resize_to_length([1, 2, 3], 3) == [1, 2, 3]
    assert sd.resize_to_length([], 3) == [0, 0, 0]

    with pytest.raises(ValueError):
        sd.resize_to_length([], -1)


def test_to_byte_array():
    assert sd.to_byte_array(0) == [0]
    assert sd.to_byte_array(3) == [3]
    assert sd.to_byte_array(0x1FF) == [1, 255]
    assert sd.to_byte_array(0x100000000) == [1, 0, 0, 0, 0]
