"""Precision policy for this fixed 1.5B local deployment."""

def choose_precision(free_bytes,requested='auto'):
    if requested not in {'auto','float16','nf4-float16'}:
        raise ValueError('BEACON_MODEL_PRECISION must be auto, float16 or nf4-float16')
    if requested!='auto':return requested
    # The RTX 2050 reports about 3300 MiB free after CUDA initialization.
    # The earlier 3.6 GiB threshold always forced slow NF4 on that device.
    # FP16 completed the same adapter workload in live comparisons. Keep a
    # lower-memory mode available when another GPU workload is already active.
    return 'float16' if free_bytes >= 3.125*1024**3 else 'nf4-float16'
