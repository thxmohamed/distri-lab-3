from __future__ import annotations

from statistics import pstdev


def perception_gap(ground_truth, perception) -> float:
    """
    Brecha percepción-realidad de un evento del canal subjetivo.

    |P_c(t) - G_c(t)|: qué tan lejos está lo percibido de lo
    objetivo en ese mismo paso.
    """

    return abs(float(perception) - float(ground_truth))


def peer_convergence(values) -> float:
    """
    Convergencia del canal objetivo entre peers.

    Dispersión (desviación estándar poblacional) de los valores que
    distintos peers reportan para el mismo tópico/canal en una misma
    ventana de tiempo. 0.0 significa que todos los peers coinciden;
    valores altos indican que la malla no ha convergido todavía.
    """

    numeric = [float(value) for value in values]

    if len(numeric) < 2:
        return 0.0

    return pstdev(numeric)
