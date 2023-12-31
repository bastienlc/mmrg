import numpy as np
import pytest

from ..implementations.sbm.numpy import NumpyImplementation
from ..implementations.sbm.pytorch import (
    PytorchImplementation,
    PytorchLogImplementation,
)


def b(x, pi):
    return pi**x * (1 - pi) ** (1 - x)


n = 10
Q = 5
X = np.random.random((n, n))
alpha = np.random.random(Q)
alpha = alpha / np.sum(alpha)
pi = np.random.random((Q, Q))
pi = pi @ np.transpose(pi)
pi = pi / np.sum(pi, axis=0)
tau = np.random.rand(n, Q)
tau = tau / np.sum(tau, axis=1)[:, np.newaxis]


@pytest.mark.parametrize(
    "compute_b, input, output",
    [
        (
            NumpyImplementation()._compute_b,
            NumpyImplementation().input,
            NumpyImplementation().output,
        ),
        (
            PytorchImplementation()._compute_b,
            PytorchImplementation().input,
            PytorchImplementation().output,
        ),
    ],
)
def test_compute_b(compute_b, input, output):
    computed_values = output(compute_b(input(X), input(pi)))

    assert computed_values.shape == (n, Q, n, Q)
    for i in range(n):
        for j in range(n):
            for q in range(Q):
                for l in range(Q):
                    if i != j:
                        expected_value = pi[q, l] ** X[i, j] * (1 - pi[q, l]) ** (
                            1 - X[i, j]
                        )
                        assert np.allclose(computed_values[i, q, j, l], expected_value)
                    else:
                        expected_value = 1
                        assert np.allclose(computed_values[i, q, j, l], expected_value)


@pytest.mark.parametrize(
    "fixed_point_iteration, input, output",
    [
        (
            NumpyImplementation().fixed_point_iteration,
            NumpyImplementation().input,
            NumpyImplementation().output,
        ),
        (
            PytorchImplementation().fixed_point_iteration,
            PytorchImplementation().input,
            PytorchImplementation().output,
        ),
        (
            PytorchLogImplementation().fixed_point_iteration,
            PytorchLogImplementation().input,
            PytorchLogImplementation().output,
        ),
    ],
)
def test_fixed_point_iteration(fixed_point_iteration, input, output):
    previous_tau = np.copy(tau)
    computed_tau = output(
        fixed_point_iteration(input(tau), input(X), input(alpha), input(pi))
    )

    for i in range(n):
        for q in range(Q):
            tau[i, q] = alpha[q]
            for j in range(n):
                if i != j:
                    for l in range(Q):
                        tau[i, q] *= b(X[i, j], pi[q, l]) ** previous_tau[j, l]
        tau[i, :] /= np.sum(tau[i, :])

    assert np.allclose(tau, computed_tau)


@pytest.mark.parametrize(
    "e_step, input, output",
    [
        (
            NumpyImplementation().e_step,
            NumpyImplementation().input,
            NumpyImplementation().output,
        ),
        (
            PytorchImplementation().e_step,
            PytorchImplementation().input,
            PytorchImplementation().output,
        ),
        (
            PytorchLogImplementation().e_step,
            PytorchLogImplementation().input,
            PytorchLogImplementation().output,
        ),
    ],
)
def test_e_step(e_step, input, output):
    tau = output(e_step(input(X), input(alpha), input(pi)))

    assert tau.shape == (n, Q)
    assert np.allclose(np.sum(tau, axis=1), np.ones(n))


@pytest.mark.parametrize(
    "m_step, input, output",
    [
        (
            NumpyImplementation().m_step,
            NumpyImplementation().input,
            NumpyImplementation().output,
        ),
        (
            PytorchImplementation().m_step,
            PytorchImplementation().input,
            PytorchImplementation().output,
        ),
        (
            PytorchLogImplementation().m_step,
            PytorchLogImplementation().input,
            PytorchLogImplementation().output,
        ),
    ],
)
def test_m_step(m_step, input, output):
    computed_alpha, computed_pi = m_step(input(X), input(tau))
    computed_alpha = output(computed_alpha)
    computed_pi = output(computed_pi)

    expected_alpha = np.sum(tau, axis=0) / n
    expected_pi = np.zeros((Q, Q))
    for q in range(Q):
        for l in range(Q):
            normalization_factor = 0
            for i in range(n):
                for j in range(n):
                    if i != j:
                        expected_pi[q, l] += tau[i, q] * tau[j, l] * X[i, j]
                        normalization_factor += tau[i, q] * tau[j, l]
            expected_pi[q, l] /= normalization_factor
    assert np.allclose(expected_alpha, computed_alpha)
    assert np.allclose(expected_pi, computed_pi)


@pytest.mark.parametrize(
    "log_likelihood, input, output",
    [
        (
            NumpyImplementation().log_likelihood,
            NumpyImplementation().input,
            NumpyImplementation().output,
        ),
        (
            PytorchImplementation().log_likelihood,
            PytorchImplementation().input,
            PytorchImplementation().output,
        ),
        (
            PytorchLogImplementation().log_likelihood,
            PytorchLogImplementation().input,
            PytorchLogImplementation().output,
        ),
    ],
)
def test_log_likelihood(log_likelihood, input, output):
    computed_ll = output(log_likelihood(input(X), input(alpha), input(pi), input(tau)))

    expected_ll = 0
    for i in range(n):
        for q in range(Q):
            tau_log = tau[i, q] * np.log(tau[i, q])
            tau_log = 0 if np.isnan(tau_log) else tau_log
            expected_ll += tau[i, q] * np.log(alpha[q]) - tau_log
            for j in range(n):
                if i != j:
                    for l in range(Q):
                        expected_ll += (
                            (1 / 2)
                            * tau[i, q]
                            * tau[j, l]
                            * np.log(b(X[i, j], pi[q, l]))
                        )
    assert np.allclose(expected_ll, computed_ll)
