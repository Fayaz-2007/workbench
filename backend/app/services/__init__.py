"""Cross-cutting application services that don't belong to one agent or
tool — e.g. conversation export, which several entry points (the chat
route's Task Router dispatch, and a dedicated REST endpoint) both need to
call without duplicating logic.
"""
