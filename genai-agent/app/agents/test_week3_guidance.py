from app.agents.guidance_generator import guidance_generator

state = {
    "root_cause_candidates_ranked": [
        {
            "cause": "Payment service unavailable",
            "confidence": 0.95,
            "affected_services": [
                "order-service",
                "payment-service"
            ]
        }
    ]
}

print(guidance_generator(state))