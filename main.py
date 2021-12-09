from synth import Synth, SAMPLE_RATE
from filter import Filter, normalize, low_pass

import os
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy.fft import fft, ifft, fftfreq


BITS = 16
BEATS_PER_BAR = 4


def notes_to_quarter_notes(notes):
    notes2 = []

    for n in notes:
        notes2 += [n] + 3 * ['']

    return notes2


def half_notes_to_quarter_notes(notes):
    notes2 = []

    for n in notes:
        notes2 += [n, '']

    return notes2


class Channel:
    def __init__(self, name, length, bpm, synths, patterns):
        self.name = name
        self.length = length
        self.bpm = bpm
        self.synths = synths
        self.patterns = patterns

        self.quarter_note = 0.25 * 60 / self.bpm * SAMPLE_RATE
        self.duration = self.length / (self.bpm / BEATS_PER_BAR / 60)

        self.arrangement = []

    def get_waveform(self):
        waveform = np.zeros([int(self.duration * SAMPLE_RATE), 2])
        for i, p in enumerate(self.arrangement):
            if p == 0:
                continue

            pattern = self.patterns[p - 1]

            for j in range(BEATS_PER_BAR * 16):
                note = pattern[int(j % len(pattern))]
                if note == '':
                    continue
                    
                for s in self.synths:
                    y = s.get_waveform(note)

                    start = int((BEATS_PER_BAR * 16 * i + j) * self.quarter_note)
                    end = int(start + len(y))

                    if end > self.duration * SAMPLE_RATE:
                        break

                    waveform[start:end] += y

        return waveform


class Track:
    def __init__(self, name):
        self.name = name
        self.channels = dict()
        self.filters = dict()
        self.length = 0

        file = open(f'tracks/{self.name}.txt')
        lines = [l for l in file.readlines() if '#' not in l]
        file.close()
        
        self.bpm = int(lines[0])

        arrangements = dict()
        i = 1
        for line in lines[1:]:
            i += 1

            if not line.strip():
                break

            name, *arrangement = line.split()
            arrangements[name] = [int(x.replace('-', '0')) for x in arrangement]
            
            self.length = max(self.length, BEATS_PER_BAR * len(arrangement))
            
        self.duration = self.length / (self.bpm / BEATS_PER_BAR / 60)

        name = ''
        synths = []
        patterns = []

        for line in lines[i:]:
            if not line.strip():
                if name:
                    if name[0] == '/':
                        self.filters[name] = Filter(
                            name, self.length, self.bpm, synths, patterns)
                    else:
                        self.channels[name] = Channel(
                            name, self.length, self.bpm, synths, patterns)
                name = ''
                continue

            if not name:
                name = line.strip()
                synths = []
                patterns = []
            elif line[0].isdigit():
                int(line.split()[0])
                notes = []

                for n in line.split()[1:]:
                    if n == '*':
                        notes = half_notes_to_quarter_notes(notes)
                    elif n == '**':
                        notes = notes_to_quarter_notes(notes)
                    elif n == '--':
                        notes.append('')
                    else:
                        notes.append(n)

                patterns.append(notes)
            else:
                if name[0] == '/':
                    synths.append(line.strip())
                else:
                    shape, freq, length, env, panning = line.split()
                    length = float(length)

                    if freq == '-':
                        frequency = None
                    elif ':' in freq:
                        start, end = [float(x) for x in freq.split(':')]
                        frequency = np.linspace(start, end, int(length * SAMPLE_RATE))
                    else:
                        frequency = float(freq)

                    if env == '-':
                        envelope = None
                    elif ':' in env:
                        start, end = [float(x) for x in env.split(':')]
                        envelope = np.linspace(start, end, int(length * SAMPLE_RATE))
                    else:
                        envelope = float(env)

                    synths.append(Synth(shape, frequency, length, envelope, float(panning)))

        for name, arrangement in arrangements.items():
            if name in self.channels:
                self.channels[name].arrangement = arrangement
            elif name in self.filters:
                self.filters[name].arrangement = arrangement
                    
    def get_waveform(self):
        waveform = np.zeros([int(self.duration * SAMPLE_RATE), 2])
        
        for name, channel in self.channels.items():
            wf = channel.get_waveform()
            for filter in self.filters.values():
                if name in filter.channels:
                    wf = low_pass(wf, filter.get_filter())
            waveform += wf
            
        return normalize(waveform)
        
    def plot(self):
        waveform = self.get_waveform()
        t = np.linspace(0, self.length, int(self.duration * SAMPLE_RATE))
        
        plt.subplot(2, 1, 1)
        plt.plot(t, waveform[:, 0])
        
        plt.subplot(2, 1, 2)
        plt.plot(t, waveform[:, 1])
        
        plt.show()
    
    def play(self):
        waveform = self.get_waveform()
        sd.play(waveform, SAMPLE_RATE)

    def save(self):
        if BITS == 16:
            waveform = np.int16(32767 * self.get_waveform())
        elif BITS == 8:
            waveform = np.uint8(255 * (0.5 * self.get_waveform() + 0.5))
        
        wavfile.write(f'{self.name}.wav', SAMPLE_RATE, waveform)
        #data, samplerate = sf.read(f'{self.name}.wav')
        #sf.write(f'{self.name}.ogg', data, samplerate)


def main():
    while True:
        command = input('> ')
        if command == 'quit':
            break
        elif command == 'help':
            print('Available commands:')
            print('    tracks')
            print('    play [track name]')
            print('    stop')
            print('    plot [track name]')
            print('    save [track name]')
            print('    quit')
        elif command == 'stop':
            sd.stop()
        elif command == 'tracks':
            print('Tracks:')
            for file in os.listdir('tracks'):
                print('    ' + file.strip('.txt'))
        else:
            try:
                command, filename = command.split(' ')
                track = Track(filename)
                if command == 'play':
                    track.play()
                elif command == 'plot':
                    track.plot()
                elif command == 'save':
                    track.save()
            #except ValueError:
            #    print('Invalid command!')
            except FileNotFoundError:
                print('Invalid track name!')


if __name__ == '__main__':
    main()
