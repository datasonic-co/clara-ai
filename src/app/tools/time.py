from datetime import datetime


async def get_time_now() -> str:
    """
    Get current date and time.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")