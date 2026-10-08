from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random
from collections import deque
from .models import Direction, GameSnapshot

from datetime import datetime

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
class MyStrategy(MoveStrategy):
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

    
@register_strategy("MINIMAX")
class MiniMax(MoveStrategy):
    # NO HANDLER FOR WHEN THE GAME MODE IS SINGLE PLAYER
    def choose_move(self, snapshot: GameSnapshot, snake_id: str, rng: Random) -> Direction:
        
        # Exception if it was chosen in single player
        if len(snapshot.snakes) < 2:
            raise ValueError("Not enough player! Choose MULTIPLAYER MODE for this algorithm")
        
        # extract snapshot.snakes -> filter the snake that match with snake_id as the agent
        agent = next(s for s in snapshot.snakes if s.snake_id == snake_id)
        opponent = next(s for s in snapshot.snakes if s.snake_id != snake_id)
        
        # print result: options of legal DIRECTION (did not eat its tail, and not hit the wall)
        # e.g. = (<Direction.UP: (0, -1)>, <Direction.LEFT: (-1, 0)>, <Direction.RIGHT: (1, 0)>)
        agent_legal_moves = snapshot.legal_moves_for(agent.snake_id)
        opponent_legal_moves = snapshot.legal_moves_for(opponent.snake_id)        

        agent_state = agent.body
        opponent_state = opponent.body
        
        # print(f"Agent State: {agent_state} ; Opponent State: {opponent_state}")

        # change: new entire body position + legal move
        def result(snake_body,direction:Direction):
            dx, dy = direction.vector
            head_x, head_y = snake_body[0]

            new_body = [(head_x + dx, head_y + dy)] + list(snake_body[:-1])
            print(f"MOVE RESULT FROM: {direction} \n{new_body}")
            
            return new_body
        
        def state_value(snake):
            new_x, new_y = snake[0]
            dist = []
            for apple_x, apple_y in snapshot.apples: # 1. Find all apples and extract each coordinate of them
                dist.append(abs(new_x - apple_x) + abs(new_y - apple_y)) # 2. Calculate distance from current 
            dist.sort()
            # Omitted Heuristics #1
            # if len(dist) > 5:
            #     dist = dist[:4]
            # snake_value = ((sum(dist)/len(dist)*0.5))+(dist[0])
            
            # Omitted Heuristics #2
            # if sum(dist) != 0:
            #     snake_value = - (dist[0] - ((sum(dist)/len(dist))*0.5))
            #     return round(snake_value, 4)
            # else:
            #     return 0

            return - dist[0]
        
        def max_value(state,opponent_state,depth,direction):
            v = float('-inf')
            move = direction
            sim_agent_legal_moves = snapshot.legal_moves_for(agent.snake_id)

            if not snapshot.apples or depth == 0:
                # calculate relative score of 
                node_utility = state_value(state) - state_value(opponent_state) 
                return node_utility, direction #                              (currently)            
            # new state --> extract legal move from that new state
            for move_option in sim_agent_legal_moves:#   new_state   ;         depth ;  chosen action
                new_state = result(state, move_option)
                
                new_v,_ = min_value(new_state, opponent_state, depth-1, move_option)
                if new_v > v:
                    v = new_v
                    move = move_option
            return v, move
        
        def min_value(state,opponent_state,depth,direction): 
            v = float('inf')
            move = direction
            sim_opponent_legal_moves = snapshot.legal_moves_for(opponent.snake_id)

            if not snapshot.apples or depth == 0:
                node_utility = state_value(state) - state_value(opponent_state) 
                return node_utility, direction 
            for move_option in sim_opponent_legal_moves:
                new_state = result(opponent_state, move_option)
                new_v,_ = max_value(state, new_state, depth-1, move_option)
                if new_v < v:
                    v = new_v
                    move = move_option
            return v, move

        
        initial_move = rng.choice(agent_legal_moves)
        alg_start = datetime.now()
        # Limitations: As I don't know how to extract a legal move from a new state
        # increasing the depth to 3 levels or more cannot be performed, 
        # Because there's no (or it hasn't discovered) mechanism to update the 
        # legal move options as the algorithm simulates new state (that will also 
        # generate new set of legal moves)
        minimax_utils,minimax_move = max_value(agent_state, opponent_state, 2, initial_move)
        time_elapsed = datetime.now() - alg_start
        print(f"MINIMAX: \n Chosen Utility Value: {minimax_utils} ; Time elapsed: {time_elapsed}")


        return minimax_move
    
