  # -*- coding: latin-1 -*-
import random
import sys
import math
sys.path.append("..")  #so other modules can be found in parent dir
from Player import *
from Constants import *
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from GameState import addCoords
from AIPlayerUtils import *


##
#AIPlayer
#Description: The responsbility of this class is to interact with the game by
#deciding a valid move based on a given game state. This class has methods that
#will be implemented by students in Dr. Nuxoll's AI course.
#
#Variables:
#   playerId - The id of the player.
##
class AIPlayer(Player):

    #__init__
    #Description: Creates a new Player
    #
    #Parameters:
    #   inputPlayerId - The id to give the new player (int)
    #   cpy           - whether the player is a copy (when playing itself)
    ##
    def __init__(self, inputPlayerId):
        super(AIPlayer,self).__init__(inputPlayerId, "AntBot9000")
        #the coordinates of the agent's food and tunnel will be stored in these
        #variables (see getMove() below)
        self.myFood = None
        self.myTunnel = None
        self.previousQueenHealth = None  # Add this line
    
    ##
    #getPlacement 
    #
    # Agent strategically places anthill and tunnel to allow for efficient food gathering
    # Enemy food is placed as far away from the tunnel as possible.
    #
    def getPlacement(self, currentState):
        self.myFoods = None
        self.myFood = None
        self.myTunnel = None
        self.myHill = None

        if currentState.phase == SETUP_PHASE_1:
            # 1) hill - somewhere on back line
            # 2) worker tunnel - center of board
            # 3-11) grass - few around hill, few at border from hill, one random
            randCoords = (random.randint(0,9), random.randint(0,3))

            moves = [(2,1), (7, 2), 
                    (9,3), (8, 3), (7, 3), (6,3), (5, 3),
                    (4,3), (3,3), (2,3), (1,3)]
            return moves

        elif currentState.phase == SETUP_PHASE_2: # place 2 food, make them as far away from enemy tunnel as possible
            enemyTunnel = getConstrList(currentState, None, (TUNNEL,))[0]

            # find all spots on enemy side of board that are empty
            furthestCoords = []
            for i in range(0, 10):
                for j in range(6, 10):
                    if currentState.board[i][j].constr == None:
                        furthestCoords.append((i,j))

            # sort spots by distance from enemy tunnel
            furthestCoords.sort(key=lambda x: abs(enemyTunnel.coords[0] - x[0]) + abs(enemyTunnel.coords[1] - x[1]))
            moves = []
            # add the two furthest spots to the moves list
            moves.append(furthestCoords[-1]) 
            moves.append(furthestCoords[-2])
            return moves
        else:            
            return None  #should never happen
    
    ##
    #getMove
    #
    # This agent gathers food, sabatoges food collection, and builds drones and ranged soldiers to protect the tunnel.
    #
    ##
    def getMove(self, currentState):
        #Useful pointers
        myInv = getCurrPlayerInventory(currentState)
        me = currentState.whoseTurn
        enemyId = 1 - me
        myQueen = myInv.getQueen()
        foodPathFound = False
        myHill = myInv.getAnthill()


        #the first time this method is called, the food and tunnel locations
        #need to be recorded in their respective instance variables
        if (self.myTunnel == None):
            self.myTunnel = getConstrList(currentState, me, (TUNNEL,))[0]
        if (self.myFood == None):
            foods = getConstrList(currentState, None, (FOOD,))
            # filter out foods that are on enemy side of board
            self.myFoods = [food for food in foods if food.coords[1] < 5]


            #find the most optimal path for food; find which route will be best for food gathering. Only do this once, 
            # as it will use the computationally expensive stepsToReach() function.
            if not foodPathFound:
                foodPathFound = True
                bestDistSoFar = 1000
                for food in self.myFoods:
                    dist = stepsToReach(currentState, self.myTunnel.coords, food.coords)
                    if (dist < bestDistSoFar):
                        self.myFood = food
                        bestDistSoFar = dist
                    dist = stepsToReach(currentState, myHill.coords, food.coords)
                    if (dist < bestDistSoFar):
                        self.myFood = food
                        bestDistSoFar = dist
                    


        #Move the queen off the anthill so we can build stuff
        if (myQueen.coords == myHill.coords):
            return Move(MOVE_ANT, [myQueen.coords, (myQueen.coords[0], myQueen.coords[1]-1)], None)

        
        # --- START WORKER ANT LOGIC ---

        #Build another worker
        myWorkers = getAntList(currentState, me, (WORKER,))
        if (len(myWorkers) < 2 and myInv.foodCount > 0):
            # Check if anthill is clear
            if getAntAt(currentState, myHill.coords) is None:
                return Move(BUILD, [myHill.coords], WORKER)

        
        # Prioritize workers carrying food first (they need to get to tunnel)
        workers = [x for x in myWorkers if not x.hasMoved and x.carrying]
        empty_workers = [x for x in myWorkers if not x.hasMoved and not x.carrying]
        

        # Move carrying workers first
        for worker in workers:
            # Calculate distances to both tunnel and anthill
            tunnel_dist = approxDist(worker.coords, self.myTunnel.coords)
            anthill_dist = approxDist(worker.coords, myHill.coords)
            
            # Choose the closer destination
            if tunnel_dist <= anthill_dist:
                target_coords = self.myTunnel.coords
            else:
                target_coords = myHill.coords
            
            path = createPathToward(currentState, worker.coords,
                                    target_coords, UNIT_STATS[WORKER][MOVEMENT])
            if path and len(path) > 1:  # Make sure we have a valid path
                return Move(MOVE_ANT, path, None)
        

        # Move empty workers toward food
        for worker in empty_workers:
            path = createPathToward(currentState, worker.coords,
                                    self.myFood.coords, UNIT_STATS[WORKER][MOVEMENT])
            if path and len(path) > 1:  # Make sure we have a valid path
                return Move(MOVE_ANT, path, None)
        
        # If pathfinding failed (blocking), try to move workers out of the way
        for worker in myWorkers:
            if not worker.hasMoved:
                adjacent_coords = listReachableAdjacent(currentState, worker.coords, 
                                                       UNIT_STATS[WORKER][MOVEMENT], False)
                if adjacent_coords:
                    # Try to move away from other ants
                    best_move = None
                    min_ants_nearby = 1000
                    
                    for coord in adjacent_coords:
                        # Count nearby ants at this potential position
                        nearby_ants = 0
                        for other_worker in myWorkers:
                            if other_worker != worker:
                                dist = approxDist(coord, other_worker.coords)
                                if dist <= 2:  # Within 2 spaces
                                    nearby_ants += 1
                        
                        if nearby_ants < min_ants_nearby:
                            min_ants_nearby = nearby_ants
                            best_move = coord
                    
                    if best_move:
                        return Move(MOVE_ANT, [worker.coords, best_move], None)
                    
        # --- END WORKER ANT LOGIC ---



        # --- START QUEEN DEFENSE LOGIC ---
        
        # Check if queen was attacked, create a soldier to protect her if no soldier exists; 
        # otherwise move the soldier to protect her
        if self.previousQueenHealth is not None and myQueen.health < self.previousQueenHealth:
            if myInv.foodCount > 1:
                if len(getAntList(currentState, me, (SOLDIER,))) == 0 and getAntAt(currentState, myHill.coords) is None:
                    return Move(BUILD, [myHill.coords], SOLDIER)
                else:
                    if len(getAntList(currentState, me, (SOLDIER,))) != 0:
                        # Move the soldier to protect the queen
                        soldier = getAntList(currentState, me, (SOLDIER,))[0]
                        if not (soldier.hasMoved):
                            path = createPathToward(currentState, soldier.coords,   
                                                (myQueen.coords[0]-1, myQueen.coords[1]), UNIT_STATS[SOLDIER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                        else:
                            return Move(MOVE_ANT, [soldier.coords], None)
        
        # Update previous health
        self.previousQueenHealth = myQueen.health

        # --- END QUEEN LOGIC ---


        # If enemy has no ants but workers, build a drone first.
        # If enemy has ants, build a ranged soldier first for protection
        if len(getAntList(currentState, enemyId, (DRONE,SOLDIER,R_SOLDIER))) == 0:
            if (len(getAntList(currentState, me, (DRONE,))) == 0 and myInv.foodCount > 1 
            and getAntAt(currentState, myHill.coords) is None):
                return Move(BUILD, [myHill.coords], DRONE)
        else:
            if (len(getAntList(currentState, me, (R_SOLDIER,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
                return Move(BUILD, [myHill.coords], R_SOLDIER)


        # If I don't have a drone, build one, make sure hill is not occupied
        if (len(getAntList(currentState, me, (DRONE,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], DRONE)


        # Move my drone toward the enemy anthill or workers
        myDrones = getAntList(currentState, me, (DRONE,))
        for drone in myDrones:
            if not (drone.hasMoved):
                # Or target enemy workers specifically
                enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
                if enemyWorkers:
                    # Target the closest enemy worker
                    closest_worker = min(enemyWorkers, 
                                        key=lambda w: approxDist(drone.coords, w.coords))
                    path = createPathToward(currentState, drone.coords,
                                      closest_worker.coords, UNIT_STATS[DRONE][MOVEMENT])
                    if path and len(path) > 1:
                        return Move(MOVE_ANT, path, None)


        # If the drone is on top of food, the anthill, or tunnel, move it
        myDrones = getAntList(currentState, me, (DRONE,))
        for drone in myDrones:
            move = self.moveAway(currentState, me, drone)
            if move is not None:
                return move


        # --- START RANGED SOLDIER LOGIC ---

        # Make a ranged soldier
        if (len(getAntList(currentState, me, (R_SOLDIER,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], R_SOLDIER)


        # If I have a ranged soldier, move it to escort workers carrying food
        myRangedSoldiers = getAntList(currentState, me, (R_SOLDIER,))
        for soldier in myRangedSoldiers:
            if not (soldier.hasMoved):
                # Find the closest worker
                workers = [x for x in getAntList(currentState, me, (WORKER,))]
                
                if workers:
                    closest_worker = min(workers, 
                                       key=lambda w: approxDist(soldier.coords, w.coords))
                    
                    # Position soldier adjacent to the worker
                    path = createPathToward(currentState, soldier.coords, 
                                          (closest_worker.coords[0]+1, closest_worker.coords[1]), UNIT_STATS[R_SOLDIER][MOVEMENT])
                    if path and len(path) > 1:
                        return Move(MOVE_ANT, path, None)
                else:
                    # No workers carrying food, default to protecting hill
                    target_coords = (myHill.coords[0], myHill.coords[1]+1)
                    path = createPathToward(currentState, soldier.coords, target_coords, UNIT_STATS[R_SOLDIER][MOVEMENT])
                    if path and len(path) > 1:
                        return Move(MOVE_ANT, path, None)


        # If the ranged soldier is on top of food, the anthill, or tunnel, move it
        for soldier in myRangedSoldiers:
            move = self.moveAway(currentState, me, soldier)
            if move is not None:
                return move

        # --- END RANGED SOLDIER LOGIC ---


        #Move the queen off of food if she's on it
        move = self.moveAway(currentState, me, myQueen)
        if move is not None:
            return move


        #If no actions are available, end the turn
        return Move(END, None, None)
    
    ##
    #moveAway
    # 
    # A helper function that moves an ant away from food, tunnel, or anthill if it is on top of one.
    # 
    def moveAway(self, currentState, playerId, ant):
        if not (ant.hasMoved):
            illegalCoords = [food.coords for food in getConstrList(currentState, None, (FOOD,))]
            illegalCoords.append(getConstrList(currentState, playerId, (ANTHILL,))[0].coords)
            illegalCoords.append(self.myTunnel.coords)
            if (ant.coords in illegalCoords):
                    adjacent_coords = listReachableAdjacent(currentState, ant.coords, 
                                                            UNIT_STATS[R_SOLDIER][MOVEMENT], False)
                    if adjacent_coords:
                        # Move to the first available position
                        for coord in adjacent_coords:
                            if coord not in illegalCoords:
                                return Move(MOVE_ANT, [ant.coords, coord], None)
            else:
                # Just move in place if it can't move away or doesn't need to so it can attack
                return Move(MOVE_ANT, [ant.coords], None) 

        return None
    
    ##
    #getAttack
    #
    # This agent never attacks
    #
    def getAttack(self, currentState, attackingAnt, enemyLocations):
        return enemyLocations[0]  #don't care
        
    ##
    #registerWin
    #
    # This agent doens't learn
    #
    def registerWin(self, hasWon):
        #method templaste, not implemented
        pass
