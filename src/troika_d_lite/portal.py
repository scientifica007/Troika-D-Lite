import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

from .pipeline import VideoStream


BUS_NAME = "org.freedesktop.portal.Desktop"
OBJECT_PATH = "/org/freedesktop/portal/desktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"
SESSION_IFACE = "org.freedesktop.portal.Session"
SCREENCAST_IFACE = "org.freedesktop.portal.ScreenCast"


class PortalCancelled(RuntimeError):
    """Normal user cancellation of a portal request."""


class PortalError(RuntimeError):
    def __init__(
        self,
        message: str,
        code: Optional[int] = None,
        results: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.results = results or {}


@dataclass(frozen=True)
class PortalCapture:
    session_handle: str
    stream: VideoStream


def portal_response_is_cancelled(code: Optional[int]) -> bool:
    return code == 1


def _unwrap(value):
    return value.unpack() if isinstance(value, GLib.Variant) else value


class PortalClient:
    def __init__(self) -> None:
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

    def _token(self, prefix: str) -> str:
        return (
            f"{prefix}_{os.getpid()}_{GLib.get_monotonic_time()}"
            .replace("-", "_")
        )

    def _request_path(self, token: str) -> str:
        sender = self.bus.get_unique_name().lstrip(":").replace(".", "_")
        return f"/org/freedesktop/portal/desktop/request/{sender}/{token}"

    def _request(
        self,
        method: str,
        parameters: GLib.Variant,
        token: str,
    ) -> Dict[str, Any]:
        loop = GLib.MainLoop()
        response: Dict[str, Any] = {}
        request_path = self._request_path(token)

        def on_response(
            _conn,
            _sender,
            _path,
            _iface,
            _signal,
            params,
            _user_data=None,
        ):
            code, results = params.unpack()
            response["code"] = int(code)
            response["results"] = results
            if loop.is_running():
                loop.quit()

        subscription = self.bus.signal_subscribe(
            BUS_NAME,
            REQUEST_IFACE,
            "Response",
            request_path,
            None,
            Gio.DBusSignalFlags.NONE,
            on_response,
        )
        try:
            returned = self.bus.call_sync(
                BUS_NAME,
                OBJECT_PATH,
                SCREENCAST_IFACE,
                method,
                parameters,
                GLib.VariantType.new("(o)"),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )
            actual_path = returned.unpack()[0]
            if actual_path != request_path:
                self.bus.signal_unsubscribe(subscription)
                subscription = self.bus.signal_subscribe(
                    BUS_NAME,
                    REQUEST_IFACE,
                    "Response",
                    actual_path,
                    None,
                    Gio.DBusSignalFlags.NONE,
                    on_response,
                )
            loop.run()
        finally:
            self.bus.signal_unsubscribe(subscription)

        code = response.get("code")
        results = response.get("results", {})
        if code != 0:
            if portal_response_is_cancelled(code):
                raise PortalCancelled(
                    f"Portal request {method} was cancelled"
                )
            raise PortalError(
                f"Portal request {method} failed (code={code})",
                code=code,
                results=results,
            )
        return results

    def create_screencast(self) -> PortalCapture:
        create_token = self._token("create")
        session_token = self._token("session")
        created = self._request(
            "CreateSession",
            GLib.Variant(
                "(a{sv})",
                (
                    {
                        "handle_token": GLib.Variant("s", create_token),
                        "session_handle_token": GLib.Variant(
                            "s",
                            session_token,
                        ),
                    },
                ),
            ),
            create_token,
        )
        session_handle = _unwrap(created.get("session_handle"))
        if not session_handle:
            raise PortalError("ScreenCast portal returned no session handle")

        try:
            select_token = self._token("select")
            self._request(
                "SelectSources",
                GLib.Variant(
                    "(oa{sv})",
                    (
                        session_handle,
                        {
                            "handle_token": GLib.Variant("s", select_token),
                            "types": GLib.Variant("u", 1),
                            "multiple": GLib.Variant("b", False),
                            "cursor_mode": GLib.Variant("u", 2),
                        },
                    ),
                ),
                select_token,
            )

            start_token = self._token("start")
            started = self._request(
                "Start",
                GLib.Variant(
                    "(osa{sv})",
                    (
                        session_handle,
                        "",
                        {
                            "handle_token": GLib.Variant(
                                "s",
                                start_token,
                            )
                        },
                    ),
                ),
                start_token,
            )

            streams = _unwrap(started.get("streams")) or []
            if not streams:
                raise PortalError("ScreenCast portal returned no streams")

            node_id, props = streams[0]
            node_id = int(_unwrap(node_id))
            props = _unwrap(props) or {}

            serial_value = props.get("pipewire-serial")
            serial_value = (
                _unwrap(serial_value)
                if serial_value is not None
                else None
            )
            pipewire_serial = (
                int(serial_value)
                if serial_value is not None
                else None
            )

            fd = self._open_pipewire_remote(session_handle)
            return PortalCapture(
                session_handle=session_handle,
                stream=VideoStream(
                    fd=fd,
                    node_id=node_id,
                    pipewire_serial=pipewire_serial,
                ),
            )
        except Exception:
            self.close_session(session_handle)
            raise

    def _open_pipewire_remote(self, session_handle: str) -> int:
        result, out_fds = self.bus.call_with_unix_fd_list_sync(
            BUS_NAME,
            OBJECT_PATH,
            SCREENCAST_IFACE,
            "OpenPipeWireRemote",
            GLib.Variant("(oa{sv})", (session_handle, {})),
            GLib.VariantType.new("(h)"),
            Gio.DBusCallFlags.NONE,
            -1,
            None,
            None,
        )
        index = result.unpack()[0]
        return out_fds.get(index)

    def watch_session_closed(
        self,
        session_handle: str,
        callback: Callable[[], None],
    ) -> int:
        def on_closed(
            _conn,
            _sender,
            _path,
            _iface,
            _signal,
            _params,
            _user_data=None,
        ):
            callback()

        return self.bus.signal_subscribe(
            BUS_NAME,
            SESSION_IFACE,
            "Closed",
            session_handle,
            None,
            Gio.DBusSignalFlags.NONE,
            on_closed,
        )

    def unwatch_session(self, subscription_id: int) -> None:
        if subscription_id:
            self.bus.signal_unsubscribe(subscription_id)

    def close_session(self, session_handle: Optional[str]) -> None:
        if not session_handle:
            return
        try:
            self.bus.call_sync(
                BUS_NAME,
                session_handle,
                SESSION_IFACE,
                "Close",
                None,
                None,
                Gio.DBusCallFlags.NONE,
                2000,
                None,
            )
        except GLib.Error:
            pass
