# Guia para Publicação Web do Social Warriors com Ruffle

Para disponibilizar o jogo "Social Warriors" na web, permitindo que usuários joguem diretamente pelo navegador sem a necessidade de downloads ou configurações locais, é fundamental entender os requisitos de hospedagem e as opções disponíveis. O jogo, por depender de um backend Flask, não pode ser hospedado como um simples site estático.

## Requisitos Essenciais para Hospedagem Web

1.  **Servidor com Python e Flask:** O componente principal é o servidor Flask que você rodou localmente. Ele precisa estar ativo em um ambiente de servidor público para responder às requisições do cliente Flash (Ruffle).
2.  **Acesso HTTP/HTTPS:** O servidor deve ser acessível via HTTP (e preferencialmente HTTPS para segurança e compatibilidade com navegadores modernos) em uma porta pública (geralmente 80 para HTTP e 443 para HTTPS).
3.  **Domínio ou IP Público:** Seu servidor precisará de um endereço IP público ou um nome de domínio associado para que os usuários possam acessá-lo.
4.  **Configuração de Firewall:** As portas necessárias (ex: 80, 443, e a porta do Flask se não estiver atrás de um proxy) devem estar abertas no firewall do servidor.
5.  **Servidor Web de Produção (WSGI):** Para um ambiente real, você precisará de um servidor WSGI (como Gunicorn ou uWSGI) para rodar a aplicação Flask, e um proxy reverso (como Nginx ou Apache) para lidar com as requisições HTTP/HTTPS e servir arquivos estáticos de forma eficiente.

## Opções de Hospedagem

Existem duas categorias principais de hospedagem para este tipo de aplicação:

### 1. Servidor Virtual Privado (VPS) ou Máquina Virtual (VM)

Esta opção oferece controle total sobre o ambiente do servidor. Você aluga uma máquina virtual e instala e configura tudo manualmente.

**Exemplos de Provedores:**
*   DigitalOcean
*   Linode
*   AWS EC2
*   Google Cloud Compute Engine
*   Azure Virtual Machines

**Vantagens:**
*   **Controle Total:** Você tem acesso root e pode instalar qualquer software e configurar o ambiente exatamente como desejar.
*   **Flexibilidade:** Ideal para aplicações com requisitos específicos ou que precisam de otimizações de performance personalizadas.
*   **Custo-benefício:** Pode ser mais econômico para projetos de médio a grande porte, ou se você já tem experiência em administração de sistemas.

**Desvantagens:**
*   **Complexidade:** Requer conhecimento em administração de sistemas Linux (ou Windows Server), configuração de servidores web (Nginx/Apache), WSGI, firewalls, etc.
*   **Manutenção:** Você é responsável por todas as atualizações de segurança, backups e monitoramento.

### 2. Plataformas como Serviço (PaaS)

As PaaS abstraem grande parte da complexidade de gerenciamento de infraestrutura, permitindo que você se concentre apenas no código da sua aplicação. Elas geralmente oferecem escalabilidade automática e ferramentas de deploy simplificadas.

**Exemplos de Provedores:**
*   Heroku (suporte a Python)
*   Google App Engine (suporte a Python)
*   AWS Elastic Beanstalk (suporte a Python)
*   Render
*   Fly.io

**Vantagens:**
*   **Facilidade de Uso:** Deploy e gerenciamento são muito mais simples, muitas vezes com integração direta com repositórios Git.
*   **Escalabilidade:** A plataforma cuida da escalabilidade da sua aplicação automaticamente.
*   **Menos Manutenção:** O provedor gerencia o sistema operacional, patches de segurança e infraestrutura subjacente.

**Desvantagens:**
*   **Menos Controle:** Você tem menos controle sobre o ambiente subjacente e as configurações do servidor.
*   **Custo:** Pode ser mais caro para aplicações com alto tráfego ou requisitos de recursos específicos, e os custos podem ser menos previsíveis.
*   **Limitações:** Algumas PaaS podem ter restrições sobre o que pode ser instalado ou configurado, o que pode ser um problema para o Ruffle self-hosted ou para o servidor Flask que serve arquivos estáticos de forma não-padrão.

