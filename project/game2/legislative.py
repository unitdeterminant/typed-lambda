import random

import jax
import jax.lax as jla
import jax.numpy as jnp
import jax.random as jrn
import jaxtyping as jtp
import typeguard

from . import utils


@jtp.jaxtyped
@typeguard.typechecked
def policies_history_init(history_size: int) -> jtp.Int[jnp.ndarray, "history 2"]:
    """
    """
    return jnp.zeros([history_size, 2], dtype=jnp.int32)


@jtp.jaxtyped
@typeguard.typechecked
def draw_pile_history_init(history_size: int) -> jtp.Int[jnp.ndarray, "history 2"]:
    """
    """
    policies = policies_history_init(history_size)
    return policies.at[0].set(jnp.array([6, 11], dtype=jnp.int32))


@jtp.jaxtyped
@typeguard.typechecked
def push_policy(
    *,
    policy: jtp.Bool[jnp.ndarray, ""],
    policies: jtp.Int[jnp.ndarray, "history 2"],
) -> jtp.Int[jnp.ndarray, "history 2"]:
    """
    Push a policy to a collection of policies

    Args:
        policy: jtp.Bool[jnp.ndarray, "history"]
            The policy to be pushed:
            - `False` for L policy
            - `True` for F policy

        policies: jtp.Int[jnp.ndarray, "history 2"]
            Discard pile:
            - `policies[0]` the number of L policies
            - `policies[1]` the number of F policies

    Returns:
        policies: jtp.Int[jnp.ndarray, "history 2"]
            New discard pile.
    """
    return jla.select(
        policy,
        policies.at[0, 1].add(1),  # F policy
        policies.at[0, 0].add(1)  # L policy
    )


@jtp.jaxtyped
@typeguard.typechecked
def draw_policy(
    key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"],
    *,
    draw_pile_history: jtp.Int[jnp.ndarray, "history 2"],
    discard_pile_history: jtp.Int[jnp.ndarray, "history 2"],
) -> tuple[
    jtp.Bool[jnp.ndarray, ""],
    jtp.Int[jnp.ndarray, "history 2"],
    jtp.Int[jnp.ndarray, "history 2"]
]:
    """
    Draw a policy from the draw pile.
    If necessary transfer the discard pile to the draw pile.

    Args:
        key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"]
            Random number generator state

        draw_pile_history: jtp.Int[jnp.ndarray, "history 2"]
            Draw pile:
            - `draw_pile[i, 0]` the number of L policies
            - `draw_pile[i, 1]` the number of F policies

        discard_pile_history: jtp.Int[jnp.ndarray, "history 2"]
            Discard pile:
            - same format as `draw_pile` above

    Returns:
        draw_pile_history: jtp.Int[jnp.ndarray, "history 2"]
            New draw pile:
            - same format as `draw_pile` above

        discard_pile_history: jtp.Int[jnp.ndarray, "history 2"]
            New discard pile:
            - same format as `draw_pile` above
    """
    draw_pile, discard_pile = draw_pile_history[0], discard_pile_history[0]

    # switch piles if draw_pile is empty
    draw_pile, discard_pile = jla.cond(
        draw_pile.sum() == 0,
        lambda: (discard_pile, draw_pile),
        lambda: (draw_pile, discard_pile)
    )

    discard_pile_history = discard_pile_history.at[0].set(discard_pile)
    draw_pile_history = draw_pile_history.at[0].set(draw_pile)

    # draw a policy from bernouli distribution
    probability = draw_pile[1] / draw_pile.sum()  # probability of F policy
    policy = jrn.bernoulli(key, probability)

    draw_pile_history = jla.select(
        policy,
        draw_pile_history.at[0, 1].add(-1),  # F policy
        draw_pile_history.at[0, 0].add(-1)  # L policy
    )

    return policy, draw_pile_history, discard_pile_history


def forced_policy(
    key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"],
    *,
    election_tracker_history: jtp.Int[jnp.ndarray, "history"],
    board_history: jtp.Int[jnp.ndarray, "history 2"],
    draw_pile_history: jtp.Int[jnp.ndarray, "history 2"],
    discard_pile_history: jtp.Int[jnp.ndarray, "history 2"],
) -> tuple[
    jtp.Int[jnp.ndarray, "history"],
    jtp.Int[jnp.ndarray, "history 2"],
    jtp.Int[jnp.ndarray, "history 2"],
    jtp.Int[jnp.ndarray, "history 2"],
]:
    """
    Assuming the election tracker has reached 2, then a policy is drawn and enacted
    """
    # draw a policy
    policy, draw_pile_history, discard_pile_history = draw_policy(
        key,
        draw_pile_history=draw_pile_history,
        discard_pile_history=discard_pile_history
    )

    # enact the policy
    board_history = push_policy(policy=policy, policies=board_history)

    # reset election tracker
    election_tracker_history = election_tracker_history.at[0].set(0)

    return election_tracker_history, board_history, draw_pile_history, discard_pile_history


@jtp.jaxtyped
@typeguard.typechecked
def session_draw(
    key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"],
    *,
    president_shown_history: jtp.Int[jnp.ndarray, "history 2"],
    draw_pile_history: jtp.Int[jnp.ndarray, "history 2"],
    discard_pile_history: jtp.Int[jnp.ndarray, "history 2"],
) -> tuple[
    jtp.Int[jnp.ndarray, "history 2"],
    jtp.Int[jnp.ndarray, "history 2"],
    jtp.Int[jnp.ndarray, "history 2"],
]:
    """
    """
    policies = jnp.zeros([2], dtype=president_shown_history.dtype)

    for key in jrn.split(key, 3):

        policy, draw_pile_history, discard_pile_history = draw_policy(
            key,
            draw_pile_history=draw_pile_history,
            discard_pile_history=discard_pile_history
        )
        # policies = push_policy(policy=policy, policies=policies)
        policies = jla.select(
            policy,
            policies.at[1].add(1),  # F policy
            policies.at[0].add(1)  # L policy
        )

    president_shown_history = president_shown_history.at[0].set(policies)

    return president_shown_history, draw_pile_history, discard_pile_history


