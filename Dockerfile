# Imagen base para correr el framework CivicMesh (peers, publicadores).
# No requiere CUDA: en el clúster DIINF, los nodos GPU solo usan la CPU
# del host (Sección 5 del enunciado).
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Por defecto abre una shell; docker-compose.yml sobreescribe el comando
# por servicio (peer, publicador).
CMD ["bash"]
