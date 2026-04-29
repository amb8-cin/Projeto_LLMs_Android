import pandas as pd
from sklearn.model_selection import train_test_split
import os

def dividir_dataset_ast(caminho_entrada, caminho_treino, caminho_teste, caminho_holdout_bugs, tamanho_teste=0.3, coluna_label='Tem_Fuga_de_Recurso'):
    """
    Lê o dataset completo e o divide em conjuntos de Treino e Teste de forma estratificada.
    Adicionalmente, gera um arquivo contendo APENAS os bugs do conjunto de teste para as LLMs.
    """
    print(f"📄 Lendo o dataset extraído: {caminho_entrada}")
    
    if not os.path.exists(caminho_entrada):
        print(f"❌ ERRO: Arquivo não encontrado em {caminho_entrada}")
        return

    df = pd.read_csv(caminho_entrada)
    total_linhas = len(df)
    print(f"📊 Total de registros encontrados: {total_linhas}")

    # Faz a divisão estratificada (stratify=df[coluna_label] garante o balanceamento)
    # random_state=42 garante que se você rodar o script 10 vezes, a divisão será a mesma (reprodutibilidade)
    df_treino, df_teste = train_test_split(
        df, 
        test_size=tamanho_teste, 
        random_state=42, 
        stratify=df[coluna_label]
    )

    # ==========================================
    # NOVO: Filtrando apenas os BUGS do Teste
    # ==========================================
    df_holdout_bugs = df_teste[df_teste[coluna_label] == 1].copy()

    # Salvando os novos arquivos
    df_treino.to_csv(caminho_treino, index=False)
    df_teste.to_csv(caminho_teste, index=False)
    df_holdout_bugs.to_csv(caminho_holdout_bugs, index=False)

    # ==========================================
    # EXIBINDO AS ESTATÍSTICAS PARA A DISSERTAÇÃO
    # ==========================================
    print("\n✅ Separação concluída com sucesso!")
    print("=" * 50)
    print(f"📈 CONJUNTO DE TREINO ({(1-tamanho_teste)*100:.0f}%):")
    print(f"   -> Total de linhas: {len(df_treino)}")
    print(f"   -> Códigos com Bug (1): {len(df_treino[df_treino[coluna_label] == 1])}")
    print(f"   -> Códigos Corrigidos (0): {len(df_treino[df_treino[coluna_label] == 0])}")
    print(f"   -> Salvo em: {caminho_treino}")
    
    print("-" * 50)
    print(f"📉 CONJUNTO DE TESTE ({tamanho_teste*100:.0f}%):")
    print(f"   -> Total de linhas: {len(df_teste)}")
    print(f"   -> Códigos com Bug (1): {len(df_teste[df_teste[coluna_label] == 1])}")
    print(f"   -> Códigos Corrigidos (0): {len(df_teste[df_teste[coluna_label] == 0])}")
    print(f"   -> Salvo em: {caminho_teste}")

    print("-" * 50)
    print(f"🎯 HOLDOUT EXCLUSIVO PARA O TORNEIO DAS LLMs:")
    print(f"   -> Total de linhas: {len(df_holdout_bugs)} (Somente os Bugs!)")
    print(f"   -> Salvo em: {caminho_holdout_bugs}")
    print("=" * 50)

# =====================================================================
# CONFIGURAÇÃO DOS ARQUIVOS
# =====================================================================
if __name__ == "__main__":
    # O arquivo que acabamos de gerar na etapa anterior
    ARQUIVO_COMPLETO = "C:/Dissertacao/data_bases/ast/dataset_ast_completo.csv" 
    
    # Onde os arquivos divididos serão salvos
    ARQUIVO_TREINO = "C:/Dissertacao/data_bases/ast/dataset_ast_treino.csv"
    ARQUIVO_TESTE = "C:/Dissertacao/data_bases/ast/dataset_ast_teste.csv"
    
    # NOVO ARQUIVO: Apenas os bugs do teste para você cruzar com as respostas das IAs
    ARQUIVO_HOLDOUT_BUGS = "C:/Dissertacao/data_bases/ast/holdout_290_ast.csv"
    
    # Aqui você escolhe a proporção. 
    PROPORCAO_TESTE = 0.30 
    
    dividir_dataset_ast(ARQUIVO_COMPLETO, ARQUIVO_TREINO, ARQUIVO_TESTE, ARQUIVO_HOLDOUT_BUGS, PROPORCAO_TESTE)