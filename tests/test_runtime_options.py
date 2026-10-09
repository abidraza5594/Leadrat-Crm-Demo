import pytest
from slm.runtime_options import choose_precision

def test_four_gb_device_can_use_fp16_after_cuda_initialization():
    assert choose_precision(3300*1024**2)=='float16'

def test_existing_gpu_workload_preserves_lower_memory_option():
    assert choose_precision(2400*1024**2)=='nf4-float16'

def test_explicit_operator_mode_is_preserved_and_invalid_modes_fail():
    assert choose_precision(4000*1024**2,'nf4-float16')=='nf4-float16'
    with pytest.raises(ValueError):choose_precision(4000*1024**2,'fp6')
