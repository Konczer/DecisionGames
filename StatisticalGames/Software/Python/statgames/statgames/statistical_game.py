from typing import Dict, Union, List, Tuple

import numpy as np
import scipy.special

def statisticalgame_solve(
    N: int,
    Kx_list: Union[List[int], List[float], np.ndarray],
    M: Union[int, float] = float('inf'),
    gamma: Union[float, int] = 1/2,
    method = "bisection",
    max_iter = float('inf'),
    max_error=1 / 2 ** 10
    # keys: List[str] = "all"
    ) -> Dict[str, Union[float, Tuple[float, float], Dict[int, float]]]:   
    """
    Solves a Statistical game and calculates equilibrium quantities.

    This function serves as a public interface to solve a Statistical game
    by invoking the internal `_statisticalgame_solve` or `_binomial_statisticalgame_solve` function.

    Parameters:
    N (int): Number of sampled bits.
    Kx_list (Union[List[int], List[float], np.ndarray]): A list or array containing two elements:
        [K_A, K_B], pair of integers or [x_A, x_B], pair of floats.
    M (Union[int, float], optional): Total length of the binary strings or float('inf'). 
        If M is a finite integer, then Kx_list contains [K_A, K_B];
        if M is infinite, then Kx_list contains [x_A, x_B].
        Default is float('inf').
    gamma (Union[int, float]): relative risk aversion parameter also known as
        the Arrow-Pratt measure of relative risk aversion

    Returns:
    dict: A dictionary containing the results:
        - 'P' (float): The probability 0 < P_star < 1.
        - 'P_interval' ([float, float]): The upper and lower bound for P_star
        - 'G' (float): Growth rate in equilibrium.
        - 'p_prime' ({int : float}): Dictionary of equilibrium splitting ratios.

    Raises:
    ValueError: If any parameter is invalid.
    TypeError: If any parameter has none appropriate type.

    References:
    The concept of the Fisher game is introduced in the following paper:
    Jozsef Konczer, "Statistical Games",  arXiv:2402.15892, 2024.
    Available at: https://arxiv.org/abs/2402.15892
    
    Example Usage:
    -------------
    Solving a Statistical game with finite M:
    
    >>> result = statisticalgame_solve(1, [0, 1], 2, gamma=0.5)
    >>> print(result)
    {'P': 0.3994140625, 
    'P_interval': [0.3984375, 0.400390625], 
    'U': -0.3999993129521612, 
    'p_prime': {
        0: 0.6388739570095546, 
        1: 0.0}
        }
    
    Solving a Statistical game with infinite M:
    
    >>> result = statisticalgame_solve(10, [0.3, 0.5], gamma=0.5)
    >>> print(result)
    {'P': 0.4951171875, 
    'P_interval': [0.494140625, 0.49609375], 
    'U': -0.38742895605774774, 
    'p_prime': {
        0: 0.9987587334732929, 
        1: 0.9932790709733905, 
        2: 0.9644695967162675, 
        3: 0.832937947072644, 
        4: 0.4780137141353738, 
        5: 0.14398267774885304, 
        6: 0.02996816223631757, 
        7: 0.00564239067955681, 
        8: 0.0010411530573117144, 
        9: 0.0001913948646887022, 
        10: 3.515965218925e-05
        }
    }
    """

    # Check if Kx_list is iterable and attempt to convert it to a list
    if not isinstance(Kx_list, (list, np.ndarray, set, tuple)):
        raise TypeError(f"Kx_list must be an iterable or convertible to a list, got {type(Kx_list)} instead.")
    
    # Converting Kx_list to a list
    try:
        if isinstance(Kx_list, (np.ndarray, set, tuple)):
            Kx_list = list(Kx_list)
    except Exception as e:
        raise TypeError(f"Kx_list conversion to list failed: {e}")

    # Check if Kx_list is a list or array containing two elements
    if len(Kx_list) != 2:
        raise TypeError("Kx_list must be a list or array containing two elements")
    
    # Check if N and M are integers and non-negative
    if not isinstance(N, int) or (not isinstance(M, int) and not np.isinf(M)):
        raise TypeError("N must be an integer and M must be an integer or float('inf')")
    if N < 0 or (isinstance(M, int) and M < 0):
        raise ValueError("N and M must be non-negative")
    if any(param < 0 for param in Kx_list):
        raise ValueError("Values in Kx_list must be non-negative")
    
    # Check the case when M is infinity
    if np.isinf(M):
        if not all(isinstance(param, (int, float)) and 0 <= param <= 1 for param in Kx_list):
            raise TypeError("When M is infinity, Kx_list must contain values between 0 and 1")

    # Check the case when M is a finite integer
    if not np.isinf(M):
        if not all(isinstance(param, int) for param in Kx_list):
            raise TypeError("Kx_list must contain two integers when M is finite")
        KA, KB = Kx_list
        if N > M or KA > M or KB > M:
            raise ValueError("N, KA, and KB must be <= M")

    # Based on the structure of the imput, 
    # returns the output of the internal:
    # _fishergame_solve or _binomial_fishergame_solve  

    # Call bayesiangame_solve if gamma == 1
    if float(gamma) == 1.:
        return bayesiangame_solve(N, Kx_list, M, method="bisection", max_iter=max_iter, max_error=max_error)

    if np.isinf(M):
        xA, xB = map(float, Kx_list)
        if xA <= xB:
            return _binomial_statisticalgame_solve(N, xA, xB, gamma)
        else:
            # Uses the convention of the paper:
            # https://arxiv.org/pdf/2402.15892#Hfootnote.16 
            return _binomial_statisticalgame_solve(N, xB, xA, gamma)
    else:
        KA, KB = Kx_list
        if KA <= KB:
            return _statisticalgame_solve(N, KA, KB, M, gamma, method="bisection", max_iter=max_iter, max_error=max_error)
        else:
            # Uses the convention of the paper:
            # https://arxiv.org/pdf/2402.15892#Hfootnote.16 
            return _statisticalgame_solve(N, KB, KA, M, gamma, method="bisection", max_iter=max_iter, max_error=max_error)


