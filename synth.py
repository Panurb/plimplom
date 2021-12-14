import numpy as np


NOTES = {'C': 16.35,
         'D': 18.35,
         'E': 20.60,
         'F': 21.83,
         'G': 24.50,
         'A': 27.50,
         'B': 30.87}
SAMPLE_RATE = 22500


def note_to_frequency(note):
    return NOTES[note[0]] * 2**int(note[1])
    
    
def sine(freq, length):
    t = np.linspace(0, length, int(length * SAMPLE_RATE))
    y = np.sin(2 * np.pi * freq * t)
    for i in range(2, 7):
        y += 2**-i * np.sin(2 * np.pi * freq * t * i)
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
