import os, sys, json, numpy

DEFAULT_PREFIX = "default"
DEFAULT_SEED = 42
DEFAULT_FIRE_COUNT = 31
DEFAULT_BURST_COUNT = 3
DEFAULT_RPM = 800
DEFAULT_RPM_BURST = 900
DEFAULT_NORMALIZE = True
DEFAULT_MONO_LOOP = True
DEFAULT_MONO_TAIL = False
DEFAULT_VARIATIONS = 3
DEFAULT_TARGET_PATH = os.getcwd() + "\\results"

if not os.path.exists(DEFAULT_TARGET_PATH):
    os.mkdir(DEFAULT_TARGET_PATH)

class WeaponFireLoopSettings:
    def __init__(self, fire_count, burst_count, rpm, rpm_burst, seed, normalize, mono_loop, mono_tail, prefix, target_path, variations):
        self.fire_count = fire_count
        self.burst_count = burst_count
        self.rpm = rpm
        self.rpm_burst = rpm_burst
        self.seed = seed
        self.normalize = normalize
        self.mono_loop = mono_loop
        self.mono_tail = mono_tail
        self.prefix = prefix
        self.target_path = target_path
        self.variations = variations

    @staticmethod
    def create(prefix=DEFAULT_PREFIX, seed=DEFAULT_SEED, fire_count=DEFAULT_FIRE_COUNT, burst_count=DEFAULT_BURST_COUNT, rpm=DEFAULT_RPM, rpm_burst=DEFAULT_RPM_BURST, normalize=DEFAULT_NORMALIZE, mono_loop=DEFAULT_MONO_LOOP, mono_tail=DEFAULT_MONO_TAIL, target_path=DEFAULT_TARGET_PATH, variations=DEFAULT_VARIATIONS):
        return WeaponFireLoopSettings(max(fire_count, 1), max(burst_count, 1), max(rpm, 1), max(rpm_burst, 1), seed, normalize, mono_loop, mono_tail, prefix, target_path, variations)

    def as_dict(self):
        as_dict = self.__dict__
        for key in as_dict: 
            if type(as_dict[key]) == numpy.int32: #does not support json 
                as_dict[key] = int(as_dict[key])
        return as_dict

    @staticmethod
    def from_dict(src):
        result = WeaponFireLoopSettings.create()

        if "fire_count" in src:
            result.fire_count = max(src["fire_count"], 1)

        if "burst_count" in src:
            result.burst_count = max(src["burst_count"], 1)

        if "rpm" in src:
            result.rpm = max(src["rpm"], 1)

        if "rpm_burst" in src:
            result.rpm_burst = max(src["rpm_burst"], 1)

        if "seed" in src:
            result.seed = src["seed"]
        
        if "normalize" in src:
            result.normalize = src["normalize"]

        if "mono_loop" in src:
            result.mono_loop = src["mono_loop"]

        if "mono_tail" in src:
            result.mono_tail = src["mono_tail"]

        if "prefix" in src:
            result.prefix = src["prefix"]

        if "target_path" in src:
            result.target_path = src["target_path"]

        return result

    

