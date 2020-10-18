from pydub import AudioSegment
import os
from weapon_fire_sample import WeaponFireSample
from pydub.playback import play

class SampleManager:
    def __init__(self):
        self.samples = {}

    @staticmethod
    def create():
        return SampleManager()

    def load_files(self, paths):
        for samplePath in paths:
            currentImport = AudioSegment.from_file(samplePath, format="wav")
            sample = WeaponFireSample.create(currentImport, samplePath, os.path.basename(samplePath))
            self.samples[samplePath] = sample
        self.samples = dict(sorted(self.samples.items(), key=lambda x: (x[1].name, x[1].path)))    

    def reload_samples(self):
        for sample_key in self.samples:
            self.samples[sample_key].source_sound = AudioSegment.from_file(self.samples[sample_key].path, format="wav")
            self.samples[sample_key].name = os.path.basename(self.samples[sample_key].path)
        
    def remove_sample(self, sample):
        self.samples = dict(filter(lambda x: x[0] != sample.path, self.samples.items()))
    
    def get_samples_list(self):
        return list(self.samples.values())

    def update_sample(self, sample):
        self.samples[sample.path] = sample

    def clear(self):
        self.samples = {}

