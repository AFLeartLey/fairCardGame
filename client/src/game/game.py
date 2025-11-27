"""
src/game should contain functions and classes that manipulate main game logic, such as game state, rules, and interactions.

functions included in the file should be implemented, whether in this file
or called from other modules.

in src/game, following functions should be implemented:

- defining game classes, basic game rules & mechanics and important game constants
- initializing game state and variables
- handling player actions and game rules
- updating game state based on player actions and network data
- checking for win/loss conditions and game progression

This file should work as a module roadmap for implementing game functionalities,
with most of the actual code being implemented in other files/modules as needed.
"""

import client.src.game.constants as gconstants
import random


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


class Player:
    def __init__(self):
        self.health = gconstants.PLAYER_MAX_HEALTH
        self.cost = gconstants.PLAYER_INIT_COST
        self.hand = []


    def takeDamage(self, damage: int):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    '''
    Return True if player is defeated
    '''
    def isDefeated(self) -> bool:
        return self.health <= 0
    
    '''
    Heal the player by given amount
    '''
    def takeHeal(self, heal: int):
        self.health += heal
        if self.health > gconstants.PLAYER_MAX_HEALTH:
            self.health = gconstants.PLAYER_MAX_HEALTH
        
    '''
    Use cost for playing cards.
    Return True if cost usage is successful, False if not enough cost.
    '''
    def costUsage(self, cost: int):
        if self.cost < cost:
            return False
        self.cost -= cost
        return True
    
    '''
    Regenerate cost by the given amount.
    '''
    def costRegen(self, regen: int):
        self.cost += regen
        if self.cost > gconstants.PLAYER_COST_LIMIT:
            self.cost = gconstants.PLAYER_COST_LIMIT


    '''
    Add a card to player's hand.
    Return True if successful, False if hand is full.
    '''
    def receiveCard(self, card: Card):
        if len(self.hand) >= gconstants.MAX_HAND_SIZE:
            # Call card discard animation
            return False
        self.hand.append(card)
        return True
    


    '''    
    Discard a card from player's hand.
    '''
    def discardCard(self, card: Card):
        if card in self.hand:
            self.hand.remove(card)
            return True
        return False

    '''
    Select a card for the opponent.
    '''
    def selectCard(self) -> Card:
        # selection logics should be resolved in UI section.
        pass
        return
