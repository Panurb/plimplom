import os
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import matplotlib.pyplot as plt
from scipy.io import wavfile


NOTES = {'C': 16.35,
         'D': 18.35,
         'E': 20.60,
         'F': 21.83,
         'G': 24.50,
         'A': 27.50,
         'B': 30.87}
SAMPLE_RATE = 44100
BITS = 16


def note_to_frequency(note):
    return NOTES[note[0]] * 2**int(note[1])


def sine(freq, length):
    t = np.linspace(0, length, int(length * SAMPLE_RATE))
    y = np.sin(2 * np.pi * freq * t)
    return y


def square(freq, length):
    return np.sign(sine(freq, length))


def triangle(freq, length):
    return 2 * np.abs(sawtooth(freq, length)) - 1


def sawtooth(freq, length):
    t = np.linspace(0, length, int(length * SAMPLE_RATE))
    return 2 * (freq * t - np.floor(0.5 + freq * t))


def noise(freq, length):
    y = np.random.uniform(-1, 1, int(length * SAMPLE_RATE))
    return y


def boost(y, factor):
    return np.maximum(np.minimum(factor * y, 1), -1)


def normalize(y):
    max_val = np.max(np.abs(y))
    if max_val:
        return y / max_val
    else:
        return y


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


class Synth:
    def __init__(self, shape, frequency, length, envelope, panning):
        self.shape = shape
        self.envelope = envelope

        self.frequency = frequency
        self.length = length
        self.envelope = envelope
        self.panning = panning

    def get_waveform(self, note):
        if self.frequency is not None:
            freq = self.frequency
        else:
            freq = note_to_frequency(note)

        if self.envelope is not None:
            env = self.envelope
        else:
            env = 1

        shapes = {'sine': sine,
                  'square': square,
                  'triangle': triangle,
                  'sawtooth': sawtooth,
                  'noise': noise}

        left = env * shapes[self.shape](freq, self.length) * min((1 - self.panning), 1)
        right = env * shapes[self.shape](freq, self.length) * min((1 + self.panning), 1)
        
        return np.column_stack([left, right])


class Channel:
    def __init__(self, name, length, bpm, synths, patterns):
        self.name = name
        self.length = length
        self.bpm = bpm
        self.synths = synths
        self.patterns = patterns

        self.quarter_note = 0.25 * 60 / self.bpm * SAMPLE_RATE
        self.duration = self.length / (self.bpm / 4 / 60)

        self.arrangement = []

    def get_waveform(self):
        waveform = np.zeros([int(self.duration * SAMPLE_RATE), 2])
        for i, p in enumerate(self.arrangement):
            if p == 0:
                continue

            pattern = self.patterns[p - 1]

            for j in range(4 * 16):
                note = pattern[int(j % len(pattern))]
                if note == '':
                    continue
                    
                for s in self.synths:
                    y = s.get_waveform(note)

                    start = int((4 * 16 * i + j) * self.quarter_note)
                    end = int(start + len(y))

                    if end > self.duration * SAMPLE_RATE:
                        break

                    waveform[start:end] += y

        return waveform


class Track:
    def __init__(self, name):
        self.name = name
        self.channels = dict()
        self.length = 0

        with open(f'tracks/{self.name}.txt') as file:
            lines = file.readlines()
            self.bpm = int(lines[0])

            arrangements = dict()
            i = 1
            for line in lines[1:]:
                i += 1

                if not line.strip():
                    break

                name, *arrangement = line.split()
                arrangements[name] = [int(x.replace('-', '0')) for x in arrangement]
                
                self.length = max(self.length, 4 * len(arrangement))
                
            self.duration = self.length / (self.bpm / 4 / 60)

            name = ''
            synths = []
            patterns = []

            for line in lines[i:]:
                if '#' in line:
                    continue

                if not line.strip():
                    if name:
                        self.channels[name] = Channel(name, self.length, self.bpm, synths, patterns)
                    name = ''
                    continue

                if not name:
                    name = line.strip()
                    synths = []
                    patterns = []
                else:
                    try:
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
                    except ValueError:
                        shape, freq, length, env, panning = line.split()

                        if freq == '-':
                            frequency = None
                        elif ':' in freq:
                            start, end = [float(x) for x in freq.split(':')]
                            frequency = np.linspace(start, end, int(float(length) * SAMPLE_RATE))
                        else:
                            frequency = float(freq)

                        if env == '-':
                            envelope = None
                        elif ':' in env:
                            start, end = [float(x) for x in env.split(':')]
                            envelope = np.linspace(start, end, int(float(length) * SAMPLE_RATE))
                        else:
                            envelope = float(env)

                        synths.append(Synth(shape, frequency, float(length), envelope, float(panning)))

            for name, arrangement in arrangements.items():
                if name in self.channels:
                    self.channels[name].arrangement = arrangement
                    
    def get_waveform(self):
        waveform = np.zeros([int(self.duration * SAMPLE_RATE), 2])
        
        for c in self.channels.values():
            waveform += c.get_waveform()
            
        return normalize(waveform)
        
    def plot(self):
        waveform = self.get_waveform()
        t = np.linspace(0, self.length, int(self.duration * SAMPLE_RATE))
        plt.plot(t, waveform)
    
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
            print('    play [track name]')
            print('    stop')
            print('    tracks')
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
                if command == 'play':
                    track = Track(filename)
                    track.play()
            except (ValueError, FileNotFoundError):
                print('Invalid track name!')


if __name__ == '__main__':
    main()
