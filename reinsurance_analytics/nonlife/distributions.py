"""
Parametric Loss Severity Distributions & Maximum Likelihood Estimation
========================================================================

Implements actuarial heavy-tailed loss distributions for reinsurance:
- Pareto (Type I and Lomax / Type II)
- Lognormal
- Weibull
- Generalized Pareto (GPD)
Includes truncated MLE fitting, Kolmogorov-Smirnov goodness-of-fit, AIC/BIC selection,
and Limited Expected Value (LEV) calculation for layer pricing.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional, List
import numpy as np
import pandas as pd
from scipy import stats, optimize


class ActuarialDistribution(ABC):
    """Abstract base class for parametric loss distributions."""

    @abstractmethod
    def pdf(self, x: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def cdf(self, x: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def ppf(self, q: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def limited_expected_value(self, limit: float) -> float:
        """
        Limited Expected Value: E[min(X, limit)] = integral_0^limit (1 - F(x)) dx
        Crucial for reinsurance excess-of-loss layer pricing:
        E[min(X - d, l)_+] = LEV(d + l) - LEV(d)
        """
        pass

    @abstractmethod
    def rvs(self, size: int, random_state: Optional[int] = None) -> np.ndarray:
        pass


class ParetoDistribution(ActuarialDistribution):
    """
    Single-parameter (Type I) Pareto Distribution with fixed or estimated threshold x_m:
    f(x) = alpha * (x_m^alpha) / (x^(alpha + 1)), for x >= x_m
    F(x) = 1 - (x_m / x)^alpha
    """

    def __init__(self, alpha: float, xm: float):
        if alpha <= 0 or xm <= 0:
            raise ValueError("alpha and xm must be positive")
        self.alpha = float(alpha)
        self.xm = float(xm)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        x_arr = np.asarray(x, dtype=float)
        out = np.zeros_like(x_arr)
        mask = x_arr >= self.xm
        out[mask] = (self.alpha * (self.xm ** self.alpha)) / (x_arr[mask] ** (self.alpha + 1.0))
        return out

    def cdf(self, x: np.ndarray) -> np.ndarray:
        x_arr = np.asarray(x, dtype=float)
        out = np.zeros_like(x_arr)
        mask = x_arr >= self.xm
        out[mask] = 1.0 - (self.xm / x_arr[mask]) ** self.alpha
        return out

    def ppf(self, q: np.ndarray) -> np.ndarray:
        q_arr = np.asarray(q, dtype=float)
        return self.xm / ((1.0 - q_arr) ** (1.0 / self.alpha))

    def limited_expected_value(self, limit: float) -> float:
        if limit <= self.xm:
            return float(limit)

        if np.isclose(self.alpha, 1.0):
            # Special case alpha = 1: LEV(u) = xm * (1 + ln(u / xm))
            return float(self.xm * (1.0 + np.log(limit / self.xm)))
        else:
            term1 = self.alpha * self.xm / (self.alpha - 1.0)
            term2 = (self.xm ** self.alpha) / (self.alpha - 1.0) * (limit ** (1.0 - self.alpha))
            return float(term1 - term2)

    def rvs(self, size: int, random_state: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(random_state)
        u = rng.uniform(0.0, 1.0, size=size)
        return self.ppf(u)

    @classmethod
    def fit_mle(cls, data: np.ndarray, xm: Optional[float] = None) -> ParetoDistribution:
        """Maximum Likelihood Estimation for Pareto alpha."""
        arr = np.asarray(data, dtype=float)
        arr = arr[arr > 0]
        threshold = xm if xm is not None else float(np.min(arr))
        excess = arr[arr >= threshold]
        if len(excess) == 0:
            raise ValueError("No data points exceed xm threshold")

        n = len(excess)
        log_sum = np.sum(np.log(excess / threshold))
        alpha_hat = float(n / log_sum)
        return cls(alpha=alpha_hat, xm=threshold)


class LognormalDistribution(ActuarialDistribution):
    """Lognormal severity distribution: ln(X) ~ N(mu, sigma^2)."""

    def __init__(self, mu: float, sigma: float):
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self.mu = float(mu)
        self.sigma = float(sigma)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        x_arr = np.asarray(x, dtype=float)
        return stats.lognorm.pdf(x_arr, s=self.sigma, scale=np.exp(self.mu))

    def cdf(self, x: np.ndarray) -> np.ndarray:
        x_arr = np.asarray(x, dtype=float)
        return stats.lognorm.cdf(x_arr, s=self.sigma, scale=np.exp(self.mu))

    def ppf(self, q: np.ndarray) -> np.ndarray:
        q_arr = np.asarray(q, dtype=float)
        return stats.lognorm.ppf(q_arr, s=self.sigma, scale=np.exp(self.mu))

    def limited_expected_value(self, limit: float) -> float:
        if limit <= 0:
            return 0.0
        # Analytical formula for Lognormal LEV:
        # LEV(u) = exp(mu + 0.5 * sigma^2) * Phi((ln(u) - mu - sigma^2) / sigma) + u * (1 - Phi((ln(u) - mu) / sigma))
        exp_mean = np.exp(self.mu + 0.5 * (self.sigma ** 2))
        d1 = (np.log(limit) - self.mu - (self.sigma ** 2)) / self.sigma
        d2 = (np.log(limit) - self.mu) / self.sigma
        return float(exp_mean * stats.norm.cdf(d1) + limit * (1.0 - stats.norm.cdf(d2)))

    def rvs(self, size: int, random_state: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(random_state)
        return stats.lognorm.rvs(s=self.sigma, scale=np.exp(self.mu), size=size, random_state=rng)

    @classmethod
    def fit_mle(cls, data: np.ndarray) -> LognormalDistribution:
        arr = np.asarray(data, dtype=float)
        arr = arr[arr > 0]
        log_data = np.log(arr)
        mu_hat = float(np.mean(log_data))
        sigma_hat = float(np.std(log_data, ddof=1))
        return cls(mu=mu_hat, sigma=sigma_hat)


class WeibullDistribution(ActuarialDistribution):
    """Weibull distribution with shape c and scale lambda."""

    def __init__(self, shape: float, scale: float):
        if shape <= 0 or scale <= 0:
            raise ValueError("shape and scale must be positive")
        self.shape = float(shape)
        self.scale = float(scale)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        return stats.weibull_min.pdf(np.asarray(x, dtype=float), c=self.shape, scale=self.scale)

    def cdf(self, x: np.ndarray) -> np.ndarray:
        return stats.weibull_min.cdf(np.asarray(x, dtype=float), c=self.shape, scale=self.scale)

    def ppf(self, q: np.ndarray) -> np.ndarray:
        return stats.weibull_min.ppf(np.asarray(q, dtype=float), c=self.shape, scale=self.scale)

    def limited_expected_value(self, limit: float) -> float:
        # Numerical quadrature for general Weibull LEV
        res, _ = optimize.quad(lambda x: 1.0 - self.cdf(x), 0.0, limit) if hasattr(optimize, "quad") else (
            # scipy.integrate.quad
            from_quad(self.cdf, limit)
        )
        return float(res)

    def rvs(self, size: int, random_state: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(random_state)
        return stats.weibull_min.rvs(c=self.shape, scale=self.scale, size=size, random_state=rng)

    @classmethod
    def fit_mle(cls, data: np.ndarray) -> WeibullDistribution:
        arr = np.asarray(data, dtype=float)
        arr = arr[arr > 0]
        shape_hat, _, scale_hat = stats.weibull_min.fit(arr, floc=0)
        return cls(shape=float(shape_hat), scale=float(scale_hat))


def from_quad(cdf_fn, limit: float) -> Tuple[float, float]:
    from scipy import integrate
    return integrate.quad(lambda x: 1.0 - cdf_fn(x), 0.0, limit)


class GeneralizedParetoDistribution(ActuarialDistribution):
    """Generalized Pareto Distribution (GPD): F(x) = 1 - (1 + xi * x / sigma)^(-1/xi)."""

    def __init__(self, xi: float, sigma: float, threshold: float = 0.0):
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        self.xi = float(xi)
        self.sigma = float(sigma)
        self.threshold = float(threshold)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        return stats.genpareto.pdf(np.asarray(x, dtype=float), c=self.xi, loc=self.threshold, scale=self.sigma)

    def cdf(self, x: np.ndarray) -> np.ndarray:
        return stats.genpareto.cdf(np.asarray(x, dtype=float), c=self.xi, loc=self.threshold, scale=self.sigma)

    def ppf(self, q: np.ndarray) -> np.ndarray:
        return stats.genpareto.ppf(np.asarray(q, dtype=float), c=self.xi, loc=self.threshold, scale=self.sigma)

    def limited_expected_value(self, limit: float) -> float:
        if limit <= self.threshold:
            return float(limit)
        from scipy import integrate
        val, _ = integrate.quad(lambda x: 1.0 - self.cdf(x), self.threshold, limit)
        return float(self.threshold + val)

    def rvs(self, size: int, random_state: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(random_state)
        return stats.genpareto.rvs(c=self.xi, loc=self.threshold, scale=self.sigma, size=size, random_state=rng)

    @classmethod
    def fit_mle(cls, data: np.ndarray, threshold: float = 0.0) -> GeneralizedParetoDistribution:
        arr = np.asarray(data, dtype=float)
        excess = arr[arr > threshold] - threshold
        if len(excess) == 0:
            raise ValueError("No observations exceed threshold")
        c_hat, _, scale_hat = stats.genpareto.fit(excess, floc=0)
        return cls(xi=float(c_hat), sigma=float(scale_hat), threshold=threshold)


class LossDistributionFitter:
    """
    Fits and compares parametric actuarial loss severity distributions.
    
    Evaluates:
    - Log-Likelihood
    - AIC (Akaike Information Criterion)
    - BIC (Bayesian Information Criterion)
    - Kolmogorov-Smirnov statistic & p-value
    Selects the best distribution for reinsurance treaty modeling.
    """

    def __init__(self, data: np.ndarray):
        arr = np.asarray(data, dtype=float)
        self.data = arr[arr > 0]
        self.n = len(self.data)
        if self.n < 10:
            raise ValueError("Insufficient data points for robust distribution fitting (n >= 10 required).")

        self.fitted_models: Dict[str, ActuarialDistribution] = {}
        self.comparison_table: Optional[pd.DataFrame] = None

    def fit_all(self, pareto_xm: Optional[float] = None) -> pd.DataFrame:
        """Fit Pareto, Lognormal, Weibull, and GPD to data and rank by AIC."""
        xm = pareto_xm if pareto_xm is not None else float(np.min(self.data))
        
        # 1. Pareto
        pareto_data = self.data[self.data >= xm]
        if len(pareto_data) >= 5:
            self.fitted_models["Pareto"] = ParetoDistribution.fit_mle(self.data, xm=xm)
        
        # 2. Lognormal
        self.fitted_models["Lognormal"] = LognormalDistribution.fit_mle(self.data)

        # 3. Weibull
        self.fitted_models["Weibull"] = WeibullDistribution.fit_mle(self.data)

        # 4. GPD (threshold at 75th percentile)
        q75 = float(np.percentile(self.data, 75))
        self.fitted_models["GPD_Tail"] = GeneralizedParetoDistribution.fit_mle(self.data, threshold=q75)

        records = []
        for name, model in self.fitted_models.items():
            if name == "Pareto":
                eval_data = self.data[self.data >= xm]
                k_params = 1
            elif name == "GPD_Tail":
                eval_data = self.data[self.data > q75]
                k_params = 2
            else:
                eval_data = self.data
                k_params = 2

            n_obs = len(eval_data)
            pdf_vals = model.pdf(eval_data)
            pdf_vals = np.clip(pdf_vals, 1e-15, None)
            log_lik = float(np.sum(np.log(pdf_vals)))

            aic = 2.0 * k_params - 2.0 * log_lik
            bic = k_params * np.log(n_obs) - 2.0 * log_lik

            # KS-test
            ks_res = stats.kstest(eval_data, model.cdf)

            records.append({
                "Distribution": name,
                "Parameters": k_params,
                "Observations": n_obs,
                "Log_Likelihood": log_lik,
                "AIC": aic,
                "BIC": bic,
                "KS_Statistic": ks_res.statistic,
                "KS_p_value": ks_res.pvalue,
            })

        self.comparison_table = pd.DataFrame(records).sort_values(by="AIC").reset_index(drop=True)
        return self.comparison_table

    def get_best_model(self) -> Tuple[str, ActuarialDistribution]:
        """Return the best-fitting distribution based on lowest AIC."""
        if self.comparison_table is None:
            self.fit_all()
        best_name = str(self.comparison_table.iloc[0]["Distribution"])
        return best_name, self.fitted_models[best_name]
