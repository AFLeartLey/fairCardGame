from src.game.process import GameState
from src.game.player import Player
from src.graphic.UI import MainApp
from src.network.core import Network
SCREEN_SIZE = (800, 600)

def main():    
    localPlayer, remotePlayer = Player(), Player()
    gs = GameState(local_player= localPlayer, remote_player=remotePlayer, NetworkManager=Network())
    app = MainApp()
    app.mainloop()

if __name__ == "__main__":
    main()