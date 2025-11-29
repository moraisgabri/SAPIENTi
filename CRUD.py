import os
os.system("cls")
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import sys
from datetime import datetime, timezone 

# --- CONEXÃO E ESTRUTURA ---

def conectar(db_name):
    return sqlite3.connect(db_name)

def verificar_e_adicionar_coluna(cursor, tabela, coluna, tipo_dado):
    """Função auxiliar para garantir que colunas existam sem apagar dados antigos"""
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [c[1] for c in cursor.fetchall()]
    if coluna not in colunas_existentes:
        try:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo_dado}")
        except sqlite3.OperationalError:
            pass

def criar_tabelas():
    # --- VIDEOS ---
    conn_v = conectar('videos.db')
    cursor_v = conn_v.cursor()
    cursor_v.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            categoria TEXT,
            ano INTEGER,
            duracao_min INTEGER,
            autor TEXT,
            data_envio TEXT,
            disciplina TEXT,
            status TEXT DEFAULT 'Pendente'
        )
    ''')
    # Garantir novas colunas se o banco já existia
    verificar_e_adicionar_coluna(cursor_v, 'videos', 'autor', 'TEXT')
    verificar_e_adicionar_coluna(cursor_v, 'videos', 'data_envio', 'TEXT') 
    verificar_e_adicionar_coluna(cursor_v, 'videos', 'disciplina', 'TEXT')
    verificar_e_adicionar_coluna(cursor_v, 'videos', 'status', "TEXT DEFAULT 'Pendente'")
    conn_v.commit()
    conn_v.close()

    # --- USUARIO ---
    conn_u = conectar('usuario.db')
    cursor_u = conn_u.cursor()
    cursor_u.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE, 
            faculdade TEXT,
            numemro_de_matricula INTEGER,
            verificacao BOOLEAN,
            carga_horaria INTEGER DEFAULT 0,
            categoria TEXT,
            senha TEXT
        )
    ''')
    # garantir coluna que armazena horas de cursos assistidos (bonus)
    verificar_e_adicionar_coluna(cursor_u, 'usuario', 'horas_assistidas_extra', 'INTEGER DEFAULT 0')
    conn_u.commit()
    conn_u.close()

    # --- CURADOR ---
    conn_c = conectar('curador.db')
    cursor_c = conn_c.cursor()
    cursor_c.execute('''
        CREATE TABLE IF NOT EXISTS curador (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT,
            faculdade TEXT,
            numemro_de_matricula INTEGER,
            verificacao BOOLEAN,
            monitor_de TEXT,
            categoria TEXT,
            senha TEXT
        )
    ''')
    # Adicionando senha ao curador para permitir login
    verificar_e_adicionar_coluna(cursor_c, 'curador', 'senha', 'TEXT')
    conn_c.commit()
    conn_c.close()

# --- AUTENTICAÇÃO ---

def login_sistema():
    print("\n--- LOGIN ---")
    email = input("Email: ")
    senha = input("Senha: ")

    # 1. Verificar ADMIN (Hardcoded)
    if email == "master@sapienti.com" and senha == "master123":
        return "admin", {"nome": "Administrador Master"}

    # 2. Verificar CURADOR
    conn_c = conectar('curador.db')
    cursor_c = conn_c.cursor()
    cursor_c.execute("SELECT id, nome, senha, monitor_de FROM curador WHERE email = ?", (email,))
    curador = cursor_c.fetchone()
    conn_c.close()

    if curador:
        # curador = (id, nome, hash_senha, monitor_de)
        # Nota: Se você cadastrou curadores manualmente sem hash antes, isso pode falhar.
        # O ideal é cadastrar via menu de admin que usa hash.
        if curador[2] and check_password_hash(curador[2], senha):
            return "curador", {"id": curador[0], "nome": curador[1], "monitor_de": curador[3]}

    # 3. Verificar USUÁRIO
    conn_u = conectar('usuario.db')
    cursor_u = conn_u.cursor()
    cursor_u.execute("SELECT id, nome, senha, carga_horaria FROM usuario WHERE email = ?", (email,))
    usuario = cursor_u.fetchone()
    conn_u.close()

    if usuario:
        if usuario[2] and check_password_hash(usuario[2], senha):
            return "usuario", {"id": usuario[0], "nome": usuario[1], "carga_horaria": usuario[3]}

    print("\nCredenciais inválidas ou usuário não encontrado.")
    return None, None