def _surewinning(k_A_minmax, k_B_minmax):
    """
    Internal function to handle sure winning Bayesian games.

    Parameters:
    k_A_minmax (Tuple[int, int]): Minimum and Maximum of k in case of scenario A.
    k_B_minmax (Tuple[int, int]): Minimum and Maximum of k in case of scenario B.

    Returns:
    dict: Contains 'P', 'P_interval', 'G', 'p_prime'.
    """

    p_prime_A = {k: 1 for k in range(k_A_minmax[0], k_A_minmax[1] + 1)}
    p_prime_B = {k: 0 for k in range(k_B_minmax[0], k_B_minmax[1] + 1)}

    return {'P': None, 'P_interval': [0, 1], 'G': 0, 'p_prime': p_prime_A | p_prime_B}


def _statisticalgame_solve(N: int, KA: int, KB: int, M: int, gamma: float, 
    method="bisection", 
    max_iter=float('inf'), 
    max_error=1 / 2 ** 10
    ):
    """
    Internal function to calculate Statistical game equilibrium quantities.

    Parameters:
    N (int): Number of sampled bits.
    KA (int): Number of 1-s in scenario A.
    KB (int): Number of 1-s in scenario B.
    M (int): Total length of the binary strings.
    gamma (float): relative risk aversion parameter.

    Returns:
    dict: Contains 'P', 'P_interval', 'U', 'p_prime'.
    """
    
    k_A_minmax = [max(0, N - (M - KA)), min(N, KA)]
    k_B_minmax = [max(0, N - (M - KB)), min(N, KB)]

    k_minmax = [min(k_A_minmax[0], k_B_minmax[0]), max(k_A_minmax[1], k_B_minmax[1])]
    k_AB_minmax = [max(k_A_minmax[0], k_B_minmax[0]), min(k_A_minmax[1], k_B_minmax[1])]

    if k_AB_minmax[0] > k_AB_minmax[1]:
        return _surewinning(k_A_minmax, k_B_minmax)

    Z = scipy.special.comb(M, N, exact=True)

    # Define the range for k values
    k_values = np.arange(k_minmax[0], k_minmax[1] + 1)

    # Calculate p_A_list and p_B_list using element-wise calculations
    p_A_list = np.array([scipy.special.comb(KA, k, exact=True) * scipy.special.comb(M - KA, N - k, exact=True) for k in k_values]) / Z
    p_B_list = np.array([scipy.special.comb(KB, k, exact=True) * scipy.special.comb(M - KB, N - k, exact=True) for k in k_values]) / Z

    # Define the slices directly for later use
    k_A_slice = slice(k_A_minmax[0] - k_minmax[0], k_A_minmax[1] - k_minmax[0] + 1)
    k_B_slice = slice(k_B_minmax[0] - k_minmax[0], k_B_minmax[1] - k_minmax[0] + 1)

    # Define a th(P) transformation from probability to log-odds
    def th(P):
        return np.log(P / (1 - P))

    # Define a(k, th)
    # $a_k$ (or a_k(z(\vartheta))) in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.724
    def a(k, th):
        return  np.exp(th / gamma / 2) * p_A_list[k]**(1 / gamma) + \
                np.exp(-th / gamma / 2) * p_B_list[k]**(1 / gamma)

    # Define Phi(th)
    # $\Phi(\vartheta)$ in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.722
    def Phi(th):
        sum_A = np.sum([p_A_list[k]**(1 / gamma) / a(k, th)**(1 - gamma) for k in k_values[k_A_slice]])
        sum_B = np.sum([p_B_list[k]**(1 / gamma) / a(k, th)**(1 - gamma) for k in k_values[k_B_slice]])
        return -gamma / (1 - gamma) * np.log(sum_A / sum_B)

    # h(P) being the quantity, which should be zero in equilibrium
    # $h(P) = \vartheta(P) - \Phi(\vartheta(P))$
    # See the requirement in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.718
    def h(P):
        return th(P) - Phi(th(P))

    # Define the isoelastic utility function u(c)
    # $u_\gamma(c)$
    def u(c):
        return (c ** (1 - gamma) - 1) / (1 - gamma)

    # Simple implementation of the Bisection method:
    # https://pythonnumericalmethods.studentorg.berkeley.edu/notebooks/chapter19.03-Bisection-Method.html
    
    # Or from Numerical Recipes: https://www.numerical.recipes/book.html
    # 9.1 Bracketing and Bisection 445:
    # https://nr304ob.s3.amazonaws.com/MNV7AKCDC7LVFQDK.pdf

    # Initial bounds
    P_lower = 0
    P_upper = 1

    i = 0
    while i < max_iter and (P_upper - P_lower) / 2 > max_error:
        P_mid = (P_lower + P_upper) / 2
        h_P_mid = h(P_mid)
        
        if h_P_mid > 0:
            P_upper = P_mid
        elif h_P_mid < 0:
            P_lower = P_mid
        elif h_P_mid == 0:
            P_star = P_mid
            break
        
        i += 1

    P_star = (P_lower + P_upper) / 2  # Set P_star to the midpoint after the loop

    # Calculate p_prime_star using the given equation
    # In the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.713
    p_prime_star = {
        k: (P_star * p_A_list[k])**(1 / gamma) / ((P_star * p_A_list[k])**(1 / gamma) + ((1 - P_star) * p_B_list[k])**(1 / gamma))
        for k in range(k_minmax[0], k_minmax[1] + 1)
    }

    # Calculate U_gamma(P_star) based on the given equation
    U_star =    P_star *        np.sum([p_A_list[k] * u(p_prime_star[k]) \
                                for k in k_values[k_A_slice]]) + \
                (1 - P_star) *  np.sum([p_B_list[k] * u(1 - p_prime_star[k]) \
                                for k in k_values[k_B_slice]])

    return {'P': P_star, 'P_interval': [P_lower, P_upper], 'U': U_star, 'p_prime': p_prime_star}