@jtp.jaxtyped
@typeguard.typechecked
def session_president(
    key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"],
    *,
    discard_F_probability: jtp.Float[jnp.ndarray, ""],
    president_shown_history: jtp.Int[jnp.ndarray, "history 2"],
    chancellor_shown_history: jtp.Int[jnp.ndarray, "history 2"],
    discard_pile_history: jtp.Int[jnp.ndarray, "history 2"],
) -> tuple[jtp.Int[jnp.ndarray, "history 2"], jtp.Int[jnp.ndarray, "history 2"]]:
    """
    """
    policies = president_shown_history[0]
    empty = policies == 0

    # set probability of discarding a F policy to 1 if there are no L policies
    discard_F_probability = jla.select(empty[0], 1.0, discard_F_probability)

    # set probability of discarding a F policy to 0 if there are no F policies
    discard_F_probability = jla.select(empty[1], 0.0, discard_F_probability)

    # draw whether to discard a F policy from bernouli distribution
    to_discard = jrn.bernoulli(key, discard_F_probability)

    policies = jla.select(
        to_discard,
        policies.at[1].add(-1),  # discard F policy
        policies.at[0].add(-1)  # discard L policy
    )

    discard_pile_history = push_policy(
        policy=to_discard, policies=discard_pile_history)

    chancellor_shown_history = chancellor_shown_history.at[0].set(policies)

    return chancellor_shown_history, discard_pile_history


@jtp.jaxtyped
@typeguard.typechecked
def session_chancellor(
    key: jrn.KeyArray | jtp.UInt32[jtp.Array, "2"],
    *,
    discard_F_probability: jtp.Float[jnp.ndarray, ""],
    chancellor_shown_history: jtp.Int[jnp.ndarray, "history 2"],
    discard_pile_history: jtp.Int[jnp.ndarray, "history 2"],
    board_history: jtp.Int[jnp.ndarray, "history 2"],
) -> tuple[jtp.Int[jnp.ndarray, "history 2"], jtp.Int[jnp.ndarray, "history 2"]]:
    """
    """
    to_enact, discard_pile_history = session_president(
        key,
        discard_F_probability=discard_F_probability,
        president_shown_history=chancellor_shown_history,
        chancellor_shown_history=jnp.zeros_like(chancellor_shown_history),
        discard_pile_history=discard_pile_history
    )

    to_enact = to_enact[0].argmax().astype(bool)
    board_history = push_policy(policy=to_enact, policies=board_history)

    return board_history, discard_pile_history


def test_legislative():
    """
    """
    history_size = 3
    president_discard_F_probability = jnp.array(0.5)
    chancellor_discard_F_probability = jnp.array(0.5)

    board_history = policies_history_init(history_size)
    discard_pile_history = policies_history_init(history_size)
    draw_pile_history = draw_pile_history_init(history_size)

    president_shown_history = policies_history_init(history_size)
    chancellor_shown_history = policies_history_init(history_size)

    session_draw_jit = jax.jit(session_draw)
    session_president_jit = jax.jit(session_president)
    session_chancellor_jit = jax.jit(session_chancellor)

    key = jrn.PRNGKey(random.randint(0, 2**32 - 1))

    for i in range(8):
        print("\n-- round", i + 1, "--")

        board_history = utils.roll_history(history=board_history)
        discard_pile_history = utils.roll_history(history=discard_pile_history)
        draw_pile_history = utils.roll_history(history=draw_pile_history)

        president_shown_history = utils.roll_history(
            history=president_shown_history
        )

        chancellor_shown_history = utils.roll_history(
            history=chancellor_shown_history
        )

        key, subkey = jrn.split(key)

        print("draw    ", utils.policies_repr(draw_pile_history[0]))
        print("discard ", utils.policies_repr(discard_pile_history[0]))

        print("- running session draw -")

        key, subkey = jrn.split(key)
        president_shown_history, draw_pile_history, discard_pile_history = session_draw(
            subkey,
            president_shown_history=president_shown_history,
            draw_pile_history=draw_pile_history,
            discard_pile_history=discard_pile_history
        )

        print("draw    ", utils.policies_repr(draw_pile_history[0]))
        print("discard ", utils.policies_repr(discard_pile_history[0]))

        print("shown p ", utils.policies_repr(president_shown_history[0]))

        print("- running session president -")

        key, subkey = jrn.split(key)
        chancellor_shown_history, discard_pile_history = session_president(
            subkey,
            discard_F_probability=president_discard_F_probability,
            president_shown_history=president_shown_history,
            chancellor_shown_history=chancellor_shown_history,
            discard_pile_history=discard_pile_history
        )

        print("discard ", utils.policies_repr(discard_pile_history[0]))
        print("shown c ", utils.policies_repr(chancellor_shown_history[0]))

        print("- running session chancellor -")

        key, subkey = jrn.split(key)
        board_history, discard_pile_history = session_chancellor(
            subkey,
            discard_F_probability=chancellor_discard_F_probability,
            chancellor_shown_history=chancellor_shown_history,
            discard_pile_history=discard_pile_history,
            board_history=board_history
        )

        print("discard ", utils.policies_repr(discard_pile_history[0]))
        print("board")
        print(utils.board_repr(board_history[0]))
