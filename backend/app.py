from flask import Flask
from flask_cors import CORS

from backend.routes import environment, navigation, predictions


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    app.register_blueprint(environment.bp)
    app.register_blueprint(navigation.bp)
    app.register_blueprint(predictions.bp)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "polarnav-backend",
        }

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
