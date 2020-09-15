import numpy as np
from lempel_ziv_complexity import lempel_ziv_complexity
from scipy import integrate, stats
import warnings

from src._ErrorHandler import _check_shape_, _check_len_ApEn_
from src._ResultsClasses import ComplexityMeasuresResults


class ComplexityMeasures:
    """
    Class that calculates Complexity Features from spo2 time series.
    Suppose that the data has been preprocessed.

    :param
        signal: 1-d array, of shape (N,) where N is the length of the signal
        CTM_Threshold: Radius of Central Tendency Measure.
        DFA_Window: Length of window to calculate DFA biomarker.
        M_Sampen: Embedding dimension to compute SampEn.
        R_Sampen: Tolerance to compute SampEn.

    :return:
        ComplexityMeasuresResults class containing the following features:
            -	ApEn: Approximate Entropy.
            -   LZ: Lempel-Ziv complexity.
            -	CTM: Central Tendency Measure.
            -   SampEn: Sample Entropy.
            -	DFA: Detrended Fluctuation Analysis.
    """

    def __init__(self, CTM_Threshold=0.25, DFA_Window=20, M_Sampen=3, R_Sampen=0.2):
        self.CTM_Threshold = CTM_Threshold
        self.DFA_Window = DFA_Window
        self.M_Sampen = M_Sampen
        self.R_Sampen = R_Sampen

    def compute(self, signal) -> ComplexityMeasuresResults:
        _check_shape_(signal)

        return ComplexityMeasuresResults(self.__CompApEn(signal), self.__CompLZ(signal),
                                         self.__CompCTM(signal),
                                         self.__CompSampEn(signal),
                                         self.__CompDFA(signal))

    def __CompApEn(self, signal):
        # Reference: Utility of Approximate Entropy From Overnight Pulse Oximetry Data
        #               in the Diagnosis of the Obstructive Sleep Apnea Syndrome
        signal = np.array(signal)
        signal = signal[np.logical_not(np.isnan(signal))]

        phi_m = self.__ApEN(2, signal)
        phi_m1 = self.__ApEN(3, signal)
        with np.errstate(invalid='ignore'):
            res = phi_m - phi_m1

        return res

    def __ApEN(self, m, signal):
        # Help function of CompApEn
        N = len(signal)
        r = 0.25 * np.nanstd(signal)
        _check_len_ApEn_(N, m)
        C = np.zeros(shape=(N - m + 1))

        res = [signal[i:i + m] for i in range(0, N - m + 1)]
        for i in range(0, N - m + 1):
            C[i] = np.nansum(self.__dist(res[i], res, r)) / (N - m + 1)

        phi_m = np.nansum(np.log(C)) / (N - m + 1)
        return phi_m

    def __dist(self, window1, window2, r):
        # Help function of ApEN_m
        window1 = np.array(window1)
        window2 = np.array(window2)

        with np.errstate(invalid='ignore'):
            return np.nanmax(abs(window1 - window2), axis=1) < r

    def __CompLZ(self, signal):
        # Reference :Non-linear characteristics of blood oxygen saturation from nocturnal oximetry
        #           for obstructive sleep apnoea detection
        median = np.median(signal)
        res = [signal[i] > median for i in range(0, len(signal))]
        byte = [str(int(b is True)) for b in res]
        return lempel_ziv_complexity(''.join(byte))

    def __CompCTM(self, signal):
        # Reference: Non-linear characteristics of blood oxygen saturation from nocturnal oximetry
        #           for obstructive sleep apnoea detection
        res = 0
        for i in range(len(signal) - 2):
            res += self.__dCTM(i, self.CTM_Threshold, signal)
        return res / (len(signal) - 2)

    def __dCTM(self, i, p, signal):
        # Help function of CompCTM
        if np.sqrt(((signal[i + 2] - signal[i + 1]) ** 2) + ((signal[i + 1] - signal[i]) ** 2)) < p:
            return 1
        return 0

    def __CompSampEn(self, signal):
        N = len(signal)
        m = self.M_Sampen
        r = self.R_Sampen

        # Split time series and save all templates of length m
        xmi = np.array([signal[i: i + m] for i in range(N - m)])
        xmj = np.array([signal[i: i + m] for i in range(N - m + 1)])

        # Save all matches minus the self-match, compute B
        with np.errstate(invalid='ignore'):
            B = np.sum([np.sum(np.abs(xmii - xmj).max(axis=1) <= r) - 1 for xmii in xmi])

        # Similar for computing A
        m += 1
        xm = np.array([signal[i: i + m] for i in range(N - m + 1)])

        with np.errstate(invalid='ignore'):
            A = np.sum([np.sum(np.abs(xmi - xm).max(axis=1) <= r) - 1 for xmi in xm])

        # Return SampEn
        return -np.log(A / B)

    def __CompDFA(self, signal):
        n = self.DFA_Window
        y = integrate.cumtrapz(signal - np.nanmean(signal))
        least_square = np.zeros(len(y))

        i = 0
        while i < len(y):
            if i + n > len(y):
                n = len(y) - i
            if n == 1:
                least_square[-1] = y[-1]
                break
            x = np.array(range(0, n))
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                slope, intercept, _, _, _ = stats.linregress(x, y[i:i + n])
            least_square[i:i + n] = slope * x + intercept
            i += n

        return np.sqrt(np.nansum((y - least_square) ** 2) / len(y))