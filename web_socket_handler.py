import json
import hashlib
import time
import threading
import websocket


class Dot2WebSocketHandler:
    def __init__(self, host="10.0.0.50", username="remote", password="1", heartbeat_step=10, debug=False):
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

    def _on_error(self, ws, err):
        if self.DEBUG:
            print("ERR", err)

    def _on_close(self, ws, code, reason):
        if self.DEBUG:
            print("CLOSE", code, reason)

    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.URL,
            header=[f"Origin: {self.ORIGIN}"],
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self._ws_thread = threading.Thread(target=lambda: self.ws.run_forever(skip_utf8_validation=True), daemon=True)
        self._ws_thread.start()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat, daemon=True)
        self._heartbeat_thread.start()

    def _heartbeat(self):
        while not self.stop_heartbeat:
            time.sleep(self.HEARTBEAT_STEP)
            if self.session_id is not None:
                self._send({"session": self.session_id})

    def send_playback_click(self, executor_index, page_index=0, button_id=0, ptype=0, pressed=True):
        if not self.logged_in or self.session_id is None:
            if self.DEBUG:
                print("Not ready (login/session); cannot send userInput yet.")
            return

        press = {
            "requestType": "playbacks_userInput",
            "cmdline": "",
            "execIndex": int(executor_index),
            "pageIndex": page_index,
            "buttonId": button_id,
            "pressed": True,
            "released": False,
            "type": ptype,
            "session": self.session_id,
            "maxRequests": 0
        }
        release = {
            "requestType": "playbacks_userInput",
            "cmdline": "",
            "execIndex": int(executor_index),
            "pageIndex": page_index,
            "buttonId": button_id,
            "pressed": False,
            "released": True,
            "type": ptype,
            "session": self.session_id,
            "maxRequests": 0
        }

        if pressed:
            if self.DEBUG:
                print("Pressed")
            self._send(press)
        else:
            if self.DEBUG:
                print("Released")
            self._send(release)

    def poll(self):
        if self.session_id is None:
            if self.DEBUG:
                print("No session yet")
            return
        self._send({
            "requestType": "getdata",
            "data": "set,clear,high",
            "session": self.session_id,
            "maxRequests": 1
        })

    def disconnect(self):
        self.stop_heartbeat = True
        if self.ws:
            self.ws.close()

    def send_playback_fader(self, fader_index, fader_value, page_index=1, type=1):
        if not self.logged_in or self.session_id is None:
            if self.DEBUG:
                print("Not ready (login/session); cannot send userInput yet.")
            return

        """if fader_value > 0: # Initiate fader in dot2
            self._send({"keyname":"ON","value":1,"cmdlineText":"","session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":"ON","value":0,"cmdlineText":"On","session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":"EXEC","value":1,"session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":"EXEC","value":0,"cmdlineText":"On Executor","session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":str(fader_index),"value":1,"session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":str(fader_index),"value":0,"cmdlineText":"On Executor 8","session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":"ENTER","value":1,"session":self.session_id,"requestType":"keyname","maxRequests":0})
            self._send({"keyname":"ENTER","value":0,"cmdlineText":"","session":self.session_id,"requestType":"keyname","maxRequests":0})"""

        payload = {"requestType":"playbacks_userInput",
                   "execIndex":fader_index,
                   "pageIndex":page_index,
                   "faderValue":fader_value/127,
                   "type":type,
                   "session":self.session_id,
                   "maxRequests":0}

        self._send(payload)