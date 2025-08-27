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
        super(AIPlayer,self).__init__(inputPlayerId, "A(nt)I")
        #the coordinates of the agent's food and tunnel will be stored in these
        #variables (see getMove() below)
        self.myFood = None
        self.myTunnel = None
    
    ##
    #getPlacement 
    #
    # The agent randomly selects section along back row to place hill and protects it with grass.
    # Enemy food is placed as far away from the tunnel as possible.
    #
    def getPlacement(self, currentState):
        self.myFood = None
        self.myTunnel = None
        if currentState.phase == SETUP_PHASE_1:
            # 1) hill - somewhere on back line
            # 2) worker tunnel - center of board
            # 3-11) grass - few around hill, few at border from hill, one random
            randNum = random.randint(1,8)
            randCoords = (random.randint(0,9), random.randint(0,3))

            moves = [(randNum,0), (5, 2), 
                    (randNum-1, 0), (randNum+1, 0), (randNum, 1), (randNum+1,1), (randNum-1,1),
                    (randNum,3), (randNum+1,3), (randNum-1,3)]
            
            while randCoords in moves:
                randCoords = (random.randint(0,9), random.randint(0,3))

            moves.append(randCoords)

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
    # This agent simply gathers food as fast as it can with its worker.  It
    # never attacks and never builds more ants.  The queen is never moved.
    # Will be modified going forward with different strategies
    # If food count is < 2, gather food
    # If food count is > 2, build soldier ant and move it toward enemy tunnel
    #
    ##
    def getMove(self, currentState):
        #Useful pointers
        myInv = getCurrPlayerInventory(currentState)
        me = currentState.whoseTurn

        #the first time this method is called, the food and tunnel locations
        #need to be recorded in their respective instance variables
        if (self.myTunnel == None):
            self.myTunnel = getConstrList(currentState, me, (TUNNEL,))[0]
        if (self.myFood == None):
            foods = getConstrList(currentState, None, (FOOD,))
            self.myFood = foods[0]
            #find the food closest to the tunnel
            bestDistSoFar = 1000 #i.e., infinity
            for food in foods:
                dist = stepsToReach(currentState, self.myTunnel.coords, food.coords)
                if (dist < bestDistSoFar):
                    self.myFood = food
                    bestDistSoFar = dist

        #if the hasn't moved, have her move in place so she will attack
        myQueen = myInv.getQueen()
        if (not myQueen.hasMoved):
            return Move(MOVE_ANT, [myQueen.coords], None)

        #if I don't have a worker, give up.  QQ
        numAnts = len(myInv.ants)
        if (numAnts == 1):
            return Move(END, None, None)

        #if the worker has already moved, we're done
        myWorker = getAntList(currentState, me, (WORKER,))[0]
        if (myWorker.hasMoved):
            return Move(END, None, None)
        
        #if the worker has food, move toward tunnel
        if (myWorker.carrying):
            path = createPathToward(currentState, myWorker.coords,
                                    self.myTunnel.coords, UNIT_STATS[WORKER][MOVEMENT])
            return Move(MOVE_ANT, path, None)
            
        #if the worker has no food, move toward food
        else:
            path = createPathToward(currentState, myWorker.coords,
                                    self.myFood.coords, UNIT_STATS[WORKER][MOVEMENT])
            return Move(MOVE_ANT, path, None)
                              
    
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
