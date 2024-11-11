import logging
import json
import sys
from uuid import uuid4
import os
from dotenv import load_dotenv
import time
from typing import Callable
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import ast

levels = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

# Load Var Envs
load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL")
DEV_MODE = str(os.getenv("DEV", default="False"))
# Create a logger
logger = logging.getLogger(__name__)
# Set Level Logs
logger.setLevel(levels[LOG_LEVEL])

# Create a stream handler to send logs to stdout
stream_handler = logging.StreamHandler(sys.stdout)

if DEV_MODE == "True":

    plain_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    stream_handler.setFormatter(plain_formatter)

else:
    # Create a custom JSON formatter
    class JSONFormatter(logging.Formatter):
        """
        Formatter that outputs JSON strings after parsing the LogRecord.

        @param dict fmt_dict: Key: logging format attribute pairs. Defaults to {"message": "message"}.
        @param str time_format: time.strftime() format string. Default: "%Y-%m-%dT%H:%M:%S"
        @param str msec_format: Microsecond formatting. Appended at the end. Default: "%s.%03dZ"
        """

        def __init__(
            self,
            fmt_dict: dict = None,
            time_format: str = "%Y-%m-%dT%H:%M:%S",
            msec_format: str = "%s.%03dZ",
        ):
            self.fmt_dict = fmt_dict if fmt_dict is not None else {"message": "message"}
            self.default_time_format = time_format
            self.default_msec_format = msec_format
            self.datefmt = None

        def usesTime(self) -> bool:
            """
            Overwritten to look for the attribute in the format dict values instead of the fmt string.
            """
            return "asctime" in self.fmt_dict.values()

        def formatMessage(self, record) -> dict:
            """
            Overwritten to return a dictionary of the relevant LogRecord attributes instead of a string.
            KeyError is raised if an unknown attribute is provided in the fmt_dict.
            """
            return {
                fmt_key: record.__dict__[fmt_val]
                for fmt_key, fmt_val in self.fmt_dict.items()
            }

        def format(self, record):

            log_record = {
                "@timestamp": self.formatTime(record),
                "event": {"duration": record.msecs},
                "process": {
                    "name": record.processName,
                    "thread": {"name": record.threadName},
                },
                "log": {
                    "level": record.levelname.lower(),
                    "origin": {
                        "file": {"name": record.filename, "line": record.lineno},
                        "function": record.funcName,
                    },
                },
            }

            try:
                json_message = ast.literal_eval(record.getMessage())
                if json_message["http"]:
                    log_record.update(json_message)
            except:
                log_record["event"]["message"] = record.getMessage()

            return json.dumps(log_record)

    class RouterLoggingMiddleware(BaseHTTPMiddleware):
        def __init__(self, app: FastAPI, *, logger: logging.Logger) -> None:
            self._logger = logger
            super().__init__(app)

        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            request_id: str = str(uuid4())

            # await self.set_body(request)
            response, response_dict = await self._log_response(
                call_next, request, request_id
            )
            if response is None:
                return {"status_code": "500"}
            request_dict = await self._log_request(request)
            logging_dict = {
                "http": {
                    "request": {
                        "parent": {"id": request_id},
                        "method": request_dict["method"],
                    },
                    "response": {
                        "status_code": response_dict["status_code"],
                    },
                },
                "url": {"original": request_dict["path"]},
                "client": {"ip": request_dict["ip"]},
            }
            self._logger.info(logging_dict)
            return response

        async def _log_request(self, request: Request) -> str:
            """
            Logs request part

            @params Request: request

            """

            path = request.url.path
            if request.query_params:
                path += f"?{request.query_params}"

            request_logging = {
                "method": request.method,
                "path": path,
                "ip": request.client.host,
            }

            try:
                body = await request.json()
                request_logging["body"] = body
            except:
                body = None

            return request_logging

        async def _log_response(
            self, call_next: Callable, request: Request, request_id: str
        ) -> Response:
            """
            Logs response part

            @params call_next: Callable (To execute the actual path function and get response back)
            @params request: Request
            @params request_id: str (uuid)

            ----------
            Returns
            ----------
            Response: response
            str: response_logging
            """

            start_time = time.perf_counter()
            response = await self._execute_request(call_next, request, request_id)
            finish_time = time.perf_counter()

            overall_status = "successful" if response.status_code < 400 else "failed"

            execution_time = finish_time - start_time

            response_logging = {
                "status": overall_status,
                "status_code": response.status_code if response else "",
                "time_taken": f"{execution_time:0.4f}s",
            }

            resp_body = [
                section async for section in response.__dict__["body_iterator"]
            ]

            response.__setattr__("body_iterator", AsyncIteratorWrapper(resp_body))

            try:
                resp_body = json.loads(resp_body[0].decode())
            except:
                resp_body = str(resp_body)

            response_logging["body"] = resp_body

            return response, response_logging

        async def _execute_request(
            self, call_next: Callable, request: Request, request_id: str
        ) -> Response:
            """
            Executes the actual path function using call_next.
            It also injects "X-API-Request-ID" header to the response.

            @params call_next: Callable (To execute the actual path function
                                and get response back)
            @params request: Request
            @params request_id: str (uuid)

            ----------
            Returns
            ----------
            response: Response
            """
            try:
                response: Response = await call_next(request)

                # Kickback X-Request-ID
                response.headers["X-API-Request-ID"] = request_id
                return response

            except Exception as e:
                self._logger.exception(
                    {
                        "http": {
                            "request": {
                                "method": request.method,
                            },
                        },
                        "url": {"original": request.url.path},
                        "error": {"stack_trace": e},
                    }
                )

    class AsyncIteratorWrapper:
        """
        The following is a utility class that transforms a
            regular iterable to an asynchronous one.
        """

        def __init__(self, obj):
            self._it = iter(obj)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                value = next(self._it)
            except StopIteration:
                raise StopAsyncIteration
            return value

        # Set the custom JSON formatter for the stream handler
        json_formatter = JSONFormatter()
        stream_handler.setFormatter(json_formatter)

    # Add the stream handler to the logger
logger.addHandler(stream_handler)
