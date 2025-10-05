"""
Session Manager for Wallet Tracker

This module handles trading session management, including session creation,
tracking, graceful shutdown, and data persistence.
"""

import asyncio
import json
import logging
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()

class SessionManager:
    """Manages trading sessions with daily tracking and graceful shutdown"""
    
    def __init__(self, config: dict, db_path: Path):
        self.config = config
        self.db_path = db_path
        
        # Session configuration
        self.enabled = config.get('enabled', True)
        self.save_directory = config.get('save_directory', 'sessions')
        self.daily_summary = config.get('daily_summary', True)
        self.graceful_shutdown = config.get('graceful_shutdown', True)
        
        # Current session state
        self.current_session_id: Optional[str] = None
        self.current_session_data: Optional[dict] = None
        self.session_start_time: Optional[datetime] = None
        
        # Setup paths
        self.sessions_dir = Path(__file__).parent / "data" / self.save_directory
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Note: Signal handlers are managed by the main application
        # to avoid conflicts with multiple signal handlers
        
        if not self.enabled:
            self.logger.info("Session tracking is disabled")
            return
            
        self.logger.info(f"Session manager initialized with save directory: {self.sessions_dir}")
    
    
    def start_session(self) -> str:
        """Start a new trading session"""
        if not self.enabled:
            return "disabled"
        
        try:
            # Generate session ID
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            session_number = self._get_next_session_number(today)
            self.current_session_id = f"{today}_session_{session_number:03d}"
            
            # Initialize session data
            self.session_start_time = datetime.now(timezone.utc)
            self.current_session_data = {
                'session_id': self.current_session_id,
                'date': today,
                'session_number': session_number,
                'start_time': self.session_start_time.isoformat(),
                'end_time': None,
                'status': 'active',
                'trades': [],
                'metrics': {
                    'total_trades': 0,
                    'profitable_trades': 0,
                    'total_profit_loss_usd': 0.0,
                    'max_drawdown_usd': 0.0,
                    'max_balance_usd': 0.0
                }
            }
            
            # Save initial session data
            self._save_session_data()
            
            self.logger.info(f"Started new session: {self.current_session_id}")
            
            # Display session start message
            self._display_session_start()
            
            return self.current_session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start session: {e}")
            raise
    
    def _get_next_session_number(self, date: str) -> int:
        """Get the next session number for the given date"""
        try:
            # Look for existing sessions for this date
            pattern = f"{date}_session_*.json"
            existing_files = list(self.sessions_dir.glob(pattern))
            
            if not existing_files:
                return 1
            
            # Extract session numbers and find the highest
            session_numbers = []
            for file in existing_files:
                try:
                    # Extract session number from filename
                    name = file.stem  # Remove .json extension
                    parts = name.split('_')
                    if len(parts) >= 3 and parts[-1].isdigit():
                        session_numbers.append(int(parts[-1]))
                except (ValueError, IndexError):
                    continue
            
            return max(session_numbers) + 1 if session_numbers else 1
            
        except Exception as e:
            self.logger.error(f"Failed to get next session number: {e}")
            return 1
    
    def update_session_metrics(self, metrics: dict):
        """Update current session metrics"""
        if not self.enabled or not self.current_session_data:
            return
        
        try:
            self.current_session_data['metrics'].update(metrics)
            self._save_session_data()
            
        except Exception as e:
            self.logger.error(f"Failed to update session metrics: {e}")
    
    def add_trade_to_session(self, trade_data: dict):
        """Add a trade to the current session"""
        if not self.enabled or not self.current_session_data:
            return
        
        try:
            self.current_session_data['trades'].append(trade_data)
            self._save_session_data()
            
        except Exception as e:
            self.logger.error(f"Failed to add trade to session: {e}")
    
    async def end_session(self, graceful: bool = True) -> Optional[dict]:
        """End the current session with summary"""
        if not self.enabled or not self.current_session_data:
            return None
        
        try:
            # Update session end time and status
            end_time = datetime.now(timezone.utc)
            self.current_session_data['end_time'] = end_time.isoformat()
            self.current_session_data['status'] = 'completed' if graceful else 'crashed'
            
            # Calculate session duration
            if self.session_start_time:
                duration = end_time - self.session_start_time
                self.current_session_data['duration_seconds'] = duration.total_seconds()
            
            # Save final session data
            self._save_session_data()
            
            # Display session summary
            if self.daily_summary:
                await self._display_session_summary()
            
            # Update overall session summary
            self._update_overall_summary()
            
            session_data = self.current_session_data.copy()
            
            # Clear current session
            self.current_session_id = None
            self.current_session_data = None
            self.session_start_time = None
            
            self.logger.info(f"Session ended: {session_data['session_id']}")
            
            return session_data
            
        except Exception as e:
            self.logger.error(f"Failed to end session: {e}")
            return None
    
    def _save_session_data(self):
        """Save current session data to JSON file"""
        if not self.current_session_data:
            return
        
        try:
            session_file = self.sessions_dir / f"{self.current_session_id}.json"
            
            with open(session_file, 'w') as f:
                json.dump(self.current_session_data, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Failed to save session data: {e}")
    
    def _display_session_start(self):
        """Display session start message"""
        try:
            start_text = Text()
            start_text.append("🚀 Starting Wallet Tracker", style="bold green")
            
            details = Text()
            details.append(f"📅 Session: {self.current_session_id}\n", style="cyan")
            details.append(f"⏰ Start Time: {self.session_start_time.strftime('%H:%M:%S')}", style="blue")
            
            panel = Panel(
                details,
                title=start_text,
                border_style="green",
                padding=(0, 1)
            )
            
            console.print(panel)
            
        except Exception as e:
            self.logger.error(f"Failed to display session start: {e}")
    
    async def _display_session_summary(self):
        """Display session summary"""
        if not self.current_session_data:
            return
        
        try:
            data = self.current_session_data
            metrics = data['metrics']
            
            # Calculate additional metrics
            duration_seconds = data.get('duration_seconds', 0)
            duration_str = self._format_duration(duration_seconds)
            
            total_return_pct = 0.0
            if metrics.get('initial_balance_usd', 0) > 0:
                total_return_pct = ((metrics.get('final_balance_usd', 0) - metrics.get('initial_balance_usd', 0)) / 
                                  metrics.get('initial_balance_usd', 1)) * 100
            
            win_rate = 0.0
            if metrics.get('total_trades', 0) > 0:
                win_rate = (metrics.get('profitable_trades', 0) / metrics.get('total_trades', 1)) * 100
            
            # Create summary table
            table = Table(title=f"📊 Session Summary - {data['session_id']}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="white")
            
            table.add_row("Final Balance", f"${metrics.get('final_balance_usd', 0):,.2f}")
            table.add_row("Total Profit", f"${metrics.get('total_profit_loss_usd', 0):+,.2f}")
            table.add_row("Total Return", f"{total_return_pct:+.2f}%")
            table.add_row("Total Trades", str(metrics.get('total_trades', 0)))
            table.add_row("Profitable Trades", f"{metrics.get('profitable_trades', 0)}/{metrics.get('total_trades', 0)} ({win_rate:.1f}%)")
            table.add_row("Max Drawdown", f"${metrics.get('max_drawdown_usd', 0):,.2f}")
            table.add_row("Session Duration", duration_str)
            
            console.print(table)
            
            # Display session file location
            session_file = self.sessions_dir / f"{data['session_id']}.json"
            console.print(f"\n💾 Session data saved to: {session_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to display session summary: {e}")
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to human readable format"""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hours > 0:
                return f"{hours}h {minutes}m {secs}s"
            elif minutes > 0:
                return f"{minutes}m {secs}s"
            else:
                return f"{secs}s"
                
        except Exception:
            return "0s"
    
    def _update_overall_summary(self):
        """Update overall session summary file"""
        try:
            summary_file = self.sessions_dir / "session_summary.json"
            
            # Load existing summary or create new
            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    summary = json.load(f)
            else:
                summary = {
                    'total_sessions': 0,
                    'total_trades': 0,
                    'total_profit_loss_usd': 0.0,
                    'best_session': None,
                    'worst_session': None,
                    'last_updated': None
                }
            
            # Update summary with current session data
            if self.current_session_data:
                data = self.current_session_data
                metrics = data['metrics']
                
                summary['total_sessions'] += 1
                summary['total_trades'] += metrics.get('total_trades', 0)
                summary['total_profit_loss_usd'] += metrics.get('total_profit_loss_usd', 0)
                summary['last_updated'] = datetime.now(timezone.utc).isoformat()
                
                # Update best/worst session
                session_pnl = metrics.get('total_profit_loss_usd', 0)
                
                if summary['best_session'] is None or session_pnl > summary['best_session'].get('profit_loss_usd', 0):
                    summary['best_session'] = {
                        'session_id': data['session_id'],
                        'date': data['date'],
                        'profit_loss_usd': session_pnl
                    }
                
                if summary['worst_session'] is None or session_pnl < summary['worst_session'].get('profit_loss_usd', 0):
                    summary['worst_session'] = {
                        'session_id': data['session_id'],
                        'date': data['date'],
                        'profit_loss_usd': session_pnl
                    }
            
            # Save updated summary
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
        except Exception as e:
            self.logger.error(f"Failed to update overall summary: {e}")
    
    def get_session_history(self, limit: int = 10) -> List[dict]:
        """Get recent session history"""
        try:
            session_files = sorted(self.sessions_dir.glob("*.json"), 
                                 key=lambda x: x.stat().st_mtime, reverse=True)
            
            sessions = []
            for file in session_files[:limit]:
                if file.name == "session_summary.json":
                    continue
                    
                try:
                    with open(file, 'r') as f:
                        session_data = json.load(f)
                        sessions.append(session_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load session file {file}: {e}")
                    continue
            
            return sessions
            
        except Exception as e:
            self.logger.error(f"Failed to get session history: {e}")
            return []
    
    def display_session_history(self, limit: int = 5):
        """Display recent session history"""
        try:
            sessions = self.get_session_history(limit)
            
            if not sessions:
                console.print("No session history found.")
                return
            
            table = Table(title="📈 Recent Session History")
            table.add_column("Session", style="cyan")
            table.add_column("Date", style="blue")
            table.add_column("Trades", style="white")
            table.add_column("P&L", style="green")
            table.add_column("Duration", style="yellow")
            
            for session in sessions:
                metrics = session.get('metrics', {})
                duration = session.get('duration_seconds', 0)
                duration_str = self._format_duration(duration)
                
                pnl = metrics.get('total_profit_loss_usd', 0)
                pnl_style = "green" if pnl >= 0 else "red"
                pnl_text = f"${pnl:+,.2f}"
                
                table.add_row(
                    session.get('session_id', 'Unknown'),
                    session.get('date', 'Unknown'),
                    str(metrics.get('total_trades', 0)),
                    pnl_text,
                    duration_str,
                    style=pnl_style
                )
            
            console.print(table)
            
        except Exception as e:
            self.logger.error(f"Failed to display session history: {e}")
    
    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self.current_session_id
    
    def is_session_active(self) -> bool:
        """Check if a session is currently active"""
        return self.current_session_id is not None
