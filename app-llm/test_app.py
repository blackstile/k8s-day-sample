# app-llm/test_app.py
import unittest
from unittest.mock import patch, MagicMock
import json
import sys
import os

# Adiciona o diretório raiz ao path para encontrar o módulo 'app'
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import is_content_inappropriate

# Classe auxiliar para simular o objeto de resposta da API
class MockResponse:
    def __init__(self, text):
        self.text = text

class TestModerator(unittest.TestCase):

    @patch('app.model.generate_content')
    def test_content_is_appropriate(self, mock_generate_content):
        """
        Testa se um conteúdo considerado apropriado pela API 
        retorna 'False' (não é inapropriado).
        """
        # Simula a resposta da API para um conteúdo apropriado
        mock_response_text = json.dumps({"inapropriado": False})
        mock_generate_content.return_value = MockResponse(text=mock_response_text)
        
        # Executa a função
        result = is_content_inappropriate("Olá, bom dia!")
        
        # Verifica se o resultado é o esperado
        self.assertFalse(result, "Deveria retornar False para conteúdo apropriado.")
        mock_generate_content.assert_called_once()

    @patch('app.model.generate_content')
    def test_content_is_inappropriate(self, mock_generate_content):
        """
        Testa se um conteúdo considerado inapropriado pela API 
        retorna 'True'.
        """
        # Simula a resposta da API para um conteúdo inapropriado
        mock_response_text = json.dumps({"inapropriado": True})
        mock_generate_content.return_value = MockResponse(text=mock_response_text)
        
        result = is_content_inappropriate("O que significa seu merda")
        
        self.assertTrue(result, "Deveria retornar True para conteúdo inapropriado.")
        mock_generate_content.assert_called_once()

    @patch('app.model.generate_content')
    def test_moderation_service_fails(self, mock_generate_content):
        """
        Testa o comportamento de fail-safe: se a API falhar, deve retornar 'True' 
        (bloqueia por segurança).
        """
        # Simula uma falha na chamada da API
        mock_generate_content.side_effect = Exception("Falha na comunicação com a API")
        
        result = is_content_inappropriate("Qualquer texto.")
        
        self.assertTrue(result, "Deveria retornar True quando a API falha.")
        mock_generate_content.assert_called_once()

    @patch('app.model.generate_content')
    def test_moderation_service_returns_invalid_json(self, mock_generate_content):
        """
        Testa o comportamento de fail-safe: se a API retornar um JSON inválido,
        deve retornar 'True'.
        """
        # Simula uma resposta da API que não é um JSON válido
        mock_generate_content.return_value = MockResponse(text="RESPOSTA_INVALIDA")
        
        result = is_content_inappropriate("Texto para teste de JSON inválido.")
        
        self.assertTrue(result, "Deveria retornar True para uma resposta JSON inválida.")
        mock_generate_content.assert_called_once()

if __name__ == '__main__':
    unittest.main()
