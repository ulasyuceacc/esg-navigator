import http.server
import socketserver
import json
import subprocess
import os
import sys
import traceback

PORT = int(os.environ.get("PORT", 8080))
MCP_EXE = os.environ.get("MCP_EXE", "notebooklm-mcp")
NOTEBOOK_ID = os.environ.get("NOTEBOOK_ID", "0c7d9ec4-1bd2-4534-84bb-880e44022ee3")

class NotebookLMSession:
    def __init__(self):
        print("Starting NotebookLM MCP Server in background...")
        self.process = subprocess.Popen(
            [MCP_EXE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding='utf-8',
            bufsize=1
        )
        
        # 1) Send initialize
        init_msg = {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"capabilities": {}, "clientInfo": {"name": "esg-web-app", "version": "1.0"}, "protocolVersion": "2024-11-05"}}
        self.send(init_msg)
        self.process.stdout.readline() # Read Init Response
        
        # 2) Send initialized notification
        initialized_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self.send(initialized_msg)
        
        self.msg_id = 1
        
        # 3) Configure chat to return shorter responses for speed
        print("Configuring notebook chat settings for speed (Shorter responses)...")
        self.msg_id += 1
        config_msg = {
            "jsonrpc": "2.0", 
            "id": self.msg_id, 
            "method": "tools/call", 
            "params": {
                "name": "chat_configure", 
                "arguments": {
                    "notebook_id": NOTEBOOK_ID,
                    "response_length": "default",
                    "goal": "default"
                }
            }
        }
        self.send(config_msg)
        self._wait_for_response(self.msg_id) # Ignore output
        
        print("NotebookLM MCP Server Ready and connected!")

    def send(self, msg):
        self.process.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def _wait_for_response(self, target_id):
        final_answer = None
        while True:
            response_line = self.process.stdout.readline()
            if not response_line:
                break
            try:
                response_data = json.loads(response_line)
                if response_data.get("id") == target_id:
                    if "result" in response_data:
                        final_answer = response_data["result"]
                    elif "error" in response_data:
                        final_answer = {"error": response_data["error"]}
                    break
            except json.JSONDecodeError:
                continue
        return final_answer

    def get_topics(self):
        print("Fetching suggested topics...")
        self.msg_id += 1
        current_id = self.msg_id
        
        query_msg = {
            "jsonrpc": "2.0", 
            "id": current_id, 
            "method": "tools/call", 
            "params": {
                "name": "notebook_describe", 
                "arguments": {"notebook_id": NOTEBOOK_ID}
            }
        }
        self.send(query_msg)
        response = self._wait_for_response(current_id)
        
        if response and "content" in response and len(response["content"]) > 0:
            text_result = response["content"][0].get("text", "{}")
            try:
                text_json = json.loads(text_result)
                return text_json.get("suggested_topics", [])
            except:
                pass
        return []

    def ask(self, query):
        print(f"Asking notebook: {query}")
        self.msg_id += 1
        current_id = self.msg_id
        
        query_msg = {
            "jsonrpc": "2.0", 
            "id": current_id, 
            "method": "tools/call", 
            "params": {
                "name": "notebook_query", 
                "arguments": {
                    "notebook_id": NOTEBOOK_ID,
                    "query": query,
                    "timeout": 120.0
                }
            }
        }
        self.send(query_msg)
        
        response = self._wait_for_response(current_id)
        if response and "error" in response:
            return f"NotebookLM Error: {response['error']}"
        elif response and "content" in response and len(response["content"]) > 0:
            text_result = response["content"][0].get("text", "{}")
            try:
                text_json = json.loads(text_result)
                return text_json.get("answer", text_result)
            except:
                return text_result
        return "Failed to parse response from NotebookLM."

try:
    notebook_session = NotebookLMSession()
except Exception as e:
    print(f"Failed to start MCP server: {e}")
    notebook_session = None

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/topics':
            try:
                if not notebook_session:
                    topics = []
                else:
                    topics = notebook_session.get_topics()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'topics': topics[:4]}, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/ask':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                query = data.get('query', '')
                
                if not notebook_session:
                    answer = "Error: Backend MCP session failed to start."
                else:
                    answer = notebook_session.ask(query)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self.end_headers()
                
                response = {'answer': answer}
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                traceback.print_exc()
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    Handler.extensions_map.update({
        '.webapp': 'application/x-webapp-manifest+json',
    })
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Shutting down...")
            if notebook_session and notebook_session.process:
                notebook_session.process.terminate()
