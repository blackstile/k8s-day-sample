import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class HallucinationValidatorTool:
    @staticmethod
    def validate(original_prompt: str, response_text: str) -> bool:
        """
        Compara a resposta com a pergunta para detectar alucinações. Retorna 'true' se for uma alucinação.
        Args:
            original_prompt: A pergunta feita pelo usuário.
            response_text: A resposta gerada pela IA.
        """
        logger.info("ADK Tool: Executando ferramenta de validação de alucinação.")
        
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        generation_config = genai.types.GenerationConfig(response_mime_type="application/json")
        prompt = f"""
        Você é um agente de verificação de fatos. Analise o par abaixo. Uma 'alucinação' ocorre se a resposta for inventada, incoerente ou não responder à pergunta original.
        PERGUNTA ORIGINAL: "{original_prompt}"
        RESPOSTA GERADA: "{response_text}"
        A resposta gerada é uma alucinação? Responda APENAS com um objeto JSON válido contendo uma única chave "is_hallucination" e o valor booleano correspondente.
        """
        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            is_hallucination = json.loads(response.text).get("is_hallucination", False)
            return is_hallucination
        except Exception as e:
            logger.error(f"Erro na ferramenta de validação de alucinação: {e}. Bloqueando por segurança.")
            return True
