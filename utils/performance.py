"""Performance monitoring and profiling utilities."""
import time
from typing import Optional, Dict
from contextlib import contextmanager


class PerformanceMonitor:
    """Monitor performance of various operations."""
    
    def __init__(self):
        """Initialize performance monitor."""
        self.timings: Dict[str, list] = {}
    
    @contextmanager
    def measure(self, operation: str):
        """
        Context manager to measure operation duration.
        
        Args:
            operation: Name of the operation being measured
        
        Example:
            with perf_monitor.measure("api_call"):
                response = api.call()
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation not in self.timings:
                self.timings[operation] = []
            self.timings[operation].append(duration)
    
    def get_stats(self, operation: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for an operation.
        
        Args:
            operation: Name of the operation
        
        Returns:
            Dictionary with min, max, avg, total times or None if no data
        """
        if operation not in self.timings or not self.timings[operation]:
            return None
        
        timings = self.timings[operation]
        return {
            "count": len(timings),
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "total": sum(timings)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get statistics for all operations.
        
        Returns:
            Dictionary mapping operation names to their statistics
        """
        return {
            operation: self.get_stats(operation)
            for operation in self.timings
            if self.get_stats(operation) is not None
        }
    
    def reset(self):
        """Reset all timing data."""
        self.timings.clear()
    
    def print_report(self):
        """Print a performance report to console."""
        from rich.console import Console
        from rich.table import Table
        
        console = Console()
        
        if not self.timings:
            console.print("[yellow]No performance data collected[/yellow]")
            return
        
        table = Table(title="Performance Report", show_header=True)
        table.add_column("Operation", style="cyan")
        table.add_column("Count", justify="right", style="white")
        table.add_column("Avg (s)", justify="right", style="yellow")
        table.add_column("Min (s)", justify="right", style="green")
        table.add_column("Max (s)", justify="right", style="red")
        table.add_column("Total (s)", justify="right", style="magenta")
        
        for operation, stats in self.get_all_stats().items():
            table.add_row(
                operation,
                str(stats["count"]),
                f"{stats['avg']:.4f}",
                f"{stats['min']:.4f}",
                f"{stats['max']:.4f}",
                f"{stats['total']:.4f}"
            )
        
        console.print(table)


# Global performance monitor instance
perf_monitor = PerformanceMonitor()


# Optimization recommendations based on profiling
OPTIMIZATION_TIPS = {
    "rich_rendering": [
        "Reduce spinner refresh rate (use refresh_per_second=8 instead of default 12.5)",
        "Use simpler spinner types (dots, arc) instead of complex ones (earth, moon)",
        "Minimize status text updates during long operations",
        "Batch console.print() calls when possible",
    ],
    "api_calls": [
        "Use prompt caching by keeping static content at the start of prompts",
        "Optimize tool descriptions to reduce token count",
        "Use 'low' detail for images when high detail isn't needed",
        "Cache repeated web fetches (1 hour TTL)",
    ],
    "tool_execution": [
        "Use command chaining (&&, ||) to reduce tool calls",
        "Truncate command output at 10,000 chars to reduce token usage",
        "Cache system info (5 minute TTL) to avoid repeated fastfetch calls",
    ],
}


def print_optimization_tips(category: Optional[str] = None):
    """
    Print optimization tips.
    
    Args:
        category: Specific category to show tips for, or None for all
    """
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    
    if category and category in OPTIMIZATION_TIPS:
        tips = "\n".join(f"• {tip}" for tip in OPTIMIZATION_TIPS[category])
        panel = Panel(
            tips,
            title=f"[bold cyan]Optimization Tips: {category}[/bold cyan]",
            border_style="cyan"
        )
        console.print(panel)
    else:
        for cat, tips in OPTIMIZATION_TIPS.items():
            tips_text = "\n".join(f"• {tip}" for tip in tips)
            panel = Panel(
                tips_text,
                title=f"[bold cyan]{cat}[/bold cyan]",
                border_style="cyan"
            )
            console.print(panel)
            console.print()
