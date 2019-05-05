# -*- coding: utf-8 -*-
import itertools
import numpy as np
import numpy.linalg as nl
import scipy.stats as ss

class MarkovChain:

    def __init__(self, states=None, obs=None, obs_p=None):
        '''Discrete Markov Chain.

        Parameters
        ----------
        states : array_like or numpy ndarray
            State names list.

        obs : array_like or numpy ndarray
            Observed transition frequency matrix.

        obs_p : array_like or numpy ndarray
            Observed transition probability matrix.
        '''

        self.states = np.array(states)
        self.observed_matrix = np.array(obs)
        self.observed_p_matrix = np.array(obs_p)


    def _transition_matrix(self, seq, states):
        '''Calculate a transition frequency matrix.

        Parameters
        ----------
        seq : str or array_like
            A string or an array-like object exposing the array interface and
            containing strings or ints.

        states : numpy ndarray
            Array containing a list of states.

        Returns
        -------
        matrix : numpy ndarray
            Transition frequency matrix.

        '''

        seql = np.array(list(seq))
        matrix = np.zeros((len(states), len(states)))

        for x, y in itertools.product(range(len(states)), repeat=2):
            xid = np.argwhere(seql == states[x]).flatten()
            yid = xid + 1
            yid = yid[yid < len(seql)]
            s = np.count_nonzero(seql[yid] == states[y])
            matrix[x, y] = s

        return matrix


    def n_order_matrix(self, mat=None, order=2):
        '''Create Nth order transition probability matrix.

        Parameters
        ----------
        mat : numpy ndarray
            Observed transition probability matrix.

        order : int, optional
            Order of transition probability matrix to return.
            Default is 2.

        Returns
        -------
        x : numpy ndarray
            Nth order transition probability matrix.
        '''

        return nl.matrix_power(mat if mat else self.observed_p_matrix, order)


    def prob_to_freq_matrix(self, mat=None, row_totals=None):
        '''Calculate a transition frequency matrix given a transition probability
        matrix and row totals. This method is meant to be used to calculate a
        frequency matrix for a Nth order transition probability matrix.

        Parameters
        ----------
        mat : numpy ndarray
            Transition probability matrix.

        row_totals : numpy ndarray
            Row totals of transition frequency matrix.

        Returns
        -------
        x : numpy ndarray
            Transition frequency matrix.
        '''
        _mat = mat if mat else self.observed_p_matrix
        _rt = row_totals if row_totals else self._obs_row_totals
        return _mat * _rt


    def from_data(self, seq):
        '''Infer a Markov chain from data. States, frequency and probability
        matrices are automatically calculated and assigned to as class
        attributes.

        Parameters
        ----------
        seq : numpy ndarray
            A string or an array-like object exposing the array interface and
            containing strings or ints.

        Returns
        -------
        MarkovChain : object
            Trained MarkovChain class instance.
        '''


        # states list
        self.states = np.unique(list(seq))

        # observed transition frequency matrix
        self.observed_matrix = self._transition_matrix(seq, self.states)
        self._obs_row_totals = np.sum(self.observed_matrix, axis=1)

        # observed transition probability matrix
        self.observed_p_matrix = self.observed_matrix / self._obs_row_totals[:, None]

        # expected transition frequency matrix
        self.expected_matrix = ss.contingency.expected_freq(self.observed_matrix)

        return self


    def chisquare(self, obs=None, exp=None, **kwargs):
        '''Wrapper function for carrying out a chi-squared test using
        `scipy.stats.chisquare` method.

        Parameters
        ----------
        obs : numpy ndarray
            Observed transition frequency matrix.

        exp : numpy ndarray
            Expected transition frequency matrix.

        kwargs : optional
            Keyword arguments passed to `scipy.stats.chisquare` method.

        Returns
        -------
        chisq : float or numpy ndarray
            Chi-squared test statistic.

        p : float or numpy ndarray
            P value of the test.
        '''
        _obs = obs if obs else self.observed_matrix
        _exp = exp if exp else self.expected_matrix
        return ss.chisquare(f_obs=_obs, f_exp=_exp, **kwargs)


    def simulate(self, n, tf=None, states=None, start=None, ret='both', seed=None):
        '''Markov chain simulation based on `scipy.stats.multinomial`.

        Parameters
        ----------
        n : int
            Number of states to simulate.

        tf : numpy ndarray
            Transition frequency matrix. If None, `self.observed_matrix`
            attribute is used.

        states : array_like
            List of state names. If None, `self.states` attribute is used.

        start : {None, 'random', str, or int}, optional
            Event to begin with. If `int`, choosed a state by index. If `str`,
            choosed by a state name. If 'random', take a random state. If
            `None`, start with an event with maximum probability.

        ret : {'indices', 'states', 'both'}
            Return state indices if 'indices' is passed. If 'states' is passed,
            return state names. Return both if 'both' is passed.

        seed : None, int, optional
            Random state used to draw random variates. Passed to
            `scipy.stats.multinomial` method.

        Returns
        -------
        x : numpy ndarray
            Sequence of state indices.

        y : numpy ndarray, optional
            Sequence of state names. Returned if `return` arg is set to 'states'
            or 'both'.

        '''

        # matrices init
        if tf is None:
            tf = self.observed_matrix
            fp = self.observed_p_matrix
        else:
            fp = tf / tf.sum(axis=1)[:, None]

        # states init
        if states is None:
            states = self.states
        if not isinstance(states, np.ndarray):
            states = np.array(states)

        # choose a state to begin with
        # `_start` is always an index of state
        if start is None:
            row_totals = tf.sum(axis=1)
            _start = np.argmax(row_totals / tf.sum())
        elif isinstance(start, int):
            _start = start if start < len(states) else len(states)-1
        elif isinstance(start, str):
            _start = np.argwhere(states == start)
        elif start == 'random':
            _start = np.random.randint(0, len(states))

        # simulated sequence init
        seq = np.zeros(n, dtype=np.int)
        seq[0] = _start

        # simulation procedure
        for i in range(1, n):
            _ps = fp[seq[i-1]]
            _sample = np.argmax(ss.multinomial.rvs(1, _ps, 1, random_state=seed))
            seq[i] = _sample

        if ret == 'indices':
            return seq
        elif ret == 'states':
            return states[seq]
        else:
            return seq, states[seq]
