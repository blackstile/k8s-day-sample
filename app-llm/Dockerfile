FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação
COPY . .

# Expõe a porta que a aplicação usa
EXPOSE 5000

# Comando para rodar a aplicação quando o contêiner iniciar
CMD ["python", "app.py"]
