"""Application entry point"""
from app import create_app 
from config import config 

app = create_app(config)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=config.API_PORT, debug=config.DEBUG_MODE)
