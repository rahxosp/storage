"""Main application - Server Manager GUI."""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from manager import ServerManager
from models import ServerStatus
from ui.server_form import ServerFormDialog
from ui.log_viewer import LogViewerDialog


class ServerManagerApp:
    """Main application window."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Server Manager")
        self.root.geometry("1400x700")
        
        self.manager = ServerManager()
        self.log_viewers = {}  # Track open log viewers
        
        self._create_widgets()
        self._create_menu()
        
        # Load configurations and start UI update loop
        self.manager.load_configs()
        self._populate_tree()
        
        # Start periodic UI update
        self.root.after(300, self._update_ui)
    
    def _create_widgets(self):
        """Create main UI widgets."""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Add Server", command=self._add_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Edit", command=self._edit_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete_server).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Start", command=self._start_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Stop", command=self._stop_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Restart", command=self._restart_server).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Force Restart", command=self._force_restart_server).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="View Logs", command=self._view_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Open Logs Folder", command=self._open_logs_folder).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Button(toolbar, text="Start All", command=self._start_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Stop All", command=self._stop_all).pack(side=tk.LEFT, padx=2)
        
        # Treeview for servers
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("name", "address", "status", "pid", "uptime", "restarts", "last_restart", "error")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        
        self.tree.heading("name", text="Name")
        self.tree.heading("address", text="Host:Port")
        self.tree.heading("status", text="Status")
        self.tree.heading("pid", text="PID")
        self.tree.heading("uptime", text="Uptime")
        self.tree.heading("restarts", text="Restarts")
        self.tree.heading("last_restart", text="Last Restart")
        self.tree.heading("error", text="Last Error")
        
        self.tree.column("name", width=150)
        self.tree.column("address", width=180)
        self.tree.column("status", width=100)
        self.tree.column("pid", width=80)
        self.tree.column("uptime", width=100)
        self.tree.column("restarts", width=80)
        self.tree.column("last_restart", width=150)
        self.tree.column("error", width=300)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Start", command=self._start_server)
        self.context_menu.add_command(label="Stop", command=self._stop_server)
        self.context_menu.add_command(label="Restart", command=self._restart_server)
        self.context_menu.add_command(label="Force Restart", command=self._force_restart_server)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="View Logs", command=self._view_logs)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Edit", command=self._edit_server)
        self.context_menu.add_command(label="Delete", command=self._delete_server)
        
        self.tree.bind("<Button-3>", self._show_context_menu)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=5, pady=2)
    
    def _create_menu(self):
        """Create menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Add Server", command=self._add_server)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Actions menu
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(label="Start All", command=self._start_all)
        actions_menu.add_command(label="Stop All", command=self._stop_all)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _populate_tree(self):
        """Populate treeview with servers."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add servers
        for config in self.manager.configs:
            state = self.manager.get_worker_state(config.name)
            
            if state:
                values = (
                    config.name,
                    config.get_display_address(),
                    state.status.value,
                    state.pid or "-",
                    self._format_uptime(state.uptime_seconds),
                    state.restarts_count,
                    state.last_restart_time or "-",
                    state.last_error or "-"
                )
            else:
                values = (
                    config.name,
                    config.get_display_address(),
                    "Unknown",
                    "-", "-", "-", "-", "-"
                )
            
            self.tree.insert('', tk.END, iid=config.name, values=values)
    
    def _update_ui(self):
        """Periodic UI update - process queue from workers."""
        # Process all queued updates
        while not self.manager.ui_queue.empty():
            try:
                msg = self.manager.ui_queue.get_nowait()
                
                if msg['type'] == 'state_update':
                    server_name = msg['server']
                    state = msg['state']
                    
                    # Update tree item
                    if self.tree.exists(server_name):
                        config = next((c for c in self.manager.configs if c.name == server_name), None)
                        if config:
                            values = (
                                config.name,
                                config.get_display_address(),
                                state.status.value,
                                state.pid or "-",
                                self._format_uptime(state.uptime_seconds),
                                state.restarts_count,
                                state.last_restart_time or "-",
                                state.last_error or "-"
                            )
                            self.tree.item(server_name, values=values)
                
                elif msg['type'] == 'log_line':
                    server_name = msg['server']
                    line = msg['line']
                    
                    # If log viewer is open, append line
                    if server_name in self.log_viewers:
                        viewer = self.log_viewers[server_name]
                        if viewer.dialog.winfo_exists():
                            viewer.append_line(f"{msg['timestamp']} {line}")
            
            except:
                pass
        
        # Schedule next update
        self.root.after(300, self._update_ui)
    
    def _format_uptime(self, seconds: int) -> str:
        """Format uptime in human-readable form."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _get_selected_server(self):
        """Get currently selected server name."""
        selection = self.tree.selection()
        if not selection:
            return None
        return selection[0]
    
    def _show_context_menu(self, event):
        """Show context menu on right-click."""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def _add_server(self):
        """Add a new server."""
        dialog = ServerFormDialog(self.root)
        config = dialog.show()
        
        if config:
            try:
                self.manager.add_server(config)
                self._populate_tree()
                self.status_var.set(f"Added server: {config.name}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _edit_server(self):
        """Edit selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            messagebox.showwarning("No Selection", "Please select a server to edit", parent=self.root)
            return
        
        # Find config
        config = next((c for c in self.manager.configs if c.name == server_name), None)
        if not config:
            return
        
        dialog = ServerFormDialog(self.root, config=config)
        new_config = dialog.show()
        
        if new_config:
            try:
                self.manager.edit_server(server_name, new_config)
                self._populate_tree()
                self.status_var.set(f"Edited server: {new_config.name}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _delete_server(self):
        """Delete selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            messagebox.showwarning("No Selection", "Please select a server to delete", parent=self.root)
            return
        
        if messagebox.askyesno("Confirm Delete", f"Delete server '{server_name}'?", parent=self.root):
            try:
                self.manager.delete_server(server_name)
                self._populate_tree()
                self.status_var.set(f"Deleted server: {server_name}")
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self.root)
    
    def _test_connection(self):
        """Test connection to selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            messagebox.showwarning("No Selection", "Please select a server to test", parent=self.root)
            return
        
        config = next((c for c in self.manager.configs if c.name == server_name), None)
        if not config:
            return
        
        self.status_var.set(f"Testing connection to {server_name}...")
        self.root.update()
        
        # Run in thread to avoid blocking UI
        def test_thread():
            success, info = self.manager.test_connection(config)
            
            def show_result():
                if success:
                    msg = f"Connection successful!\n\n"
                    msg += f"OS: {info.get('os', 'Unknown')}\n"
                    msg += f"Python: {info.get('python', 'Not found')}\n"
                    if 'python_version' in info:
                        msg += f"Version: {info['python_version']}\n"
                    messagebox.showinfo("Test Connection", msg, parent=self.root)
                else:
                    messagebox.showerror("Test Connection Failed", info.get('error', 'Unknown error'), parent=self.root)
                
                self.status_var.set("Ready")
            
            self.root.after(0, show_result)
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def _start_server(self):
        """Start selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            return
        
        self.manager.start_server(server_name)
        self.status_var.set(f"Starting {server_name}...")
    
    def _stop_server(self):
        """Stop selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            return
        
        if messagebox.askyesno("Confirm Stop", f"Stop server '{server_name}'?", parent=self.root):
            self.manager.stop_server(server_name)
            self.status_var.set(f"Stopping {server_name}...")
    
    def _restart_server(self):
        """Restart selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            return
        
        self.manager.restart_server(server_name)
        self.status_var.set(f"Restarting {server_name}...")
    
    def _force_restart_server(self):
        """Force restart selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            return
        
        if messagebox.askyesno("Confirm Force Restart", 
                              f"Force restart server '{server_name}'? This will kill any existing process.",
                              parent=self.root):
            self.manager.force_restart_server(server_name)
            self.status_var.set(f"Force restarting {server_name}...")
    
    def _view_logs(self):
        """View logs for selected server."""
        server_name = self._get_selected_server()
        if not server_name:
            messagebox.showwarning("No Selection", "Please select a server to view logs", parent=self.root)
            return
        
        # Check if viewer already open
        if server_name in self.log_viewers:
            viewer = self.log_viewers[server_name]
            if viewer.dialog.winfo_exists():
                viewer.dialog.lift()
                return
        
        # Create new log viewer
        viewer = LogViewerDialog(self.root, server_name)
        self.log_viewers[server_name] = viewer
    
    def _open_logs_folder(self):
        """Open logs folder in file explorer."""
        import os
        logs_dir = os.path.abspath("logs")
        if os.path.exists(logs_dir):
            os.startfile(logs_dir)  # Windows
    
    def _start_all(self):
        """Start all servers."""
        self.manager.start_all()
        self.status_var.set("Starting all servers...")
    
    def _stop_all(self):
        """Stop all servers."""
        if messagebox.askyesno("Confirm Stop All", "Stop all servers?", parent=self.root):
            self.manager.stop_all()
            self.status_var.set("Stopping all servers...")
    
    def _show_about(self):
        """Show about dialog."""
        messagebox.showinfo(
            "About",
            "Server Manager v1.0\n\n"
            "Manages and monitors remote server processes via SSH.\n"
            "Automatically restarts processes on failure or server reboot.",
            parent=self.root
        )
    
    def run(self):
        """Run the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = ServerManagerApp()
    app.run()
