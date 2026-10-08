from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random
from collections import deque
from .models import Direction, GameSnapshot
from heapq import heappush, heappop
from itertools import count

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
    
@register_strategy("BFS")
class BFSStrategy(MoveStrategy):
    def choose_move(self, snapshot, snake_id, rng) -> Direction:
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)

        if not legal_moves:
            return snake.direction

        if not snapshot.apples:
            return rng.choice(legal_moves)

        apples = set(snapshot.apples)
        head_x, head_y = snake.body[0]
        visited = {(head_x, head_y)}
        queue = deque()

        occupied = {
            position 
            for other_snake in snapshot.snakes
            for position in other_snake.body
        }

        for direction in legal_moves:
            dx, dy = direction.vector
            position = (head_x + dx, head_y + dy)
            queue.append((position, direction))
            visited.add(position)

        while queue:
            position, first_move = queue.popleft()
            if position in apples:
                return first_move
            x, y = position
            for direction in Direction:
                dx, dy = direction.vector
                neighbor = (x + dx, y + dy)
                nx, ny = neighbor
                inside_board = (
                    0 <= nx < snapshot.columns
                    and 0 <= ny < snapshot.rows
                )
                if not inside_board:
                    continue
                if neighbor in visited or neighbor in occupied:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, first_move))

        return rng.choice(legal_moves)

@register_strategy("ASTAR")
class ASTARStrategy(MoveStrategy):
    def choose_move(self, snapshot, snake_id, rng):
        def heuristic(position):
            return min(
                abs(position[0] - apple[0]) + abs(position[1] - apple[1])
                for apple in snapshot.apples
            )   

        snake = snapshot.snake(snake_id)
        head = snake.body[0]
        legal_moves = snapshot.legal_moves_for(snake_id)
        apples = set(snapshot.apples)

        if not legal_moves:
            return snake.direction
        if not snapshot.apples:
            return rng.choice(legal_moves)
        
        gn = {head : 0}

        occupied = {
            position 
            for other_snake in snapshot.snakes
            for position in other_snake.body
        }

        queue = []
        order = count()
        head_x, head_y = head
        for direction in legal_moves:
            dx, dy = direction.vector
            position = (head_x + dx, head_y + dy)
            gn[position] = 1
            fn = gn[position] + heuristic(position)
            heappush(
                queue,
                (fn, next(order), 1, position, direction),
            )
        while queue:
            _, _, current_g, position, first_move = heappop(queue)
            if current_g != gn[position]:
                continue
            if position in apples:
                return first_move
            x, y = position
            for direction in Direction:
                dx, dy = direction.vector
                neighbor = (x + dx, y + dy)
                nx, ny = neighbor
                inside_board = (
                    0 <= nx < snapshot.columns
                    and 0 <= ny < snapshot.rows
                )
                if not inside_board:
                    continue
                if neighbor in occupied:
                    continue
                new_g = current_g + 1
                if new_g >= gn.get(neighbor, float("inf")):
                    continue
                gn[neighbor] = new_g
                fn = new_g + heuristic(neighbor)
                heappush(
                    queue,
                    (fn, next(order), new_g, neighbor, first_move),
                )
        return rng.choice(legal_moves)

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
