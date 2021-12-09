from synth import SAMPLE_RATE

import numpy as np
from scipy.fft import fft, ifft, fftfreq
import matplotlib.pyplot as plt
from numba import njit

BEATS_PER_BAR = 4


def boost(y, factor):
    return np.maximum(np.minimum(factor * y, 1), -1)


def normalize(y):
    max_val = np.max(np.abs(y))
    if max_val:
        return y / max_val
    else:
        return y
    
    
@njit
def low_pass(x, alpha):
    y = np.zeros_like(x)
    y[0] = alpha[0] * x[0]
    for i in range(1, y.shape[0]):
        y[i] = alpha[i] * x[i] + (1 - alpha[i]) * y[i - 1]

    return y
    
    
@njit
def high_pass(x, alpha):
    y = np.zeros_like(x)
    y[0] = alpha[0] * x[0]
    for i in range(1, y.shape[0]):
        y[i] = alpha[i] * x[i] + (1 - alpha[i]) * y[i - 1]

    return y


class Filter:
    def __init__(self, name, length, bpm, channels, patterns):
        self.name = name
        self.length = length
        self.bpm = bpm
        self.channels = channels
        self.patterns = patterns
        self.function = low_pass
        self.quarter_note = 0.25 * 60 / self.bpm * SAMPLE_RATE
        self.duration = self.length / (self.bpm / BEATS_PER_BAR / 60)
        
    def get_filter(self):
        filter = np.ones(int(self.duration * SAMPLE_RATE))
        for i, p in enumerate(self.arrangement):
            if p == 0:
                continue

            pattern = self.patterns[p - 1]

            start = int(4 * 16 * i * self.quarter_note)
            end = start
            start_note = None
            for j in range(4 * 16):
                n = 4 * 16 * i + j
            
                note = pattern[int(j % len(pattern))]
                if note:
                    end = int(min(self.duration * SAMPLE_RATE, 
                                  (n + 4) * self.quarter_note))
                    if start_note is not None:
                        filter[start:end] = np.linspace(start_note, int(note) / 99, 
                                                        end - start)
                        start = end
                    start_note = int(note) / 99

        return filter
