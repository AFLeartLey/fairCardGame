class Card:
    def __init__(
        self,
        item_power: int,
        pcarditem_type: str,
        ncarditem_type: str,
        card_effect: str,
    ):
        self.item_power = item_power
        self.pcarditem_type = pcarditem_type
        self.ncarditem_type = ncarditem_type
        self.card_effect = card_effect

    def getNcarditem(self) -> str:
        return self.ncarditem_type
    
    def getPcarditem(self) -> str:
        return self.pcarditem_type
    
    def getItemPower(self) -> int:
        return self.item_power
    
    def getCardEffect(self) -> str:
        return self.card_effect
    
    
