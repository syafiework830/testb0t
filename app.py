import sys
import traceback
from datetime import datetime
from http import HTTPStatus
from botbuilder.schema import Activity, ActivityTypes

from aiohttp import web
from aiohttp.web import Request, Response, json_response
from botbuilder.core import TurnContext
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity, ActivityTypes

from bot_llm_router import TeamsBot
from config import Config

CONFIG = Config()

# Create adapter.
# See https://aka.ms/about-bot-adapter to learn more about how bots work.
ADAPTER = CloudAdapter(ConfigurationBotFrameworkAuthentication(CONFIG))

routes = web.RouteTableDef()

async def handle_404(request):
    return web.Response(status=404, text="Page not found")

# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    await context.send_activity(
        "To continue to run this bot, please fix the bot source code."
    )
    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.now(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)

ADAPTER.on_turn_error = on_error

# Create the Bot
BOT = TeamsBot()

APP = web.Application(middlewares=[aiohttp_error_middleware])
# Listen for incoming requests on /api/messages

async def messages(req: Request) -> Response:
    if "application/json" in req.headers["Content-Type"]:
        body = await req.json()
    else:
        return Response(status=HTTPStatus.UNSUPPORTED_MEDIA_TYPE)

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    try:
        response = await ADAPTER.process_activity(auth_header, activity, BOT.on_turn)
        if response:
            return json_response(data=response.body, status=response.status)
        return Response(status=HTTPStatus.OK)
    except Exception as error:
        print(f"Exception: {error}", file=sys.stderr)
        traceback.print_exc()
        return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

# Health check endpoint

async def health_check(req: Request) -> Response:
   return json_response({"status": "healthy"}, status=HTTPStatus.OK)

# Set up the application and routes
APP = web.Application(middlewares=[aiohttp_error_middleware])

APP.router.add_post("/api/messages", messages)
APP.router.add_get("/api/health", health_check)  # Health check endpoint

if __name__ == "__main__":
    try:
        start = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        print(f"++Start server: {CONFIG.PORT}\n++Start time: {start}")
        web.run_app(APP, host="0.0.0.0", port=CONFIG.PORT)
        end = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        print(f"==Start server: {CONFIG.PORT}\n==End time: {end}")
    except Exception as error:
        print(f"Failed to start server: {error}", file=sys.stderr)
        raise error