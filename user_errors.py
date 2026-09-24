"""Actionable messages; detailed tracebacks stay in the local server log."""
import asyncio


def friendly_error(exc):
    detail = str(exc).lower()
    if isinstance(exc, PermissionError) or 'winerror 32' in detail or 'permissionerror' in detail:
        return 'Windows is still releasing an audio file. This script will retry; later scripts stay in order. If it repeats, close apps using the recording and try again.'
    if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or 'timeout' in detail:
        return 'Speech generation took too long. Please check your internet for Edge, or try a shorter script for Kokoro. This script will retry before the next one.'
    if isinstance(exc, ConnectionError) or any(x in detail for x in ('connect', 'websocket', 'no audio', '403', '503', 'network')):
        return 'The online voice service could not finish this request. Check your internet connection and try again. Queued scripts retry automatically.'
    if 'full script' in detail or 'incomplete audio' in detail:
        return 'The voice service stopped before reading the full script. We will retry it before starting the next script.'
    if 'cuda' in detail:
        return 'The selected GPU is unavailable. Choose CPU in Local model controls and retry.'
    if 'silent' in detail or 'empty audio' in detail or 'pronounce' in detail:
        return 'No usable speech was returned. Check that the script contains words in the selected voice’s language, then retry.'
    if 'memory' in detail:
        return 'The computer ran out of available memory. Close unused apps or split the script into smaller parts, then retry.'
    if isinstance(exc, ValueError): return str(exc)
    return 'Speech generation could not finish. Try again, or use Edit & fix to check the script and voice. Technical details were saved in server-error.log.'
