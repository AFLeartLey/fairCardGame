from random import choice
from src.game.card import Card
from src.game.player import Player
from src.network.core import Network
from src.game.constants import CARD_ITEM_VALUES as gValues, EVENT_CARD_PLAYED
import src.game.constants as gconstants

class GameState:
    def __init__(
        self,
        local_player: Player,
        remote_player: Player,
        NetworkManager: Network
    ):
        self.local_player = local_player
        self.remote_player = remote_player
        self.NetworkManager = NetworkManager        
        self.on_game_start_callback = None
        self.is_my_turn = False
        self.ui_draw_card_selection_callback = None


    
    # -------------- Getter Methods -----------------
    # -----------------------------------------------

    def getLocalHand(self) -> list[Card]:
        """Return the local player's hand of cards.

        Returns:
            list[Card]: The local player's current hand of cards.
        """
        return self.local_player.hand

    def getRemoteHandSize(self) -> int:
        """Return the size of the remote player's hand.

        Returns:
            int: The number of cards in the remote player's hand.
        """
        return len(self.remote_player.hand)
    
    def getLocalHealth(self) -> int:
        """Return the local player's current health.

        Returns:
            int: The local player's health points.
        """
        return self.local_player.health
    
    def getRemoteHealth(self) -> int:
        """Return the remote player's current health.

        Returns:
            int: The remote player's health points.
        """
        return self.remote_player.health
    
    def getLocalCost(self) -> int:
        """Return the local player's current cost.

        Returns:
            int: The local player's available cost.
        """
        return self.local_player.cost
    
    def getRemoteCost(self) -> int:
        """Return the remote player's current cost.

        Returns:
            int: The remote player's available cost.
        """
        return self.remote_player.cost
    
    # -------------- Network Methods ----------------
    # ------------------------------------------------
    
    def initNetwork(self, is_host, ip, port):
        """Initialize the network connection.

        Args:
            is_host (bool): True if the local player is the host.
            ip (str): The IP address to connect to or bind.
            port (int): The port number to connect to or bind.

        Returns:
            None
        """
        self.NetworkManager = Network(is_host, ip, port)
        self.is_my_turn = is_host  # 主机先手
        try:                            
            if is_host:
                self.NetworkManager.start()
                self.NetworkManager.on_message = self.handle_network_message
                print("服务器已启动，等待连接...")
            else:
                self.NetworkManager.connect(ip)
                self.NetworkManager.on_message = self.handle_network_message
                print("已连接到服务器")
        except Exception as e:
            print(f"初始化失败: {e}")

    def closeNetwork(self):
        """Close the network connection.

        Returns:
            None
        """
        self.NetworkManager.close()

    def sendData(self, data: dict):
        """Send data to the remote player.

        Args:
            data (dict): The data to send.

        Returns:
            None
        """
        self.NetworkManager.send(data)

    def handle_network_message(self, msg: dict) -> None:
        """处理来自网络的消息"""
        print(f"[GameState] 收到网络消息: {msg}")
        
        msg_type = msg.get("type")  # ✅ 修正: 应该用 "type" 而不是 "event"
        
        if msg_type == gconstants.EVENT_GAME_START:
            print("[GameState] ✅ 客户端收到游戏开始通知")
            if self.on_game_start_callback:
                self.on_game_start_callback()
        
        elif msg_type == EVENT_CARD_PLAYED:
            print("[GameState] 收到对手出牌消息")
            self.parseRemotePlayedCard(msg.get("card"))
        
        elif msg_type == gconstants.EVENT_TURN_END:
            print("[GameState] 收到对手回合结束消息")
            # 【新增】对手结束回合后，轮到本地玩家
            self.is_my_turn = True
            print("[GameState] 对手已结束回合，现在轮到本地玩家")

        elif msg_type == gconstants.EVENT_CARD_DRAWN:
            print("[GameState] 收到对手抽牌消息")
            card: Card = msg.get("card")
            self.local_player.hand.append(card)
    
        else:
            print(f"[GameState] 未处理的消息类型: {msg_type}")


    # ------------- Gameplay Methods -----------------
    # ------------------------------------------------

    def checkGameOver(self) -> str | None:
        """Check if the game is over.

        Returns:
            str | None: "local" if the local player wins,
                         "remote" if the remote player wins,
                         None if the game is still ongoing.
        """

        if self.remote_player.isDefeated():
            return "local"
        elif self.local_player.isDefeated():
            return "remote"
        else:
            return None
        
    def _card_to_str(self, card: Card) -> str:
        """给 UI 用的卡牌展示文字，可按你自己喜好调整。"""
        return f"{card.getPcarditem()} | {card.getNcarditem()} (Lv{card.getItemPower()})"

    def get_ui_state(self) -> dict:
        """返回给 UI 的完整状态快照。"""
        return {
            "player_status": {
                "self": {
                    "hp": self.local_player.health,
                    "hand_count": len(self.local_player.hand),
                    "cost": self.local_player.cost,
                    "hand_cards": [self._card_to_str(c) for c in self.local_player.hand],
                },
                "opponent": {
                    "hp": self.remote_player.health,
                    "hand_count": len(self.remote_player.hand),
                    "cost": self.remote_player.cost,
                },
            }
        }

    # ------------ Player Action Methods -------------
    # ------------------------------------------------

    def checkCardPlayable(self, targetCard: Card) -> bool:
        """Check if a card in the local player's hand is playable.

        Args:
            card_index (int): The index of the card to check.

        Returns:
            bool: True if the card is playable, False otherwise.
        """

        match targetCard.getNcarditem():
            case "self_damage":
                if self.local_player.health > gValues[targetCard.getNcarditem()][targetCard.getItemPower()]:
                    return True
                else:
                    return False
            case "card_discard":
                if len(self.local_player.hand) > gValues[targetCard.getNcarditem()][targetCard.getItemPower()]:
                    return True
                else:
                    return False
            case "cost_usage":
                if self.local_player.cost >= gValues[targetCard.getNcarditem()][targetCard.getItemPower()]:
                    return True
                else:
                    return False
            case _:
                return True
            
    """
    对需要做牌的函数，实现逻辑为：
    发出 EVENT_CARD_PLAYED 事件，附带 card 数据
    在 remote 端收到时间后，调用 parseRemotePlayedCard(card) 解析牌效果
    此时 remote 端会根据做牌效果对应做出牌并发出 EVENT_RETURN_CARD 事件
    本地需要捕获这一事件并将其中 card 数据作为得到的牌加入手牌
    """
    
    def playCard(self, card_index: int) -> bool:
        """Play a card from the local player's hand.

        Args:
            card_index (int): The index of the card to play.

        Returns:
            bool: True if the card was played successfully, False otherwise.
        """
        if card_index < 0 or card_index >= len(self.local_player.hand):
            return False
        
        card = self.local_player.hand[card_index]
        if not self.checkCardPlayable(card):
            return False
        
        # Apply negative card item effects
        match card.getNcarditem():
            case "self_damage":
                damage = gValues[card.getNcarditem()][card.getItemPower()]
                self.local_player.takeDamage(damage)
            case "card_discard":
                discard_count = gValues[card.getNcarditem()][card.getItemPower()]
                for _ in range(discard_count):
                    if self.local_player.hand:
                        self.local_player.hand.pop(0)  # Discard the first card in hand
            case "cost_usage":
                cost = gValues[card.getNcarditem()][card.getItemPower()]
                self.local_player.costUsage(cost)
            case _:
                pass

        
        self.NetworkManager.send({
            "type": EVENT_CARD_PLAYED,
            "card": card,
            "param": None,
            "player": "remote"
        })

        match card.getPcarditem():
            case "heal":
                heal = gValues[card.getPcarditem()][card.getItemPower()]
                self.local_player.takeHeal(heal)
            case "card_draw":
                draw_count = gValues[card.getPcarditem()][card.getItemPower()]
                for _ in range(draw_count):
                    request_info = self.NetworkManager.request({
                        "type": gconstants.EVENT_REQUEST_CARD,
                        "param": None,
                        "player": "remote"
                    }, 120, "rpc_request", False)
                    card_recv: Card = request_info["card"]
                    # should be card received from network module
                    self.local_player.hand.append(card_recv)
            case "damage":
                damage = gValues[card.getPcarditem()][card.getItemPower()]
                self.remote_player.takeDamage(damage)
            case "cost_recover":
                recover = gValues[card.getPcarditem()][card.getItemPower()]
                self.local_player.costRegen(recover)
            case _:
                pass


        # Remove the card from hand after playing
        self.local_player.hand.pop(card_index)
        return True
    
    
    def parseRemotePlayedCard(self, card: Card) -> None:
        """
        Parse and apply the effects of a card played by the remote player.

        Args:
            card_data (dict): The data of the card played by the remote player.
        Returns:
            None
        """
        # Apply negative card item effects
        match card.getNcarditem():
            case "self_damage":
                damage = gValues[card.getNcarditem()][card.getItemPower()]
                self.remote_player.takeDamage(damage)
            case "card_discard":
                discard_count = gValues[card.getNcarditem()][card.getItemPower()]
                for _ in range(discard_count):
                    if self.remote_player.hand:
                        self.remote_player.hand.pop(0)  # Discard the first card in hand
            case "cost_usage":
                cost = gValues[card.getNcarditem()][card.getItemPower()]
                self.remote_player.costUsage(cost)
            case _:
                pass

        match card.getPcarditem():
            case "heal":
                heal = gValues[card.getPcarditem()][card.getItemPower()]
                self.remote_player.takeHeal(heal)
            case "card_draw":
                draw_count = gValues[card.getPcarditem()][card.getItemPower()]
                for _ in range(draw_count):
                    card_list = []
                    for i in range(3):
                        card_list.append(
                            Card(
                                choice(gconstants.ITEM_POWER_LIST),
                                choice(gconstants.PCARDITEMLIST),
                                choice(gconstants.NCARDITEMLIST),
                                gconstants.STATUS_CARD_NO_EFFECT
                            )
                        )
                    choice_card: Card = card_list[0] # = ui.drawCardSelection(card_list)
                    self.remote_player.hand.append(choice_card)
                    self.NetworkManager.send({
                        "type": gconstants.EVENT_CARD_DRAWN,
                        "card": choice_card,
                        "param": None,
                        "player": "local"
                    })
            case "damage":
                damage = gValues[card.getPcarditem()][card.getItemPower()]
                self.local_player.takeDamage(damage)
            case "cost_recover":
                recover = gValues[card.getPcarditem()][card.getItemPower()]
                self.remote_player.costRegen(recover)
            case _:
                pass

        return

    def turnEnd(self) -> None:
        """Handle end-of-turn logic for the local player.

        Returns:
            None
        """
        self.is_my_turn = False  # 结束本地玩家回合
        card_list = []
        for _ in range(3):
            card_list.append(
                Card(
                    choice(gconstants.ITEM_POWER_LIST),
                    choice(gconstants.PCARDITEMLIST),
                    choice(gconstants.NCARDITEMLIST),
                    gconstants.STATUS_CARD_NO_EFFECT
                )
            )        
        self.local_player.costRegen(2)  # Regenerate 2 cost at end of turn
        self.ui_draw_card_selection_callback(card_list)

    def sendTurnEnd(self, cardToSend) -> None:
        """Send end-of-turn notification to the remote player.

        Returns:
            None
        """        
        # TBD : 从UI侧获取要递给对手的牌
        self.NetworkManager.send({
            "type": gconstants.EVENT_TURN_END,
            "card": None,
            "player": "remote"
        })    

        

