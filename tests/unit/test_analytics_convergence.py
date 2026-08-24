from civicmesh.analytics import (
    peer_convergence,
    perception_gap,
)


def test_perception_gap_is_absolute_difference():

    assert (
        perception_gap(
            ground_truth=10.0,
            perception=7.0,
        )
        == 3.0
    )

    assert (
        perception_gap(
            ground_truth=7.0,
            perception=10.0,
        )
        == 3.0
    )


def test_perception_gap_zero_when_equal():

    assert (
        perception_gap(5.0, 5.0) == 0.0
    )


def test_peer_convergence_zero_when_all_peers_agree():

    assert (
        peer_convergence([12.0, 12.0, 12.0])
        == 0.0
    )


def test_peer_convergence_zero_with_single_value():

    assert peer_convergence([12.0]) == 0.0


def test_peer_convergence_zero_with_no_values():

    assert peer_convergence([]) == 0.0


def test_peer_convergence_grows_with_dispersion():

    low_dispersion = peer_convergence(
        [10.0, 11.0, 9.0]
    )

    high_dispersion = peer_convergence(
        [0.0, 20.0, 10.0]
    )

    assert low_dispersion < high_dispersion
