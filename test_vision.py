from PIL import Image

from agents.vision_agent import VisionAgent


IMAGE_PATH = "glasses.PNG"


def main():

    print("Loading image...")

    image = Image.open(
        IMAGE_PATH
    )

    print("Initializing Vision Agent...")

    agent = VisionAgent()

    print("Sending image to Gemini...")
    print("Please wait...\n")

    result = agent.analyze(
        image=image,
        customer_description=(
            "The shoes arrived with a stain "
            "on the left shoe."
        )
    )

    print("\n================================")
    print("VISION AGENT RESULT")
    print("================================\n")

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()