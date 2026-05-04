from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from fastmcp import FastMCP

def register_mcp_prompts(mcp: "FastMCP"):
    import datetime
    from loguru import logger

    @mcp.prompt()
    def analyze_price_trend(commodity: str, location: str = "Jakarta", days: int = 7, price_type_id: int = 2) -> str:
        """
        Instructs the AI to perform a detailed historical trend analysis for a specific commodity.
        Useful for seeing if a price is going up, down, or remaining stable over time.
        """
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=days)
        
        return f"""
        Please act as an Economic Data Analyst. Your task is to analyze the price trend of '{commodity}' in the '{location}' region.
        The analysis timeframe is the last {days} days, specifically from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}.

        Please strictly follow these execution steps:
        1. Use the `get_comodity_prices` tool with:
        - comodity_keyword: "{commodity}"
        - location_keyword: "{location}"
        - start_date: "{start_date.strftime('%Y-%m-%d')}"
        - end_date: "{end_date.strftime('%Y-%m-%d')}"
        - price_type_id: {price_type_id}
        2. Review the tool's output. Note the exact commodity variants (e.g., Quality I, Quality II) and the exact location matched.
        3. Format the extracted time-series data into a clean, easy-to-read Markdown table.
        4. Provide an 'Analysis Summary' below the table:
        - Calculate the absolute and percentage price difference between the start date and end date.
        - Identify the overall trend (e.g., Bullish/Inflationary, Bearish/Deflationary, or Stagnant/Stable).
        - Highlight any sudden price spikes or drops within this window.

        Ensure your final response is professional, objective, and data-driven.
        """

    @mcp.prompt()
    def current_market_snapshot(commodity: str, location: str = "Jakarta") -> str:
        """
        Instructs the AI to get the most recent price of a commodity without needing a long historical trend.
        Great for quick daily check-ins.
        """
        today = datetime.date.today().strftime('%Y-%m-%d')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        
        return f"""
        Please provide a quick market snapshot for the current price of '{commodity}' in '{location}'.
        
        Execution steps:
        1. Call `get_comodity_prices` using:
        - comodity_keyword: "{commodity}"
        - location_keyword: "{location}"
        - start_date: "{yesterday}"
        - end_date: "{today}"
        - price_type_id: 2
        2. Check the "matched" block to confirm which specific items and region were retrieved.
        3. Output a concise summary listing the exact commodity variants and their latest prices. 
        4. Briefly state if the price changed compared to yesterday. Keep the answer brief and straight to the point.
        """

    @mcp.prompt()
    def explore_available_data(keyword: str) -> str:
        """
        Instructs the AI to explore and list what exact data variants and locations are available for a given keyword.
        Useful when the user is unsure of the exact commodity name or supported regions.
        """
        return f"""
        The user wants to know what data is available regarding the keyword '{keyword}'.
        
        Please follow these steps to explore the database:
        1. First, call the `list_comodities` tool with keyword="{keyword}" to see all matching commodity items.
        2. Then, call the `list_location` tool with keyword="{keyword}" to see if there are any specific regions matching this name.
        3. Present your findings to the user:
        - List the exact commodity names and IDs found.
        - List the locations and their hierarchy levels (Province/City) found.
        4. Conclude by suggesting 1 or 2 `get_comodity_prices` queries they could run using these exact names. Do not execute the price query yet, just suggest it.
        """
    SKILL = None

    with open("SKILL.md") as f:
        SKILL = f.read()

    @mcp.resource("file://skill-guidelines")
    def get_skill_md() -> str:
        """
        Read the SKILL.md file to understand how to use the commodity price tools,
        data interpretation rules, and triggering conditions.
        """

        if SKILL is None:
            logger.warning("SKILL.md not found!")
            return "SKILL.md not found!"
        return SKILL

    