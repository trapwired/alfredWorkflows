from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("mix_server")

# Add a tool decorator method to make tools accessible
def tool(*args, **kwargs):
    return mcp.tool(*args, **kwargs)

# Method to run the server
def run():
    try:
        print("Starting MCP server 'mix_server'...")
        mcp.run()
    except Exception as e:
        print(f"Failed to initialize MCP server 'mix_server': {str(e)}")
        print("Please check the logs for more details.")
