import logging
import time
from flask import Flask, render_template
from flask_socketio import SocketIO
from q_bot.risk.rules import RiskManager
from q_bot.execution.mt5_broker import MT5Broker

log = logging.getLogger('Q.bot.WebServer')

class WebServer:
    """
    Handles the web server and real-time dashboard via WebSockets.
    """
    def __init__(self, risk_manager: RiskManager, broker: MT5Broker, symbol: str):
        self.risk_manager = risk_manager
        self.broker = broker
        self.symbol = symbol
        self._running = False

        self.app = Flask(__name__, template_folder='templates')
        self.socketio = SocketIO(self.app, async_mode='threading')

        self._setup_routes()
        self._setup_socketio_events()

    def _setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('index.html')

    def _setup_socketio_events(self):
        @self.socketio.on('connect')
        def handle_connect():
            log.info("Web client connected")

    def _status_emitter_loop(self):
        """
        Periodically gets stats and emits them to the client.
        """
        self._running = True
        while self._running:
            try:
                stats = self.risk_manager.get_stats()
                stats['open_trades'] = len(self.broker.get_open_positions())
                stats['symbol'] = self.symbol
                stats['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')

                self.socketio.emit('status_update', stats)
                self.socketio.sleep(1)
            except Exception as e:
                log.error(f"Error in status emitter loop: {e}")
                self.socketio.sleep(5)

    def run(self, host='127.0.0.1', port=5000):
        """
        Runs the web server, which will be the target of a daemon thread.
        """
        # Start the emitter loop as a background task managed by SocketIO
        self.socketio.start_background_task(self._status_emitter_loop)

        log.info(f"Starting web server on http://{host}:{port}")
        self.socketio.run(self.app, host=host, port=port, allow_unsafe_werkzeug=True)

    def stop(self):
        """
        Signals the emitter loop to stop.
        The web server itself will be stopped when the main app exits.
        """
        log.info("Signaling web server emitter to stop.")
        self._running = False
