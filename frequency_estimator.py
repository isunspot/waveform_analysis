#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from common import load, analyze_channels
from common import parabolic_polyfit as parabolic
from scikits.audiolab import flacread
from numpy.fft import rfft, irfft
from numpy import argmax, sqrt, mean, diff, log
from matplotlib.mlab import find
from scipy.signal import fftconvolve, blackmanharris, kaiser, gaussian
from time import time
import sys

# I have a modified version for speed from
# http://projects.scipy.org/scipy/browser/trunk/scipy/signal/signaltools.py?rev=5968
from signaltools import fftconvolve

def freq_from_crossings(sig, fs):
    """Estimate frequency by counting zero crossings
    
    Pros: Fast, accurate (increasing with signal length).  Works well for long 
    low-noise sines, square, triangle, etc.
    
    Cons: Doesn't work if there are multiple zero crossings per cycle, 
    low-frequency baseline shift, noise, etc.
    
    """
    # Find all indices right before a rising-edge zero crossing
    indices = find((sig[1:] >= 0) & (sig[:-1] < 0))
    
    # Naive (Measures 1000.185 Hz for 1000 Hz, for instance)
    #crossings = indices
    
    # More accurate, using linear interpolation to find intersample 
    # zero-crossings (Measures 1000.000129 Hz for 1000 Hz, for instance)
    crossings = [i - sig[i] / (sig[i+1] - sig[i]) for i in indices]
    
    # Some other interpolation based on neighboring points might be better. Spline, cubic, whatever
    
    return fs / mean(diff(crossings))

def freq_from_fft(signal, fs):
    """Estimate frequency from peak of FFT
    
    Pros: Accurate, usually even more so than zero crossing counter 
    (1000.000004 Hz for 1000 Hz, for instance).  Due to parabolic interpolation 
    being a very good fit for windowed log FFT peaks?
    https://ccrma.stanford.edu/~jos/sasp/Quadratic_Interpolation_Spectral_Peaks.html
    Accuracy also increases with signal length
    
    Cons: Doesn't find the right value if harmonics are stronger than 
    fundamental, which is common.
    
    """
    # Compute Fourier transform of windowed signal
    windowed = signal * kaiser(len(signal), 100)    #  because 0.001% accuracy just isn't good enough
    f = rfft(windowed)
    # Find the peak and interpolate to get a more accurate peak
    i = argmax(abs(f)) # Just use this for less-accurate, naive version
    true_i = parabolic(log(abs(f)), i)[0]
    
    # Convert to equivalent frequency 
    freq = fs * true_i / len(windowed)
    
    print '%f Hz' % freq
    return freq # Hz

def freq_from_autocorr(sig, fs):
    """Estimate frequency using autocorrelation
    
    Pros: Best method for finding the true fundamental of any repeating wave, 
    even with strong harmonics or completely missing fundamental
    
    Cons: Not as accurate, currently has trouble with finding the true peak
    
    """
    # Calculate autocorrelation (same thing as convolution, but with one input 
    # reversed in time), and throw away the negative lags
    corr = fftconvolve(sig, sig[::-1], mode='full')
    corr = corr[len(corr)/2:]
    
    # Find the first low point
    d = diff(corr)
    start = find(d > 0)[0]
    
    # Find the next peak after the low point (other than 0 lag).  This bit is 
    # not reliable for long signals, due to the desired peak occurring between 
    # samples, and other peaks appearing higher.
    peak = argmax(corr[start:]) + start
    px, py = parabolic(corr, peak)
    
    return fs / px

files = sys.argv[1:]
if files:
    for filename in files:
        try:
            start_time = time()
            analyze_channels(filename, freq_from_fft)
            print '\nTime elapsed: %.3f s\n' % (time() - start_time)

        except IOError:
            print 'Couldn\'t analyze "' + filename + '"\n'
        print ''
else:
    sys.exit("You must provide at least one file to analyze")
raw_input()

"""
obsolete
filename = sys.argv[1]
print 'Reading file "%s"\n' % filename
signal, fs, channels = load(filename)
#plot (signal)

print 'Calculating frequency from FFT:',
start_time = time()
print '%.9f Hz'   % freq_from_fft(signal, fs)
print 'Time elapsed: %.3f s\n' % (time() - start_time)

print 'Calculating frequency from zero crossings:',
start_time = time()
print '%f Hz' % freq_from_crossings(signal, fs)
print 'Time elapsed: %.3f s\n' % (time() - start_time)

print 'Calculating frequency from autocorrelation:',
start_time = time()
print '%f Hz' % freq_from_autocorr(signal, fs)
print 'Time elapsed: %.3f s\n' % (time() - start_time)
"""