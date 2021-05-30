# README #

Tracks are defined in a custom txt format. They are read in as a numpy array and played using the sounddevice module.

### Track file structure ###
[bpm]\
[channel name] [pattern number] ... [pattern number]\
...\
[channel name] [pattern number] ... [pattern number]\

[channel name]\
[synth shape] [frequency] [length] [volume] [panning]\
...\
[synth shape] [frequency] [length] [volume] [panning]\
[pattern number] [note][octave] ... [note][octave] [interval]\
...\
[pattern number] [note][octave] ... [note][octave] [interval]

### Synth shape ###
Possible values are:
* sine
* square
* triangle
* sawtooth
* noise

### Frequency ###
Frequency of notes in Herz.\
Can also be given as [start frequency]:[end frequency]\
Use - to have individual note frequencies.

### Length ###
Length of one note in seconds.

### Volume ###
Allowed values: 0 - 1\
Can also be given as [start volume]:[end volume]

### Note interval ###
Blank for quarter notes\
\* for half notes\
\*\* for full notes
