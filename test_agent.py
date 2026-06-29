import sys
import os
import logging

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from config import fetch_all_business_profiles, fetch_profile_and_catalog
from orchestrator.graph import agent_run_graph

logging.basicConfig(level=logging.INFO)

def run_test():
    print("=== Step 1: Testing Mock Profile Loading ===")
    profiles = fetch_all_business_profiles()
    if not profiles:
        print("Error: No profiles found.")
        return
        
    print(f"Success: Found {len(profiles)} mock business profiles.")
    for p in profiles:
        print(f" - Profile ID {p['id']}: {p['name']} ({p['category']})")
        
    target_profile = profiles[0]
    print(f"\n=== Step 2: Loading Product Catalog for Profile ID {target_profile['id']} ===")
    ctx = fetch_profile_and_catalog(target_profile['id'])
    print(f"Success: Loaded profile: {ctx['profile'].get('name')}")
    print(f"Products count: {len(ctx['products'])}")
    for prod in ctx['products']:
        print(f" - Product: {prod['name']} (Price: {prod['price']} LE)")
        
    print("\n=== Step 3: Invoking Multi-Agent Graph (Marketing Query) ===")
    state_input = {
        "profile_id": target_profile['id'],
        "current_query": "Give me a brief 2-sentence marketing idea for Eid holiday",
        "session_id": "test_session_999",
        "routed_agent": "CONTINUE",
        "logo_prompt": "",
        "logo_base64": "",
        "agent_output": "",
        "user_ip": "127.0.0.1"
    }
    
    try:
        output_state = agent_run_graph.invoke(state_input)
        print("\n=== Agent Result ===")
        print(f"Routed Agent: {output_state.get('routed_agent')}")
        print(f"Agent Output:\n{output_state.get('agent_output')}")
        print("====================")
        print("Graph executed successfully!")
    except Exception as e:
        print(f"Error invoking agent graph: {e}")

if __name__ == "__main__":
    run_test()
