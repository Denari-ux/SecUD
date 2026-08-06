# SecUD
Clonagem automática - Baixa a página de login e modifica o formulário para capturar credenciais

Como usar
bash



# Instalar dependências
pip3 install requests beautifulsoup4

# Clonar e servir página de login
python3 SecUD.py https://site-alvo.com/login

# Especificar porta diferente
python3 SecUD.py https://site-alvo.com/login --port 80

Funcionalidades

Clonagem automática - Baixa a página de login e modifica o formulário para capturar credenciais
Remoção de proteções - Remove CSRF tokens, nonces, captchas e scripts de segurança automaticamente
Proxy de recursos - Serve CSS, JS e imagens do site original para parecer legítimo
Redirecionamento real - Após capturar, reenvia o POST para o site original e retorna a resposta real
Relatório detalhado - Exibe credenciais capturadas em tempo real e resumo ao final

Técnicas de evasão incluídas

Remoção de CSRF tokens para aceitar submissão direta
Proxy de assets para manter aparência idêntica
Reenvio real de credenciais ao site alvo para login funcional
Headers preservados para não levantar suspeitas
Nota de segurança: Este script é exclusivo para testes de penetração autorizados. Sempre valide o escopo do teste antes de usar.
