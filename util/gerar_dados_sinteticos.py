import pandas as pd
from google import genai
from google.genai import types
import json
import time
import os

# 1. Configurar o Cliente do Google Gemini
CHAVE_API = "AIzaSyCiWQs5sGsfWvNUPGtVjCplEjoI1hPXFT4"
client = genai.Client(api_key=CHAVE_API)

def gerar_sinteticos_com_gemini(codigo_bug, codigo_fix, classe_recurso):
    """Envia o prompt para o Gemini com sistema de Retry (Tentativas)"""
    
    prompt = f"""
    Atue como um Engenheiro de Software Android Especialista. Estou a construir um dataset para treinar um modelo de Machine Learning focado em detetar falhas de 'Resource Leaks' no ecossistema Android, especificamente envolvendo a classe: {classe_recurso}.
    
    Aqui está um exemplo real de um código com fuga de recurso (Buggy) e a sua respetiva correção (Fix):
    
    BUG:
    {codigo_bug}
    
    FIX:
    {codigo_fix}
    
    A sua tarefa:
    Gere 3 novos exemplos sintéticos baseados neste exato mesmo tipo de falha, aplicados em contextos de aplicações Android diferentes (ex: app de música, scanner, fitness, etc).
    
    ATENÇÃO: Retorne a resposta ESTRITAMENTE num formato JSON válido, como um array de objetos. 
    COMO O JSON VAI CONTER CÓDIGO JAVA, ESCAPE CORRETAMENTE TODAS AS QUEBRAS DE LINHA (usando \\n) E ASPAS para manter o JSON válido.
    
    Formato exigido:
    [
      {{
        "contexto": "App de Musica",
        "buggy_code": "codigo java do bug aqui",
        "fix_code": "codigo java corrigido aqui"
      }}
    ]
    """
    
    # SISTEMA DE AUTO-RETRY (Tenta 3 vezes se a internet falhar)
    max_tentativas = 3
    for tentativa in range(max_tentativas):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            return json.loads(response.text.strip())
            
        except Exception as e:
            print(f"    ⚠️ Falha na tentativa {tentativa + 1} de {max_tentativas}: {e}")
            if tentativa < max_tentativas - 1:
                print("    ⏳ A aguardar 10 segundos antes de tentar novamente...")
                time.sleep(10)
            else:
                print("    ❌ Erro definitivo neste caso. Vamos saltar para não parar o script.")
                return []

def main():
    print("🚀 A iniciar o Aumento de Dados (MODO BLINDADO)...\n")
    
    ARQUIVO_SAIDA = './data_bases/dataset_sintetico_completo.csv'
    
    # 1. Carregar os dados originais
    df = pd.read_csv('./data_bases/dataset_balanceado.csv', sep=';')
    
    casos_ja_processados = set()
    novos_dados_sinteticos = []
    
    # 2. AUTO-RESUME: Verificar se já temos progresso guardado
    if os.path.exists(ARQUIVO_SAIDA):
        print("📂 Ficheiro anterior encontrado! A retomar de onde paramos...")
        df_existente = pd.read_csv(ARQUIVO_SAIDA, sep=';')
        novos_dados_sinteticos = df_existente.to_dict('records')
        
        for idx, row in df_existente.iterrows():
            id_base = str(row['ID_Caso']).split('_SINTETICO')[0]
            casos_ja_processados.add(id_base)
            
        print(f"✅ Já temos {len(casos_ja_processados)} casos processados e guardados.\n")

    # 3. Agrupar os pares de BUG e FIX
    casos_reais = {}
    for index, row in df.iterrows():
        id_base = str(row['ID_Caso']).replace('_BUG', '').replace('_FIX', '')
        
        if id_base not in casos_reais:
            casos_reais[id_base] = {'recurso': row['Classe_Recurso']}
            
        if '_BUG' in str(row['ID_Caso']):
            casos_reais[id_base]['bug'] = row['Codigo_Snippet']
        elif '_FIX' in str(row['ID_Caso']):
            casos_reais[id_base]['fix'] = row['Codigo_Snippet']

    # 4. Processar todos os casos que faltam
    for id_base, dados in casos_reais.items():
        # Se já foi processado antes, salta logo!
        if id_base in casos_ja_processados:
            continue
            
        if 'bug' in dados and 'fix' in dados:
            print(f"A gerar sintéticos para o caso: {id_base}...")
            
            sinteticos = gerar_sinteticos_com_gemini(
                codigo_bug=dados['bug'], 
                codigo_fix=dados['fix'],
                classe_recurso=dados['recurso']
            )
            
            if not sinteticos:
                continue # Se falhou as 3 vezes, salta este caso
                
            for i, sint in enumerate(sinteticos):
                id_sintetico_base = f"{id_base}_SINTETICO_{i+1}"
                
                novos_dados_sinteticos.append({
                    "ID_Caso": f"{id_sintetico_base}_BUG",
                    "Aplicacao": sint.get('contexto', 'Sintetico'),
                    "Classe_Recurso": dados['recurso'],
                    "Codigo_Snippet": sint.get('buggy_code', ''),
                    "Tem_Fuga_de_Recurso": 1
                })
                
                novos_dados_sinteticos.append({
                    "ID_Caso": f"{id_sintetico_base}_FIX",
                    "Aplicacao": sint.get('contexto', 'Sintetico'),
                    "Classe_Recurso": dados['recurso'],
                    "Codigo_Snippet": sint.get('fix_code', ''),
                    "Tem_Fuga_de_Recurso": 0
                })
                
            # AUTO-SAVE: Grava o ficheiro imediatamente a cada caso terminado!
            df_sintetico = pd.DataFrame(novos_dados_sinteticos)
            df_sintetico.to_csv(ARQUIVO_SAIDA, index=False, sep=';', encoding='utf-8-sig')
            
           # Pausa de 15 segundos para evitar limites da API
            time.sleep(15)

    print("\n🎉 Processo totalmente concluído!")
    print(f"📁 Dataset final guardado em: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()