"""ResNet-50 binary pneumonia classifier with an MC-Dropout classification head.

The backbone is the torchvision ResNet-50 (ImageNet initialisation during
training). The head contains two dropout layers that stay *active* at
inference time to perform Monte Carlo Dropout (Gal & Ghahramani, 2016).
The network outputs a single logit for P(pneumonia).
"""
from __future__ import annotations

import torch
from torch import nn
from torchvision.models import ResNet50_Weights, resnet50

FEATURE_DIM = 2048


class MCDropoutHead(nn.Module):
    def __init__(self, in_features: int = FEATURE_DIM, hidden: int = 256, dropout: float = 0.5):
        super().__init__()
        self.dropout_p = dropout
        self.net = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, hidden),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(hidden, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.net(features).squeeze(-1)


class PneumoniaResNet50(nn.Module):
    def __init__(self, hidden: int = 256, dropout: float = 0.5, pretrained_backbone: bool = False):
        super().__init__()
        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained_backbone else None
        backbone = resnet50(weights=weights)
        backbone.fc = nn.Identity()
        self.backbone = backbone
        self.head = MCDropoutHead(FEATURE_DIM, hidden, dropout)

    @property
    def gradcam_layer(self) -> nn.Module:
        return self.backbone.layer4

    def features(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.backbone(x))
