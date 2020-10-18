from weapon_fire_loop_settings import WeaponFireLoopSettings
from weapon_fire_sample import WeaponFireSample
from sample_manager import SampleManager
import shutil, os, numpy, sys, math, json

from pydub import AudioSegment
from pydub.playback import play, _play_with_pyaudio
from pydub.effects import normalize, strip_silence
import winsound

KINDA_BIG_NUMBER = 999999999

class WeaponFireLoopGenerator:
    def __init__(self, log_callback):
        self.current_loop_settings = WeaponFireLoopSettings.create()
        self.sample_manager = SampleManager.create()
        self.current_sample = None
        self.current_preview = None
        self.current_sample_copy = None
        self.log_callback = log_callback

    @staticmethod
    def create(log_callback):
        return WeaponFireLoopGenerator(log_callback)

    @staticmethod
    def prevent_overflow(text, max_width, left_width=5):
        return text if len(text) <= max_width else text[:left_width] + "..." + text[left_width-max_width:]

    def open_files(self, paths):
        self.sample_manager.load_files(paths)
        
        samples = self.sample_manager.get_samples_list()
        if len(samples) > 0:
            self.current_sample = samples[0]

    def set_target_directory(self, path):
        self.current_loop_settings.target_path = path

    def remove_current_sample(self):
        if self.current_sample:
            self.sample_manager.remove_sample(self.current_sample)
            self.current_sample = None

    def set_current_loop_settings(self, nu_settings):
        self.current_loop_settings = nu_settings

    def set_current_sample(self, sample):
        self.current_sample = sample

    def copy_current_sample_props(self):
        if self.current_sample:
            self.current_sample_copy = self.current_sample
    
    def paste_current_sample_props(self):
        if self.current_sample_copy:
            self.current_sample.headroom = self.current_sample_copy.headroom
            self.current_sample.rand_offset_cents = self.current_sample_copy.rand_offset_cents
            self.current_sample.loop_fadeout_start_ms = self.current_sample_copy.loop_fadeout_start_ms
            self.current_sample.loop_fadeout_length_ms = self.current_sample_copy.loop_fadeout_length_ms
            self.current_sample.tail_offset_ms = self.current_sample_copy.tail_offset_ms
            self.current_sample.tail_fadein_ms = self.current_sample_copy.tail_fadein_ms
            self.current_sample.solo = self.current_sample_copy.solo
            self.sample_manager.reload_samples()

    def generate_sequences(self, is_burst, seed, variations=1):
        numpy.random.seed(seed) 
        
        rpm = self.current_loop_settings.rpm_burst if is_burst else self.current_loop_settings.rpm
        count = self.current_loop_settings.burst_count if is_burst else self.current_loop_settings.fire_count
        
        raw_sequences = []

        state = " - Burst ..." if is_burst else " - Auto ..."

        self.log("Generating variations" + state, True)

        for i in range(variations):
            raw_sequences.append((self.generate_list_sequence(count), None))

        audio = []

        avg_boost = 0.0

        self.log("Mixing audio" + state, True)

        for raw in raw_sequences:
            render = self.mix_sequence(raw[0], rpm)
            avg_boost = avg_boost + render[1]
            audio.append(render[0])

        if avg_boost > 0:
            avg_boost = avg_boost / len(raw_sequences)

        return (audio, avg_boost)

    def mix_sequence(self, raw_sequence, rpm):
        count = len(raw_sequence)
        time_between_ms = math.ceil((60.0 * 1000) / rpm) 
        last_sample_len = len(raw_sequence[-1])
        total_length = (count - 1) * time_between_ms + last_sample_len

        mix = AudioSegment.silent(duration=total_length)

        offset = 0
        for sample in raw_sequence:
            mix = mix.overlay(sample, position=offset)
            offset = offset + time_between_ms

            
        max_old = mix.max_dBFS

        if self.current_loop_settings.normalize:
            mix = normalize(mix)
        
        diff = abs(max_old - mix.max_dBFS)

        return (mix, diff)

    def log(self, text, display=False):
        print(text)
        self.log_callback(text)

    def generate_list_sequence(self, count):
        sequence = []

        samples = self.sample_manager.get_samples_list()

        #count = count - 1 # append last shot manually

        solo_samples = list(filter(lambda x: x.solo, samples))

        for i in range(count):
            rand_idx = numpy.random.randint(len(samples))
            rand_seed = numpy.random.randint(KINDA_BIG_NUMBER)
            sample = samples[rand_idx] if len(solo_samples) == 0 else solo_samples[0]
            sequence.append(sample.render_looped(self.current_loop_settings.mono_loop, rand_seed))

        #rand_idx = numpy.random.randint(len(samples))
        #rand_seed = numpy.random.randint(KINDA_BIG_NUMBER)
        #sequence.append(samples[rand_idx].render_default(self.current_loop_settings.mono_loop, rand_seed))

        return sequence


    def generate_tails(self, variations, seed):
        tails = []
        samples = self.sample_manager.get_samples_list()
        for sample in samples:
            for i in range(max(variations, 1)):
                tails.append(sample.render_tail(self.current_loop_settings.mono_tail, numpy.random.randint(KINDA_BIG_NUMBER)))        

        return tails   

    def import_project(self, path):
        f = open(path)
        data = json.load(f)
        self.set_current_loop_settings(WeaponFireLoopSettings.from_dict(data["loop_settings"]))
        self.sample_manager.clear()
        for sample in data["sample_props"]:
            self.sample_manager.update_sample(WeaponFireSample.from_dict(sample))
        
        self.sample_manager.reload_samples()
        
        samples = self.sample_manager.get_samples_list()

        if len(samples) > 0:
            self.current_sample = samples[0]
    
    def export_project(self):
        prefix = self.current_loop_settings.prefix
        path = self.current_loop_settings.target_path + "\\" + prefix

        if not os.path.exists(path):
            os.mkdir(path)

        config_path = path + "\\config.json"

        if os.path.exists(config_path):
            bak_path = path + "\\config.json.bak"
            if os.path.exists(bak_path):
                os.remove(bak_path)
            shutil.copy2(config_path, bak_path)
            os.remove(config_path)
        
        to_dump = {
            "loop_settings": self.current_loop_settings.as_dict(),
            "sample_props": list(map(lambda x: x.as_dict(), self.sample_manager.get_samples_list()))
        }
       
        with open(config_path, 'w') as fp:
            json.dump(to_dump, fp=fp, indent=4, sort_keys=True)

        
    def export_all(self):
        prefix = self.current_loop_settings.prefix
        path = self.current_loop_settings.target_path + "\\" + prefix

        if not os.path.exists(path):
            os.mkdir(path)
        
        path = path + "\\render"
        if os.path.exists(path):
            shutil.rmtree(path)  
        os.mkdir(path)

        variations = self.current_loop_settings.variations

        seed = self.current_loop_settings.seed

        self.log("Generating sounds ...", True)
        self.log("Rendering defaults ...", True)
        defaults = list(map(lambda x: x.render_default(False, 0, True), self.sample_manager.get_samples_list()))
        self.log("Rendering tails ...", True)
        tails = self.generate_tails(variations, seed)
        self.log("Rendering bursts ...", True)
        bursts = self.generate_sequences(True, seed, variations)[0] # make sure burst and are not the same partially
        self.log("Rendering loops ...", True)
        loops = self.generate_sequences(False, seed * 1000, variations)

        volume_boost_loop = loops[1]

        if volume_boost_loop > 0:
            self.log("Adjusting volumes (tails, defaults) ...", True)
            tails = list(map(lambda tail: tail + min(-tail.max_dBFS - 0.01, volume_boost_loop), tails))
            defaults = list(map(lambda default: default + min(-default.max_dBFS - 0.01, volume_boost_loop), defaults))

        self.log("Exporting files ...", True)

        prefix = self.current_loop_settings.prefix

        self.log("Exporting defaults ...", True)
        for i in range(len(defaults)):
            self.export_audio_segment(path, defaults[i], prefix + "_default_" + str(i))

        self.log("Exporting tails ...", True)
        for i in range(len(tails)):
            self.export_audio_segment(path, tails[i], prefix + "_tail_" + str(i))
        
        self.log("Exporting bursts ...", True)
        for i in range(len(bursts)):
            self.export_audio_segment(path, bursts[i], prefix + "_burst_" + str(i))

        self.log("Exporting loops ...", True)
        for i in range(len(loops[0])):
            self.export_audio_segment(path, loops[0][i], prefix + "_loop_" + str(i))
        
        self.log("Ready", True)

    def render_preview_burst(self):
        if len(self.sample_manager.get_samples_list()) > 0:
            self.log("Rendering preview burst ...", True)
            seed = self.current_loop_settings.seed
            bursts = self.generate_sequences(True, seed)
            self.current_preview = bursts[0][0]
            self.log("Ready", True)

    def render_preview_loop(self):
        if len(self.sample_manager.get_samples_list()) > 0:
            self.log("Rendering preview loop ...", True)
            seed = self.current_loop_settings.seed
            bursts = self.generate_sequences(False, seed)
            self.current_preview = bursts[0][0]
            self.log("Ready", True)
    
    def play_preview(self):
        if self.current_preview:
            self.play_audio(self.current_preview)

    def reload_samples(self):
        self.log("Reloading samples ...", True)
        self.sample_manager.reload_samples()
        samples = self.sample_manager.get_samples_list()
        if len(samples) > 0:
            self.current_sample = samples[0]
        self.log("Ready", True)

    def change_path_current_sample(self, path):
        if self.current_sample:
            self.current_sample.path = path
            self.sample_manager.update_sample(self.current_sample)
            self.sample_manager.reload_samples()

    def play_audio(self, audio):
        self.export_audio_segment(self.current_loop_settings.target_path, audio, "preview_temp")
        path = self.current_loop_settings.target_path + "\\preview_temp.wav"
        log_path = WeaponFireLoopGenerator.prevent_overflow(path, 44) # prevent overflow 
        self.log("Playback " + log_path, True)
        winsound.PlaySound(path, winsound.SND_FILENAME)
        self.log("Ready", True)  

    def export_audio_segment(self, path, audio_segment, name):
        target_file = path + "\\" + name + ".wav"
        audio_segment.export(target_file, format="wav")
        log_path = WeaponFireLoopGenerator.prevent_overflow(target_file, 44) # prevent overflow
        self.log("Exported: " + log_path)

    def play_current_loop_sample(self):
        if self.current_sample:
            self.play_audio(self.current_sample.render_looped(self.current_loop_settings.mono_loop, numpy.random.randint(KINDA_BIG_NUMBER)))

    def play_current_tail_sample(self):
        if self.current_sample:
            self.play_audio(self.current_sample.render_tail(self.current_loop_settings.mono_tail, numpy.random.randint(KINDA_BIG_NUMBER)))

if __name__ == '__main__':
    import weapon_fire_loop_generator_ui
    weapon_fire_loop_generator_ui.vp_start_gui()
