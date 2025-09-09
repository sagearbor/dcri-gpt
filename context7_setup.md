# Context7 MCP Setup Instructions

To enable Context7 MCP for professional UI component generation:

## 1. Get Context7 API Key
Visit https://context7.ai or your Context7 dashboard to obtain your API key.

## 2. Add to Environment
Add your Context7 API key to the backend/.env file:
```
CONTEXT7_API_KEY=your-context7-api-key-here
```

## 3. Configure MCP Server
Create or update your MCP configuration file (typically ~/.config/claude/mcp.json or similar):

```json
{
  "servers": {
    "context7": {
      "command": "npx",
      "args": ["@context7/mcp-server"],
      "env": {
        "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}"
      }
    }
  }
}
```

## 4. Restart Claude Code
After configuration, restart Claude Code to load the MCP server.

## Without Context7
If you don't have a Context7 API key, I can still create a professional frontend using:
- Shadcn/ui components (recommended)
- Material-UI
- Ant Design
- Custom styled-components with enterprise patterns

The frontend will still be professional and enterprise-grade, following best practices from apps like Vercel Dashboard and Linear.