def realizar_cadastro_usuario():
    print("\n--- CADASTRO DE ESTUDANTE ---")
    nome = input("Nome completo: ")
    email = input("Email: ")
    faculdade = input("Universidade: ")
    try:
        matricula = int(input("Número de Matrícula: "))
    except ValueError:
        print("Matrícula inválida.")
        return

    while True:
        senha = input("Crie uma senha: ")
        conf = input("Confirme a senha: ")
        if senha == conf:
            break
        print("Senhas não coincidem.")

    hashed = generate_password_hash(senha)
    
    try:
        conn = conectar('usuario.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO usuario (nome, email, faculdade, numemro_de_matricula, verificacao, carga_horaria, categoria, senha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, email, faculdade, matricula, False, 0, "Estudante", hashed))
        conn.commit()
        conn.close()
        print("\nCadastro realizado com sucesso! Faça login.")
    except sqlite3.IntegrityError:
        print("\nEmail já cadastrado.")

def apagar_video_usuario(nome):
    conn = conectar('videos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, duracao_min, status FROM videos WHERE autor = ?", (nome,))
    videos = cursor.fetchall()

    if not videos:
        print("\nVocê ainda não enviou vídeos.")
        conn.close()
        return

    print("\n--- MEUS VÍDEOS ---")
    for idx, v in enumerate(videos, start=1):
        print(f"{idx}. ID:{v[0]} | {v[1]} | {v[3]} | {v[2]} min")

    try:
        escolha = int(input("\nEscolha o número do vídeo para apagar (0 para cancelar): "))
    except ValueError:
        print("Escolha inválida.")
        conn.close()
        return

    if escolha == 0:
        conn.close()
        return

    if escolha < 1 or escolha > len(videos):
        print("Seleção inválida.")
        conn.close()
        return

    vid_id, titulo_sel, duracao_sel, status_sel = videos[escolha - 1]
    confirmar = input(f"Tem certeza que deseja apagar '{titulo_sel}' (ID {vid_id})? (s/N): ").strip().lower()
    if confirmar != 's':
        print("Operação cancelada.")
        conn.close()
        return

    try:
        # salvar valor atual para informar alteração posterior
        conn_u = conectar('usuario.db')
        cursor_u = conn_u.cursor()
        cursor_u.execute("SELECT carga_horaria FROM usuario WHERE nome = ?", (nome,))
        res = cursor_u.fetchone()
        carga_antiga = res[0] if res else 0
        conn_u.close()

        cursor.execute("DELETE FROM videos WHERE id = ?", (vid_id,))
        conn.commit()
        conn.close()

        if status_sel == 'Aprovado':
            nova = atualizar_carga_horaria_por_videos(nome)
            removido = carga_antiga - nova
            print(f"Vídeo apagado. Foram removidos {removido} minutos das suas horas complementares (nova carga: {nova}).")
        else:
            print("Vídeo apagado com sucesso.")
    except Exception as e:
        print("Erro ao apagar vídeo:", e)

def assistir_video(nome):
    raise NotImplementedError

# --- LÓGICA DO USUÁRIO (ALUNO) ---

def menu_aluno(dados_usuario):
    while True:
        print(f"\n=== PAINEL DO ALUNO: {dados_usuario['nome']} ===")
        # Não recalcular automaticamente sobrescrevendo o bonus — recuperar_horas_atualizadas já considera bônus.
        print(f"Suas Horas Complementares Aprovadas: {recuperar_horas_atualizadas(dados_usuario['nome'])} min")
        print("1. Assistir vídeo")
        print("2. Carregar Vídeo")
        print("3. Listar meus Vídeos")
        print("4. Apagar Vídeo")
        print("5. Editar (Perfil / Vídeo)")
        print("6. Sair (Logout)")
        
        op = input("Opção: ")

        if op == '1':
            assistir_video(dados_usuario['nome'])
        elif op == '2':
            carregar_video(dados_usuario['nome'])
        elif op == '3':
            listar_videos_usuario(dados_usuario['nome'])
        elif op == '4':
            apagar_video_usuario(dados_usuario['nome'])
        elif op == '5':
            editar_menu_aluno(dados_usuario)
        elif op == '6':
            break
        else:
            print("Inválido.")

def recuperar_horas_atualizadas(nome_usuario):
    # Busca o valor fresco do banco
    # Agora recalculamos a carga horária a partir dos vídeos aprovados (3x somatório)
    return atualizar_carga_horaria_por_videos(nome_usuario)

def atualizar_carga_horaria_por_videos(nome_autor):
    """Recalcula a carga horária do usuário: 3x somatório das durações aprovadas + bônus de cursos assistidos."""
    conn_v = conectar('videos.db')
    cursor_v = conn_v.cursor()
    cursor_v.execute("SELECT SUM(duracao_min) FROM videos WHERE autor = ? AND status = 'Aprovado'", (nome_autor,))
    soma = cursor_v.fetchone()[0] or 0
    conn_v.close()

    base = soma * 3

    conn_u = conectar('usuario.db')
    cursor_u = conn_u.cursor()
    # obter horas assistidas extra (bônus)
    cursor_u.execute("SELECT horas_assistidas_extra FROM usuario WHERE nome = ?", (nome_autor,))
    res = cursor_u.fetchone()
    extra = res[0] if res and res[0] else 0

    nova_carga = base + extra
    cursor_u.execute("UPDATE usuario SET carga_horaria = ? WHERE nome = ?", (nova_carga, nome_autor))
    conn_u.commit()
    conn_u.close()
    return nova_carga

#Função implementada par automatizar data e hora no momento do cadastro do vídeo.
def timezone():
    """Retorna timestamp ISO com timezone local (ex: 2025-11-25T14:23:00-03:00)."""
    return datetime.now().astimezone().isoformat()

def carregar_video(nome_autor):
    print("\n--- CARREGAR VÍDEO ---")
    titulo = input("Nome do Vídeo: ")
    try:
        duracao = int(input("Duração (em minutos): "))
    except ValueError:
        print("Duração deve ser um número.")
        return

    # Categoria e duração
    cat_op = input("Categoria (1 para vídeo simples e 2 para curso): ").strip()
    if cat_op == '1':
        categoria = "Vídeo simples"
    elif cat_op == '2':
        categoria = "Curso"
    else:
        print("Categoria inválida — será usada 'Geral'.")
        categoria = "Geral"

    # Validação: duração válida sempre; limite de 15 min só para "Vídeo simples"
    if duracao <= 0:
        print("Duração inválida.")
        return
    if categoria == "Vídeo simples" and duracao > 15:
        print("O tempo máximo de vídeo é de 15 minutos.")
        return

    disciplina = input("Disciplina (ex: Matematica, Historia, Python): ")
    
    # Inserção
    data_envio = timezone()  # preenchido automaticamente após autor
    conn = conectar('videos.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO videos (titulo, categoria, ano, duracao_min, autor, data_envio, disciplina, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (titulo, categoria, 2024, duracao, nome_autor, data_envio, disciplina, "Pendente"))
    conn.commit()
    conn.close()
    print(f"\nVídeo '{titulo}' enviado para curadoria com sucesso!")

def listar_videos_usuario(nome_autor):
    conn = conectar('videos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT titulo, disciplina, duracao_min, status FROM videos WHERE autor = ?", (nome_autor,))
    videos = cursor.fetchall()
    conn.close()
    
    if not videos:
        print("\nVocê ainda não enviou vídeos.")
    else:
        print("\n--- MEUS VÍDEOS ---")
        print(f"{'TÍTULO':<20} | {'DISCIPLINA':<15} | {'STATUS'}")
        for v in videos:
            print(f"{v[0]:<20} | {v[1]:<15} | {v[3]}")

def editar_menu_aluno(dados_usuario):
    while True:
        print("\n--- EDITAR ---")
        print("1. Editar Perfil")
        print("2. Editar um dos meus Vídeos")
        print("3. Voltar")
        escolha = input("Escolha: ")
        if escolha == '1':
            editar_perfil_usuario(dados_usuario)
        elif escolha == '2':
            editar_video_usuario(dados_usuario['nome'])
        elif escolha == '3':
            break
        else:
            print("Inválido. Tente novamente.")

def editar_perfil_usuario(dados_usuario):
    print("\n--- EDITAR PERFIL ---")
    user_id = dados_usuario.get('id')

    # Buscar atuais para mostrar
    conn = conectar('usuario.db')
    cursor = conn.cursor()
    if user_id:
        cursor.execute("SELECT nome, email, faculdade, numemro_de_matricula FROM usuario WHERE id = ?", (user_id,))
    else:
        cursor.execute("SELECT nome, email, faculdade, numemro_de_matricula FROM usuario WHERE nome = ?", (dados_usuario['nome'],))
    atual = cursor.fetchone()
    if not atual:
        print("Usuário não encontrado.")
        conn.close()
        return

    nome_atual, email_atual, fac_atual, mat_atual = atual
    print(f"Nome atual: {nome_atual}")
    print(f"Email atual: {email_atual}")
    print(f"Universidade atual: {fac_atual}")
    print(f"Matrícula atual: {mat_atual}")

    novo_nome = input("Novo nome (enter para manter): ").strip()
    novo_email = input("Novo email (enter para manter): ").strip()
    nova_fac = input("Nova universidade (enter para manter): ").strip()
    novo_mat = input("Nova matrícula (enter para manter): ").strip()

    # Senha (confirmação)
    while True:
        senha_nova = input("Nova senha (Digite enter para manter): ")
        if senha_nova == "":
            senha_hashed = None
            break
        conf = input("Confirme a nova senha: ")
        if senha_nova == conf:
            senha_hashed = generate_password_hash(senha_nova)
            break
        print("Senhas não coincidem. Tente novamente.")

    # UPDATE
    campos = []
    valores = []
    alterações = []
    if novo_nome:
        campos.append("nome = ?")
        valores.append(novo_nome)
        alterações.append(("Nome", nome_atual, novo_nome))
    if novo_email:
        campos.append("email = ?")
        valores.append(novo_email)
        alterações.append(("Email", email_atual, novo_email))
    if nova_fac:
        campos.append("faculdade = ?")
        valores.append(nova_fac)
        alterações.append(("Universidade", fac_atual, nova_fac))
    if novo_mat:
        try:
            mat_int = int(novo_mat)
            campos.append("numemro_de_matricula = ?")
            valores.append(mat_int)
            alterações.append(("Matrícula", mat_atual, mat_int))
        except ValueError:
            print("Matrícula inválida, desconsiderada.")
    if senha_hashed:
        campos.append("senha = ?")
        valores.append(senha_hashed)
        alterações.append(("Senha", "********", "********"))

    if not campos:
        print("Nada a atualizar.")
        conn.close()
        return

    # Mostrar mudanças e confirmar (em curador)
    print("\nVocê está prestes a aplicar as seguintes alterações ao seu perfil:")
    for campo, antes, depois in alterações:
        print(f"- {campo}: '{antes}' -> '{depois}'")
    confirmar = input("Confirmar alterações? (S/N): ").strip().lower()
    if confirmar != 's':
        print("Alterações canceladas.")
        conn.close()
        return

    valores.append(user_id if user_id else nome_atual)
    try:
        if user_id:
            cursor.execute(f"UPDATE usuario SET {', '.join(campos)} WHERE id = ?", tuple(valores))
        else:
            cursor.execute(f"UPDATE usuario SET {', '.join(campos)} WHERE nome = ?", tuple(valores))
        conn.commit()
        # Se mudou de nome, atualizar autor dos vídeos
        if novo_nome:
            cursor.execute("UPDATE videos SET autor = ? WHERE autor = ?", (novo_nome, nome_atual))
            conn.commit()
            dados_usuario['nome'] = novo_nome
        print("Perfil atualizado com sucesso.")
    except sqlite3.IntegrityError:
        print("Erro: email já está em uso.")
    finally:
        conn.close()

def editar_video_usuario(nome_autor):
    conn = conectar('videos.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, duracao_min, disciplina, status FROM videos WHERE autor = ?", (nome_autor,))
    videos = cursor.fetchall()
    if not videos:
        print("\nVocê ainda não enviou vídeos.")
        conn.close()
        return

    print("\n--- SEUS VÍDEOS ---")
    for idx, v in enumerate(videos, start=1):
        print(f"{idx}. ID:{v[0]} | {v[1]} | {v[3]} | {v[2]} min")

    try:
        escolha = int(input("Escolha o número do vídeo para editar (0 para cancelar): "))
    except ValueError:
        print("Escolha inválida.")
        conn.close()
        return

    if escolha == 0:
        conn.close()
        return

    if escolha < 1 or escolha > len(videos):
        print("Seleção inválida.")
        conn.close()
        return

    video = videos[escolha - 1]
    vid_id, titulo_atual, duracao_atual, disc_atual, status_atual = video
    print(f"\nEditando '{titulo_atual}' (ID {vid_id})")
    novo_titulo = input("Novo título (enter para manter): ").strip()
    nova_dur = input("Nova duração em minutos (enter para manter): ").strip()
    nova_disc = input("Nova disciplina (enter para manter): ").strip()

    campos = []
    valores = []
    alterações = []
    dur_delta = 0
    dur_alterada = False
    if novo_titulo:
        campos.append("titulo = ?")
        valores.append(novo_titulo)
        alterações.append(("Título", titulo_atual, novo_titulo))
    if nova_dur:
        try:
            dur_int = int(nova_dur)
            campos.append("duracao_min = ?")
            valores.append(dur_int)
            alterações.append(("Duração (min)", duracao_atual, dur_int))
            dur_delta = dur_int - (duracao_atual or 0)
            dur_alterada = True
        except ValueError:
            print("Duração inválida. Mantida.")
    if nova_disc:
        campos.append("disciplina = ?")
        valores.append(nova_disc)
        alterações.append(("Disciplina", disc_atual, nova_disc))

    if not campos:
        print("Nada a atualizar.")
        conn.close()
        return

    # Mostrar mudanças e confirmar
    print("\nVocê está prestes a aplicar as seguintes alterações ao vídeo selecionado:")
    for campo, antes, depois in alterações:
        print(f"- {campo}: '{antes}' -> '{depois}'")
    confirmar = input("Confirmar alterações? (s/N): ").strip().lower()
    if confirmar != 's':
        print("Alterações canceladas.")
        conn.close()
        return

    valores.append(vid_id)
    cursor.execute(f"UPDATE videos SET {', '.join(campos)} WHERE id = ?", tuple(valores))
    conn.commit()
    conn.close()
    # Se o vídeo estava aprovado e a duração foi alterada, recalcule carga horária do autor
    if status_atual == 'Aprovado' and dur_alterada:
        nova_carga = atualizar_carga_horaria_por_videos(nome_autor)
        print(f"Vídeo atualizado e carga horária recalculada (nova carga: {nova_carga} minutos).")
    else:
        print("Vídeo atualizado com sucesso.")

def editar_perfil_curador(dados_curador):
    raise NotImplementedError

# --- LÓGICA DO CURADOR ---

def menu_curador(dados_curador):
    monitor_de = dados_curador['monitor_de']
    while True:
        print(f"\n=== PAINEL DO CURADOR: {dados_curador['nome']} ===")
        print(f"Responsável por: {monitor_de}")
        print("1. Avaliar Vídeos Pendentes")
        print("2. Editar Perfil")
        print("3. Sair (Logout)")
        
        op = input("Opção: ")
        
        if op == '1':
            avaliar_videos(monitor_de)
        elif op == '2':
            editar_perfil_curador(dados_curador)
        elif op == '3':
            break

def avaliar_videos(disciplina_alvo):
    conn = conectar('videos.db')
    cursor = conn.cursor()
    # Busca apenas pendentes da disciplina do curador
    cursor.execute("SELECT id, titulo, autor, duracao_min FROM videos WHERE disciplina = ? AND status = 'Pendente'", (disciplina_alvo,))
    pendentes = cursor.fetchall()
    conn.close()

    if not pendentes:
        print(f"\nNenhum vídeo pendente para a disciplina '{disciplina_alvo}'.")
        return

    print(f"\n--- AVALIAÇÃO ({len(pendentes)} encontrados) ---")
    for v in pendentes:
        vid_id, titulo, autor, duracao = v
        print(f"\nVídeo: {titulo}")
        print(f"Autor: {autor}")
        print(f"Duração: {duracao} min")
        print("1. APROVAR")
        print("2. REPROVAR")
        print("3. Pular")
        
        decisao = input("Decisão: ")
        
        if decisao == '1':
            processar_aprovacao(vid_id, autor, duracao)
        elif decisao == '2':
            processar_reprovacao(vid_id)
        else:
            print("Pulado.")

def processar_aprovacao(id_video, nome_autor, duracao):
    # 1. Atualizar status do vídeo
    conn_v = conectar('videos.db')
    cursor_v = conn_v.cursor()
    cursor_v.execute("UPDATE videos SET status = 'Aprovado' WHERE id = ?", (id_video,))
    conn_v.commit()
    conn_v.close()

    # 2. Recalcular carga horária do usuário como 3x somatório
    nova = atualizar_carga_horaria_por_videos(nome_autor)
    print(f"Vídeo APROVADO! {duracao * 3} minutos adicionados a {nome_autor}. Carga atual: {nova} minutos.")

def processar_reprovacao(id_video):
    conn = conectar('videos.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE videos SET status = 'Reprovado' WHERE id = ?", (id_video,))
    conn.commit()
    conn.close()
    print("Vídeo REPROVADO.")

# --- LÓGICA DO ADMIN ---

def menu_admin():
    while True:
        print("\n=== PAINEL ADMINISTRATIVO (MASTER) ===")
        print("1. Cadastrar Novo Curador")
        print("2. Listar Usuários")
        print("3. Apagar Cadastro")
        print("4. Sair")
        
        op = input("Opção: ")
        
        if op == '1':
            cadastrar_curador_admin()
        elif op == '2':
            # Listar usuários sem expor senhas (mostramos '******' ao Admin)
            conn = conectar('usuario.db')
            cursor = conn.cursor()
            # Exibir todos os campos conhecidos exceto a senha (senha mascarada)
            cursor.execute("SELECT id, nome, email, faculdade, numemro_de_matricula, verificacao, carga_horaria, categoria FROM usuario")
            usuarios_para_listagem = cursor.fetchall()
            print("\n--- USUÁRIOS ---")
            print(f"{'ID':<4} {'NOME':<20} {'EMAIL':<30} {'FACULDADE':<18} {'MATRÍCULA':<10} {'VERIFICADO':<11} {'SENHA':<8} {'CARGA'}")
            for registro_usuario in usuarios_para_listagem:
                print(f"{registro_usuario[0]:<4} {registro_usuario[1]:<20} {registro_usuario[2]:<30} {str(registro_usuario[3])[:18]:<18} {str(registro_usuario[4]):<10} {str(registro_usuario[5]):<11} {'******':<8} {registro_usuario[6]}")
            conn.close()
        elif op == '3':
            apagar_cadastro_admin()
        elif op == '4':
            break

def cadastrar_curador_admin():
    print("\n--- NOVO CURADOR ---")
    nome = input("Nome: ")
    email = input("Email: ")
    monitor_de = input("Monitor da Disciplina (ex: Python, Matematica): ")
    # Confirmação de senha (igual ao cadastro de usuário)
    while True:
        senha = input("Defina a Senha do Curador: ")
        conf = input("Confirme a Senha: ")
        if senha == conf:
            break
        print("Senhas não coincidem. Tente novamente.")
    hashed = generate_password_hash(senha)

    conn = conectar('curador.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO curador (nome, email, monitor_de, senha, categoria, verificacao)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (nome, email, monitor_de, hashed, "Curador", True))
    conn.commit()
    conn.close()
    print(f"Curador {nome} cadastrado para a disciplina {monitor_de}.")

def apagar_cadastro_admin():
    """
    Submenu administrativo para apagar registros:
    - Apagar Usuário
    - Apagar Curador
    """
    while True:
        print("\n--- APAGAR CADASTRO (ADMIN) ---")
        print("1. Apagar Usuário")
        print("2. Apagar Curador")
        print("3. Voltar")
        escolha = input("Escolha: ")
        if escolha == '1':
            apagar_usuario_admin()
        elif escolha == '2':
            apagar_curador_admin()
        elif escolha == '3':
            break
        else:
            print("Opção inválida. Tente novamente.")

def apagar_usuario_admin():
    """Lista usuários cadastrados com índices e permite apagar um com confirmação."""
    conn = conectar('usuario.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email FROM usuario")
    usuarios = cursor.fetchall()
    if not usuarios:
        print("\nNenhum usuário cadastrado.")
        conn.close()
        return

    print("\n--- USUÁRIOS CADASTRADOS ---")
    for idx, u in enumerate(usuarios, start=1):
        print(f"{idx}. ID:{u[0]} | {u[1]} | {u[2]}")

    try:
        escolha = int(input("\nQual deles você deseja apagar do Banco de Dados? (número, 0 para cancelar): "))
    except ValueError:
        print("Escolha inválida.")
        conn.close()
        return

    if escolha == 0:
        print("Operação cancelada.")
        conn.close()
        return

    if escolha < 1 or escolha > len(usuarios):
        print("Seleção inválida.")
        conn.close()
        return

    user_id, nome_sel, email_sel = usuarios[escolha - 1]
    confirmar = input(f"Tem certeza que deseja apagar o usuário '{nome_sel}' ({email_sel})? (s/N): ").strip().lower()
    if confirmar != 's':
        print("Operação cancelada.")
        conn.close()
        return

    try:
        cursor.execute("DELETE FROM usuario WHERE id = ?", (user_id,))
        conn.commit()
        print(f"Usuário '{nome_sel}' apagado com sucesso.")
    except Exception as e:
        print("Erro ao apagar usuário:", e)
    finally:
        conn.close()

def apagar_curador_admin():
    """Lista curadores cadastrados com índices e permite apagar um com confirmação."""
    conn = conectar('curador.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, monitor_de FROM curador")
    curadores = cursor.fetchall()
    if not curadores:
        print("\nNenhum curador cadastrado.")
        conn.close()
        return

    print("\n--- CURADORES CADASTRADOS ---")
    for idx, c in enumerate(curadores, start=1):
        print(f"{idx}. ID:{c[0]} | {c[1]} | {c[2]} | Monitor de: {c[3]}")

    try:
        escolha = int(input("\nQual deles você deseja apagar do Banco de Dados? (número, 0 para cancelar): "))
    except ValueError:
        print("Escolha inválida.")
        conn.close()
        return

    if escolha == 0:
        print("Operação cancelada.")
        conn.close()
        return

    if escolha < 1 or escolha > len(curadores):
        print("Seleção inválida.")
        conn.close()
        return

    cur_id, nome_sel, email_sel, monitor_sel = curadores[escolha - 1]
    confirmar = input(f"Tem certeza que deseja apagar o curador '{nome_sel}' ({email_sel})? (s/N): ").strip().lower()
    if confirmar != 's':
        print("Operação cancelada.")
        conn.close()
        return

    try:
        cursor.execute("DELETE FROM curador WHERE id = ?", (cur_id,))
        conn.commit()
        print(f"Curador '{nome_sel}' apagado com sucesso.")
    except Exception as e:
        print("Erro ao apagar curador:", e)
    finally:
        conn.close()

# --- FLUXO PRINCIPAL ---

def main():
    criar_tabelas()
    
    while True:
        print("\nBEM-VINDO AO SAPIENTI")
        print("1. Entrar (Login)")
        print("2. Cadastrar-se (Estudante)")
        print("3. Encerrar")
        
        escolha = input("Escolha: ")
        
        if escolha == '1':
            tipo_user, dados = login_sistema()
            
            if tipo_user == "admin":
                menu_admin()
            elif tipo_user == "curador":
                menu_curador(dados)
            elif tipo_user == "usuario":
                menu_aluno(dados)
                
        elif escolha == '2':
            realizar_cadastro_usuario()
        elif escolha == '3':
            print("Até logo!")
            break

if __name__ == "__main__":
    main()