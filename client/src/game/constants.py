PLAYER_MAX_HEALTH = 25
MAX_HAND_SIZE = 7
PLAYER_INIT_COST = 4
TURN_TIME_LIMIT = 120 # in seconds


'''
EVENT items should be indicating different game events
that can occur during gameplay, such as player actions,
status changes, and game state updates.
'''
EVENT_PLAYER_DAMAGE = "player_damage"
EVENT_PLAYER_HEAL = "player_heal"
EVENT_GAME_START = "game_start"
EVENT_GAME_END = "game_end"

EVENT_TURN_START = "turn_start"
EVENT_TURN_END = "turn_end"

EVENT_CARD_DRAWN = "card_drawn"
EVENT_CARD_PLAYED = "card_played"
EVENT_CARD_DISCARDED = "card_discarded"

'''
STATUS items should be indicating different status effects
that can be applied to players or card items, such as buffs or debuffs.
'''
STATUS_CARD_BUFF = 'card_buff'
STATUS_CARD_DEBUFF = 'card_debuff'

'''
NCARDITEM items are different types of card items
that is of negative effect in the game.
''' 
NCARDITEM_SELF_DAMAGE = "self_damage"
NCARDITEM_CARD_DISCARD = "card_discard"
NCARDITEM_COST_USAGE = "cost_usage"

'''
PCARDITEM items are different types of card items
that is of positive effect in the game.
'''
PCARDITEM_HEAL = "heal"
PCARDITEM_CARD_DRAW = "card_draw"
PCARDITEM_DAMAGE = "damage"
PCARDITEM_COST_RECOVER = "cost_recover"

'''
ITEM_POWER values indicate the level for every card item effect,
affecting the numerical outcome of the effect.
'''
ITEM_POWER_LOW = 0
ITEM_POWER_MEDIUM = 1
ITEM_POWER_HIGH = 2

'''
here we define different values for every card item type,
which will be used in card item effect calculations,
including damage amount, heal amount, cost amount, etc.
'''
CARD_ITEM_VALUES = {}

CARD_ITEM_VALUES[NCARDITEM_SELF_DAMAGE] = {1, 2, 3}
CARD_ITEM_VALUES[NCARDITEM_CARD_DISCARD] = {1, 2, 3}
CARD_ITEM_VALUES[NCARDITEM_COST_USAGE] = {1, 2, 3}

CARD_ITEM_VALUES[PCARDITEM_HEAL] = {1, 2, 4}
CARD_ITEM_VALUES[PCARDITEM_CARD_DRAW] = {1, 2, 3}
CARD_ITEM_VALUES[PCARDITEM_DAMAGE] = {2, 3, 5}
CARD_ITEM_VALUES[PCARDITEM_COST_RECOVER] = {1, 2, 3}

