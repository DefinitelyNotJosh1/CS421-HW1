# AUTHOR: Joshua Krasnogorov
# HW1 for CS-421.
# Used one of the other AI's as a starting point - if I'm honest I can't remember which ones

# CREDIT - Used Claude Sonnet 4 to generate header comments for most of the methods
# I read over the coding guidelines and had to refactor my getMove method (my fault)
# so it just made my job a bit easier to have them generated


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
        myWorkers = getAntList(currentState, me, (WORKER,))


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

        # Cycle through all the logic methods
        
        # Attack Mode Logic
        move = self.handleAttackMode(currentState, myInv, enemyInv, myWorkers, me, enemyId, myHill)
        if move is not None:
            return move
        
        # Ant Unstuck Logic
        move = self.handleAntUnstuckLogic(currentState, myInv, me)
        if move is not None:
            return move
        
        # Queen Movement
        move = self.handleQueenMovement(currentState, myQueen, enemyId, myHill)
        if move is not None:
            return move
        
        # Worker Ant Logic
        move = self.handleWorkerAntLogic(currentState, myInv, me, enemyId, myHill, myQueen)
        if move is not None:
            return move
        
        # Queen Defense Logic
        move = self.handleQueenDefenseLogic(currentState, myInv, me, enemyId, myHill, myQueen, mySoldiers)
        if move is not None:
            return move
        
        # Hill Defense Logic
        move = self.handleHillDefenseLogic(currentState, me, myHill)
        if move is not None:
            return move
        
        # Unit Building
        move = self.handleUnitBuilding(currentState, myInv, me, myHill)
        if move is not None:
            return move
        
        # Drone Logic
        move = self.handleDroneLogic(currentState, myDrones, enemyId)
        if move is not None:
            return move
        
        # Soldier Logic
        move = self.handleSoldierLogic(currentState, enemyId, me, myInv, myHill, mySoldiers)
        if move is not None:
            return move
        
        # Cleanup
        return self.handleCleanup(currentState, myRangedSoldiers, mySoldiers, myDrones)


    ##
    # moveAway - HELPER
    #
    # Moves an ant away from food, tunnel, or anthill if it is on top of one.
    # If no adjacent position is available, move ant in place to attack.
    # If ant is not on top of food, tunnel, or anthill, move in place to attack.
    #
    # Parameters:
    #   currentState - the current game state
    #   ant - the ant to move
    #
    # Returns:
    #   A Move object if the ant was moved, None otherwise
    #
    def moveAway(self, currentState, ant):
        myHill = getCurrPlayerInventory(currentState).getAnthill()
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
    def isSafePosition(self, currentState, coords, enemyPlayerId, isAgressive):
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
    def findSafeMoves(self, currentState, ant, enemyPlayerId, isAgressive):
        safeMoves = []

        possiblePaths = listAllMovementPaths(currentState, ant.coords, 
                                    UNIT_STATS[ant.type][MOVEMENT], True)
        for path in possiblePaths:
            if len(path) > 0:
                finalCoord = path[-1]  # Get the last coordinate in the path
                if self.isSafePosition(currentState, finalCoord, enemyPlayerId, isAgressive):
                    safeMoves.append(finalCoord)
        return safeMoves

    ##
    # handleAttackMode - 
    #
    # Handles attack mode logic. If it seems the enemy will win before us due to food gathering,
    # switch to attack mode. Drone ants will throw caution to the wind and attack workers more aggressively.
    #
    # Parameters:
    #   currentState - the current game state
    #   myInv - current player's inventory
    #   enemyInv - enemy player's inventory
    #   myWorkers - list of worker ants
    #   me - current player id
    #   enemyId - enemy player id
    #   myHill - current player's anthill
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleAttackMode(self, currentState, myInv, enemyInv, myWorkers, me, enemyId, myHill):
        # If it seems the enemy will win before us due to food gathering, switch to attack mode.
        # Drone ants will throw caution to the wind and attack workers more aggressively.
        if enemyInv.foodCount > 5 and myInv.foodCount < 5 or enemyInv.foodCount > 8 and myInv.foodCount < 7:
            # print("Attack mode activated, my food count: %d, enemy food count: %d" % (myInv.foodCount, enemyInv.foodCount))
            self.attackMode = True

        if myInv.foodCount == 0 and len(myWorkers) == 0:
            # print("attack mode activated, no more workers")
            self.attackMode = True

        if self.attackMode:
            # Build soldiers with all food
            if myInv.foodCount > 1 and getAntAt(currentState, myHill.coords) is None:
                return Move(BUILD, [myHill.coords], SOLDIER)
            
            # Move towards enemy hill with all units
            enemyHill = getConstrList(currentState, enemyId, (ANTHILL,))[0]
            # print("Enemy queen at %s" % str(enemyQueen.coords))

            myAnts = getAntList(currentState, me, (SOLDIER, R_SOLDIER))
            # print("Attacking with %d soldiers" % len(myAnts))
            for ant in myAnts:
                # print("Considering %s at %s, movement status: %s" % (ant.type, str(ant.coords), str(ant.hasMoved)))
                if not (ant.hasMoved):
                    # print("Moving %s at %s towards enemy queen" % (ant.type, str(ant.coords)))
                    path = createPathToward(currentState, ant.coords, enemyHill.coords, UNIT_STATS[ant.type][MOVEMENT]) # CHANGED TO HILL
                    if path and len(path) > 1:
                        # print("Path found: %s" % str(path))
                        return Move(MOVE_ANT, path, None)
                    else:
                        # print("No path found, attacking in place")
                        return Move(MOVE_ANT, [ant.coords], None)
        # else:
        #     # disable attack mode if gap is closed - maybe enable in future?
        #     self.attackMode = False

        return None
        

    ##
    # handleAntUnstuckLogic - 
    #
    # Check if it's been a few turns since the last time we've collected food;
    # this is how we get ants unstuck if there happens to be a bunch of collisions.
    #
    # Parameters:
    #   currentState - the current game state
    #   myInv - current player's inventory
    #   me - current player id
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleAntUnstuckLogic(self, currentState, myInv, me):
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
                self.foodCount = [] # memory leaks are bad.

        return None


    ##
    # handleQueenMovement - 
    #
    # Move the queen off the anthill so we can build stuff - unless an enemy ant is in range and on our side of the board
    #
    # Parameters:
    #   currentState - the current game state
    #   myQueen - the queen ant
    #   enemyId - enemy player id
    #   myHill - current player's anthill
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleQueenMovement(self, currentState, myQueen, enemyId, myHill):
        if not myQueen.hasMoved:
            # First check if there are any enemy drones/workers/soldiers in attack range
            enemyAnts = getAntList(currentState, enemyId, (DRONE, SOLDIER, WORKER, R_SOLDIER,))
            if enemyAnts:
                for enemyDrone in enemyAnts:
                    distance = approxDist(myQueen.coords, enemyDrone.coords)
                    if distance <= UNIT_STATS[QUEEN][RANGE] + UNIT_STATS[QUEEN][MOVEMENT]:
                        # Attack the enemy drone if it's in range
                        path = createPathToward(currentState, myQueen.coords, enemyDrone.coords, UNIT_STATS[QUEEN][MOVEMENT])
                        if path and isPathOkForQueen(path):
                            return Move(MOVE_ANT, path, None)
            
            # If we're far from the hill, move back towards it
            if approxDist(myQueen.coords, myHill.coords) > 3:
                path = createPathToward(currentState, myQueen.coords, myHill.coords, UNIT_STATS[QUEEN][MOVEMENT])
                if path and isPathOkForQueen(path):
                    return Move(MOVE_ANT, path, None)
            # Otherwise, make sure we're off of food/tunnel/hill
            else:
                move = self.moveAway(currentState, myQueen)
                if move is not None:
                    return move
        
        return None

        
    ##
    # handleWorkerAntLogic - 
    #
    # Handles all worker ant logic including building workers, moving them safely,
    # prioritizing food collection, and managing worker pathfinding.
    #
    # Parameters:
    #   currentState - the current game state
    #   myInv - current player's inventory
    #   me - current player id
    #   enemyId - enemy player id
    #   myHill - current player's anthill
    #   myQueen - the queen ant
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleWorkerAntLogic(self, currentState, myInv, me, enemyId, myHill, myQueen):
        #Build another worker if i have a drone
        myWorkers = getAntList(currentState, me, (WORKER,))
        if (len(myWorkers) == 1 and myInv.foodCount > 0 and len(getAntList(currentState, me, (DRONE,))) > 0):
            # Check if anthill is clear and make sure no enemy ants are on our side; don't waste food if they are
            if getAntAt(currentState, myHill.coords) is None and self.isSafePosition(currentState, myHill.coords, enemyId, True):
                return Move(BUILD, [myHill.coords], WORKER)

        # If I don't have any workers, build one if it's safe
        if (len(myWorkers) == 0 and myInv.foodCount > 0):
            if getAntAt(currentState, myHill.coords) is None and self.isSafePosition(currentState, myHill.coords, enemyId, True):
                # print("No food, building worker")
                return Move(BUILD, [myHill.coords], WORKER)

        # Check if workers are in danger; move them for safety if so
        for worker in myWorkers:
            if not (worker.hasMoved):
                enemyDronesAndRanged = getAntList(currentState, enemyId, (DRONE,R_SOLDIER))
                for ant in enemyDronesAndRanged:
                    if ant.coords[1] < 5:
                        # If enemy is attempting to attack with a drone or R_Soldier right away, save the worker
                        if not self.isSafePosition(currentState, worker.coords, enemyId, True) \
                            or (len(enemyDronesAndRanged) > 0 and myInv.foodCount < 3):
                            path = createPathToward(currentState, worker.coords, myQueen.coords, UNIT_STATS[WORKER][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            else:
                                return Move(MOVE_ANT, [worker.coords], None)

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
                    move = self.moveAway(currentState, ant)
                    return move
            return Move(END, None, None)

        return None


    ##
    # handleQueenDefenseLogic - 
    #
    # Check if queen was attacked, create a soldier to protect her if no soldier exists; 
    # otherwise move the soldier to protect her
    #
    # Parameters:
    #   currentState - the current game state
    #   myInv - current player's inventory
    #   me - current player id
    #   enemyId - enemy player id
    #   myHill - current player's anthill
    #   myQueen - the queen ant
    #   mySoldiers - list of soldier ants
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleQueenDefenseLogic(self, currentState, myInv, me, enemyId, myHill, myQueen, mySoldiers):
        # Check if queen was attacked, create a soldier to protect her if no soldier exists; 
        # otherwise move the soldier to protect her
        if self.previousQueenHealth is not None and myQueen.health < self.previousQueenHealth:
            # print("Queen was attacked")
            if myInv.foodCount > 1:
                if len(getAntList(currentState, me, (SOLDIER,))) == 0 and getAntAt(currentState, myHill.coords) is None:
                    # print("Building soldier at hill")
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
                safeMoves = self.findSafeMoves(currentState, myQueen, enemyId, False)
                random.shuffle(safeMoves)
                for move in safeMoves:
                    if getAntAt(currentState, move) is None:
                        return Move(MOVE_ANT, [myQueen.coords, move], None)
                # If no safe moves, attack in place
                # print("Queen has no safe moves, attacking in place")
                return Move(MOVE_ANT, [myQueen.coords], None)

        # Update previous health
        self.previousQueenHealth = myQueen.health
        # print("Queen health: %d" % myQueen.health)

        return None


    ##
    # handleHillDefenseLogic - 
    #
    # Check if hill was attacked, defend it if so with any ants capable of doing so
    #
    # Parameters:
    #   currentState - the current game state
    #   me - current player id
    #   myHill - current player's anthill
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleHillDefenseLogic(self, currentState, me, myHill):
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

        return None


    ##
    # handleUnitBuilding - 
    #
    # Build a drone first for maximum harassment, then build a soldier if needed
    #
    # Parameters:
    #   currentState - the current game state
    #   myInv - current player's inventory
    #   me - current player id
    #   myHill - current player's anthill
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleUnitBuilding(self, currentState, myInv, me, myHill):
        # Build a drone first, maximum harassment
        if (len(getAntList(currentState, me, (DRONE,))) == 0 and myInv.foodCount > 2 
            and getAntAt(currentState, myHill.coords) is None):
                return Move(BUILD, [myHill.coords], DRONE)
        else:
            # TRIAL - MAKE RANGED SOLDIER JUST SOLDIER INSTEAD - MARKING WITH COMMENT R_S to S
            if (len(getAntList(currentState, me, (SOLDIER,))) == 0 and myInv.foodCount > 2 
        and getAntAt(currentState, myHill.coords) is None):
                return Move(BUILD, [myHill.coords], SOLDIER)
        
        return None

        
    ##
    # handleDroneLogic - 
    #
    # Handles drone behavior including attacking enemy workers, fighting enemy drones,
    # and retreating when necessary.
    #
    # Parameters:
    #   currentState - the current game state
    #   myDrones - list of drone ants
    #   enemyId - enemy player id
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleDroneLogic(self, currentState, myDrones, enemyId):
        for drone in myDrones:
            if not (drone.hasMoved):
                # Killing workers is priority
                enemyDronesAndRanged = getAntList(currentState, enemyId, (DRONE, R_SOLDIER,))

                # If enemy workers are vulnerable, attack them
                enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
                for enemyWorker in enemyWorkers:
                    if self.isSafePosition(currentState, enemyWorker.coords, enemyId, True):

                        # Find safe moves for the drone
                        safeMoves = self.findSafeMoves(currentState, drone, enemyId, self.attackMode)
                        
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
                            # No enemy workers, retreat to (5,3) unless it's not safe
                            retreatTarget = (5, 3)
                            if legalCoord(retreatTarget) and self.isSafePosition(currentState, retreatTarget, enemyId, True):
                                path = createPathToward(currentState, drone.coords,
                                                    retreatTarget, UNIT_STATS[DRONE][MOVEMENT])
                                if path and len(path) > 1:
                                    return Move(MOVE_ANT, path, None)
                                else: 
                                    return Move(MOVE_ANT, [drone.coords], None)
                            else:
                                safeMoves = self.findSafeMoves(currentState, drone, enemyId, True)
                                if safeMoves:
                                    randomSafeMove = random.choice(safeMoves)
                                    path = createPathToward(currentState, drone.coords,
                                                        randomSafeMove, UNIT_STATS[DRONE][MOVEMENT])
                                    if path and len(path) > 1:
                                        return Move(MOVE_ANT, path, None)
                                    else:
                                        return Move(MOVE_ANT, [drone.coords], None)


                # When attacking a drone, stay outside of the range of the other enemy's ants
                if enemyDronesAndRanged:
                    # print("Enemy has a drone/Ranged Soldier, attacking")

                    # Only attack drone if I can attack first; this guarantees a win assuming no other enemies interfere
                    for enemyDRS in enemyDronesAndRanged:
                        if approxDist(drone.coords, enemyDRS.coords) <= UNIT_STATS[DRONE][RANGE] + UNIT_STATS[DRONE][MOVEMENT]:
                            path = createPathToward(currentState, drone.coords, enemyDRS.coords, UNIT_STATS[DRONE][MOVEMENT])
                            if path:
                                return Move(MOVE_ANT, path, None)
                        else: 
                            # In this case, stay outside of enemy drone's range
                            safeMoves = self.findSafeMoves(currentState, drone, enemyId, False)
                            # Now move to the safe move closest to the enemy drone
                            if safeMoves:
                                closestSafeMove = min(safeMoves,    
                                                    key=lambda m: approxDist(m, enemyDRS.coords))
                                path = createPathToward(currentState, drone.coords,
                                                        closestSafeMove, UNIT_STATS[DRONE][MOVEMENT])
                                if path and len(path) > 1:
                                    return Move(MOVE_ANT, path, None)
                            else:
                                return Move(MOVE_ANT, [drone.coords], None)
                else:
                    # Get enemy workers
                    enemyWorkers = getAntList(currentState, enemyId, (WORKER,))
                    
                    # Find safe moves for the drone
                    safeMoves = self.findSafeMoves(currentState, drone, enemyId, self.attackMode)
                    
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
                        # No enemy workers, retreat to (5,3) unless it's not safe
                        retreatTarget = (5, 3)
                        if legalCoord(retreatTarget) and self.isSafePosition(currentState, retreatTarget, enemyId, True):
                            path = createPathToward(currentState, drone.coords,
                                                retreatTarget, UNIT_STATS[DRONE][MOVEMENT])
                            if path and len(path) > 1:
                                return Move(MOVE_ANT, path, None)
                            else: 
                                return Move(MOVE_ANT, [drone.coords], None)
                        else:
                            safeMoves = self.findSafeMoves(currentState, drone, enemyId, True)
                            if safeMoves:
                                randomSafeMove = random.choice(safeMoves)
                                path = createPathToward(currentState, drone.coords,
                                                    randomSafeMove, UNIT_STATS[DRONE][MOVEMENT])
                                if path and len(path) > 1:
                                    return Move(MOVE_ANT, path, None)
                                else:
                                    return Move(MOVE_ANT, [drone.coords], None)

        return None


    ##
    # handleSoldierLogic - 
    #
    # Make soldiers when needed and handle their behavior including defending and escorting workers
    #
    # Parameters:
    #   currentState - the current game state
    #   enemyId - enemy player id
    #   me - current player id
    #   myInv - current player's inventory
    #   myHill - current player's anthill
    #   mySoldiers - list of soldier ants
    #
    # Returns:
    #   A Move object if an action was taken, None otherwise
    #
    def handleSoldierLogic(self, currentState, enemyId, me, myInv, myHill, mySoldiers):
        # Make a soldier if enemy has ants other than workers and a queen. If they don't, no need to waste food
        if (len(getAntList(currentState, enemyId, (DRONE,SOLDIER,R_SOLDIER))) > 0 and 
        len(getAntList(currentState, me, (SOLDIER,))) == 0 and myInv.foodCount > 2 
        and getAntAt(currentState, myHill.coords) is None):
            return Move(BUILD, [myHill.coords], SOLDIER)

        # If I have a soldier, make it defend and escort workers carrying food
        for soldier in mySoldiers:
            if not (soldier.hasMoved):
                # First check if there are any enemy ants on our side of the board
                enemyAnts = getAntList(currentState, enemyId, (DRONE,SOLDIER,R_SOLDIER))
                for enemyAnt in enemyAnts:
                    if enemyAnt.coords[1] < 5:
                        # Attack the enemy ant
                        path = createPathToward(currentState, soldier.coords, enemyAnt.coords, UNIT_STATS[R_SOLDIER][MOVEMENT])
                        if path and len(path) > 1:
                            return Move(MOVE_ANT, path, None)
                        else:
                            return Move(MOVE_ANT, [soldier.coords], None)

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
                else:
                    # No workers, default to defending the hill
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

        return None
  
   
    ##
    # handleCleanup - 
    #
    # Cleanup phase: move ants off illegal positions and end turn if no actions available
    #
    # Parameters:
    #   currentState - the current game state
    #   myRangedSoldiers - list of ranged soldier ants
    #   mySoldiers - list of soldier ants
    #   myDrones - list of drone ants
    #
    # Returns:
    #   A Move object if an action was taken, otherwise Move(END, None, None)
    #
    def handleCleanup(self, currentState, myRangedSoldiers, mySoldiers, myDrones):
        # If a ranged soldier is on top of food, the anthill, or tunnel, move it
        if not self.attackMode:
            for soldier in myRangedSoldiers:
                move = self.moveAway(currentState, soldier)
                if move is not None:
                    return move

        # If a soldier is on top of food, the anthill, or tunnel, move it
        if not self.attackMode:
            for soldier in mySoldiers:
                move = self.moveAway(currentState, soldier)
                if move is not None:
                    return move

        # If a drone is on top of food, the anthill, or tunnel, move it
        for drone in myDrones:
            move = self.moveAway(currentState, drone)
            if move is not None:
                return move

        #If no actions are available, end the turn
        self.firstMove = True
        return Move(END, None, None)
    
    
    
    ##
    #getAttack
    #
    # This agent attacks the closest enemy ant, soldier prioritize other soldiers, then ranged soldiers, then anything else
    #
    def getAttack(self, currentState, attackingAnt, enemyLocations):
        # if the ant attacking is a soldier, prioritize other soldiers, then anything else
        if attackingAnt.type == SOLDIER:
            enemySoldiers = [loc for loc in enemyLocations if getAntAt(currentState, loc).type == SOLDIER]
            if enemySoldiers:
                return enemySoldiers[0]
            else: 
                return enemyLocations[0]
        
        # If attacking ant is a drone, prioritize enemy drones, enemy ranged soldiers, then anything else
        elif attackingAnt.type == DRONE:
            enemySoldiers = [loc for loc in enemyLocations if getAntAt(currentState, loc).type == DRONE]
            enemyRanged = [loc for loc in enemyLocations if getAntAt(currentState, loc).type == R_SOLDIER]

            if enemySoldiers:
                return enemySoldiers[0]
            elif enemyRanged:
                return enemyRanged[0]
            else:
                return enemyLocations[0]

        return enemyLocations[0]
    


    ##
    #registerWin
    #
    # This agent doens't learn
    #
    def registerWin(self, hasWon):
        #method templaste, not implemented
        pass
