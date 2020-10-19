from pydub import AudioSegment
from pydub.playback import play
from pydub.effects import normalize, strip_silence
import numpy, math, os, sys, json

DEFAULT_HEADROOM = -6
DEFAULT_RAND_OFFSET_CENTS = 24
DEFAULT_LOOP_FADEOUT_START_MS = 120
DEFAULT_LOOP_FADOUT_LENGTH_MS = 48
DEFAULT_TAIL_OFFSET_MS = 36
DEFAULT_TAIL_FADEIN_MS = 30
STRIP_SILENCE_THRESHOLD = -72
MAX_SILENCE_LENGTH = 111
SILENCE = -120

class WeaponFireSample:
    def __init__(self, source_sound, path, name, headroom, rand_offset_cents, loop_fadeout_start_ms, loop_fadeout_length_ms, tail_offset_ms, tail_fadein_ms, solo):
        self.source_sound = source_sound
        self.path = path
        self.name = name 
        self.headroom = headroom
        self.rand_offset_cents = rand_offset_cents
        self.loop_fadeout_start_ms = loop_fadeout_start_ms
        self.loop_fadeout_length_ms = loop_fadeout_length_ms
        self.tail_offset_ms = tail_offset_ms
        self.tail_fadein_ms = tail_fadein_ms
        self.solo = solo
    
    def __str__(self):
        return self.name + ": " + self.path

    def __eq__(self, other):
        return self.path == other.path

    def as_dict(self):
        as_dict = self.__dict__.copy()
        as_dict.pop("source_sound")
        for key in as_dict: 
            if type(as_dict[key]) == numpy.int32: #does not support json 
                as_dict[key] = int(as_dict[key])
        return as_dict

    @staticmethod
    def from_dict(src):

        result = WeaponFireSample.create(None, src["path"], src["name"])

        if "headroom" in src:
            result.headroom = float(src["headroom"])
        
        if "rand_offset_cents" in src:
            result.rand_offset_cents = int(src["rand_offset_cents"])

        if "loop_fadeout_start_ms" in src:
            result.loop_fadeout_start_ms = int(src["loop_fadeout_start_ms"])

        if "loop_fadeout_length_ms" in src:
            result.loop_fadeout_length_ms = int(src["loop_fadeout_length_ms"])

        if "tail_offset_ms" in src:
            result.tail_offset_ms = int(src["tail_offset_ms"])

        if "tail_fadein_ms" in src:
            result.tail_fadein_ms = int(src["tail_fadein_ms"])

        if "solo" in src:
            result.solo = bool(src["solo"])
        
        return result

    @staticmethod
    def create(source_sound, path, name, headroom=DEFAULT_HEADROOM, rand_offset_cents=DEFAULT_RAND_OFFSET_CENTS, loop_fadeout_start_ms=DEFAULT_LOOP_FADEOUT_START_MS, loop_fadeout_length_ms=DEFAULT_LOOP_FADOUT_LENGTH_MS, tail_offset_ms=DEFAULT_TAIL_OFFSET_MS, tail_fadein_ms=DEFAULT_TAIL_FADEIN_MS, solo=False):
        if source_sound:
            len_source = len(source_sound)
            loop_fadeout_start_ms = numpy.clip(loop_fadeout_start_ms, 0, len_source)
            loop_fadeout_length_ms = numpy.clip(loop_fadeout_length_ms, 0, len_source - loop_fadeout_start_ms)
            tail_offset_ms = numpy.clip(tail_offset_ms, 0, len_source)
            tail_fadein_ms = numpy.clip(tail_fadein_ms, 0, len_source - tail_offset_ms)
        return WeaponFireSample(source_sound, path, name, min(headroom, -0.01), abs(rand_offset_cents), loop_fadeout_start_ms, loop_fadeout_length_ms, tail_offset_ms, tail_fadein_ms, solo)

    def set_headroom(self, target):
        self.headroom = min(target, -0.01)

    def random_pitch_from_seed(self, seed):
        numpy.random.seed(seed)
        total_range = 2 * self.rand_offset_cents
        rand_val = numpy.random.randint(total_range)
        return rand_val - (total_range / 2.0)

    def process_render(self, render, seed, skip_pitch=False):
        processed = strip_silence(render, MAX_SILENCE_LENGTH, STRIP_SILENCE_THRESHOLD)
        if not skip_pitch: 
            processed = self.pitch(processed, self.random_pitch_from_seed(seed))
        return processed 

    def pitch(self, audio, cents):
        octaves = cents / 1200.0
        old_sample_rate = audio.frame_rate
        new_sample_rate = int(old_sample_rate * (2.0 ** octaves))

        pitched = audio._spawn(audio.raw_data, overrides={'frame_rate': new_sample_rate})
        pitched = pitched.set_frame_rate(old_sample_rate)
        return pitched

    def render_default(self, mono, seed, skip_pitch=False):
        default = self.source_sound

        default = normalize(default, abs(self.headroom))

        if mono:
            default = default.set_channels(1)

        return self.process_render(default, seed, skip_pitch)

    def render_tail(self, mono, seed):
        tail = self.source_sound

        tail = normalize(tail, abs(self.headroom))

        if mono:
            tail = tail.set_channels(1)

        if self.tail_offset_ms > 0 and self.tail_fadein_ms > 0:
            offset = -numpy.clip(len(tail) - self.tail_offset_ms, 0, len(tail))
            tail = tail[offset:]
            tail = tail.fade(from_gain=SILENCE, start=0, duration=self.tail_fadein_ms)

        return self.process_render(tail, seed)

    def render_looped(self, mono, seed):
        looped = self.source_sound

        looped = normalize(looped, abs(self.headroom))

        if mono:
            looped = looped.set_channels(1)
        
        if self.loop_fadeout_start_ms > 0 and self.loop_fadeout_length_ms > 0:
            looped = looped.fade(to_gain=SILENCE, start=self.loop_fadeout_start_ms, duration=self.loop_fadeout_length_ms)
        
        return self.process_render(looped, seed)
    
    def get_volumes(self, mono=False):
        render = self.render_default(mono, 42, True)
        return (round(render.max_dBFS, 2), round(render.dBFS, 2))

        