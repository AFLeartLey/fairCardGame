from random import choice
from client.src.game.card import Card
from client.src.game.player import Player
from client.src.network.core import Network
from client.src.game.constants import CARD_ITEM_VALUES as gValues, EVENT_CARD_PLAYED
import client.src.game.constants as gconstants

class GameState:
    def __init__(
        self,
        local_player: Player,
        remote_player: Player,
        NetworkManager: Network
    ):
        self.local_player = local_player
        self.remote_player = remote_player

    
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
        try:                            
            if is_host:
                self.NetworkManager.start()
            else:
                self.NetworkManager.connect(ip)
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
        
        self.NetworkManager.send({
            "event": EVENT_CARD_PLAYED,
            "card": card,
            "param": None,
            "player": "remote"
        })
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

        match card.getPcarditem():
            case "heal":
                heal = gValues[card.getPcarditem()][card.getItemPower()]
                self.local_player.takeHeal(heal)
            case "card_draw":
                draw_count = gValues[card.getPcarditem()][card.getItemPower()]
                for _ in range(draw_count):
                    card_recv = Card(0, "", "", "")
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
                        "event": gconstants.EVENT_CARD_DRAWN,
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
            
        choice_card: Card = card_list[0] # = ui.drawCardSelection(card_list)

        self.NetworkManager.send({
            "event": gconstants.EVENT_TURN_END,
            "card": choice_card,
            "param": None,
            "player": "remote"
        })

        self.local_player.costRegen(2)  # Regenerate 2 cost at end of turn
        return
    

        

