import javalang
import pandas as pd
import re

def tentar_fazer_parse(codigo_limpo):
    """
    Tenta empacotar o código em diferentes níveis (Classe, Método ou Statements)
    até o javalang conseguir montar a árvore (AST).
    """
    # 1. Tenta fazer o parse como está (caso já seja uma classe completa gerada pelo LLM)
    try:
        return javalang.parse.parse(codigo_limpo)
    except Exception:
        pass

    # 2. Separa os imports do resto do código.
    # Colocar 'import' dentro de uma classe ou método quebra o parser do Java.
    linhas = codigo_limpo.split('\n')
    imports = []
    corpo = []
    for linha in linhas:
        if linha.strip().startswith("import ") or linha.strip().startswith("package "):
            imports.append(linha)
        else:
            corpo.append(linha)
            
    str_imports = "\n".join(imports)
    str_corpo = "\n".join(corpo)

    # 3. TENTATIVA 2: O snippet é um método solto? 
    # Envelopa apenas com uma Classe Dummy.
    codigo_classe = f"{str_imports}\npublic class DummyClass {{\n{str_corpo}\n}}"
    try:
        return javalang.parse.parse(codigo_classe)
    except Exception:
        pass

    # 4. TENTATIVA 3: O snippet é apenas uma lógica solta (Statements)?
    # Envelopa com uma Classe e um Método Dummy.
    codigo_metodo = f"{str_imports}\npublic class DummyClass {{\n public void dummyMethod() throws Exception {{\n{str_corpo}\n}}\n}}"
    try:
        return javalang.parse.parse(codigo_metodo)
    except Exception:
        pass

    # 5. TENTATIVA 4 (Salva-vidas): O LLM cortou o código antes de fechar as chaves?
    # Tenta adicionar chaves fechando no final para compensar cortes bruscos.
    codigo_chaves = codigo_metodo + "\n}\n}\n}"
    try:
        return javalang.parse.parse(codigo_chaves)
    except Exception:
        return None # Desiste, a sintaxe está realmente destruída

def extrair_caminhos_ast(codigo_java):
    """
    Extrai as assinaturas sintáticas do código, limpando sujeiras de LLMs.
    """
    codigo_str = str(codigo_java)
    
    # 1. Limpeza agressiva de artefatos de LLMs (Markdown, colchetes, etc)
    codigo_limpo = codigo_str.replace("【", "").replace("】", "")
    codigo_limpo = re.sub(r"^```java|```$", "", codigo_limpo, flags=re.MULTILINE).strip()
    
    # 2. Busca a árvore sintática usando as tentativas progressivas
    arvore = tentar_fazer_parse(codigo_limpo)
    
    if arvore is None:
        return "ERRO_SINTAXE"

    # 3. Extração das features
    features_extraidas = []
    for caminho, no in arvore:
        # Pega a estrutura do Try e se tem Finally ou é Try-with-resources
        if isinstance(no, javalang.tree.TryStatement):
            features_extraidas.append("TryStatement")
            if no.resources and len(no.resources) > 0:
                features_extraidas.append("HasResources_ImplicitClose")
            if getattr(no, 'finally_block', None):
                features_extraidas.append("HasFinallyBlock")
                
        # Pega as chamadas de método (foco em MEMORY LEAKS e Resource Leaks)
        elif isinstance(no, javalang.tree.MethodInvocation):
            if no.member == "close":
                features_extraidas.append("MethodCall_close") # Arquivos, Streams, Sockets
            elif no.member == "disconnect":
                features_extraidas.append("MethodCall_disconnect") # Conexões HTTP/Banco
            elif no.member == "release":
                features_extraidas.append("MethodCall_release") # WakeLocks, MediaPlayers, Camera (CRÍTICO ANDROID)
            elif no.member == "recycle":
                features_extraidas.append("MethodCall_recycle") # Bitmaps, TypedArrays (CRÍTICO ANDROID)
            elif no.member == "free":
                features_extraidas.append("MethodCall_free") # Cursores nativos, Memória C
            elif no.member == "destroy":
                features_extraidas.append("MethodCall_destroy") # WebViews, Threads
            else:
                features_extraidas.append("MethodCall_Other")
                
        # Pega os blocos Catch
        elif isinstance(no, javalang.tree.CatchClause):
            features_extraidas.append("CatchClause")
            
    # Se não extraiu nada (código em branco ou não bateu com as regras), retorna um indicativo
    if not features_extraidas:
        return "SEM_FEATURES_RELEVANTES"
        
    return " ".join(features_extraidas)

