"""
PC Automation Framework - Stress Test Script
"""
import sys
import os
import time
import psutil
import statistics
from rich.console import Console
from rich.live import Live
from rich.table import Table

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.orchestrator import Orchestrator, ExecutionContext
from core.config import config, SafetyMode, State
from core.logger import logger

console = Console()

def run_stress_test(num_iterations=8):
    """Run repetitive stress test."""
    
    console.print(f"[bold red]⚠️  WARNING: Starting Stress Test ({num_iterations} iterations)[/bold red]")
    console.print("System will switch to [bold red]AUTONOMOUS[/bold red] mode for this test.")
    if not console.input("   Type 'yes' to proceed: ").lower() == 'yes':
        console.print("Aborted.")
        return

    # Force Autonomous Mode
    config.safety_mode = SafetyMode.AUTONOMOUS
    
    process = psutil.Process(os.getpid())
    results = []
    errors = 0
    
    orchestrator = Orchestrator()
    
    # Using a simple, consistent query
    test_query = "Check system status"
    
    console.print(f"\n🚀 Starting loop for query: [cyan]'{test_query}'[/cyan]\n")
    
    start_time_global = time.time()
    
    table = Table(title="Stress Test Metrics", show_lines=True)
    table.add_column("Iter", justify="right")
    table.add_column("Time (s)", justify="right")
    table.add_column("RAM (MB)", justify="right")
    table.add_column("Status", justify="center")
    
    try:
        with Live(table, refresh_per_second=4):
            for i in range(1, num_iterations + 1):
                iter_start = time.time()
                mem_before = process.memory_info().rss / 1024 / 1024
                
                try:
                    # Run Orchestrator
                    # Note: We capture stdout to avoid cluttering the table
                    # but real logs go to file
                    execution_results = orchestrator.run(test_query)
                    
                    status = "✅ Success"
                    # Check if actually succeeded
                    if any(r.get("status") == "failed" for r in execution_results):
                        status = "⚠️  Partial Fail"
                        errors += 1
                        
                except Exception as e:
                    status = f"❌ Error: {str(e)[:20]}"
                    errors += 1
                
                iter_duration = time.time() - iter_start
                mem_after = process.memory_info().rss / 1024 / 1024
                
                results.append(iter_duration)
                
                table.add_row(
                    str(i),
                    f"{iter_duration:.2f}",
                    f"{mem_after:.1f}",
                    status
                )
                
                # Small delay to prevent maxing out CPU instantly if it's too fast
                # (Though LLM calls will natural limit speed)
                time.sleep(0.5)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted![/yellow]")
    
    finally:
        orchestrator.cleanup()
        total_time = time.time() - start_time_global
        
        console.print("\n[bold]Test Summary:[/bold]")
        console.print(f"Total Time: {total_time:.2f}s")
        if results:
            console.print(f"Avg Time/Iter: {statistics.mean(results):.2f}s")
            console.print(f"Min Time: {min(results):.2f}s")
            console.print(f"Max Time: {max(results):.2f}s")
        console.print(f"Total Errors: {errors}")
        
        if errors == 0:
            console.print("[bold green]✅ STRESS TEST PASSED[/bold green]")
        else:
            console.print("[bold red]❌ STRESS TEST FAILED with ERRORS[/bold red]")

if __name__ == "__main__":
    n = 8
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except:
            pass
    run_stress_test(n)