@register_strategy("Alpha Beta Pruning")
class ABPruning(MoveStrategy):
    def choose_move(self, snapshot: GameSnapshot, snake_id: str, rng: Random) -> Direction:
        
        if len(snapshot.snakes) < 2:
            raise ValueError("Not enough player! Choose MULTIPLAYER MODE for this algorithm")
        # print(snapshot.snakes) # results tuples that contain each snake information 
        
        # extract snapshot.snakes -> filter the snake that match with snake_id as the agent
        agent = next(s for s in snapshot.snakes if s.snake_id == snake_id)
        opponent = next(s for s in snapshot.snakes if s.snake_id != snake_id)
        
        agent_legal = snapshot.legal_moves_for(agent.snake_id)
        opponent_legal = snapshot.legal_moves_for(opponent.snake_id)        

        # Terminal State
        if not agent_legal or not snapshot.apples:
            return agent.direction

        agent_state = agent.body[0]
        opponent_state = opponent.body[0]

        print(f"Agent State: {agent_state} ; Opponent State: {opponent_state}")

        def result(state,direction:Direction):
            dx, dy = direction.vector
            new_x, new_y = state[0] + dx, state[1] + dy
            return new_x, new_y

        
        #    Here, I'm thinking that utility value would be represented by the average
        # distance of an agent towards all of available apples.
        #    Since higher distance means that the snake is not in the most ideal position
        # I used (1/utility) as a value to return
        def state_value(state):
            new_x, new_y = state
            dist = []
            for apple_x, apple_y in snapshot.apples: # 1. Find all apples and extract each coordinate of them
                dist.append(abs(new_x - apple_x) + abs(new_y - apple_y)) # 2. Calculate distance from current 
            dist.sort()
            if sum(dist) != 0:
                state_value = - (dist[0] - ((sum(dist)/len(dist))*0.5))
                return round(state_value, 4)
            else:
                return 0

        def max_value(state,opponent_state,depth,direction,alpha,beta):
            v = float('-inf')
            move = direction

            if not snapshot.apples or depth == 0:
                # calculate relative score of 
                node_utility = state_value(state) - state_value(opponent_state) 
                return node_utility, direction #                              (currently)            
            for move_option in agent_legal:#   new_state   ;          opponent info ; depth ;  chosen action
                new_v,new_move = min_value(result(state,move_option), opponent_state, depth-1, move_option, alpha, beta)
                if new_v > v:
                    v = new_v
                    alpha = max(alpha,v)
                    move = move_option
                # argument to cutout search
                if v >= beta:
                    return v, move
            return v, move
        
        def min_value(state,opponent_state,depth,direction,alpha,beta): 
            v = float('inf')
            move = direction

            if not snapshot.apples or depth == 0:
                node_utility = state_value(state) - state_value(opponent_state) 
                return node_utility, direction 
            for move_option in opponent_legal:
                new_v,new_move = max_value(state,result(opponent_state, move_option), depth-1, move_option, alpha, beta)
                if new_v < v:
                    v = new_v
                    beta = min(beta,v)
                    move = move_option
                if v <= alpha:
                    return v, move
            return v, move

        best_state_value = max(state_value(result(agent_state,direction)) for direction in agent_legal)
        best_moves = [direction for direction in agent_legal if state_value(result(agent_state,direction)) == best_state_value]

        alg_start = datetime.now()
        alphabeta_utils,alphabeta_move = max_value(agent_state, opponent_state, 2, rng.choice(best_moves),float('-inf'),float('inf'))
        print(alphabeta_utils)
        time_elapsed = datetime.now() - alg_start
        print(f"ALPHA BETA: \nChosen Utility Value: {alphabeta_utils} ; Time elapsed: {time_elapsed}")

        return alphabeta_move

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
