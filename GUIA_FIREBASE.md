# Guia de Integração Firebase - Social Warriors

## Visão Geral

Esta versão do Social Warriors inclui integração com o **Firebase** para:

- **Autenticação real** com email e senha (Firebase Auth)
- **Armazenamento na nuvem** das vilas dos jogadores (Firebase Firestore)
- **Modo dual**: funciona com Firebase OU em modo local (fallback automático)

---

## Arquivos Novos/Modificados

| Arquivo | Descrição |
|---------|-----------|
| `firebase_config.py` | Configuração e inicialização do Firebase |
| `firebase_sessions.py` | Gerenciamento de vilas via Firestore (substitui `sessions.py`) |
| `templates/login_firebase.html` | Tela de login/registro com Firebase Auth |
| `migrate_to_firebase.py` | Script para migrar saves locais para o Firestore |
| `server.py` | Servidor atualizado com rotas Firebase |
| `requirements.txt` | Atualizado com `firebase-admin` |

---

## Passo a Passo para Configurar

### 1. Criar Projeto no Firebase

1. Acesse [https://console.firebase.google.com](https://console.firebase.google.com)
2. Clique em **"Adicionar projeto"**
3. Dê um nome (ex: `social-warriors`)
4. Desative o Google Analytics (opcional) e clique em **"Criar projeto"**

### 2. Ativar Authentication

1. No painel lateral, clique em **"Authentication"**
2. Clique em **"Começar"**
3. Na aba **"Sign-in method"**, ative **"E-mail/senha"**
4. Clique em **"Salvar"**

### 3. Ativar Firestore Database

1. No painel lateral, clique em **"Firestore Database"**
2. Clique em **"Criar banco de dados"**
3. Selecione **"Iniciar no modo de teste"** (para desenvolvimento)
4. Escolha a região mais próxima (ex: `southamerica-east1` para Brasil)
5. Clique em **"Ativar"**

**IMPORTANTE:** Em produção, configure as regras de segurança do Firestore!

### 4. Baixar Credenciais do Servidor (Service Account)

1. Clique no ícone de engrenagem > **"Configurações do projeto"**
2. Vá na aba **"Contas de serviço"**
3. Clique em **"Gerar nova chave privada"**
4. Baixe o arquivo JSON
5. **Renomeie** para `firebase-credentials.json`
6. **Coloque na pasta raiz do projeto** (junto com `server.py`)

### 5. Configurar o Firebase Web SDK

1. Ainda em **"Configurações do projeto"** > aba **"Geral"**
2. Role até **"Seus apps"** e clique em **"</>** (Web)"
3. Dê um nome ao app (ex: `social-warriors-web`)
4. Copie as configurações que aparecem:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSy...",
  authDomain: "social-warriors.firebaseapp.com",
  projectId: "social-warriors",
  storageBucket: "social-warriors.appspot.com",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
};
```

5. Abra o arquivo `firebase_config.py` e cole os valores na variável `FIREBASE_WEB_CONFIG`:

```python
FIREBASE_WEB_CONFIG = {
    "apiKey": "AIzaSy...",
    "authDomain": "social-warriors.firebaseapp.com",
    "projectId": "social-warriors",
    "storageBucket": "social-warriors.appspot.com",
    "messagingSenderId": "123456789",
    "appId": "1:123456789:web:abcdef",
}
```

**Alternativa:** Você pode usar variáveis de ambiente ao invés de editar o arquivo:

```bash
export FIREBASE_API_KEY="AIzaSy..."
export FIREBASE_AUTH_DOMAIN="social-warriors.firebaseapp.com"
export FIREBASE_PROJECT_ID="social-warriors"
export FIREBASE_STORAGE_BUCKET="social-warriors.appspot.com"
export FIREBASE_MESSAGING_SENDER_ID="123456789"
export FIREBASE_APP_ID="1:123456789:web:abcdef"
```

### 6. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 7. Executar o Servidor

```bash
python server.py
```

Se tudo estiver correto, você verá:

```
 [+] Loading Firebase...
 [+] FIREBASE: Inicializado com sucesso!
 [+] Firebase ATIVO - Usando autenticação e Firestore
```

### 8. (Opcional) Migrar Saves Locais

Se você já tem vilas salvas na pasta `saves/`, pode migrá-las para o Firestore:

```bash
python migrate_to_firebase.py
```

---

## Como Funciona

### Fluxo de Login

```
Usuário abre o site
        │
        ▼
┌─────────────────────┐
│  login_firebase.html │  ← Tela de login/registro
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
 [LOGIN]    [REGISTRO]
    │           │
    ▼           ▼
Firebase Auth   /api/register
(client-side)   (server-side)
    │           │
    ▼           ▼
 ID Token    Firebase Auth
    │        + Firestore
    ▼           │
 /api/login     ▼
(server-side)  Auto-login
    │           │
    ▼           ▼
Sessão Flask ← Sessão Flask
    │
    ▼
 /play-ruffle.html
```

### Fluxo de Salvamento

```
Jogador faz ação no jogo
        │
        ▼
command.php (Flask)
        │
        ▼
save_session(USERID)
        │
        ▼
┌───────────────────────┐
│  Firebase habilitado? │
└───────┬───────────────┘
   SIM  │  NÃO
   ▼    │   ▼
Firestore   Arquivo JSON
(nuvem)     (local)
```

### Modo Dual (Fallback)

O sistema funciona em **dois modos**:

- **Com Firebase**: Se `firebase-credentials.json` existir e estiver correto, usa Firebase Auth + Firestore
- **Sem Firebase**: Se o arquivo não existir, funciona exatamente como antes (modo local com arquivos JSON)

Isso significa que você pode testar sem Firebase e ativar quando quiser!

---

## Estrutura do Firestore

```
Firestore
├── users/                    ← Dados dos usuários
│   └── {firebase_uid}/
│       ├── email: "user@email.com"
│       ├── display_name: "Warrior"
│       ├── userid: "uuid-da-vila"
│       ├── created_at: 1234567890
│       └── last_login: 1234567890
│
└── saves/                    ← Vilas dos jogadores
    └── {userid}/
        ├── playerInfo: {...}
        ├── maps: [{...}]
        ├── privateState: {...}
        └── version: "0.02a"
```

---

## Regras de Segurança do Firestore (Produção)

Para produção, configure estas regras no Firestore:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Usuários só podem ler/escrever seus próprios dados
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Saves são gerenciados pelo servidor (Admin SDK)
    // O frontend não acessa diretamente
    match /saves/{saveId} {
      allow read, write: if false; // Apenas Admin SDK
    }
  }
}
```

---

## Solução de Problemas

| Problema | Solução |
|----------|---------|
| "Firebase não está configurado" | Verifique se `firebase-credentials.json` está na pasta do projeto |
| "Token inválido" | Verifique se a `apiKey` no `FIREBASE_WEB_CONFIG` está correta |
| "Email já cadastrado" | O email já existe no Firebase Auth |
| Servidor roda em modo local | O arquivo de credenciais não foi encontrado ou está inválido |
| Erro de CORS | Adicione o domínio do seu servidor nas configurações do Firebase Auth |

---

## Notas Importantes

- As vilas estáticas (NPCs) e quests continuam sendo carregadas do disco (não precisam estar no Firebase)
- O Firebase Admin SDK (server-side) usa as credenciais do Service Account
- O Firebase Web SDK (client-side) usa a configuração pública (apiKey, etc.)
- Em produção, use HTTPS e configure as regras de segurança do Firestore
- O `firebase-credentials.json` é **secreto** - nunca compartilhe ou commite no Git!
