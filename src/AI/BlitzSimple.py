# AUTHOR: Joshua Krasnogorov
# HW1 for CS-421.
# Used FoodGatherer.py as a starting point.

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
        super(AIPlayer,self).__init__(inputPlayerId, "Blitz Simple") # Named due to it's blitzkrieg-esque gameplay
        #the coordinates of the agent's food and tunnel will be stored in these
        #variables (see getMove() below)
        self.myFood = None
        self.myFoods = None
        self.myTunnel = None
        self.myHill = None
        self.previousQueenHealth = None
        self.previousHillHealth = None
        self.foodCount = []
        self.firstMove = True
        self.attackMode = False
    
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
        self.foodCount.append(getCurrPlayerInventory(currentState).foodCount)
        self.firstMove = True
        self.attackMode = False

        if currentState.phase == SETUP_PHASE_1:

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
    # This agent gathers food quickly, sabatoges enemy food collection, and protects its queen and hill.
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
        enemyInv = getEnemyInv(me, currentState)
        enemyId = 1 - me
        myQueen = myInv.getQueen()
        foodPathFound = False
        myHill = myInv.getAnthill()
        myDrones = getAntList(currentState, me, (DRONE,))
        myRangedSoldiers = getAntList(currentState, me, (R_SOLDIER,))
        mySoldiers = getAntList(currentState, me, (SOLDIER,))
        myWorkers = getAntList(currentState, me, (WORKER,))
        # self.attackMode = False # set to true for debugging


        ##
        # moveAway - HELPER
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
                illegalCoords = getConstrList(currentState, None, (FOOD,))
                illegalCoords = [food.coords for food in illegalCoords]
                illegalCoords.append(myHill.coords)
                illegalCoords.append(self.myTunnel.coords)
                if (ant.coords in illegalCoords):
                    # print("%s is on top of illegal coords, %s" % (ant.type, str(ant.coords)))
                    adjacent_coords = listReachableAdjacent(currentState, ant.coords, 
                                                            UNIT_STATS[ant.type][MOVEMENT], UNIT_STATS[ant.type][IGNORES_GRASS])
                    if adjacent_coords:
                        # Move to a random available position that's not illegal
                        random.shuffle(adjacent_coords)
                        for coord in adjacent_coords:
                            # print("Checking %s" % str(coord))
                                if coord not in illegalCoords and getAntAt(currentState, coord) is None:
                                    # print("Moving to %s" % str(coord))
                                    return Move(MOVE_ANT, [ant.coords, coord], None)
                        # If no adjacent position is available, move ant in place to attack
                        return Move(MOVE_ANT, [ant.coords], None)
                # Move ant in  place to attack otherwise
                else: 
                    return Move(MOVE_ANT, [ant.coords], None)

            return None


        ##
        # isSafePosition - HELPER
        #
        # Checks if a position is safe for an ant to move to by checking if it is within enemy attack range.
        #
        # Parameters:
        #   currentState - the current game state
        #   coords - the coordinates to check
        #   enemyPlayerId - the id of the enemy player
        #   isAgressive - If false, checks if within movement range + attack range of enemy ants
        #                 If true, only checks if within attack range of enemy ants
        #
        # Returns:
        #   True if the position is safe, False otherwise
        #
        def isSafePosition(currentState, coords, enemyPlayerId, isAgressive):
            enemyAnts = getAntList(currentState, enemyPlayerId, (DRONE,SOLDIER,R_SOLDIER,QUEEN))
            for enemyAnt in enemyAnts:
                # Enemy range is the sum of their range and movement, as they can move before attacking
                enemyRange = UNIT_STATS[enemyAnt.type][RANGE]
                if not isAgressive:
                    enemyRange = enemyRange + UNIT_STATS[enemyAnt.type][MOVEMENT]
                distance = approxDist(coords, enemyAnt.coords)

                # If within enemy attack range, return false
                if distance <= enemyRange:
                    return False
            return True

        ##
        # findSafeMoves - HELPER
        #
        # Finds all safe moves for an ant to move to by checking if it is within enemy attack range.
        #
        # Parameters:
        #   currentState - the current game state
        #   ant - the ant to find safe moves for
        #   enemyPlayerId - the id of the enemy player
        #   isAgressive - If false, checks if within movement range + attack range of enemy ants
        #                 If true, only checks if within attack range of enemy ants
        #
        # Returns:
        #   A list of safe move coordinates
        #
        def findSafeMoves(currentState, ant, enemyPlayerId, isAgressive):
            safeMoves = []

            possiblePaths = listAllMovementPaths(currentState, ant.coords, 
                                        UNIT_STATS[ant.type][MOVEMENT], True)
            for path in possiblePaths:
                if len(path) > 0:
                    finalCoord = path[-1]  # Get the last coordinate in the path
                    if isSafePosition(currentState, finalCoord, enemyPlayerId, isAgressive):
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

            #find the most optimal path for food
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


        


        #Move the queen off the anthill so we can build stuff - unless an enemy ant is in range and on our side of the board
        if not myQueen.hasMoved:
            # First check if there are any enemy drones in attack range
            enemyAnts = getAntList(currentState, enemyId, (DRONE, SOLDIER,))
            if enemyAnts:
                for enemyDrone in enemyAnts:
                    distance = approxDist(myQueen.coords, enemyDrone.coords)
                    if distance <= UNIT_STATS[QUEEN][RANGE] + UNIT_STATS[QUEEN][MOVEMENT]:
                        # Attack the enemy drone if it's in range
                        path = createPathToward(currentState, myQueen.coords, enemyDrone.coords, UNIT_STATS[QUEEN][MOVEMENT])
                        if path and isPathOkForQueen(path) and len(path) > 1:
                            return Move(MOVE_ANT, path, None)
                        else:
                            return Move(MOVE_ANT, [myQueen.coords], None)
            
            move = moveAway(currentState, myQueen)
            if move is not None:
                return move

        
        # --- START WORKER ANT LOGIC ---



        # If I don't have any workers, build one if it's safe
        if (len(myWorkers) == 0 and myInv.foodCount > 0):
            if getAntAt(currentState, myHill.coords) is None and isSafePosition(currentState, myHill.coords, enemyId, True):
                print("No food, building worker")
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
                    random.shuffle(adjacentCoords)
                    # Try to move away from other ants
                    return Move(MOVE_ANT, [worker.coords, adjacentCoords[0]], None)
                    

        # End my turn if I'm about to win; don't build anything
        if myInv.foodCount > 10:
            myAnts = getAntList(currentState, me, (QUEEN, R_SOLDIER, DRONE, SOLDIER))
            for ant in myAnts:
                if not (ant.hasMoved):
                    move = moveAway(currentState, ant)
            return Move(END, None, None)
        

        # --- END WORKER ANT LOGIC ---


        
        # --- START DRONE LOGIC ---

        for drone in myDrones:
            if not (drone.hasMoved):
                # Get enemy workers
                enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
                
                # Find safe moves for the drone
                safeMoves = findSafeMoves(currentState, drone, enemyId, self.attackMode)
                
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
                     # No enemy workers, stay on enemy side of board
                    safeMoves = findSafeMoves(currentState, drone, enemyId, False)
                    if safeMoves:
                        bestSafeMove = min(safeMoves,
                                           key=lambda m: approxDist(m, enemyDrone.coords))
                        path = createPathToward(currentState, drone.coords,
                                                bestSafeMove, UNIT_STATS[DRONE][MOVEMENT])
                        if path:
                            return Move(MOVE_ANT, path, None)


        # --- END DRONE LOGIC ---


        
        # --- START CLEANUP ---



        # If a drone is on top of food, the anthill, or tunnel, move it
        for drone in myDrones:
            move = moveAway(currentState, drone)
            if move is not None:
                return move


        #If no actions are available, end the turn
        self.firstMove = True
        return Move(END, None, None)


        # --- END CLEANUP ---
    
    
    
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
