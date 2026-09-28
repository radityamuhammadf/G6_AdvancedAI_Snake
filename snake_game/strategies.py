from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot


class MoveStrategy(ABC):
    """Base class for every automated snake movement method."""

    @abstractmethod
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        """Return the direction for ``snake_id`` for the current turn."""


STRATEGY_REGISTRY: dict[str, type[MoveStrategy]] = {}


def register_strategy(name: str) -> Callable[[type[MoveStrategy]], type[MoveStrategy]]:
    """Register a strategy class so it appears in the setup-screen dropdown."""

    def decorator(strategy_class: type[MoveStrategy]) -> type[MoveStrategy]:
        if not name.strip():
            raise ValueError("Strategy names cannot be empty.")
        STRATEGY_REGISTRY[name] = strategy_class
        return strategy_class

    return decorator


def create_strategy(name: str) -> MoveStrategy:
    try:
        return STRATEGY_REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown strategy: {name}") from exc


@register_strategy("Safe Random")
class SafeRandomStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        if legal:
            return rng.choice(legal)
        return snapshot.snake(snake_id).direction


@register_strategy("Greedy")
class GreedyStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction

        head_x, head_y = snake.body[0]

        def distance(direction: Direction) -> int:
            dx, dy = direction.vector
            new_x, new_y = head_x + dx, head_y + dy
            return min(
                abs(new_x - apple_x) + abs(new_y - apple_y)
                for apple_x, apple_y in snapshot.apples
            )

        best_distance = min(distance(direction) for direction in legal)
        best_moves = [direction for direction in legal if distance(direction) == best_distance]
        return rng.choice(best_moves)

@register_strategy("REV. ENG. MODE")
class DebugStrategy_Greedy(MoveStrategy):
    # 
    def choose_move(self, snapshot: GameSnapshot, snake_id: str, rng: Random) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        print(f"legal move: {legal}") 
        # print result: options of legal DIRECTION (did not eat its tail, and not hit the wall)
        # e.g. = (<Direction.UP: (0, -1)>, <Direction.LEFT: (-1, 0)>, <Direction.RIGHT: (1, 0)>)
        snake = snapshot.snake(snake_id)
        # basis: will return the latest direction (?) 
        # when there's no move options available or all apples has been eaten
        if not legal or not snapshot.apples:
            print(f"Basis: {snake.direction}") #strange...
            return snake.direction

        head_x, head_y = snake.body[0]
        # print(f"head x: {head_x} ; head y: {head_y}")
        # print result: current position of snake's head
        # e.g. = head x: 15 ; head y: 16

        def distance(direction: Direction) -> int:
            dx, dy = direction.vector
            new_x, new_y = head_x + dx, head_y + dy # calculate the change of position based on the direction

            closest_apple = min(
                abs(new_x - apple_x) + abs(new_y - apple_y) # 2. Calculate distance from current 
                for apple_x, apple_y in snapshot.apples # 1. Find all apples and extract each coordinate of them
            )
            print(f"Closest apple's distance from {direction} is {closest_apple}")

            return min(
                abs(new_x - apple_x) + abs(new_y - apple_y)
                for apple_x, apple_y in snapshot.apples
            )

        # Greedy logic #1: measure the currently-closest apple's distance
        # From EACH DIRECTION of LEGAL MOVE that're obtained on top of the method
        best_distance = min(distance(direction) for direction in legal)
        print(f"best distance: {best_distance}")

        # Gather the possible move with the smallest distance to apple,
        # Store it as a List to accomodate more than 1 best possible move
        best_moves = [direction for direction in legal if distance(direction) == best_distance]
        print(f"best moves: {best_moves}")
        return rng.choice(best_moves)



# Assignment template -------------------------------------------------------
# 1. Copy this class and give it a unique name.
# 2. Implement choose_move using only the immutable snapshot.
# 3. Add @register_strategy("My Strategy") above the class. It will then appear
#    automatically in the setup screen.
#
# @register_strategy("My Strategy")
# class MyStrategy(MoveStrategy):
#     def choose_move(self, snapshot, snake_id, rng):
#         legal_moves = snapshot.legal_moves_for(snake_id)
#         return legal_moves[0] if legal_moves else snapshot.snake(snake_id).direction
