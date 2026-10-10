from PIL import Image

from agents.vision_agent import VisionAgent


IMAGE_PATH = "glasses.png"


def main():

    print("Loading image...")

    image = Image.open(
        IMAGE_PATH
    )

    print("Initializing Vision Agent...")

    agent = VisionAgent()

    print("Starting autonomous analysis...\n")

    result = agent.analyze(
        image=image,
        customer_description=(
            "The shoes arrived with a stain "
            "on the left shoe."
        )
    )

    state = agent.get_state()

    print("\n================================")
    print("VISION AGENT RESULT")
    print("================================\n")

    print(
        result.model_dump_json(
            indent=2
        )
    )

    print("\n================================")
    print("AGENT STATE")
    print("================================\n")

    print(
        f"Attempts      : {state.attempt}"
    )

    print(
        f"Status        : {state.status}"
    )

    print(
        f"Confidence    : {state.confidence:.2f}"
    )

    print(
        f"Needs retry   : {state.needs_reanalysis}"
    )

    print(
        f"Last action   : {state.last_action}"
    )

    print(
        f"Reason        : {state.reason}"
    )

    print("\n================================")
    print("REASONING HISTORY")
    print("================================")

    for index, reasoning in enumerate(
        state.reasoning_history,
        start=1
    ):

        print(
            f"\nAttempt {index}:"
        )

        print(
            reasoning
        )


if __name__ == "__main__":
    main()