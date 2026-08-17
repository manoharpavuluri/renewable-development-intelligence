#!/usr/bin/env python3

import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


endpoint = os.environ[
    "FOUNDRY_PROJECT_ENDPOINT"
]

model = os.environ[
    "FOUNDRY_MODEL_NAME"
]


credential = DefaultAzureCredential()

project = AIProjectClient(
    endpoint=endpoint,
    credential=credential,
)


with project.get_openai_client() as client:

    response = client.responses.create(
        model=model,
        input=(
            "Reply with exactly one short sentence: "
            "Foundry planner connectivity is working."
        ),
    )


print("=== FOUNDRY RESPONSES TEST ===")
print("Model deployment:", model)
print("Response ID:", response.id)
print("Output:", response.output_text)


project.close()
credential.close()
