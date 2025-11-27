from client.src.game import Player


class GameProcess:
    def __init__(self):
        self.opponentPlayer = Player()
        self.currentPlayer = Player()
        self.gameState = "MENU"
        self.turnState = "MENU"

    
    def startGame(self):
        self.gameState = "RUNNING"

        # decide the first turn player

        # send the result through network

        
