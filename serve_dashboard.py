#!/usr/bin/env python3
"""
Servidor simples para servir o dashboard sem problemas de CORS.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

class CORSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

def serve_dashboard():
    """Serve o dashboard em um servidor local."""
    
    # Mudar para o diretório do projeto
    os.chdir(Path(__file__).parent)
    
    PORT = 8080
    Handler = CORSRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("🚀 Servidor do Dashboard iniciado!")
        print(f"📊 Acesse: http://localhost:{PORT}/dashboard.html")
        print(f"🔗 API rodando em: http://localhost:8000")
        print("\n⚠️  Pressione Ctrl+C para parar")
        
        # Abrir automaticamente no navegador
        webbrowser.open(f'http://localhost:{PORT}/dashboard.html')
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Servidor parado")

if __name__ == "__main__":
    serve_dashboard()
