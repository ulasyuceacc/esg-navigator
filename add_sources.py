
import json
import subprocess
import sys
import time
import os

MCP_EXE = os.environ.get("MCP_EXE", "notebooklm-mcp")
NOTEBOOK_ID = os.environ.get("NOTEBOOK_ID", "0c7d9ec4-1bd2-4534-84bb-880e44022ee3")

def add_url(process, url, mcp_id):
    query_msg = {
        "jsonrpc": "2.0", 
        "id": mcp_id, 
        "method": "tools/call", 
        "params": {
            "name": "notebook_add_url", 
            "arguments": {
                "notebook_id": NOTEBOOK_ID,
                "url": url
            }
        }
    }
    process.stdin.write(json.dumps(query_msg) + "\n")
    
    # Read response
    response_line = process.stdout.readline()
    print(f"Added {url}: {response_line.strip()[:100]}...")

def main():
    with open("videos.txt", "r") as f:
        videos = [line.strip() for line in f.readlines() if line.strip()]

    # Limit to 45 videos to be safe (max NotebookLM sources = 50)
    videos = videos[:45]

    process = subprocess.Popen(
        [MCP_EXE],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Send initialize
    init_msg = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"capabilities": {}, "clientInfo": {"name": "esg-web-app", "version": "1.0"}, "protocolVersion": "2024-11-05"}}
    process.stdin.write(json.dumps(init_msg) + "\n")
    process.stdout.readline()
    
    # Send initialized notification
    initialized_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    process.stdin.write(json.dumps(initialized_msg) + "\n")
    
    mcp_id = 1
    for vid in videos:
        url = f"https://www.youtube.com/watch?v={vid}"
        add_url(process, url, mcp_id)
        mcp_id += 1
        time.sleep(1) # a bit of delay to avoid rate limiting
        
    process.terminate()

if __name__ == "__main__":
    main()
