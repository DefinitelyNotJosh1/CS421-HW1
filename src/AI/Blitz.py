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
        super(AIPlayer,self).__init__(inputPlayerId, "Blitz") # Named due to it's blitzkrieg-esque gameplay
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
        self.attackMode = True # set to true for debugging


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
        #   isAgressive - Ignores be
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



        # --- START ATTACK MODE LOGIC ---


        # If it seems the enemy will wil before us due to food gathering, switch to attack mode.
        # Drone ants will throw caution to the wind and attack workers more aggressively.
        if enemyInv.foodCount == 8 and myInv.foodCount < 8:
            print("Attack mode activated")
            self.attackMode = True


        if self.attackMode:
            # Build soldiers with all food
            if myInv.foodCount > 1 and getAntAt(currentState, myHill.coords) is None:
                return Move(BUILD, [myHill.coords], SOLDIER)
            
            # Move towards enemy queen with all units
            enemyQueen = getAntList(currentState, enemyId, (QUEEN,))[0]
            print("Enemy queen at %s" % str(enemyQueen.coords))

            myAnts = getAntList(currentState, me, (SOLDIER, R_SOLDIER))
            print("Attacking with %d soldiers" % len(myAnts))
            for ant in myAnts:
                if not (ant.hasMoved):
                    print("Moving %s at %s towards enemy queen" % (ant.type, str(ant.coords)))
                    path = createPathToward(currentState, ant.coords, enemyQueen.coords, False)
                    if path:
                        print("Path found: %s" % str(path))
                        return Move(MOVE_ANT, path, None)
                    else:
                        print("No path found, attacking in place")
                        return Move(MOVE_ANT, [ant.coords], None)


        # --- END ATTACK MODE LOGIC ---
        

        # --- START ANT UNSTUCK LOGIC ---


        # Check if it's been a few turns since the last time we've collected food;
        # this is how we get ants unstuck if there happens to be a bunch of collisions.

        if self.firstMove:
            self.firstMove = False
            self.foodCount.append(myInv.foodCount)

            if len(self.foodCount) > 20:
                if (self.foodCount[-1] == self.foodCount[-2] == self.foodCount[-3] == 
                    self.foodCount[-4] == self.foodCount[-5]):
                    # print("Food count is the same for multiple turns in a row, getting ants unstuck")
                    self.foodCount = [] # Reset food count list
                    antList = getAntList(currentState, me, (WORKER, QUEEN, R_SOLDIER, DRONE, SOLDIER))
                    random.shuffle(antList)
                    for ant in antList:
                        if not (ant.hasMoved):
                            randomCoord = (random.randint(0, 9), random.randint(0, 3))
                            path = createPathToward(currentState, ant.coords, randomCoord, 
                                                    UNIT_STATS[ant.type][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)

            elif len(self.foodCount) > 60:
                self.foodCount = [] # don't let list grow infinitely


        # --- END ANT UNSTUCK LOGIC ---


        #Move the queen off the anthill so we can build stuff
        if not myQueen.hasMoved:
            move = moveAway(currentState, myQueen)
            if move is not None:
                return move

        
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
                    random.shuffle(adjacentCoords)
                    # Try to move away from other ants
                    return Move(MOVE_ANT, [worker.coords, adjacentCoords[0]], None)
                    

        # --- END WORKER ANT LOGIC ---


        # --- START QUEEN DEFENSE LOGIC ---
        

        # Check if queen was attacked, create a soldier to protect her if no soldier exists; 
        # otherwise move the soldier to protect her
        if self.previousQueenHealth is not None and myQueen.health < self.previousQueenHealth:
            print("Queen was attacked")
            if myInv.foodCount > 1:
                if len(getAntList(currentState, me, (SOLDIER,))) == 0 and getAntAt(currentState, myHill.coords) is None:
                    print("Building soldier at hill")
                    return Move(BUILD, [myHill.coords], SOLDIER)

            if len(mySoldiers) != 0:
                # Move the soldier to attack closest enemy ant to queen
                for soldier in mySoldiers:
                    if not (soldier.hasMoved):
                        enemyAnts = getAntList(currentState, enemyId, (DRONE,SOLDIER,R_SOLDIER,QUEEN))
                        closestEnemy = min(enemyAnts, key=lambda x: approxDist(myQueen.coords, x.coords))

                        path = createPathToward(currentState, soldier.coords, closestEnemy.coords, UNIT_STATS[SOLDIER][MOVEMENT])
                        if path and len(path) > 1:
                            return Move(MOVE_ANT, path, None)
                        
                        # move in place otherwise
                        return Move(MOVE_ANT, [soldier.coords], None)
        
            # Now move the queen into a safe position
            if not myQueen.hasMoved:
                safeMoves = findSafeMoves(currentState, myQueen, enemyId, False)
                for moves in safeMoves:
                    if getAntAt(currentState, moves) is None:
                        return Move(MOVE_ANT, moves, None)
                return Move(MOVE_ANT, [myQueen.coords], None)

        
        # Update previous health
        self.previousQueenHealth = myQueen.health
        # print("Queen health: %d" % myQueen.health)


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
                        potentialTargets = listAdjacent(myHill.coords)
                        potentialTargets.append(myHill.coords)
                        random.shuffle(potentialTargets)
                        
                        for target in potentialTargets:
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
        # TODO: MAKE DRONES ATTACK IF THEY WON'T DIE FROM ATTACKER (DRONE OR R_SOLDIER)


        # If I don't have a drone, build one, make sure hill is not occupied
        if (len(getAntList(currentState, me, (DRONE,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], DRONE)

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


        # Make a ranged soldier if enemy has ants other than workers and a queen
        if (len(getAntList(currentState, enemyId, (DRONE,SOLDIER,R_SOLDIER))) > 0 and 
        len(getAntList(currentState, me, (R_SOLDIER,))) == 0 and myInv.foodCount > 1 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], R_SOLDIER)


        # If I have a ranged soldier, move it to escort workers carrying food
        for soldier in myRangedSoldiers:
            if not (soldier.hasMoved):
                # Find the closest worker
                workers = [x for x in getAntList(currentState, me, (WORKER,))]
                
                if workers:
                    closestWorker = min(workers, key=lambda w: approxDist(soldier.coords, w.coords))
                    
                    # Find positions adjacent to the closest worker
                    potentialTargets = listAdjacent(closestWorker.coords)
                    random.shuffle(potentialTargets)
                    foodCoords = [x.coords for x in self.myFoods]

                    for target in potentialTargets:
                        # Check if target is valid and not occupied
                        if (legalCoord(target) and getAntAt(currentState, target) is None
                            and target != soldier.coords and target not in foodCoords):
                            path = createPathToward(currentState, soldier.coords, target, UNIT_STATS[R_SOLDIER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            break
                else:
                    # No workers, default to protecting hill
                    potentialTargets = listAdjacent(myHill.coords)
                    potentialTargets.append(myHill.coords)

                    random.shuffle(potentialTargets)
                    
                    for target in potentialTargets:
                        # Check if target is valid and not occupied
                        if (legalCoord(target) and getAntAt(currentState, target) is None 
                            and target != soldier.coords):
                            path = createPathToward(currentState, soldier.coords, target, UNIT_STATS[R_SOLDIER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            break

        
        # --- END RANGED SOLDIER LOGIC ---
  
   
        # --- START CLEANUP ---


        # If a ranged soldier is on top of food, the anthill, or tunnel, move it
        for soldier in myRangedSoldiers:
            move = moveAway(currentState, soldier)
            if move is not None:
                return move
        
        # If a soldier is on top of food, the anthill, or tunnel, move it
        for soldier in mySoldiers:
            move = moveAway(currentState, soldier)
            if move is not None:
                return move



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
