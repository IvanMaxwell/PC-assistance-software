"""
PC Automation Framework - Rich CLI Display
Beautiful terminal output using the Rich library.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED, DOUBLE
from rich import print as rprint
from typing import Dict, Any, List, Optional
import json


console = Console()


class Display:
    """Handles all CLI output formatting."""
    
    def __init__(self):
        self.console = Console()
    
    def header(self):
        """Show application header."""
        header_text = Text()
        header_text.append("⚡ ", style="bold yellow")
        header_text.append("PC Automation Framework", style="bold cyan")
        header_text.append(" ⚡", style="bold yellow")
        
        self.console.print(Panel(
            header_text,
            box=DOUBLE,
            style="bold blue",
            padding=(0, 2)
        ))
    
    def show_tools(self, tools: List[Dict]):
        """Display registered tools in a table."""
        table = Table(title="🛠️  Registered Tools", box=ROUNDED, show_lines=True)
        table.add_column("Tool", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Risk", justify="center")
        
        risk_styles = {
            "safe": "[green]● SAFE[/green]",
            "medium": "[yellow]◐ MEDIUM[/yellow]",
            "high": "[red]● HIGH[/red]"
        }
        
        for tool in tools:
            risk = risk_styles.get(tool["risk"], tool["risk"])
            table.add_row(tool["name"], tool["description"][:50], risk)
        
        self.console.print(table)
    
    def show_request(self, request: str):
        """Display user request."""
        self.console.print(Panel(
            f"[bold white]{request}[/bold white]",
            title="📝 User Request",
            border_style="green"
        ))
    
    def show_state_transition(self, from_state: str, to_state: str):
        """Show FSM state transition."""
        self.console.print(
            f"  [dim]→[/dim] [bold blue]{from_state}[/bold blue] "
            f"[dim]➜[/dim] [bold cyan]{to_state}[/bold cyan]"
        )
    
    def show_router_result(self, query: str, tool: str, score: float, hit: bool):
        """Display semantic router result."""
        if hit:
            self.console.print(Panel(
                f"[bold green]🚀 SHORTCUT![/bold green]\n"
                f"Query: [white]{query}[/white]\n"
                f"Tool: [cyan]{tool}[/cyan] (Score: {score:.2f})",
                title="Semantic Router",
                border_style="green"
            ))
        else:
            self.console.print(
                f"  [dim]Router:[/dim] {query} → {tool} "
                f"[dim](Score: {score:.2f} < threshold)[/dim]"
            )
    
    def show_plan(self, plan: Dict):
        """Display the generated plan."""
        if not plan or "steps" not in plan:
            return
            
        table = Table(title="📋 Execution Plan", box=ROUNDED)
        table.add_column("#", style="dim", width=3)
        table.add_column("Tool", style="cyan")
        table.add_column("Arguments", style="white")
        table.add_column("On Fail", style="yellow")
        
        for step in plan.get("steps", []):
            args = json.dumps(step.get("arguments", {}))
            if len(args) > 30:
                args = args[:30] + "..."
            table.add_row(
                str(step.get("step_id", "?")),
                step.get("tool_name", "?"),
                args,
                step.get("on_failure", "abort")
            )
        
        self.console.print(table)
        
        if "reasoning" in plan:
            self.console.print(f"  [dim]Reasoning: {plan['reasoning'][:100]}...[/dim]")
    
    def show_confidence(self, score: float):
        """Display confidence score with visual bar."""
        color = "green" if score >= 0.8 else "yellow" if score >= 0.5 else "red"
        bar_length = int(score * 20)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        
        self.console.print(
            f"  [bold]Confidence:[/bold] [{color}]{bar}[/{color}] "
            f"[bold {color}]{score:.0%}[/bold {color}]"
        )
    
    def show_step_result(self, step_id: int, tool: str, status: str, result: Any = None, error: str = None):
        """Display individual step execution result."""
        if status == "success":
            icon = "[green]✓[/green]"
            msg = f"Step {step_id}: [cyan]{tool}[/cyan] completed"
        else:
            icon = "[red]✗[/red]"
            msg = f"Step {step_id}: [cyan]{tool}[/cyan] [red]failed[/red]"
            if error:
                msg += f"\n    [dim red]{error}[/dim red]"
        
        self.console.print(f"  {icon} {msg}")
    
    def show_results(self, results: List[Dict]):
        """Display final execution results."""
        success_count = sum(1 for r in results if r.get("status") == "success")
        fail_count = len(results) - success_count
        
        if fail_count == 0:
            status_panel = Panel(
                f"[bold green]✅ All {success_count} steps completed successfully![/bold green]",
                border_style="green"
            )
        else:
            status_panel = Panel(
                f"[bold yellow]⚠️ {success_count} succeeded, {fail_count} failed[/bold yellow]",
                border_style="yellow"
            )
        
        self.console.print(status_panel)
        
        # Show detailed results
        for r in results:
            if r.get("status") == "success" and r.get("result"):
                result_str = json.dumps(r["result"], indent=2, default=str)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "\n..."
                self.console.print(Panel(
                    result_str,
                    title=f"Result: Step {r.get('step_id', '?')}",
                    border_style="dim"
                ))
    
    def ask_permission(self, step_id: int, tool_name: str, risk: str, args: Dict) -> bool:
        """Ask user for permission to execute a tool."""
        
        risk_color = "green" if risk == "safe" else "yellow" if risk == "medium" else "red"
        
        self.console.print(Panel(
            f"Step {step_id}: [cyan]{tool_name}[/cyan]\n"
            f"Risk: [{risk_color}]{risk.upper()}[/{risk_color}]\n"
            f"Args: {json.dumps(args, indent=2)}",
            title="⚠️  Permission Required",
            border_style="yellow"
        ))
        
        from rich.prompt import Confirm
        return Confirm.ask("Allow this step?", default=False)

    def show_final_summary(self, summary: str):
        """Display the final AI-generated summary."""
        self.console.print(Panel(
            f"[bold white]{summary}[/bold white]",
            title="🤖 Summary",
            border_style="cyan",
            padding=(1, 2)
        ))
    
    def show_error(self, message: str):
        """Display error message."""
        self.console.print(Panel(
            f"[bold red]❌ {message}[/bold red]",
            border_style="red"
        ))
    
    def show_loading(self, message: str):
        """Create a loading spinner context."""
        return self.console.status(f"[bold cyan]{message}[/bold cyan]", spinner="dots")
    
    def divider(self):
        """Print a divider line."""
        self.console.print("─" * 60, style="dim")


# Global display instance
display = Display()
