from evalbase import configure_telemetry, workflow, step

# Optional manual config, otherwise defaults will be used
configure_telemetry(service_name="my-ai-agent", api_key="API_KEY")

@workflow
def run_ai_workflow(query):
    response = call_llm(query)
    embedding = generate_embedding(response)
    return embedding

@step(subtype="LLM Query")
def call_llm(query):
    # Call OpenAI or other LLM
    return "Hello from GPT-4"

@step(subtype="Embedder")
def generate_embedding(text):
    # Call embedding model
    return [0.1, 0.2, 0.3]

if __name__ == "__main__":
    result = run_ai_workflow("What is the capital of France?")
    print(result)
