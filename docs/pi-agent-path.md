# Pi-agent path (CLI-equivalent)

> pi has no MCP support (pi-acp rejects non-empty `mcpServers`), and the
> pi CLI is not installed on this box. Agents without MCP drive the
> factory through the CLI — identical tools, identical receipts.

```bash
# signals
python3 mcp_server.py signals_top '{"garden":"ukgraph","limit":10}'

# rank + route
python3 mcp_server.py rank_signals '{"garden":"ukgraph","limit":4}'
python3 mcp_server.py route_signal '{"signal_id":"sig_..."}'

# expand + compile
python3 mcp_server.py expand_signal '{"signal_id":"sig_..."}'
python3 mcp_server.py ingest '{"signal_id":"sig_..."}'
python3 mcp_server.py compile '{"proof_id":"proof_...","query":"OPPORTUNITY"}'

# render + narrate (or run for the whole chain)
python3 mcp_server.py run '{"signal_id":"sig_...","query":"OPPORTUNITY"}'

# concepts / theses / relationships (powpowpow garden)
python3 mcp_server.py concepts_top '{}'
python3 mcp_server.py concept_explain '{"topic":"QUBIC","angle":"explain"}'
python3 mcp_server.py relationships '{"a":"QUBIC","b":"XMR"}'
python3 mcp_server.py theses_top '{}'

# review + publish gate
python3 mcp_server.py lineage '{"limit":20}'
python3 mcp_server.py publish '{"video_id":"vid_..."}'
python3 mcp_server.py measure '{"video_id":"vid_...","metrics":{...}}'
python3 mcp_server.py inspect '{"target":"receipts"}'
```

Dashboard equivalents (`/api/content/*` on the influence dash):
status, signals, list, generate, video, approve. The Content tab
renders the same lineage with watch-before-live playback.
