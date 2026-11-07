"""Asistente de Distribuidora Río Claro: web app (Flask) que consume un agente de Microsoft Foundry."""
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

PROJECT_ENDPOINT = os.environ.get("PROJECT_ENDPOINT", "")
AGENT_NAME = os.environ.get("AGENT_NAME", "")
AGENT_VERSION = os.environ.get("AGENT_VERSION", "1")

app = Flask(__name__)

# Misma idea que en clase: el cliente del proyecto se autentica con DefaultAzureCredential
# (az login en tu computadora; identidad administrada / Entra ID cuando está en App Service).
_project_client = None
_openai_client = None


def get_openai_client():
    global _project_client, _openai_client
    if _openai_client is None:
        _project_client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=DefaultAzureCredential(),
        )
        _openai_client = _project_client.get_openai_client()
    return _openai_client


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    previous_id = data.get("previous_response_id")

    if not message:
        return jsonify({"error": "Escribe un mensaje antes de enviar."}), 400
    if not PROJECT_ENDPOINT or not AGENT_NAME:
        return jsonify({"error": "Falta configurar PROJECT_ENDPOINT y AGENT_NAME en el servidor."}), 500

    try:
        client = get_openai_client()
        kwargs = {
            "input": [{"role": "user", "content": message}],
            "extra_body": {
                "agent_reference": {
                    "name": AGENT_NAME,
                    "version": AGENT_VERSION,
                    "type": "agent_reference",
                }
            },
        }
        if previous_id:
            kwargs["previous_response_id"] = previous_id  # mantiene el hilo de la conversación
        response = client.responses.create(**kwargs)
        return jsonify({"reply": response.output_text, "response_id": response.id})
    except Exception as exc:  # noqa: BLE001
        app.logger.exception("Error al consultar el agente")
        return jsonify({"error": f"No se pudo consultar al asistente: {exc}"}), 502


if __name__ == "__main__":
    app.run(debug=True, port=5000)
