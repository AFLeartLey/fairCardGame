from typing import Optional

import client.src.game.constants as gconstants
from client.src.game.card import Card


class Player:
    """Represents a player in the card game.

    Attributes:
        health (int): current health points (0..PLAYER_MAX_HEALTH).
        cost (int): current available cost/resources to play cards.
        hand (list[Card]): cards currently held by the player.

    All methods mutate the player's state in place and prefer clear
    return values for success/failure so callers (UI or game engine)
    can react accordingly.
    """
    def __init__(self):
        self.health = gconstants.PLAYER_MAX_HEALTH
        self.cost = gconstants.PLAYER_INIT_COST
        self.hand = []

    def takeDamage(self, damage: int) -> None:
        """Reduce the player's health by `damage`.

        Ensures health never drops below zero.

        Args:
            damage (int): amount of damage to apply (non-negative).

        Returns:
            None

        Example:
            player.takeDamage(3)
        """

        self.health -= damage
        if self.health < 0:
            self.health = 0

    def isDefeated(self) -> bool:
        """Return True if the player's health is zero or below.

        Returns:
            bool: True when the player is defeated.
        """

        return self.health <= 0

    def takeHeal(self, heal: int) -> None:
        """Increase the player's health by `heal`.

        Health is clamped to `gconstants.PLAYER_MAX_HEALTH`.

        Args:
            heal (int): number of health points to restore.

        Returns:
            None
        """

        self.health += heal
        if self.health > gconstants.PLAYER_MAX_HEALTH:
            self.health = gconstants.PLAYER_MAX_HEALTH

    def costUsage(self, cost: int) -> bool:
        """Attempt to spend `cost` resource to play a card.

        Args:
            cost (int): amount of resource needed.

        Returns:
            bool: True if the player had enough cost and it was deducted,
            otherwise False (no deduction performed).

        Example:
            if player.costUsage(card.cost):
                play(card)
        """

        if self.cost < cost:
            return False
        self.cost -= cost
        return True

    def costRegen(self, regen: int) -> None:
        """Increase the player's cost/resource by `regen`.

        Cost is clamped to `gconstants.PLAYER_COST_LIMIT`.

        Args:
            regen (int): amount to restore.

        Returns:
            None
        """

        self.cost += regen
        if self.cost > gconstants.PLAYER_COST_LIMIT:
            self.cost = gconstants.PLAYER_COST_LIMIT

    def receiveCard(self, card: Card) -> bool:
        """Add a `card` to the player's hand.

        If the hand is full the card is not added and False is returned.
        The UI layer may want to animate a discard if the hand is at
        maximum capacity.

        Args:
            card (Card): the card to add to the hand.

        Returns:
            bool: True when the card was added, False if the hand is full.
        """

        if len(self.hand) >= gconstants.MAX_HAND_SIZE:
            # Call card discard animation
            return False
        self.hand.append(card)
        return True


    def discardCard(self, card: Card) -> bool:
        """Remove `card` from the player's hand if present.

        Args:
            card (Card): the card to remove.

        Returns:
            bool: True if the card was present and removed, False otherwise.
        """
        if card in self.hand:
            self.hand.remove(card)
            return True
        return False

    def selectCard(self) -> Optional[Card]:
        """Choose a card (the method is a placeholder for UI/AI selection).

        Selection of a card to play or give to the opponent depends on the
        UI or AI layer and therefore this method is intentionally
        unimplemented in the model. Implementers should return a `Card` or
        None if no selection is possible.

        Returns:
            Optional[Card]: chosen card or None when no card is selected.
        """

        # selection logic should be resolved in the UI or AI layer.
        return None
