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


def test_decode_two_complement():
    assert sd.decode_twos_complement(0xFF, 8) == -1
    assert sd.decode_twos_complement(1, 8) == 1
    assert sd.decode_twos_complement(0xFF01, 16) == -255
    assert sd.decode_twos_complement(0x0FFF01, 20) == -255
    assert sd.decode_twos_complement(0x3FFF01, 22) == -255

def test_encode_two_complement():
    assert sd.encode_twos_complement(1, 8) == 0x01
    assert sd.encode_twos_complement(-1, 8) == 0xFF
    assert sd.encode_twos_complement(-1, 22) == 0x3FFFFF
    assert sd.encode_twos_complement(-255, 22) ==0x3FFF01
    assert sd.encode_twos_complement(10000, 22) == 10000
