import json
import hashlib
import time
import threading
import websocket

class Dot2WebSocketHandler:
    def __init__(self,
                 host="10.0.0.50",
                 username="remote",
                 password="1",
                 heartbeat_step=10,
                 debug=True,

                 bwing_start_index=[300, 400, 500, 600, 700, 800],
                 bwing_items_count=[16, 16, 16, 16, 16, 16],
                 bwing_items_type=[3, 3, 3, 3, 3, 3],
                 bwing_view=3,
                 bwing_exec_view_mode=2,

                 fwing_start_index=[0, 100, 200],
                 fwing_items_count=[22, 22, 22],
                 fwing_items_type=[2, 3, 3],
                 fwing_view=3,
                 fwing_exec_view_mode=2,
                 ):
        self.HOST = host
        self.URL = f"ws://{self.HOST}/?ma=1"
        self.ORIGIN = f"http://{self.HOST}"
        self.USERNAME = username
        self.PLAINTEXT_PASSWORD = password
        self.PASSWORD_MD5 = hashlib.md5(self.PLAINTEXT_PASSWORD.encode("utf-8")).hexdigest()
        self.HEARTBEAT_STEP = heartbeat_step
        self.DEBUG = debug

        self.session_id = None
        self.logged_in = False
        self.stop_heartbeat = False
        self.ws = None
        self._ws_thread = None
        self._heartbeat_thread = None

        # Callback registry: { "requestType": [callable, ...] }
        self._callbacks = {}
        # One-shot callbacks waiting for next matching message
        self._one_shot_callbacks = {}
        self._callbacks_lock = threading.Lock()

        self.BWING_START_INDEX = bwing_start_index
        self.BWING_ITEMS_COUNT = bwing_items_count
        self.BWING_ITEMS_TYPE = bwing_items_type
        self.BWING_VIEW = bwing_view
        self.BWING_EXEC_VIEW_MODE = bwing_exec_view_mode

        self.FWING_START_INDEX = fwing_start_index
        self.FWING_ITEMS_COUNT = fwing_items_count
        self.FWING_ITEMS_TYPE = fwing_items_type
        self.FWING_VIEW = fwing_view
        self.FWING_EXEC_VIEW_MODE = fwing_exec_view_mode

    ###################################################
    #                    Callbacks                    #
    ###################################################

    def on(self, request_type, callback):
        """
        Register a persistent callback for a given requestType (or any key in the response).
        The callback receives the full parsed message dict.

        Example:
            dot2_ws.on("playbacks", handle_playbacks)
        """
        with self._callbacks_lock:
            if request_type not in self._callbacks:
                self._callbacks[request_type] = []
            self._callbacks[request_type].append(callback)

    def off(self, request_type, callback=None):
        """
        Remove a persistent callback.
        If callback is None, removes all callbacks for that request_type.
        """
        with self._callbacks_lock:
            if request_type not in self._callbacks:
                return
            if callback is None:
                del self._callbacks[request_type]
            else:
                self._callbacks[request_type] = [
                    cb for cb in self._callbacks[request_type] if cb != callback
                ]

    def once(self, request_type, callback):
        """
        Register a one-shot callback that fires only on the next matching message then removes itself.

        Example:
            dot2_ws.once("playbacks", handle_single_playback_response)
        """
        with self._callbacks_lock:
            if request_type not in self._one_shot_callbacks:
                self._one_shot_callbacks[request_type] = []
            self._one_shot_callbacks[request_type].append(callback)

    def _dispatch(self, data):
        # Build the set of keys to match against
        keys_to_check = set(data.keys())

        # Also add the value of responseType as a matchable key
        if "responseType" in data:
            keys_to_check.add(data["responseType"])

        with self._callbacks_lock:
            persistent = {k: list(v) for k, v in self._callbacks.items()}
            one_shot = {k: list(v) for k, v in self._one_shot_callbacks.items()}
            for key in one_shot:
                if key in keys_to_check:
                    self._one_shot_callbacks.pop(key, None)

        for key, callbacks in persistent.items():
            if key in keys_to_check:
                for cb in callbacks:
                    try:
                        cb(data)
                    except Exception as e:
                        if self.DEBUG:
                            print(f"Callback error [{key}]: {e}")

        for key, callbacks in one_shot.items():
            if key in keys_to_check:
                for cb in callbacks:
                    try:
                        cb(data)
                    except Exception as e:
                        if self.DEBUG:
                            print(f"One-shot callback error [{key}]: {e}")

    ###################################################
    #                   WS Internals                  #
    ###################################################

    def _send(self, obj):
        if self.ws:
            self.ws.send(json.dumps(obj, separators=(",", ":")))

    def _on_open(self, ws):
        if self.DEBUG:
            print("WS open")

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
        except Exception:
            if self.DEBUG:
                print("<< (non-JSON)", msg[:120])
            return

        if self.DEBUG:
            print("<<", data)

        # Internal handshake handling
        if data.get("status") == "server ready":
            self._send({"session": 0})
            return

        if "session" in data and self.session_id is None:
            self.session_id = data["session"]
            if self.DEBUG:
                print("Assigned session:", self.session_id)
            if data.get("forceLogin", True):
                self._send({
                    "requestType": "login",
                    "username": self.USERNAME,
                    "password": self.PASSWORD_MD5,
                    "session": self.session_id,
                    "maxRequests": 10
                })
            else:
                self.logged_in = True
            return

        if data.get("responseType") == "login":
            if data.get("result") is True:
                if self.DEBUG:
                    print("Login OK")
                self.logged_in = True
            else:
                if self.DEBUG:
                    print("Login FAILED")
            return

        # Dispatch to user callbacks
        self._dispatch(data)

    def _on_error(self, ws, err):
        if self.DEBUG:
            print("ERR", err)

    def _on_close(self, ws, code, reason):
        if self.DEBUG:
            print("CLOSE", code, reason)

    ###################################################
    #                   Public API                    #
    ###################################################

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.URL,
            header=[f"Origin: {self.ORIGIN}"],
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self._ws_thread = threading.Thread(
            target=lambda: self.ws.run_forever(skip_utf8_validation=True),
            daemon=True
        )
        self._ws_thread.start()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat(self):
        while not self.stop_heartbeat:
            time.sleep(self.HEARTBEAT_STEP)
            if self.session_id is not None:
                self._send({"session": self.session_id})

    def disconnect(self):
        self.stop_heartbeat = True
        if self.ws:
            self.ws.close()

    def send_playback_click(self, executor_index, page_index=0, button_id=0, ptype=0, pressed=True):
        if not self.logged_in or self.session_id is None:
            if self.DEBUG:
                print("Not ready; cannot send userInput yet.")
            return

        payload = {
            "requestType": "playbacks_userInput",
            "cmdline": "",
            "execIndex": int(executor_index),
            "pageIndex": page_index,
            "buttonId": button_id,
            "pressed": pressed,
            "released": not pressed,
            "type": ptype,
            "session": self.session_id,
            "maxRequests": 0
        }
        self._send(payload)

    def send_playback_fader(self, fader_index, fader_value, page_index=1, type=1):
        if not self.logged_in or self.session_id is None:
            if self.DEBUG:
                print("Not ready; cannot send userInput yet.")
            return

        payload = {
            "requestType": "playbacks_userInput",
            "execIndex": fader_index,
            "pageIndex": page_index,
            "faderValue": fader_value / 127,
            "type": type,
            "session": self.session_id,
            "maxRequests": 0
        }
        self._send(payload)

    def poll_exec_state(self):
        if self.session_id is None:
            if self.DEBUG:
                print("No session yet")
            return

        # Poll B-Wings
        self._send({
        "requestType": "playbacks",
        "startIndex": self.BWING_START_INDEX,
        "itemsCount": self.BWING_ITEMS_COUNT,
        "pageIndex": 0,
        "itemsType": self.BWING_ITEMS_TYPE,
        "view": self.BWING_VIEW,
        "execButtonViewMode": self.BWING_EXEC_VIEW_MODE,
        "buttonsViewMode": 0,
        "session": self.session_id,
        "maxRequests": 1
    })

        # Poll F-Wings
        self._send({
            "requestType": "playbacks",
            "startIndex": self.FWING_START_INDEX,
            "itemsCount": self.FWING_ITEMS_COUNT,
            "pageIndex": 0,
            "itemsType": self.FWING_ITEMS_TYPE,
            "view": self.FWING_VIEW,
            "execButtonViewMode": self.FWING_EXEC_VIEW_MODE,
            "buttonsViewMode": 0,
            "session": self.session_id,
            "maxRequests": 1
        })
