# Author: Chengen Li

import random
import sys
sys.path.append("..")  
from Player import *
from Constants import *
from Construction import CONSTR_STATS
from Ant import UNIT_STATS
from Move import Move
from GameState import addCoords
from AIPlayerUtils import *


class AIPlayer(Player):

    #__init__
    #Description: Creates a new Player
    #
    #Parameters:
    #   inputPlayerId - The id to give the new player (int)
    #   cpy           - whether the player is a copy (when playing itself)
    ##
    def __init__(self, inputPlayerId):
        super(AIPlayer, self).__init__(inputPlayerId, "Ant Edwards")
        #the coordinates of the agent's food and tunnel will be stored in these
        #variables (see getMove() below)
        self.myFood = None
        self.myTunnel = None

        
    ##
    # getPlacement 
    #
    # The agent uses a hardcoded arrangement for phase 1 to make sure the fruits at closest to the tunnel 
    # Enemy food is placed randomly on each 4 corner
    #
    def getPlacement(self, currentState):
        self.myFood = None
        self.myTunnel = None

        # building state
        if currentState.phase == SETUP_PHASE_1:
            return [(2,2), (5, 2), 
                    (2,3), (1,3), (1,2), (1,1), (1,0), (0,3), (0,2), (0,1), (0,0) ]

        # fruit state
        elif currentState.phase == SETUP_PHASE_2:
            numToPlace = 2
            moves = []

            for i in range(0, numToPlace):
                move = None
                while move == None:
                    
                    # COME BACK LATER
                    enemyCorners = [(0,6), (0,9), (9, 6), (9, 9)]
                    # Choose a random spot in the corner
                    idx = random.randint(0, 3)

                    x = enemyCorners[idx][0]
                    y = enemyCorners[idx][1]
                    
                    #Set the move if this space is empty
                    if currentState.board[x][y].constr == None and (x, y) not in moves:
                        move = (x, y)
                        #Just need to make the space non-empty. So I threw whatever I felt like in there.
                        currentState.board[x][y].constr == True
                moves.append(move)

            return moves
        else:
            return None
        


    ##
    # getMove
    #
    # This agent simply gathers food as fast as it can with its worker, 
    # Moves the queen one spot so it can spawn drowns
    # The drones will first target the enemy's workers and then attack the queen
    # The drones follows the shortest paths to their targets
    #
    ##
    def getMove(self, currentState):
        myInv = getCurrPlayerInventory(currentState)
        me = currentState.whoseTurn # my player ID

        if (self.myTunnel == None):
            self.myTunnel = getConstrList(currentState, me, (TUNNEL,))[0]

        if (self.myFood == None):
            foods = getConstrList(currentState, None, (FOOD,))
            self.myFood = foods[0]

            # find the fruit closest to the tunnel
            bestDistSoFar = 1000
            for food in foods:
                dist = stepsToReach(currentState, self.myTunnel.coords, food.coords)
                if (dist < bestDistSoFar):
                    self.myFood = food
                    bestDistSoFar = dist
        

        
        # if I don't have a worker, give up.  QQ
        numAnts = len(myInv.ants)
        if (numAnts == 1):
            return Move(END, None, None)
    
            
        # ------------------------ QUEEN ---------------------------
        # if the queen is on the ant hill move her
        myQueen = myInv.getQueen()
        if (myQueen.coords == myInv.getAnthill().coords):
            return Move(MOVE_ANT, [myInv.getQueen().coords, (1,2)], None)
        
        if (not myQueen.hasMoved):
            return Move(MOVE_ANT, [myQueen.coords], None)


        # ------------------------ DRONE ---------------------------
        # Make a drone if enough food
        if (myInv.foodCount > 2):
            if (getAntAt(currentState, myInv.getAnthill().coords) is None):
                return Move(BUILD, [myInv.getAnthill().coords], DRONE)
            
        # return a list of my drones
        myDrones = getAntList(currentState, me, (DRONE,))
        enemyId = 1 - me 

        # get the enemy queen
        enemyQueen = getAntList(currentState, enemyId, (QUEEN,))[0]

        # get the list of enemy workers
        enemyWorkers = getAntList(currentState, enemyId, (WORKER,))

        for i, drone in enumerate(myDrones):
            if not (drone.hasMoved):                
                
                # Make the first drone attack the workers
                if i == 0 and enemyWorkers:
                    enemyWorker = enemyWorkers[0] 
                    pathToWorker = createPathToward(currentState, drone.coords, enemyWorker.coords, UNIT_STATS[DRONE][MOVEMENT])
                    return Move(MOVE_ANT, pathToWorker, None)
                
                # The rest should go after the queen
                else:
                    pathToQueen = createPathToward(currentState, drone.coords, enemyQueen.coords, UNIT_STATS[DRONE][MOVEMENT])
                    return Move(MOVE_ANT, pathToQueen, None)
            
      
        # ------------------------ WORKER --------------------------
        # if the worker has already moved, we're done
        workerList = getAntList(currentState, me, (WORKER,))
        if (len(workerList) < 1):
            return Move(END, None, None)
        else:
            myWorker = workerList[0]
            if (myWorker.hasMoved):
                return Move(END, None, None)

        # if the worker has food, move toward tunnel
        if (myWorker.carrying):
            # creates a list of coords that show the quickest path to the tunnel
            
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
    #
    def getAttack(self, currentState, attackingAnt, enemyLocations):
        return enemyLocations[0]  #don't care, first enemy on the list
        
    ##
    #registerWin
    #
    # This agent doens't learn
    #
    def registerWin(self, hasWon):
        #method templaste, not implemented
        pass