def _binomial_statisticalgame_solve(N: int, xA: float, xB: float, gamma: float, 
    method="bisection", 
    max_iter=float('inf'), 
    max_error=1 / 2 ** 10):
    """
    Internal function to calculate binomial Statistical game equilibrium quantities.

    Parameters:
    N (int): Number of sampled bits.
    xA (float): Density of 1 in scenario A.
    xB (float): Density of 1 in scenario B.
    gamma (float): Relative risk aversion parameter.
    method (str, optional): Method to use for solving the game. Default is "bisection".
    max_iter (int, optional): Maximum number of iterations allowed. Default is float('inf').
    max_error (float, optional): Maximum acceptable error. Default is 1 / 2 ** 10.

    Returns:
    dict: Contains 'P', 'P_interval', 'U', 'p_prime'.
    """
    
    if xA == 0 and xB == 1:
        return _surewinning([0,0],[N,N])
    
    # Define the range for k values
    k_values = np.arange(0, N + 1)
    
    # Calculate binomial probabilities p_A_list and p_B_list
    p_A_list = np.array([scipy.special.comb(N, k, exact=True) * (xA ** k) * ((1 - xA) ** (N - k)) for k in k_values])
    p_B_list = np.array([scipy.special.comb(N, k, exact=True) * (xB ** k) * ((1 - xB) ** (N - k)) for k in k_values])
    
    # Define a th(P) transformation from probability to log-odds
    def th(P):
        return np.log(P / (1 - P))

    # Define a(k, th)
    # $a_k$ (or a_k(z(\vartheta))) in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.724
    def a(k, th):
        term1 = np.exp(th / gamma / 2) * p_A_list[k]**(1 / gamma)
        term2 = np.exp(-th / gamma / 2) * p_B_list[k]**(1 / gamma)
        return term1 + term2

    # Define Phi(th)
    # $\Phi(\vartheta)$ in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.722
    def Phi(th):
        sum_A = np.sum([p_A_list[k]**(1 / gamma) / a(k, th)**(1 - gamma) for k in k_values])
        sum_B = np.sum([p_B_list[k]**(1 / gamma) / a(k, th)**(1 - gamma) for k in k_values])
        return -gamma / (1 - gamma) * np.log(sum_A / sum_B)

    # h(P) being the quantity, which should be zero in equilibrium
    # $h(P) = \vartheta(P) - \Phi(\vartheta(P))$
    # See the requirement in the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.718
    def h(P):
        return th(P) - Phi(th(P))

    # Define the isoelastic utility function u(c)
    # $u_\gamma(c)$
    def u(c):
        return (c ** (1 - gamma) - 1) / (1 - gamma)

    # Simple implementation of the Bisection method:
    # https://pythonnumericalmethods.studentorg.berkeley.edu/notebooks/chapter19.03-Bisection-Method.html
    
    # Or from Numerical Recipes: https://www.numerical.recipes/book.html
    # 9.1 Bracketing and Bisection 445:
    # https://nr304ob.s3.amazonaws.com/MNV7AKCDC7LVFQDK.pdf

    P_lower = 0
    P_upper = 1
    
    i = 0
    while i < max_iter and (P_upper - P_lower) / 2 > max_error:
        P_mid = (P_lower + P_upper) / 2
        h_P_mid = h(P_mid)
        
        if h_P_mid > 0:
            P_upper = P_mid
        elif h_P_mid < 0:
            P_lower = P_mid
        elif h_P_mid == 0:
            P_star = P_mid
            break
        
        i += 1
    
    P_star = (P_lower + P_upper) / 2  # Set P_star to the midpoint after the loop
    
    # Calculate p_prime_star using the given equation
    # In the Statistical Games paper:
    # https://arxiv.org/pdf/2402.15892#equation.F.713
    p_prime_star = {
        k: (P_star * p_A_list[k])**(1 / gamma) / ((P_star * p_A_list[k])**(1 / gamma) + ((1 - P_star) * p_B_list[k])**(1 / gamma))
        for k in k_values
    }
    
    # Calculate U_star based on the given equation
    U_star =    P_star *        np.sum([p_A_list[k] * u(p_prime_star[k]) \
                                for k in k_values]) + \
                (1 - P_star) *  np.sum([p_B_list[k] * u(1 - p_prime_star[k]) \
                                for k in k_values])
    
    return {'P': P_star, 'P_interval': [P_lower, P_upper], 'U': U_star, 'p_prime': p_prime_star}