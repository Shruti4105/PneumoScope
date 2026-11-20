"""Monte Carlo Dropout utilities."""
from __future__ import annotations

import torch
from torch import nn

DEFAULT_PASSES = 30


def set_mc_dropout(module: nn.Module, active: bool = True) -> nn.Module:
    """Put ``module`` in eval mode but keep every Dropout layer stochastic."""
    module.eval()
    if active:
        for m in module.modules():
            if isinstance(m, nn.Dropout):
                m.train()
    return module


@torch.no_grad()
def mc_head_logits(head: nn.Module, features: torch.Tensor, passes: int = DEFAULT_PASSES,
                   seed: int | None = None) -> torch.Tensor:
    """Run ``passes`` stochastic forward passes of ``head``.

    Features are computed once by the (deterministic) backbone; each pass
    samples an independent dropout mask. Returns logits of shape [passes, N].
    """
    if passes < 1:
        raise ValueError("passes must be >= 1")
    was_training = head.training
    set_mc_dropout(head, True)
    n = features.shape[0]
    with torch.random.fork_rng(devices=[]):
        if seed is not None:
            torch.manual_seed(seed)
        stacked = features.repeat(passes, 1)          # [passes*N, D] — independent masks per row
        logits = head(stacked).reshape(passes, n)
    head.train(was_training)
    return logits


@torch.no_grad()
def deterministic_head_logits(head: nn.Module, features: torch.Tensor) -> torch.Tensor:
    was_training = head.training
    head.eval()
    out = head(features)
    head.train(was_training)
    return out
