# Development servers — each app must run from its module directory
default:
    @just --list

web:
    cd web && uv run flask --app web.app:app --debug run --host 0.0.0.0 --port 8082

receiver:
    cd receiver && uv run flask --app receiver.app:app --debug run --host 0.0.0.0 --port 9001

crawler:
    @echo "Starting crawler on port 9009"
    cd crawler && uv run flask --app "crawler/app.py:create_app()" --debug run --host 0.0.0.0 --port 9009
