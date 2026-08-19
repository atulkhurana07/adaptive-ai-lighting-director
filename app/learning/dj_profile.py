import json
import math
import os


# Read-time normalization scale for get_normalized_preference() /
# get_normalized_context_preference(). Does not affect stored/raw
# preference values -- see those methods for details.
NORMALIZATION_SCALE = 5.0


class DJProfile:
    def __init__(self, profile_name="default_dj"):
        self.profile_name = profile_name

        # Overall preferences
        self.preferences = {
            "PULSE": 0.0,
            "FLASH": 0.0,
            "STROBE": 0.0,
            "DIM": 0.0,
            "IDLE": 0.0
        }

        # Context-based preferences
        self.context_preferences = {}

        self.observations = 0

    def observe(self, lighting_action, rating=1.0, context=None):
        """
        Learn from a DJ's lighting choice.

        rating:
        1.0  = DJ strongly prefers this
        0.5  = moderate preference
        0.0  = neutral
        -1.0 = DJ dislikes this
        """

        if lighting_action not in self.preferences:
            self.preferences[lighting_action] = 0.0

        # Overall learning
        self.preferences[lighting_action] += rating

        # Context-based learning
        if context is not None:

            if context not in self.context_preferences:
                self.context_preferences[context] = {
                    "PULSE": 0.0,
                    "FLASH": 0.0,
                    "STROBE": 0.0,
                    "DIM": 0.0,
                    "IDLE": 0.0
                }

            if lighting_action not in self.context_preferences[context]:
                self.context_preferences[context][lighting_action] = 0.0

            self.context_preferences[context][lighting_action] += rating

        self.observations += 1

    def get_preference(self, lighting_action):
        return self.preferences.get(
            lighting_action,
            0.0
        )

    def get_context_preference(self, context, lighting_action):
        return self.context_preferences.get(
            context,
            {}
        ).get(
            lighting_action,
            0.0
        )

    def get_normalized_preference(self, action):
        """
        Bounded view of the raw overall preference, in (-1, 1).

        The raw preference in self.preferences keeps accumulating
        unbounded, exactly as before -- this is a read-only,
        saturating lens on top of it, not a replacement.
        """
        raw = self.get_preference(action)

        return math.tanh(
            raw / NORMALIZATION_SCALE
        )

    def get_normalized_context_preference(self, context, action):
        """
        Bounded view of the raw context preference, in (-1, 1).
        See get_normalized_preference() for why this is a lens,
        not a stored value.
        """
        raw = self.get_context_preference(
            context,
            action
        )

        return math.tanh(
            raw / NORMALIZATION_SCALE
        )

    def best_action(self):
        return max(
            self.preferences,
            key=self.preferences.get
        )

    def best_action_for_context(self, context):
        if context not in self.context_preferences:
            return self.best_action()

        return max(
            self.context_preferences[context],
            key=self.context_preferences[context].get
        )

    def save(self, file_path):
        data = {
            "profile_name": self.profile_name,
            "preferences": self.preferences,
            "context_preferences": self.context_preferences,
            "observations": self.observations
        }

        directory = os.path.dirname(file_path)

        if directory:
            os.makedirs(
                directory,
                exist_ok=True
            )

        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                data,
                file,
                indent=4
            )

    def load(self, file_path):
        if not os.path.exists(file_path):
            return

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

        self.profile_name = data.get(
            "profile_name",
            self.profile_name
        )

        self.preferences = data.get(
            "preferences",
            self.preferences
        )

        self.context_preferences = data.get(
            "context_preferences",
            {}
        )

        self.observations = data.get(
            "observations",
            0
        )

    def show_profile(self):
        print("\n==============================")
        print("        DJ PROFILE")
        print("==============================")

        print(f"DJ: {self.profile_name}")

        print(
            f"Observations: "
            f"{self.observations}"
        )

        print("\nOverall Preferences:")

        for action, score in self.preferences.items():
            print(
                f"{action:<8} → {score:.2f}"
            )

        print("\nContext Preferences:")

        for context, actions in self.context_preferences.items():

            print(f"\n{context}:")

            for action, score in actions.items():
                print(
                    f"    {action:<8} → {score:.2f}"
                )

        print(
            f"\nOverall Preferred action: "
            f"{self.best_action()}"
        )