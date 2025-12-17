PLAYER_MAX_HEALTH = 25
MAX_HAND_SIZE = 7
PLAYER_INIT_COST = 4
TURN_TIME_LIMIT = 120  # in seconds
PLAYER_COST_LIMIT = 20


"""
EVENT items should be indicating different game events
that can occur during gameplay, such as player actions,
status changes, and game state updates.
"""
EVENT_PLAYER_DAMAGE = "玩家受伤"
EVENT_PLAYER_HEAL = "玩家治疗"
EVENT_GAME_START = "game_start"
EVENT_GAME_END = "game_end"

EVENT_TURN_START = "turn_start" # deprecated
EVENT_TURN_END = "turn_end"
"""
upon EVENT_TURN_END, the json file should contain:
{
    "event": EVENT_TURN_END,
    "card": card // card drawn by remote at the start of the turn
    "param": None,
    "player": "remote"
}
"""

EVENT_CARD_DRAWN = "card_drawn"
EVENT_CARD_PLAYED = "card_played"
EVENT_CARD_DISCARDED = "card_discarded"

EVENT_REQUEST_CARD = "request_card"
"""
upon event_request_card, the json file should contain:
{
    "event": EVENT_REQUEST_CARD,
    "param": None
    "player": "remote"
}
"""
EVENT_RETURN_CARD = "return_card"
"""
upon event_return_card, the json file should contain:
{
    "event": EVENT_RETURN_CARD,
    "card": card,
    "param": None,
    "player": "remote"
}
"""

EVENT_LIST = [
    EVENT_PLAYER_DAMAGE,
    EVENT_PLAYER_HEAL,
    EVENT_GAME_START,
    EVENT_GAME_END,
    EVENT_TURN_START,
    EVENT_TURN_END,
    EVENT_CARD_DRAWN,
    EVENT_CARD_PLAYED,
    EVENT_CARD_DISCARDED,
    
]

"""
STATUS items should be indicating different status effects
that can be applied to players or card items, such as buffs or debuffs.
"""

STATUS_CARD_BUFF = "card_buff"
STATUS_CARD_DEBUFF = "card_debuff"
STATUS_CARD_NO_EFFECT = "card_no_effect"
STATUS_LIST = [STATUS_CARD_BUFF, STATUS_CARD_DEBUFF, STATUS_CARD_NO_EFFECT]

# deprecated for now

"""
NCARDITEM items are different types of card items
that is of negative effect in the game.
"""
NCARDITEM_SELF_DAMAGE = "对自己造成伤害"
NCARDITEM_CARD_DISCARD = "丢弃手牌"
NCARDITEM_COST_USAGE = "花费Cost"

NCARDITEMLIST = [NCARDITEM_SELF_DAMAGE, NCARDITEM_CARD_DISCARD, NCARDITEM_COST_USAGE]

"""
PCARDITEM items are different types of card items
that is of positive effect in the game.
"""
PCARDITEM_HEAL = "治疗自身"
PCARDITEM_CARD_DRAW = "获取卡牌"
PCARDITEM_DAMAGE = "对对手造成伤害"
PCARDITEM_COST_RECOVER = "回复Cost"

PCARDITEMLIST = [
    PCARDITEM_HEAL,
    PCARDITEM_CARD_DRAW,
    PCARDITEM_DAMAGE,
    PCARDITEM_COST_RECOVER,
]

"""
ITEM_POWER values indicate the level for every card item effect,
affecting the numerical outcome of the effect.
"""
ITEM_POWER_LOW = 0
ITEM_POWER_MEDIUM = 1
ITEM_POWER_HIGH = 2
ITEM_POWER_LIST = [ITEM_POWER_LOW, ITEM_POWER_MEDIUM, ITEM_POWER_HIGH]

"""
here we define different values for every card item type,
which will be used in card item effect calculations,
including damage amount, heal amount, cost amount, etc.
"""
CARD_ITEM_VALUES: dict[str, list[int]] = {}

CARD_ITEM_VALUES[NCARDITEM_SELF_DAMAGE]: list[int] = [1, 2, 3]
CARD_ITEM_VALUES[NCARDITEM_CARD_DISCARD]: list[int] = [1, 1, 2]
CARD_ITEM_VALUES[NCARDITEM_COST_USAGE]: list[int] = [1, 2, 3]

CARD_ITEM_VALUES[PCARDITEM_HEAL]: list[int] = [2, 3, 4]
CARD_ITEM_VALUES[PCARDITEM_CARD_DRAW]: list[int] = [1, 2, 3]
CARD_ITEM_VALUES[PCARDITEM_DAMAGE]: list[int] = [2, 3, 5]
CARD_ITEM_VALUES[PCARDITEM_COST_RECOVER]: list[int] = [1, 2, 3]