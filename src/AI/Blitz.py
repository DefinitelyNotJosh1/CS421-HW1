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
        super(AIPlayer,self).__init__(inputPlayerId, "Blitz") # Named due to it's blitzkrieg-esque gameplay
        #the coordinates of the agent's food and tunnel will be stored in these
        #variables (see getMove() below)
        self.myFood = None
        self.myTunnel = None
        self.previousQueenHealth = None
        self.previousHillHealth = None
    
    ##
    #getPlacement 
    #
    # Places anthill and tunnel for efficient food gathering.
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

            moves = [(2,1), (7, 2), 
                    (9,3), (8, 3), (7, 3), (6,3), (5, 3),
                    (4,3), (3,3), (2,3), (1,3)]
            return moves
        # place 2 food, make them as far away from enemy tunnel and hill as possible
        elif currentState.phase == SETUP_PHASE_2:
            enemyTunnel = getConstrList(currentState, None, (TUNNEL,))[0]
            enemyHill = getConstrList(currentState, None, (ANTHILL,))[0]

            # find all spots on enemy side of board that are empty
            furthestCoords = []
            for i in range(0, 10):
                for j in range(6, 10):
                    if currentState.board[i][j].constr == None:
                        furthestCoords.append((i,j))

            # sort spots by distance from enemy tunnel
            furthestCoords.sort(key=lambda x: 
                        abs(enemyTunnel.coords[0] - x[0]) + abs(enemyTunnel.coords[1] - x[1]) + 
                        abs(enemyHill.coords[0] - x[0]) + abs(enemyHill.coords[1] - x[1]))
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
    # Parameters:
    #   currentState - the current game state
    #
    # Returns:
    #   A Move object if the ant was moved, None otherwise
    #
    def getMove(self, currentState):
        #Useful pointers
        myInv = getCurrPlayerInventory(currentState)
        me = currentState.whoseTurn
        enemyId = 1 - me
        myQueen = myInv.getQueen()
        foodPathFound = False
        myHill = myInv.getAnthill()
        myDrones = getAntList(currentState, me, (DRONE,))
        myRangedSoldiers = getAntList(currentState, me, (R_SOLDIER,))


        ##
        # moveAway
        #
        # Moves an ant away from food, tunnel, or anthill if it is on top of one.
        # If no adjacent position is available, move ant in place to attack.
        # If ant is not on top of food, tunnel, or anthill, move in place to attack.
        #
        # Parameters:
        #   currentState - the current game state
        #   playerId - the id of the player
        #   ant - the ant to move
        #
        # Returns:
        #   A Move object if the ant was moved, None otherwise
        #
        def moveAway(currentState, ant):
            if not (ant.hasMoved):
                illegalCoords = self.myFoods
                illegalCoords.append(myHill.coords)
                illegalCoords.append(self.myTunnel.coords)
                if (ant.coords in illegalCoords):
                    adjacent_coords = listReachableAdjacent(currentState, ant.coords, 
                                                            UNIT_STATS[ant.type][MOVEMENT], UNIT_STATS[ant.type][IGNORES_GRASS])
                    if adjacent_coords:
                        # Move to a random available position that's not illegal
                        random.shuffle(adjacent_coords)
                        for coord in adjacent_coords:
                            if coord not in illegalCoords and getAntAt(currentState, coord) is None:
                                return Move(MOVE_ANT, [ant.coords, coord], None)
                        # If no adjacent position is available, move ant in place to attack
                        return Move(MOVE_ANT, [ant.coords], None)
                # Move ant in  place to attack otherwise
                else: 
                    return Move(MOVE_ANT, [ant.coords], None)

            return None


        ##
        # isSafePosition
        #
        # Checks if a position is safe for an ant to move to by checking if it is within enemy attack range.
        #
        # Parameters:
        #   currentState - the current game state
        #   coords - the coordinates to check
        #   enemyPlayerId - the id of the enemy player
        #
        # Returns:
        #   True if the position is safe, False otherwise
        #
        def isSafePosition(currentState, coords, enemyPlayerId):
            enemyAnts = getAntList(currentState, enemyPlayerId, (DRONE,SOLDIER,R_SOLDIER,QUEEN))
            for enemyAnt in enemyAnts:
                # Enemy range is the sum of their range and movement, as they can move before attacking
                enemyRange = UNIT_STATS[enemyAnt.type][RANGE] + UNIT_STATS[enemyAnt.type][MOVEMENT]
                distance = approxDist(coords, enemyAnt.coords)

                # If within enemy attack range, return false
                if distance <= enemyRange:
                    return False
            return True

        ##
        # findSafeMoves
        #
        # Finds all safe moves for an ant to move to by checking if it is within enemy attack range.
        #
        # Parameters:
        #   currentState - the current game state
        #   ant - the ant to find safe moves for
        #   enemyPlayerId - the id of the enemy player
        #
        # Returns:
        #   A list of safe move coordinates
        #
        def findSafeMoves(currentState, ant, enemyPlayerId):
            safeMoves = []

            possiblePaths = listAllMovementPaths(currentState, ant.coords, 
                                        UNIT_STATS[ant.type][MOVEMENT], True)
            for path in possiblePaths:
                if len(path) > 0:
                    finalCoord = path[-1]  # Get the last coordinate in the path
                    if isSafePosition(currentState, finalCoord, enemyPlayerId):
                        safeMoves.append(finalCoord)
            return safeMoves



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
        emptyWorkers = [x for x in myWorkers if not x.hasMoved and not x.carrying]
        

        # Move carrying workers first
        for worker in workers:
            # Calculate distances to both tunnel and anthill
            tunnelDist = approxDist(worker.coords, self.myTunnel.coords)
            anthillDist = approxDist(worker.coords, myHill.coords)
            
            # Choose the closer destination
            if tunnelDist <= anthillDist:
                targetCoords = self.myTunnel.coords
            else:
                targetCoords = myHill.coords
            
            path = createPathToward(currentState, worker.coords,
                                    targetCoords, UNIT_STATS[WORKER][MOVEMENT])
            if path and len(path) > 1:  # Make sure we have a valid path
                return Move(MOVE_ANT, path, None)
        

        # Move empty workers toward food
        for worker in emptyWorkers:
            path = createPathToward(currentState, worker.coords,
                                    self.myFood.coords, UNIT_STATS[WORKER][MOVEMENT])
            if path and len(path) > 1:  # Make sure we have a valid path
                return Move(MOVE_ANT, path, None)
        

        # If pathfinding failed (blocking), try to move workers out of the way
        for worker in myWorkers:
            if not worker.hasMoved:
                adjacentCoords = listReachableAdjacent(currentState, worker.coords, 
                                                       UNIT_STATS[WORKER][MOVEMENT], False)
                if adjacentCoords:
                    # Try to move away from other ants
                    bestMove = None
                    minAntsNearby = 1000
                    
                    for coord in adjacentCoords:
                        # Count nearby ants at this potential position
                        nearbyAnts = 0
                        for otherWorker in myWorkers: 
                            if otherWorker != worker:
                                dist = approxDist(coord, otherWorker.coords)
                                if dist <= 2:  # Within 2 spaces
                                    nearbyAnts += 1
                        
                        if nearbyAnts < minAntsNearby:
                            minAntsNearby = nearbyAnts
                            bestMove = coord
                    
                    if bestMove:
                        return Move(MOVE_ANT, [worker.coords, bestMove], None)
                    

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
                            # Try multiple positions around the queen to find a valid target
                            potential_targets = [
                                (myQueen.coords[0]-1, myQueen.coords[1]),
                                (myQueen.coords[0]+1, myQueen.coords[1]),
                                (myQueen.coords[0], myQueen.coords[1]-1),
                                (myQueen.coords[0], myQueen.coords[1]+1)
                            ]
                            
                            for target in potential_targets:
                                if legalCoord(target) and getAntAt(currentState, target) is None and target != soldier.coords:
                                    path = createPathToward(currentState, soldier.coords, target, UNIT_STATS[SOLDIER][MOVEMENT])
                                    if path and len(path) > 1:
                                        return Move(MOVE_ANT, path, None)
                            
                            # If no movement possible, attack in place
                            return Move(MOVE_ANT, [soldier.coords], None)
        
        # Update previous health
        self.previousQueenHealth = myQueen.health


        # --- END QUEEN DEFENSE LOGIC ---


        # --- START HILL DEFENSE LOGIC ---
        

        # Check if hill was attacked, defend it if so with any ants capable of doing so
        if self.previousHillHealth is not None and myHill.captureHealth < self.previousHillHealth:
            myAnts = getAntList(currentState, me, (SOLDIER, R_SOLDIER, DRONE))
            if len(myAnts) != 0:
                # Move ants to protect the hill
                for ant in myAnts:
                    if not (ant.hasMoved):
                        # Try multiple positions around the hill to find a valid target
                        potential_targets = [
                            (myHill.coords[0]-1, myHill.coords[1]),
                            (myHill.coords[0]+1, myHill.coords[1]),
                            (myHill.coords[0], myHill.coords[1]-1),
                            (myHill.coords[0], myHill.coords[1]+1)
                        ]
                        
                        for target in potential_targets:
                            if legalCoord(target) and target != ant.coords:
                                path = createPathToward(currentState, ant.coords, target, UNIT_STATS[ant.type][MOVEMENT])
                                if path and len(path) > 1:
                                    return Move(MOVE_ANT, path, None)
                        
                        # If no movement possible, attack in place
                        return Move(MOVE_ANT, [ant.coords], None)
        
        # Update previous health
        self.previousHillHealth = myHill.captureHealth


        # --- END HILL DEFENSE LOGIC ---


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

        
        # --- START DRONE LOGIC ---


        # If I don't have a drone, build one, make sure hill is not occupied
        if (len(getAntList(currentState, me, (DRONE,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], DRONE)


        # MY OLD CODE - WORKS, BUT LETS MAKE IT BETTER
        # Move my drone toward enemy workers while avoiding enemies
        # for drone in myDrones:
        #     if not (drone.hasMoved):
        #         # Or target enemy workers specifically
        #         enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
        #         if enemyWorkers:
        #             # Target the closest enemy worker
        #             closest_worker = min(enemyWorkers, 
        #                                 key=lambda w: approxDist(drone.coords, w.coords))
        #             path = createPathToward(currentState, drone.coords,
        #                               closest_worker.coords, UNIT_STATS[DRONE][MOVEMENT])
        #             if path and len(path) > 1:
        #                 return Move(MOVE_ANT, path, None)
        #         else:
        #             # No enemy workers, retreat to (5,3)
        #             retreatTarget = (5, 3)
        #             if legalCoord(retreatTarget):
        #                 path = createPathToward(currentState, drone.coords,
        #                                       retreatTarget, UNIT_STATS[DRONE][MOVEMENT])
        #                 if path and len(path) > 1:
        #                     return Move(MOVE_ANT, path, None)
        # END MY OLD CODE
        for drone in myDrones:
            if not (drone.hasMoved):
                # Get enemy workers
                enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
                
                # Find safe moves for the drone
                safeMoves = findSafeMoves(currentState, drone, enemyId)
                
                if enemyWorkers and safeMoves:
                    # Target the closest enemy worker, but only move to safe positions
                    closestWorker = min(enemyWorkers,
                                        key=lambda w: approxDist(drone.coords, w.coords))
                    
                    # Among safe moves, choose the one that gets closest to the target
                    bestSafeMove = min(safeMoves,
                                       key=lambda m: approxDist(m, closestWorker.coords))
                    
                    # Create path to the best safe move
                    path = createPathToward(currentState, drone.coords,
                                            bestSafeMove, UNIT_STATS[DRONE][MOVEMENT])
                    if path and len(path) > 1:
                        return Move(MOVE_ANT, path, None)
                else:
                     # No enemy workers, retreat to (5,3)
                    retreatTarget = (5, 3)
                    if legalCoord(retreatTarget):
                        path = createPathToward(currentState, drone.coords,
                                            retreatTarget, UNIT_STATS[DRONE][MOVEMENT])
                        if path and len(path) > 1:
                            return Move(MOVE_ANT, path, None)
                        else: 
                            return Move(MOVE_ANT, [drone.coords], None)
        # END MY NEW CODE



        # --- END DRONE LOGIC ---


        # --- START RANGED SOLDIER LOGIC ---


        # Make a ranged soldier
        if (len(getAntList(currentState, me, (R_SOLDIER,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], R_SOLDIER)


        # If I have a ranged soldier, move it to escort workers carrying food
        for soldier in myRangedSoldiers:
            if not (soldier.hasMoved):
                # Find the closest worker
                workers = [x for x in getAntList(currentState, me, (WORKER,))]
                
                if workers:
                    closestWorker = min(workers, 
                                       key=lambda w: approxDist(soldier.coords, w.coords))
                    
                    # Try multiple positions adjacent to the worker to find a valid one
                    potential_targets = [
                        (closestWorker.coords[0]+1, closestWorker.coords[1]),
                        (closestWorker.coords[0]-1, closestWorker.coords[1]),
                        (closestWorker.coords[0], closestWorker.coords[1]+1),
                        (closestWorker.coords[0], closestWorker.coords[1]-1)
                    ]
                    
                    for target in potential_targets:
                        # Check if target is valid and not occupied
                        if (legalCoord(target) and getAntAt(currentState, target) is None 
                            and target != soldier.coords):
                            path = createPathToward(currentState, soldier.coords, target, UNIT_STATS[R_SOLDIER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            break
                else:
                    # No workers, default to protecting hill with valid coordinates
                    potential_targets = [
                        (myHill.coords[0], myHill.coords[1]+1),
                        (myHill.coords[0], myHill.coords[1]-1),
                        (myHill.coords[0]+1, myHill.coords[1]),
                        (myHill.coords[0]-1, myHill.coords[1])
                    ]
                    
                    for target in potential_targets:
                        # Check if target is valid and not occupied
                        if (legalCoord(target) and getAntAt(currentState, target) is None 
                            and target != soldier.coords):
                            path = createPathToward(currentState, soldier.coords, target, UNIT_STATS[R_SOLDIER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            break

        
        # --- END RANGED SOLDIER LOGIC ---
  
   
        # --- START CLEANUP LOGIC ---


        # If the ranged soldier is on top of food, the anthill, or tunnel, move it
        for soldier in myRangedSoldiers:
            move = moveAway(currentState, soldier)
            if move is not None:
                return move


        #Move the queen off of food if she's on it
        move = moveAway(currentState, myQueen)
        if move is not None:
            return move


        # If a drone is on top of food, the anthill, or tunnel, move it
        for drone in myDrones:
            move = moveAway(currentState, drone)
            if move is not None:
                return move


        #If no actions are available, end the turn
        return Move(END, None, None)


        # --- END CLEANUP LOGIC ---
    
    
    
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