def gerar_dataset_ast_do_csv(caminho_csv_entrada, caminho_csv_saida, coluna_id, coluna_codigo, coluna_label):
    print(f"📄 Lendo os snippets do arquivo: {caminho_csv_entrada}")
    
    # Bloco de leitura blindado contra erros de formatação (ParserError)
    try:
        df = pd.read_csv(caminho_csv_entrada)
    except pd.errors.ParserError:
        try:
            df = pd.read_csv(caminho_csv_entrada, sep=';')
        except Exception:
            print("⚠️ Formatação irregular detectada. Usando motor Python de leitura...")
            df = pd.read_csv(caminho_csv_entrada, sep=None, engine='python', on_bad_lines='skip')
    except UnicodeDecodeError:
        df = pd.read_csv(caminho_csv_entrada, encoding='latin1', sep=';')

    print(f"📊 Total de registros lidos do CSV: {len(df)}")
    
    # Verifica se as colunas informadas realmente existem no CSV lido, incluindo a coluna de ID
    if coluna_id not in df.columns or coluna_codigo not in df.columns or coluna_label not in df.columns:
        print(f"❌ ERRO CRÍTICO: As colunas '{coluna_id}', '{coluna_codigo}' ou '{coluna_label}' não foram encontradas!")
        print(f"Colunas disponíveis no arquivo: {list(df.columns)}")
        return

    print("🌲 Extraindo as Árvores de Sintaxe Abstrata (AST)... Isso pode levar alguns segundos.")

    # Aplica a função de extração garantindo que o valor é uma string
    df['AST_Features'] = df[coluna_codigo].astype(str).apply(extrair_caminhos_ast)
    
    # Conta quantos deram erro de sintaxe
    erros = len(df[df['AST_Features'] == "ERRO_SINTAXE"])
    print(f"⚠️ Snippets ignorados por erro de sintaxe intransponível: {erros}")
    
    # Removemos as linhas com erro
    df = df[df['AST_Features'] != "ERRO_SINTAXE"]
    
    # Filtramos para salvar mantendo a coluna de ID intacta
    df_final = df[[coluna_id, 'AST_Features', coluna_label]].copy()
    
    # Salva o novo CSV completo
    df_final.to_csv(caminho_csv_saida, index=False)
    
    print(f"\n✅ Extração concluída com sucesso!")
    print(f"💾 Novo dataset estrutural ({len(df_final)} linhas válidas) salvo em: {caminho_csv_saida}")

# =====================================================================
# CONFIGURAÇÃO DOS ARQUIVOS
# =====================================================================
if __name__ == "__main__":
    # Caminho do seu CSV completo com 2014 exemplos
    ARQUIVO_ENTRADA = "C:/Dissertacao/data_bases/dataset_sintetico_chatgpt.csv" 
    
    # Onde o novo arquivo pronto para o modelo AST será salvo
    ARQUIVO_SAIDA = "C:/Dissertacao/data_bases/ast/dataset_ast_completo.csv"
    
    # ATENÇÃO: Nomes exatos das colunas no seu arquivo
    COLUNA_ID = 'ID_Caso' # Adicionado o mapeamento do ID
    COLUNA_CODIGO = 'Codigo_Snippet' 
    COLUNA_LABEL = 'Tem_Fuga_de_Recurso'
    
    gerar_dataset_ast_do_csv(ARQUIVO_ENTRADA, ARQUIVO_SAIDA, COLUNA_ID, COLUNA_CODIGO, COLUNA_LABEL)