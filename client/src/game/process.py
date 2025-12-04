from client.src.game.player import Player


class GameProcess:
    def __init__(
        self,
        local_player: Player,
        remote_player: Player,
        is_host: bool,
    ):
        self.local_player = local_player
        self.remote_player = remote_player
        self.is_host = is_host

        

