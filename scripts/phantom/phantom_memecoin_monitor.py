#!/usr/bin/env python3
"""
Phantom Memecoin Monitor

Monitors trending memecoins on Phantom's explore page and alerts when changes
are detected in the top 10 list. This helps discover new memecoins early
and track emerging trends.

Features:
- Fetches top 10 trending memecoins from Phantom explore page
- Detects changes in the trending list
- Continuous monitoring with configurable frequency
- Rich console output with alerts
- JSON logging for analysis
- Configurable alert thresholds
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta
import logging
import requests
from bs4 import BeautifulSoup
from rich.console import Console

# Selenium imports (required)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("❌ Selenium is required but not installed. Install with: pip install selenium")
    sys.exit(1)
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.tracker.config_manager import ConfigManager


class PhantomMemecoinMonitor:
    """Monitors trending memecoins on Phantom's explore page."""
    
    def __init__(self):
        self.base_url = "https://phantom.com/explore"
        self.console = Console()
        self.current_top_10: List[Dict[str, Any]] = []
        self.previous_top_10: List[Dict[str, Any]] = []
        self.change_history: List[Dict[str, Any]] = []
        
        # Setup logging first
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/phantom_monitor.log'),
                logging.StreamHandler()
            ]
        )
        
        # Setup Selenium WebDriver
        self.driver = None
        self._setup_selenium()
        
        # Load configuration
        self._load_config()
    
    def _setup_selenium(self):
        """Setup Selenium WebDriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("Selenium WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Selenium: {e}")
            self.logger.error("Make sure Chrome/Chromium is installed and chromedriver is available")
            sys.exit(1)
        
    def _load_config(self):
        """Load configuration from config files."""
        try:
            config_path = str(Path(__file__).parent.parent / "config" / "config.yaml")
            self.config_manager = ConfigManager(config_path)
            self.config = self.config_manager.load_full_config()
            
            # Default configuration
            self.monitor_config = self.config.get('phantom_monitor', {
                'check_interval': 30,  # seconds
                'alert_threshold': 1,  # minimum changes to alert
                'max_history': 100,     # maximum change history entries
                'enable_notifications': True,
                'log_changes': True
            })
            
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}. Using defaults.")
            self.monitor_config = {
                'check_interval': 30,
                'alert_threshold': 1,
                'max_history': 100,
                'enable_notifications': True,
                'log_changes': True
            }
    
    def fetch_trending_memecoins(self) -> List[Dict[str, Any]]:
        """Fetch the current top 10 trending memecoins from Phantom using Selenium."""
        try:
            self.driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Wait a bit more for dynamic content
            time.sleep(5)
            
            # Get page source after JavaScript execution
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Look for trending tokens in the rendered content
            trending_tokens = self._extract_tokens_from_soup(soup)
            
            self.logger.info(f"Successfully fetched {len(trending_tokens)} trending tokens")
            return trending_tokens
            
        except Exception as e:
            self.logger.error(f"Selenium fetch failed: {e}")
            return []
    
    def _extract_tokens_from_soup(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract token data from BeautifulSoup object."""
        trending_tokens = []
        
        # Look for specific token patterns
        # Try to find elements that might contain token information
        token_elements = soup.find_all(['div', 'span', 'p', 'h1', 'h2', 'h3'], 
                                     string=lambda text: text and len(text.strip()) > 1 and len(text.strip()) < 50)
        
        for element in token_elements:
            text = element.get_text().strip()
            if self._is_likely_token_name(text):
                # Look for associated price/change data
                price_data = self._find_price_data(element)
                change_data = self._find_change_data(element)
                
                token_data = {
                    'name': text,
                    'price': price_data,
                    'change_24h': change_data,
                    'timestamp': datetime.now().isoformat(),
                    'raw_line': f"{text} {change_data:+.2f}%" if change_data else text
                }
                trending_tokens.append(token_data)
        
        # Remove duplicates and limit to top 10
        seen_names = set()
        unique_tokens = []
        for token in trending_tokens:
            if token['name'] not in seen_names and len(unique_tokens) < 10:
                seen_names.add(token['name'])
                unique_tokens.append(token)
        
        return unique_tokens
    
    def _find_price_data(self, element) -> Optional[float]:
        """Find price data near an element."""
        try:
            # Look in parent and sibling elements
            parent = element.parent
            if parent:
                text = parent.get_text()
                import re
                price_match = re.search(r'\$(\d+\.?\d*)', text)
                if price_match:
                    return float(price_match.group(1))
        except:
            pass
        return None
    
    def _find_change_data(self, element) -> Optional[float]:
        """Find change data near an element."""
        try:
            parent = element.parent
            if parent:
                text = parent.get_text()
                import re
                change_match = re.search(r'([+-]?\d+\.?\d*)%', text)
                if change_match:
                    return float(change_match.group(1))
        except:
            pass
        return None
    
    def _is_likely_token_name(self, text: str) -> bool:
        """Check if text is likely a token name."""
        if not text or len(text) < 3 or len(text) > 30:
            return False
        
        # Token names usually have some uppercase letters
        if not any(char.isupper() for char in text):
            return False
        
        # Avoid common non-token words
        common_words = ['trending', 'tokens', 'market', 'overview', 'price', 'change', 'volume', 'cap', 'phantom', 'explore', 'download', 'features', 'learn', 'company', 'support']
        if text.lower() in common_words:
            return False
        
        # Filter out garbled text - check for too many special characters
        special_char_count = sum(1 for char in text if not char.isalnum() and char not in ' ')
        if special_char_count > len(text) * 0.3:  # More than 30% special chars
            return False
        
        # Filter out text with too many non-ASCII characters
        non_ascii_count = sum(1 for char in text if ord(char) > 127)
        if non_ascii_count > len(text) * 0.2:  # More than 20% non-ASCII
            return False
        
        # Token names should be mostly alphanumeric with some spaces
        alphanumeric_count = sum(1 for char in text if char.isalnum())
        if alphanumeric_count < len(text) * 0.5:  # Less than 50% alphanumeric
            return False
        
        # Avoid single characters or very short strings
        if len(text.strip()) < 3:
            return False
        
        # Avoid strings that are mostly punctuation
        if text.count(' ') == 0 and special_char_count > 2:
            return False
        
        # Avoid strings that look like HTML/JavaScript artifacts
        if any(artifact in text.lower() for artifact in ['<', '>', '&', ';', '=', '"', "'", '(', ')', '[', ']', '{', '}']):
            return False
        
        return True
    
    def _extract_token_data(self, element) -> List[Dict[str, Any]]:
        """Extract token data from a DOM element."""
        tokens = []
        
        # Look for text patterns that might contain token information
        text_content = element.get_text()
        
        # Split by common delimiters and look for token-like patterns
        lines = text_content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for patterns like "TokenName +47.08% $0.00016318"
            if '$' in line and ('%' in line or '+' in line or '-' in line):
                token_data = self._parse_token_line(line)
                if token_data:
                    tokens.append(token_data)
        
        return tokens
    
    def _extract_token_data_from_elements(self, elements) -> List[Dict[str, Any]]:
        """Extract token data from a list of elements."""
        tokens = []
        
        for element in elements:
            text = element.get_text().strip()
            if text and '$' in text:
                token_data = self._parse_token_line(text)
                if token_data:
                    tokens.append(token_data)
        
        return tokens
    
    def _parse_token_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a line of text to extract token information."""
        try:
            # Remove extra whitespace
            line = ' '.join(line.split())
            
            # Look for price pattern
            price_match = None
            if '$' in line:
                parts = line.split('$')
                if len(parts) > 1:
                    price_part = parts[1].split()[0]
                    try:
                        price_match = float(price_part.replace(',', ''))
                    except ValueError:
                        pass
            
            # Look for percentage change
            change_match = None
            if '%' in line:
                # Find percentage pattern
                import re
                percent_pattern = r'([+-]?\d+\.?\d*)%'
                matches = re.findall(percent_pattern, line)
                if matches:
                    try:
                        change_match = float(matches[0])
                    except ValueError:
                        pass
            
            # Extract token name (everything before the first number or special character)
            name_parts = []
            for char in line:
                if char.isdigit() or char in ['$', '+', '-', '%']:
                    break
                name_parts.append(char)
            
            name = ''.join(name_parts).strip()
            
            # Clean up name
            name = name.replace('+', '').replace('-', '').strip()
            
            if name and len(name) > 1:
                return {
                    'name': name,
                    'price': price_match,
                    'change_24h': change_match,
                    'timestamp': datetime.now().isoformat(),
                    'raw_line': line
                }
            
        except Exception as e:
            self.logger.debug(f"Error parsing token line '{line}': {e}")
        
        return None
    
    def detect_changes(self) -> Dict[str, Any]:
        """Detect changes between current and previous top 10 lists."""
        if not self.previous_top_10:
            return {'has_changes': False, 'changes': []}
        
        current_names = {token['name'] for token in self.current_top_10}
        previous_names = {token['name'] for token in self.previous_top_10}
        
        added = current_names - previous_names
        removed = previous_names - current_names
        
        changes = []
        
        # New tokens
        for token_name in added:
            token_data = next((t for t in self.current_top_10 if t['name'] == token_name), None)
            changes.append({
                'type': 'added',
                'token': token_data,
                'position': self.current_top_10.index(token_data) + 1 if token_data else None
            })
        
        # Removed tokens
        for token_name in removed:
            token_data = next((t for t in self.previous_top_10 if t['name'] == token_name), None)
            changes.append({
                'type': 'removed',
                'token': token_data,
                'position': self.previous_top_10.index(token_data) + 1 if token_data else None
            })
        
        # Position changes
        for i, current_token in enumerate(self.current_top_10):
            if current_token['name'] in previous_names:
                prev_position = next((j for j, t in enumerate(self.previous_top_10) if t['name'] == current_token['name']), None)
                if prev_position is not None and prev_position != i:
                    changes.append({
                        'type': 'position_change',
                        'token': current_token,
                        'old_position': prev_position + 1,
                        'new_position': i + 1
                    })
        
        return {
            'has_changes': len(changes) > 0,
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        }
    
    def log_changes(self, change_data: Dict[str, Any]):
        """Log changes to file and console."""
        if not change_data['has_changes']:
            return
        
        # Add to history
        self.change_history.append(change_data)
        
        # Limit history size
        if len(self.change_history) > self.monitor_config['max_history']:
            self.change_history = self.change_history[-self.monitor_config['max_history']:]
        
        # Log to file
        log_entry = {
            'timestamp': change_data['timestamp'],
            'changes': change_data['changes'],
            'current_top_10': self.current_top_10,
            'previous_top_10': self.previous_top_10
        }
        
        log_file = Path(__file__).parent / "logs" / f"phantom_changes_{datetime.now().strftime('%Y%m%d')}.jsonl"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        self.logger.info(f"Changes detected: {len(change_data['changes'])} changes logged")
    
    def display_current_status(self):
        """Display current trending tokens in a rich table."""
        table = Table(title="🔥 Phantom Trending Memecoins", show_header=True, header_style="bold magenta")
        table.add_column("Rank", style="dim", width=6)
        table.add_column("Token", style="cyan", width=20)
        table.add_column("Price", style="green", width=15)
        table.add_column("24h Change", style="yellow", width=12)
        table.add_column("Raw Data", style="dim", width=30)
        
        for i, token in enumerate(self.current_top_10, 1):
            change_str = f"{token['change_24h']:+.2f}%" if token['change_24h'] is not None else "N/A"
            price_str = f"${token['price']:.8f}" if token['price'] is not None else "N/A"
            
            # Color code the change
            if token['change_24h'] is not None:
                if token['change_24h'] > 0:
                    change_str = f"[green]{change_str}[/green]"
                else:
                    change_str = f"[red]{change_str}[/red]"
            
            table.add_row(
                str(i),
                token['name'],
                price_str,
                change_str,
                token['raw_line'][:30] + "..." if len(token['raw_line']) > 30 else token['raw_line']
            )
        
        self.console.print(table)
    
    def display_changes(self, change_data: Dict[str, Any]):
        """Display detected changes in a rich panel."""
        if not change_data['has_changes']:
            return
        
        changes_text = Text()
        
        for change in change_data['changes']:
            if change['type'] == 'added':
                changes_text.append(f"🆕 NEW: {change['token']['name']} (#{change['position']})\n", style="green")
            elif change['type'] == 'removed':
                changes_text.append(f"❌ REMOVED: {change['token']['name']} (#{change['position']})\n", style="red")
            elif change['type'] == 'position_change':
                changes_text.append(f"📈 MOVED: {change['token']['name']} #{change['old_position']} → #{change['new_position']}\n", style="yellow")
        
        panel = Panel(
            changes_text,
            title="🚨 Changes Detected!",
            border_style="red",
            padding=(1, 2)
        )
        
        self.console.print(panel)
    
    async def monitor_continuously(self):
        """Start continuous monitoring of trending memecoins."""
        self.console.print(Panel(
            "🔥 Starting Phantom Memecoin Monitor\n"
            f"📊 Checking every {self.monitor_config['check_interval']} seconds\n"
            f"🎯 Alert threshold: {self.monitor_config['alert_threshold']} changes\n"
            f"📝 Logging: {'Enabled' if self.monitor_config['log_changes'] else 'Disabled'}",
            title="Phantom Monitor Status",
            border_style="blue"
        ))
        
        # Initial fetch
        self.current_top_10 = self.fetch_trending_memecoins()
        if not self.current_top_10:
            self.console.print("[red]❌ Failed to fetch initial data. Exiting.[/red]")
            return
        
        self.console.print(f"[green]✅ Initial fetch successful: {len(self.current_top_10)} tokens[/green]")
        self.display_current_status()
        
        # Start monitoring loop
        while True:
            try:
                await asyncio.sleep(self.monitor_config['check_interval'])
                
                # Update previous list
                self.previous_top_10 = self.current_top_10.copy()
                
                # Fetch new data
                self.current_top_10 = self.fetch_trending_memecoins()
                
                if not self.current_top_10:
                    self.console.print("[yellow]⚠️ Failed to fetch data, retrying...[/yellow]")
                    continue
                
                # Detect changes
                change_data = self.detect_changes()
                
                if change_data['has_changes']:
                    self.console.print(f"\n[bold red]🚨 CHANGES DETECTED! ({len(change_data['changes'])} changes)[/bold red]")
                    self.display_changes(change_data)
                    self.display_current_status()
                    
                    # Log changes
                    if self.monitor_config['log_changes']:
                        self.log_changes(change_data)
                    
                    # Alert if threshold met
                    if len(change_data['changes']) >= self.monitor_config['alert_threshold']:
                        self.console.print(f"[bold green]🎯 Alert threshold met! ({len(change_data['changes'])} changes)[/bold green]")
                else:
                    self.console.print(f"[dim]⏰ {datetime.now().strftime('%H:%M:%S')} - No changes detected[/dim]")
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]🛑 Monitoring stopped by user[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]❌ Error in monitoring loop: {e}[/red]")
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    def run_single_check(self):
        """Run a single check and display results."""
        self.console.print("[blue]🔍 Running single check...[/blue]")
        
        self.current_top_10 = self.fetch_trending_memecoins()
        
        if not self.current_top_10:
            self.console.print("[red]❌ Failed to fetch data[/red]")
            return
        
        self.display_current_status()
        
        if self.previous_top_10:
            change_data = self.detect_changes()
            if change_data['has_changes']:
                self.display_changes(change_data)
            else:
                self.console.print("[green]✅ No changes detected[/green]")
    
    def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()
            self.logger.info("Selenium WebDriver closed")


async def main():
    """Main entry point."""
    monitor = PhantomMemecoinMonitor()
    
    try:
        # Check command line arguments
        if len(sys.argv) > 1 and sys.argv[1] == '--single':
            monitor.run_single_check()
        else:
            await monitor.monitor_continuously()
    finally:
        monitor.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
