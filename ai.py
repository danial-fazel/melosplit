import requests

class AIService:
    def __init__(self, api_key, model="tiiuae/falcon-7b-instruct"):
        """
        Initialize the AI service with API key and model.
        :param api_key: Your Hugging Face API key.
        :param model: The model to use (default is 'gpt2').
        """
        self.api_key = api_key
        self.api_url = f"https://api-inference.huggingface.co/models/{model}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def send_request(self, prompt, max_length=800):
        """
        Send the prompt to the Hugging Face API and return the response.
        :param prompt: The input text for the AI model.
        :param max_length: The maximum length of the generated text.
        :return: The generated text or an error message.
        """
        data = {
            "inputs": prompt,
            "parameters": {
                "max_length": max_length,   # Increase to allow longer responses
                "temperature": 0.9,         # Add more randomness for creativity
                "top_p": 0.9,               # Use nucleus sampling
                "num_return_sequences": 1,  # Ensure only one response
                "repetition_penalty": 1.2,  # Penalize repeated phrases
            },
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json=data)
            response.raise_for_status()
            generated_text = response.json()[0]["generated_text"].strip()
            return generated_text.replace(prompt, "").strip()
        except requests.RequestException as e:
            print(f"Error communicating with Hugging Face API: {e}")
            return "Error generating text. Please try again later."

    @staticmethod
    def create_prompt(group_name, group_description, members, transactions, genre):
        genre_instructions = {
            "scary": "Create a suspenseful and thrilling story.",
            "funny": "Make it humorous and lighthearted.",
            "mysterious": "Add mystery and intrigue.",
            "mixed": "Combine suspense, humor, and mystery.",
            "random": "Feel free to be creative in any way you like.",
        }

        genre_instruction = genre_instructions.get(genre.lower(), "Be creative.")
        member_names = ", ".join(members.values())
        transaction_details = "\n".join([
            f"{t['payer']} paid {t['amount']} for {t.get('description', 'an unspecified purpose')}"
            for t in transactions.values()
        ])

        return (
            f"The group '{group_name}' consists of: {member_names}.\n\n"
            f"Group description: {group_description}.\n\n"
            f"Recent transactions:\n{transaction_details}\n\n"
            f"{genre_instruction} Begin the story directly, ensuring it is detailed, engaging, and at least 200 words long."
        )
    


# import requests

# api_key = "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"
# api_url = "https://api.openai.com/v1/chat/completions"

# headers = {
#     "Authorization": f"Bearer {api_key}",
#     "Content-Type": "application/json",
# }
# data = {
#     "model": "gpt-4o-mini",  # Or another model you have access to
#     "messages": [{"role": "system", "content": "You are a helpful assistant."},
#                  {"role": "user", "content": "Hello! What can you do?"}],
#     "max_tokens": 50,
# }
# import time

# def send_request():
#     time.sleep(1)  
#     response = requests.post(api_url, headers=headers, json=data)
#     return response.json()

# print(send_request())