## Recomendações para o Social Warriors

Dado que o projeto inclui um servidor Flask que serve tanto a lógica de backend quanto os arquivos estáticos (incluindo os do Ruffle e os SWFs), uma **VPS** oferece a maior flexibilidade e controle para garantir que todos os caminhos de arquivo e configurações funcionem como esperado. Para iniciantes, uma PaaS como Heroku ou Render pode ser uma opção mais fácil, mas exigirá adaptações para garantir que todos os arquivos estáticos sejam servidos corretamente e que o Ruffle seja carregado de forma autohospedada.

## Preparação do Projeto para Produção

Antes de fazer o deploy, algumas modificações no código são importantes para um ambiente de produção:

1.  **Variável de Ambiente para `SECRET_KEY`:** A `SECRET_KEY` do Flask é usada para segurança de sessões. Em produção, ela **NÃO** deve ser um valor fixo no código. O `server.py` foi atualizado para ler essa chave de uma variável de ambiente `FLASK_SECRET_KEY`. Se a variável não for definida, ele usará uma chave de desenvolvimento, mas com um aviso no log.
2.  **Logging:** O `server.py` foi ajustado para usar o sistema de logging do Flask, que é mais adequado para ambientes de produção, direcionando os logs para a saída padrão (stdout/stderr), que pode ser capturada por ferramentas de monitoramento.
3.  **Servidor WSGI (`gunicorn`):** Para rodar o Flask em produção, usaremos o Gunicorn, que é um servidor WSGI robusto. Ele foi adicionado ao `requirements.txt` e um arquivo `wsgi.py` foi criado para que o Gunicorn possa iniciar a aplicação Flask.

## Guia de Deploy em um Servidor Linux (VPS)

Este guia assume que você tem acesso SSH a um servidor Linux (ex: Ubuntu 22.04).

### 1. Conectar ao Servidor via SSH

Use um cliente SSH (como PuTTY no Windows ou o terminal no Linux/macOS) para se conectar ao seu servidor:

```bash
ssh seu_usuario@seu_ip_do_servidor
```

### 2. Atualizar o Sistema e Instalar Dependências

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip python3-dev nginx -y
```

### 3. Copiar o Projeto para o Servidor

Você pode usar `scp` (Secure Copy Protocol) para copiar a pasta do projeto para o servidor. No seu computador local:

```bash
scp -r /caminho/para/social-warriors_0.02a seu_usuario@seu_ip_do_servidor:/home/seu_usuario/
```

No servidor, mova a pasta para um local adequado, por exemplo, `/var/www/social-warriors/`:

```bash
sudo mv /home/seu_usuario/social-warriors_0.02a /var/www/social-warriors/
cd /var/www/social-warriors/social-warriors_0.02a
```

### 4. Configurar Ambiente Virtual e Instalar Dependências Python

É uma boa prática usar um ambiente virtual para isolar as dependências do projeto:

```bash
sudo apt install python3.11-venv -y # Instala o módulo venv para Python 3.11
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Configurar a `SECRET_KEY`

Defina a variável de ambiente `FLASK_SECRET_KEY` com uma chave forte e única. Você pode gerar uma com `python -c 'import os; print(os.urandom(24))'`.

```bash
export FLASK_SECRET_KEY='SUA_CHAVE_SECRETA_FORTE_AQUI'
```

Para que essa variável seja persistente, você pode adicioná-la ao arquivo de serviço do Gunicorn (passo 7).

### 6. Testar o Gunicorn

Certifique-se de que o Gunicorn pode iniciar sua aplicação Flask:

```bash
gunicorn --bind 0.0.0.0:5000 wsgi:app
```

