from app.agents.root_cause_identifier import root_cause_identifier

# Fake output from LogAnalyzer
state = {
    "observations": {
        "order-service": [
            "Request timeout",
            "Latency exceeded threshold",
            "Payment service unavailable"
        ]
    }
}

result = root_cause_identifier(state)

print(result)