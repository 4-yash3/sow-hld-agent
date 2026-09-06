import os
import logging
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("A2AClient")


class A2AClientTool:
    """Outbound Agent-to-Agent (A2A) client tool for inter-agent communication."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.timeout = httpx.Timeout(timeout_seconds)

    async def invoke_agent(
        self, 
        agent_url: str, 
        action: str, 
        payload: Dict[str, Any], 
        auth_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Asynchronously invokes an external agent API via JSON POST contract.

        Args:
            agent_url: Target endpoint URL of the external agent.
            action: The specific action or tool method requested (e.g., "estimate_cost").
            payload: Data payload required by the target agent.
            auth_token: Optional Bearer token for inter-agent authentication.

        Returns:
            Dict[str, Any]: Response data dictionary from the target agent.
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "sow-hld-agent/1.0"
        }

        # Attach auth token if provided or set in environment
        token = auth_token or os.getenv("A2A_AUTH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        request_data = {
            "action": action,
            "sender": "sow-hld-agent",
            "data": payload
        }

        logger.info(f"Invoking A2A agent at: {agent_url} [Action: {action}]")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(agent_url, json=request_data, headers=headers)
                
                # Raise exception for 4xx and 5xx status codes
                response.raise_for_status()
                
                logger.info(f"Successfully received response from A2A agent ({response.status_code})")
                return response.json()

        except httpx.HTTPStatusError as http_err:
            logger.error(f"A2A agent returned HTTP error status: {http_err.response.status_code} - {http_err.response.text}")
            raise RuntimeError(f"A2A Agent Invocation Failed: {http_err.response.text}") from http_err
        except httpx.RequestError as req_err:
            logger.error(f"A2A Network request failed: {str(req_err)}")
            raise RuntimeError(f"A2A Network Error: {str(req_err)}") from req_err

    async def query_pricing_agent(self, hld_components: list) -> Dict[str, Any]:
        """Convenience method to query an external Cloud Cost Estimation Agent."""
        pricing_agent_url = os.getenv("PRICING_AGENT_URL", "http://localhost:8001/a2a/invoke")
        
        return await self.invoke_agent(
            agent_url=pricing_agent_url,
            action="estimate_infrastructure_cost",
            payload={"components": hld_components}
        )



# Standalone Execution / Testing Block


if __name__ == "__main__":
    import asyncio

    async def test_a2a_client():
        client = A2AClientTool()

        # Testing with a mock/httpbin endpoint to simulate external agent invocation
        mock_agent_url = "https://httpbin.org/post"
        mock_payload = {
            "components": [
                {"name": "AWS ECS Fargate", "nodes": 4},
                {"name": "Amazon OpenSearch", "instance_type": "or1.xlarge"}
            ]
        }

        print("Testing A2AClientTool asynchronously...")
        try:
            response = await client.invoke_agent(
                agent_url=mock_agent_url,
                action="estimate_cost",
                payload=mock_payload
            )
            print("\n--- A2A Invocations Response Received! ---")
            print(f"Server URL Echoed: {response.get('url')}")
            print(f"Action Sent: {response.get('json', {}).get('action')}")
        except Exception as err:
            print(f"A2A invocation failed: {err}")

    # Run async test loop
    asyncio.run(test_a2a_client())