"""Log Viewer Dialog."""
import tkinter as tk
from tkinter import ttk, scrolledtext
import os
from logging_setup import get_log_file_path


class LogViewerDialog:
    """Dialog for viewing server logs with live updates."""
    
    def __init__(self, parent, server_name: str):
        self.parent = parent
        self.server_name = server_name
        self.autoscroll = True
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Logs - {server_name}")
        self.dialog.geometry("900x600")
        
        self._create_widgets()
        self._load_logs()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.dialog.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create widgets."""
        # Toolbar
        toolbar = ttk.Frame(self.dialog)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Refresh", command=self._load_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Clear", command=self._clear_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open Logs Folder", command=self._open_logs_folder).pack(side=tk.LEFT, padx=2)
        
        self.autoscroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(toolbar, text="Auto-scroll", variable=self.autoscroll_var, 
                       command=self._toggle_autoscroll).pack(side=tk.LEFT, padx=10)
        
        # Search frame
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=2)
        search_entry.bind('<Return>', lambda e: self._search())
        
        ttk.Button(search_frame, text="Find", command=self._search).pack(side=tk.LEFT, padx=2)
        
        # Text widget for logs
        text_frame = ttk.Frame(self.dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier", 9))
        self.text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for highlighting
        self.text.tag_config('highlight', background='yellow')
        self.text.tag_config('error', foreground='red')
        self.text.tag_config('warning', foreground='orange')
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
    
    def _toggle_autoscroll(self):
        """Toggle autoscroll."""
        self.autoscroll = self.autoscroll_var.get()
    
    def _load_logs(self):
        """Load logs from file."""
        log_file = get_log_file_path(self.server_name)
        
        if not os.path.exists(log_file):
            self.text.delete('1.0', tk.END)
            self.text.insert(tk.END, f"Log file not found: {log_file}\n")
            self.status_var.set("No log file")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                # Read last 500 lines
                lines = f.readlines()
                last_lines = lines[-500:] if len(lines) > 500 else lines
                content = ''.join(last_lines)
            
            self.text.delete('1.0', tk.END)
            self.text.insert(tk.END, content)
            
            # Apply syntax highlighting
            self._apply_highlighting()
            
            # Scroll to end if autoscroll
            if self.autoscroll:
                self.text.see(tk.END)
            
            self.status_var.set(f"Loaded {len(last_lines)} lines from {log_file}")
        
        except Exception as e:
            self.text.delete('1.0', tk.END)
            self.text.insert(tk.END, f"Error loading logs: {e}\n")
            self.status_var.set(f"Error: {e}")
    
    def _apply_highlighting(self):
        """Apply syntax highlighting to log content."""
        content = self.text.get('1.0', tk.END)
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            line_start = f"{i+1}.0"
            line_end = f"{i+1}.end"
            
            if 'ERROR' in line or '[ERROR]' in line:
                self.text.tag_add('error', line_start, line_end)
            elif 'WARNING' in line or '[WARNING]' in line or 'WARN' in line:
                self.text.tag_add('warning', line_start, line_end)
    
    def _clear_logs(self):
        """Clear log display."""
        self.text.delete('1.0', tk.END)
        self.status_var.set("Cleared")
    
    def _search(self):
        """Search for text in logs."""
        query = self.search_var.get()
        if not query:
            return
        
        # Remove previous highlights
        self.text.tag_remove('highlight', '1.0', tk.END)
        
        # Search and highlight
        start_pos = '1.0'
        count = 0
        
        while True:
            start_pos = self.text.search(query, start_pos, stopindex=tk.END, nocase=True)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(query)}c"
            self.text.tag_add('highlight', start_pos, end_pos)
            start_pos = end_pos
            count += 1
        
        if count > 0:
            self.status_var.set(f"Found {count} matches")
            # Scroll to first match
            first_match = self.text.search(query, '1.0', stopindex=tk.END, nocase=True)
            if first_match:
                self.text.see(first_match)
        else:
            self.status_var.set("No matches found")
    
    def _open_logs_folder(self):
        """Open logs folder in file explorer."""
        logs_dir = os.path.abspath("logs")
        if os.path.exists(logs_dir):
            os.startfile(logs_dir)  # Windows
    
    def append_line(self, line: str):
        """Append a new log line (for live updates)."""
        self.text.insert(tk.END, line + '\n')
        
        # Apply highlighting to new line
        last_line_num = int(self.text.index(tk.END).split('.')[0]) - 1
        line_start = f"{last_line_num}.0"
        line_end = f"{last_line_num}.end"
        
        if 'ERROR' in line or '[ERROR]' in line:
            self.text.tag_add('error', line_start, line_end)
        elif 'WARNING' in line or '[WARNING]' in line:
            self.text.tag_add('warning', line_start, line_end)
        
        # Autoscroll if enabled
        if self.autoscroll:
            self.text.see(tk.END)
