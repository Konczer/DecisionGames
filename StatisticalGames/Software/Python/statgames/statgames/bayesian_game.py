from typing import Dict, Union

import numpy as np
import scipy.special

def bayesiangame_solve(N: int, KA: int, KB: int, M: int):
    """
    Solve the Fisher game problem and calculate equilibrium quantities.

    This function serves as a public interface to solve the Fisher game problem
    by invoking the internal `_fishergame_solve` function.

    Parameters:
    N (int): Number of sampled bits.
    KA (int): Number of 1-s in scenario A.
    KB (int): Number of 1-s in scenario B.
    M (int): Total length of the binary strings.

    Returns:
    dict: A dictionary containing the results:
        - 'P' (float): The probability 0 < P_star < 1.
        - 'P_interval' ([float, float]): The upper and lower bound for P_star
        - 'G' (float): Growth rate in equilibrium.
        - 'p_prime' ({int : float}): Dictionary of equilibrium splitting ratios.

    Raises:
    ValueError: If any parameter is invalid.
    TypeError: If any parameter is not an integer.

    References:
    The concept of the Fisher game is introduced in the following paper:
    Jozsef Konczer, "Statistical Games",  arXiv:2402.15892, 2024.
    Available at: https://arxiv.org/abs/2402.15892
    """

    # Check if all parameters are integers and non-negative
    if not all(isinstance(param, int) for param in [N, KA, KB, M]):
        raise TypeError("All parameters must be integers")
    if not all(param >= 0 for param in [N, KA, KB, M]):
        raise ValueError("All parameters must be non-negative")
    
    # Check if N <= M and KA, KB <= M
    if N > M:
        raise ValueError("N must be less than or equal to M")
    if KA > M:
        raise ValueError("KA must be less than or equal to M")
    if KB > M:
        raise ValueError("KB must be less than or equal to M")

    # Return the output of the internal _fishergame_solve   
    return _bayesiangame_solve(N, KA, KB, M, method="Bisection")

def _bayesiangame_solve(N: int, KA: int, KB: int, M: int, method="bisection"):
    """
    Internal function to calculate Bayesian game equilibrium quantities.

    Parameters:
    N (int): Number of sampled bits.
    KA (int): Number of 1-s in scenario A.
    KB (int): Number of 1-s in scenario B.
    M (int): Total length of the binary strings.

    Returns:
    dict: Contains 'P', 'P_interval', 'G', 'p_prime'.
    """
    
    k_A_minmax = [max(0, N - (M - KA)), min(N, KA)]
    k_B_minmax = [max(0, N - (M - KB)), min(N, KB)]

    k_minmax = [min(k_A_minmax[0], k_B_minmax[0]), max(k_A_minmax[1], k_B_minmax[1])]
    k_AB_minmax = [max(k_A_minmax[0], k_B_minmax[0]), min(k_A_minmax[1], k_B_minmax[1])]

    Z = scipy.special.comb(M, N, exact=True)

    p_A_list = np.array([scipy.special.comb(KA, k, exact=True) * scipy.special.comb(M - KA, N - k, exact=True) for k in range(N + 1)]) / Z
    p_B_list = np.array([scipy.special.comb(KB, k, exact=True) * scipy.special.comb(M - KB, N - k, exact=True) for k in range(N + 1)]) / Z

    HA = -sum(p_A_list[k] * np.log(p_A_list[k]) for k in range(k_A_minmax[0], k_A_minmax[1] + 1))
    HB = -sum(p_B_list[k] * np.log(p_B_list[k]) for k in range(k_B_minmax[0], k_B_minmax[1] + 1))
    
    def g(P):
        return np.log(P / (1 - P)) - HA + HB - sum((p_A_list[k] - p_B_list[k]) * np.log(P * p_A_list[k] + (1 - P) * p_B_list[k]) for k in range(k_minmax[0], k_minmax[1] + 1))

    def next(PLU):
        mean_PLU = np.mean(PLU)
        g_mean_PLU = g(mean_PLU)
        if g_mean_PLU > 0:
            return [PLU[0], mean_PLU]
        elif g_mean_PLU < 0:
            return [mean_PLU, PLU[1]]
        else:
            return [mean_PLU, mean_PLU]

    PLU = [0, 1]
    i = 1
    while i < 10 and PLU[1] - PLU[0] > 1 / 2**10:
        PLU = next(PLU)
        i += 1

    P_star = np.mean(PLU)

    G_star = P_star * np.log(P_star) + (1 - P_star) * np.log(1 - P_star) - (P_star * HA + (1 - P_star) * HB) - \
            sum((P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) * np.log(P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) for k in range(k_minmax[0], k_minmax[1] + 1))

    p_prime_star = {k: P_star * p_A_list[k] / (P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) for k in range(N + 1)}

    return {'P': P_star, 'P_interval': PLU, 'G': G_star, 'p_prime': p_prime_star}

def _binomial_bayesiangame_solve(N: int, xA: float, xB: float, method="bisection"):
    """
    Internal function to calculate Binomial Bayesian game equilibrium quantities.

    Parameters:
    N (int): Number of sampled bits.
    xA (float): Fraction of 1-s in case of scenario A.
    xB (float): Fraction of 1-s in case of scenario B.

    Returns:
    dict: Contains 'P', 'P_interval', 'G', 'p_prime'.
    """

    p_A_list = np.array([scipy.special.comb(N, k, exact=True) * (xA ** k) * ((1 - xA) ** (N - k)) for k in range(N + 1)])
    p_B_list = np.array([scipy.special.comb(N, k, exact=True) * (xB ** k) * ((1 - xB) ** (N - k)) for k in range(N + 1)])

    HA = -sum(p_A_list[k] * np.log(p_A_list[k]) for k in range(N + 1))
    HB = -sum(p_B_list[k] * np.log(p_B_list[k]) for k in range(N + 1))
    
    def g(P):
        return np.log(P / (1 - P)) - HA + HB - sum((p_A_list[k] - p_B_list[k]) * np.log(P * p_A_list[k] + (1 - P) * p_B_list[k]) for k in range(N + 1))

    def next(PLU):
        mean_PLU = np.mean(PLU)
        g_mean_PLU = g(mean_PLU)
        if g_mean_PLU > 0:
            return [PLU[0], mean_PLU]
        elif g_mean_PLU < 0:
            return [mean_PLU, PLU[1]]
        else:
            return [mean_PLU, mean_PLU]

    PLU = [0, 1]
    i = 1
    while i < 10 and PLU[1] - PLU[0] > 1 / 2**10:
        PLU = next(PLU)
        i += 1

    P_star = np.mean(PLU)

    G_star = P_star * np.log(P_star) + (1 - P_star) * np.log(1 - P_star) - (P_star * HA + (1 - P_star) * HB) - \
            sum((P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) * np.log(P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) for k in range(N + 1))

    p_prime_star = {k: P_star * p_A_list[k] / (P_star * p_A_list[k] + (1 - P_star) * p_B_list[k]) for k in range(N + 1)}

    return {'P': P_star, 'P_interval': PLU, 'G': G_star, 'p_prime': p_prime_star}