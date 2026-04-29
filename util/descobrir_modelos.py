import os
from dotenv import load_dotenv
import google.generativeai as genai
from anthropic import Anthropic

# Carregar as chaves
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print("🔍 A INQUIRIR A API DO GOOGLE (GEMINI)...")
try:
    genai.configure(api_key=GEMINI_API_KEY)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"   ✅ Modelo válido encontrado: {m.name}")
except Exception as e:
    print(f"Erro no Gemini: {e}")

print("\n=========================================\n")

print("🔍 DICA PARA A API DA ANTHROPIC (CLAUDE)...")
print("A Anthropic não tem um método simples de listar modelos via código Python da mesma forma.")
print("No entanto, os nomes clássicos e mais estáveis que costumam funcionar são:")
print("   👉 'claude-3-sonnet-20240229' (Muito estável e excelente para código)")
print("   👉 'claude-3-haiku-20240307' (Mais rápido e barato)")
print("   👉 'claude-3-opus-20240229' (O mais potente, mas mais caro)")