"""avocado-web tools, grouped by department.

One module per department/domain (reservations, finance, …). Each exposes a
`register(mcp)` function that attaches that department's tools to the shared
server. `server.py` imports the modules and calls each `register(...)`, so it
stays a flat list of "which departments are wired in" — no matter how many tools
each team adds to its own file.
"""