Se tudo estiver correto, você verá mensagens do Gunicorn. Pressione `Ctrl+C` para parar.

### 7. Criar um Serviço Systemd para Gunicorn

Crie um arquivo de serviço Systemd para que o Gunicorn rode em segundo plano e inicie automaticamente. Crie o arquivo `/etc/systemd/system/socialwars.service`:

```bash
sudo nano /etc/systemd/system/socialwars.service
```

Cole o seguinte conteúdo (ajuste `User`, `Group`, `WorkingDirectory` e `ExecStart` conforme necessário):

```ini
[Unit]
Description=Gunicorn instance to serve Social Wars Flask app
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/social-warriors/social-warriors_0.02a
Environment="PATH=/var/www/social-warriors/social-warriors_0.02a/venv/bin"
Environment="FLASK_SECRET_KEY=SUA_CHAVE_SECRETA_FORTE_AQUI" # Substitua pela sua chave
ExecStart=/var/www/social-warriors/social-warriors_0.02a/venv/bin/gunicorn --workers 3 --bind unix:socialwars.sock -m 007 wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Salve e feche o arquivo (Ctrl+X, Y, Enter).

Inicie e habilite o serviço:

```bash
sudo systemctl start socialwars
sudo systemctl enable socialwars
```

Verifique o status:

```bash
sudo systemctl status socialwars
```

### 8. Configurar Nginx como Proxy Reverso

Crie um arquivo de configuração Nginx para seu site em `/etc/nginx/sites-available/socialwars`:

```bash
sudo nano /etc/nginx/sites-available/socialwars
```

Cole o seguinte conteúdo (substitua `seu_dominio.com` pelo seu domínio ou IP do servidor):

```nginx
server {
    listen 80;
    server_name seu_dominio.com seu_ip_do_servidor;

    location / {
        include proxy_params;
        proxy_pass http://unix:/var/www/social-warriors/social-warriors_0.02a/socialwars.sock;
    }

    location /static/ {
        alias /var/www/social-warriors/social-warriors_0.02a/static/;
    }

    location /ruffle/ {
        alias /var/www/social-warriors/social-warriors_0.02a/ruffle/;
    }

    location /img/ {
        alias /var/www/social-warriors/social-warriors_0.02a/templates/img/;
    }

    location /avatars/ {
        alias /var/www/social-warriors/social-warriors_0.02a/templates/avatars/;
    }

    location /css/ {
        alias /var/www/social-warriors/social-warriors_0.02a/templates/css/;
    }
}
```

Crie um link simbólico para `sites-enabled` e teste a configuração:

```bash
sudo ln -s /etc/nginx/sites-available/socialwars /etc/nginx/sites-enabled
sudo nginx -t
```

Se o teste for bem-sucedido, reinicie o Nginx:

```bash
sudo systemctl restart nginx
```

### 9. Configurar HTTPS com Certbot (Opcional, mas Recomendado)

Para segurança e para evitar avisos de navegador, configure HTTPS com Let's Encrypt via Certbot:

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d seu_dominio.com
```

Siga as instruções na tela. O Certbot irá configurar automaticamente o Nginx para HTTPS e renovar os certificados.

### 10. Ajustar Firewall (UFW)

Permita o tráfego HTTP e HTTPS no firewall:

```bash
sudo ufw allow 'Nginx Full'
sudo ufw delete allow 'Nginx HTTP' # Se você já tinha permitido apenas HTTP
sudo ufw enable # Se o firewall não estiver ativo
```

### 11. Acessar o Jogo

Agora você pode acessar o jogo pelo seu domínio (ou IP, se não configurou um domínio) no navegador:

`http://seu_dominio.com` (ou `https://seu_dominio.com` se configurou HTTPS)

Este guia fornece uma base sólida para a publicação do seu jogo. Lembre-se de que a manutenção e monitoramento contínuos são essenciais para um ambiente de produção. 

[1]: https://www.python.org/downloads/ "Python Downloads"
